# Screen cast (phone to PC) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a paired, connected phone put its screen (and optionally its audio) on the PC, in a separate PC window both devices can control while it runs.

**Architecture:** The existing `MeshSession` TLS connection carries cast control messages only. A second, short-lived TLS connection — the media plane — carries H.264 video and AAC audio frames, so video never delays chat or heartbeats. One settings record (quality, audio, window placement) is replicated over the control plane from whichever side changed it; last write wins.

**Tech Stack:** Kotlin / Android `MediaProjection` + `MediaCodec` + `AudioPlaybackCapture`; .NET 8 / WPF with the Windows Media Foundation H.264 decoder reached through `Vortice.MediaFoundation` (or equivalent managed interop); existing `PairingProtocol` framing and TLS with certificate-fingerprint pinning.

**Spec:** `docs/superpowers/specs/2026-10-28-screen-cast-design.md`

## Global Constraints

- The two protocol copies are mirrored by hand and must stay byte-identical: `src/windows/Mesh.Core` and `android/app/src/main/java/com/mesh/core`.
- New wire tags continue the existing sequence in both `MeshMessage` copies: `0x07` CastStart, `0x08` CastReady, `0x09` CastStop, `0x0A` CastSettings.
- A cast message is only ever sent to a peer whose mDNS TXT record carries `cast=1`; both apps already throw on an unknown tag, and an older peer must not be fed one.
- The media plane authenticates by certificate fingerprint against the trust store plus a one-time token from the control plane. No PIN, and it must never be a way to reach an unpaired device.
- Quality is one value `0..100`, 0 = smooth, 100 = sharp. Latency target: under 150 ms on a LAN at the smooth end; the receiver draws each frame as it decodes it and never buffers for smoothness.
- The PC never asks permission to receive a cast. The window appearing is the notice; closing it ends the cast.
- Android's capture consent dialog appears on every start and cannot be suppressed; the capture runs under a foreground service declaring `mediaProjection`.
- The desktop release stays a single self-contained `.exe`; a decoder that adds tens of megabytes needs the author's agreement first.
- Commit messages follow the repo's kysaro settings (header ≤72, lower-case subject, body for `feat`/`fix`).

## Review Focus

- A cast started while the session drops mid-handshake: the phone must stop the projection and release the foreground service rather than stream into a dead socket (Task 5).
- A settings record naming a monitor that was unplugged: the PC falls back to the primary monitor and sends the corrected record (Task 8).
- A peer without `cast=1`: the Cast control is not offered and no cast message is ever written to that session (Task 9).
- A media-plane connection from a device whose fingerprint is not trusted, or with a wrong/expired token: refused and closed, with the control session untouched (Task 4).
- The phone's screen rotating mid-cast: the encoder restarts, re-sends codec configuration, and the receiver re-letterboxes instead of drawing a torn frame (Tasks 5 and 7).

---

### Task 1: Cast control messages on the wire

**Files:**
- Modify: `src/windows/Mesh.Core/MeshMessage.cs`
- Modify: `android/app/src/main/java/com/mesh/core/MeshMessage.kt`
- Test: `src/windows/Mesh.Tests/MeshMessageTests.cs`, `android/app/src/test/java/com/mesh/core/MeshMessageTest.kt`

**Interfaces:**
- Produces (C#): `CastStartMessage(string CastId)`, `CastReadyMessage(string CastId, int Port, string Token)`, `CastStopMessage(string CastId, string Reason)`, all `MeshMessage` subclasses; tags `0x07`, `0x08`, `0x09`.
- Produces (Kotlin): `MeshMessage.CastStart(castId: String)`, `CastReady(castId: String, port: Int, token: String)`, `CastStop(castId: String, reason: String)`.
- `CastId` is a UUID string made by the sender; `Token` is 32 bytes of CSPRNG output, base64url, made by the receiver.

- [ ] **Step 1: Write the failing round-trip tests**

C#, in `MeshMessageTests.cs`:

```csharp
[Fact] public async Task CastStart_RoundTrips()
[Fact] public async Task CastReady_RoundTrips()          // port 65535 and a 43-char token
[Fact] public async Task CastStop_RoundTrips()           // reason "", and a reason at MaxStringBytes
```

Kotlin, in `MeshMessageTest.kt`: the same three, named `castStart_roundTrips`, `castReady_roundTrips`, `castStop_roundTrips`.

- [ ] **Step 2: Run both suites to verify they fail**

Run: `dotnet test src/windows/Mesh.sln --filter Cast` and `./gradlew testDebugUnitTest --tests '*MeshMessageTest*'`
Expected: FAIL, the cast types do not exist.

- [ ] **Step 3: Add the three messages to both copies**

Port is written as a u16 big-endian; `CastId`, `Token` and `Reason` use the existing short-string helper. Keep the tag list and the header comment in `MeshMessage.kt` in step with the new tags.

- [ ] **Step 4: Run both suites to verify they pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(core): carry cast start, ready and stop on the session"
```

---

### Task 2: The cast settings record

**Files:**
- Create: `src/windows/Mesh.Core/CastSettings.cs`, `android/app/src/main/java/com/mesh/core/CastSettings.kt`
- Modify: both `MeshMessage` copies (tag `0x0A`)
- Test: `src/windows/Mesh.Tests/CastSettingsTests.cs`, `android/app/src/test/java/com/mesh/core/CastSettingsTest.kt`

**Interfaces:**
- Produces (C#): `sealed record CastSettings(int Quality, bool Audio, CastPlacement Placement, IReadOnlyList<CastMonitor> Monitors)`; `sealed record CastPlacement(CastPlacementMode Mode, string MonitorId, int X, int Y, int Width, int Height)`; `enum CastPlacementMode { Window, Fullscreen, AllMonitors }`; `sealed record CastMonitor(string Id, string Name, int Width, int Height, bool IsPrimary)`; `static CastSettings Read(...)` / `Write(...)` mirroring the `MeshMessage` helpers.
- Produces (Kotlin): the same four types as `data class`/`enum class`, same field order.
- Produces: `CastSettingsMessage(string CastId, CastSettings Settings)` / `MeshMessage.CastSettingsUpdate(castId: String, settings: CastSettings)` on tag `0x0A`.
- `Quality` is clamped to `0..100` on read on both sides; `Monitors` is capped at 16 entries and a longer list is a protocol error.

- [ ] **Step 1: Write the failing tests**

Both platforms, same cases: a record with every field non-default round-trips; `Quality` of `-5` and `250` read back as `0` and `100`; a monitor list of 17 entries throws.

- [ ] **Step 2: Run both suites to verify they fail**

- [ ] **Step 3: Implement the types and their serialization in both copies**

- [ ] **Step 4: Run both suites to verify they pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(core): describe a cast with one settings record"
```

---

### Task 3: Media-plane frame format

**Files:**
- Create: `src/windows/Mesh.Core/CastFrame.cs`, `android/app/src/main/java/com/mesh/core/CastFrame.kt`
- Test: `src/windows/Mesh.Tests/CastFrameTests.cs`, `android/app/src/test/java/com/mesh/core/CastFrameTest.kt`

**Interfaces:**
- Produces (C#): `enum CastFrameType { VideoConfig = 1, VideoKey = 2, VideoDelta = 3, AudioConfig = 4, AudioData = 5 }`; `sealed record CastFrame(CastFrameType Type, long TimestampUs, ReadOnlyMemory<byte> Payload)`; `static Task WriteAsync(Stream, CastFrame)` and `static Task<CastFrame> ReadAsync(Stream)`.
- Produces (Kotlin): `enum class CastFrameType` with the same values, `data class CastFrame(val type: CastFrameType, val timestampUs: Long, val payload: ByteArray)`, `write(output, frame)` / `read(input): CastFrame`.
- Wire: 1 byte type, 8 bytes big-endian microsecond timestamp, u32 big-endian payload length, payload. `MaxPayloadBytes = 8 * 1_048_576`; a longer declared length is a protocol error on read.

- [ ] **Step 1: Write the failing tests**

Both platforms: a frame of each type round-trips; a payload at `MaxPayloadBytes` round-trips; a declared length of `MaxPayloadBytes + 1` throws; an unknown type byte throws.

- [ ] **Step 2: Run both suites to verify they fail**

- [ ] **Step 3: Implement both copies**

- [ ] **Step 4: Run both suites to verify they pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(core): frame video and audio for the media plane"
```

---

### Task 4: The media-plane connection

**Files:**
- Create: `src/windows/Mesh.Core/CastChannel.cs`, `android/app/src/main/java/com/mesh/core/CastChannel.kt`
- Test: `src/windows/Mesh.Tests/CastChannelTests.cs`, `android/app/src/test/java/com/mesh/core/CastChannelLoopbackTest.kt`

**Interfaces:**
- Produces (C#, receiver side): `sealed class CastChannelListener : IDisposable` with `static CastChannelListener Start(X509Certificate2 identity, string token, string expectedFingerprint)`, `int Port`, `Task<CastChannel> AcceptAsync(CancellationToken)`.
- Produces (C#, both): `sealed class CastChannel : IDisposable` with `Task<CastFrame> ReadFrameAsync()`, `Task WriteFrameAsync(CastFrame)`.
- Produces (Kotlin, sender side): `CastChannel.connect(identity, ip, port, token, expectedFingerprint): CastChannel` with `suspend fun writeFrame(frame: CastFrame)` and `close()`.
- Handshake after TLS: the dialer writes the token as a short string; the listener compares it in constant time and compares the peer certificate fingerprint to `expectedFingerprint`. A mismatch closes the socket without reading further.

- [ ] **Step 1: Write the failing tests**

C# (loopback, the two test identities already in `Mesh.Tests`): a frame written by a connected dialer arrives at the listener; a dialer with the wrong token gets its connection closed and the listener keeps listening; a dialer whose fingerprint is not the expected one is refused.

Kotlin (`CastChannelLoopbackTest`, in the style of `PairingSessionLoopbackTest`): the same three.

- [ ] **Step 2: Run both suites to verify they fail**

- [ ] **Step 3: Implement both copies**

Reuse `PairingSession.buildSslContext` / the desktop's equivalent so the TLS setup and fingerprinting stay in one place.

- [ ] **Step 4: Run both suites to verify they pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(core): open a second tls channel for cast media"
```

---

### Task 5: Android capture and encode

**Files:**
- Create: `android/app/src/main/java/com/mesh/core/CastQuality.kt`, `android/app/src/main/java/com/mesh/core/ScreenCaster.kt`
- Modify: `android/app/src/main/AndroidManifest.xml`, `android/app/src/main/java/com/mesh/core/MeshConnectionService.kt`
- Test: `android/app/src/test/java/com/mesh/core/CastQualityTest.kt`

**Interfaces:**
- Produces: `object CastQuality { fun profileFor(quality: Int, screenWidth: Int, screenHeight: Int): CastProfile }` and `data class CastProfile(val width: Int, val height: Int, val frameRate: Int, val bitrate: Int, val keyframeIntervalSeconds: Int)`.
- Produces: `class ScreenCaster(projection: MediaProjection, channel: CastChannel)` with `fun start(profile: CastProfile)`, `fun applyProfile(profile: CastProfile)`, `fun stop()`, and `var onEnded: ((String) -> Unit)?`.
- Anchors the mapping must hit: quality `0` → 60 fps, long side scaled to 1920, keyframe every 2 s; quality `100` → 10 fps, native resolution, keyframe every 1 s. Bitrate rises with resolution and frame rate and never exceeds 20 Mbit/s.

- [ ] **Step 1: Write the failing `CastQualityTest`**

Cases: `profileFor(0, 1080, 2400)` has `frameRate == 60` and a long side of `1920`; `profileFor(100, 1080, 2400)` has `frameRate == 10` and the native size; frame rate is monotonically non-increasing across `0..100`; bitrate never exceeds `20_000_000`; the width and height are always even (H.264 requires it).

- [ ] **Step 2: Run it to verify it fails**

- [ ] **Step 3: Implement `CastQuality`**

- [ ] **Step 4: Run it to verify it passes**

- [ ] **Step 5: Implement `ScreenCaster`**

`MediaProjection` → `VirtualDisplay` rendering into the input surface of an H.264 `MediaCodec`, output frames pushed to the `CastChannel` as `VideoConfig` (on `INFO_OUTPUT_FORMAT_CHANGED` and on every restart), `VideoKey` (`BUFFER_FLAG_KEY_FRAME`) and `VideoDelta`. `applyProfile` changes bitrate and frame rate through `setParameters` when only those differ, and otherwise restarts the encoder and re-sends `VideoConfig`. A rotation arrives as a display size change and takes the restart path. `stop()` releases the codec, the virtual display and the projection, in that order. Any failure calls `onEnded` with a short reason.

- [ ] **Step 6: Declare the foreground service type**

`android:foregroundServiceType="mediaProjection"` on the service plus `FOREGROUND_SERVICE_MEDIA_PROJECTION` in the manifest; the service keeps running for the life of the cast exactly as it does for a session.

- [ ] **Step 7: Commit**

```bash
git commit -m "feat(cast): encode the phone screen for a cast"
```

---

### Task 6: Android audio capture

**Files:**
- Modify: `android/app/src/main/java/com/mesh/core/ScreenCaster.kt` (or a sibling `AudioCaster.kt` if that file is already large)
- Modify: `android/app/src/main/AndroidManifest.xml`

**Interfaces:**
- Produces: `fun setAudioEnabled(enabled: Boolean)` on `ScreenCaster`, safe to call while the cast runs.
- Audio is AAC-LC, 44.1 kHz stereo, 128 kbit/s, written as `AudioConfig` once and `AudioData` per buffer on the same channel as video.

- [ ] **Step 1: Implement audio capture**

`AudioPlaybackCaptureConfiguration` built from the same `MediaProjection`, `AudioRecord` → `MediaCodec` AAC encoder. Enabling starts the recorder and sends `AudioConfig`; disabling stops it and sends nothing further. Apps that opt out of capture simply produce silence — do not try to detect or work around it.

- [ ] **Step 2: Add `RECORD_AUDIO` and `FOREGROUND_SERVICE_MICROPHONE` to the manifest and request `RECORD_AUDIO` at the point audio is first switched on**

- [ ] **Step 3: Verify on the phone that a cast with audio on plays sound on the PC side once Task 10 lands; until then, verify the encoder produces `AudioData` frames in the log**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(cast): send the phone's audio with the picture"
```

---

### Task 7: Windows receiver window

**Files:**
- Create: `src/windows/Mesh.App/CastWindow.xaml`, `src/windows/Mesh.App/CastWindow.xaml.cs`, `src/windows/Mesh.App/CastDecoder.cs`
- Modify: `src/windows/Mesh.App/Mesh.App.csproj` (decoder package reference)

**Interfaces:**
- Produces: `sealed class CastDecoder : IDisposable` with `void Configure(ReadOnlySpan<byte> codecConfig)`, `BitmapSource? Decode(CastFrame frame)` returning null while the decoder needs more data, and `event Action<string>? Failed`.
- Produces: `sealed partial class CastWindow : Window` with `CastWindow(string peerName)`, `void Push(CastFrame frame)`, `void ShowState(string text)`, `event Action? Closed` (the existing WPF event is enough), and `void ApplyPlacement(CastPlacement placement)`.
- The window uses the dark theme already in `Theme.xaml`, has no chrome of its own beyond the standard one, and letterboxes the picture to its aspect ratio.

- [ ] **Step 1: Implement `CastDecoder` over the Media Foundation H.264 decoder**

Feed `VideoConfig` through `Configure`; feed key and delta frames through `Decode`. If the Media Foundation path cannot be made to work, stop and raise it with the author before bundling FFmpeg (the spec allows the fallback but not silently).

- [ ] **Step 2: Implement `CastWindow`**

An `Image` filling the window, a centred state line shown when there is no picture, and `ApplyPlacement` moving the window per `CastPlacementMode`: `Window` restores the stored rectangle, `Fullscreen` fills the named monitor, `AllMonitors` spans the virtual desktop. A placement naming an unknown monitor falls back to the primary one and the method returns the corrected `CastPlacement`.

- [ ] **Step 3: Verify by hand with a recorded H.264 clip**

Run the desktop app, push the clip's frames through a temporary debug entry point, and confirm the picture draws, scales and letterboxes.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(cast): show a cast in its own window on the pc"
```

---

### Task 8: Windows cast session wiring

**Files:**
- Modify: `src/windows/Mesh.App/MainWindow.xaml.cs`, `src/windows/Mesh.App/MainWindow.xaml`
- Create: `src/windows/Mesh.App/CastSession.cs`
- Test: `src/windows/Mesh.Tests/CastPlacementTests.cs`

**Interfaces:**
- Consumes: Task 1's messages, Task 2's `CastSettings`, Task 4's `CastChannelListener`, Task 7's `CastWindow`.
- Produces: `sealed class CastSession : IDisposable` with `static Task<CastSession> AcceptAsync(string castId, string peerName, string expectedFingerprint, X509Certificate2 identity)` (opens the listener, returns once it is listening, exposes `Port` and `Token`), `void Start()` (begins reading frames into the window), `event Action<CastSettings>? SettingsCorrected`, `event Action<string>? Ended`.
- Produces: `static CastMonitor[] CurrentMonitors()` and `static CastPlacement Correct(CastPlacement wanted, IReadOnlyList<CastMonitor> monitors)` in `CastSession`.

- [ ] **Step 1: Write the failing `CastPlacementTests`**

Cases: `Correct` with a monitor id that is present returns it unchanged; with an id that is absent returns the primary monitor's id and keeps the mode; `AllMonitors` is unchanged by a missing id.

- [ ] **Step 2: Run it to verify it fails**

- [ ] **Step 3: Implement `CastSession` and wire it into `MainWindow`**

On `CastStartMessage`: build the session, reply `CastReadyMessage(castId, port, token)`, open the `CastWindow` in the foreground on the first frame. On `CastSettingsMessage`: apply placement, send back a corrected record when `Correct` changed it. On the window closing, the session ending or the peer disconnecting: send `CastStopMessage` and dispose. A dropped media plane shows "Reconnecting" and waits for the sender's new connection on the same listener. Unpairing or blacklisting the peer ends its cast the same way a disconnect does.

- [ ] **Step 4: Run the suite to verify it passes**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(cast): receive a cast from a paired phone"
```

---

### Task 9: Capability flag in discovery

**Files:**
- Modify: `src/windows/Mesh.Core/MeshDiscovery.cs`, `android/app/src/main/java/com/mesh/core/MeshDiscovery.kt`
- Modify: `src/windows/Mesh.App/DeviceRow.cs`, `android/app/src/main/java/com/mesh/ui/DeviceRow.kt`
- Test: `src/windows/Mesh.Tests/MeshDiscoveryTests.cs`

**Interfaces:**
- Produces: both `Advertise`/`advertise` add the TXT property `cast` with value `1`.
- Produces: `DiscoveredDevice.SupportsCast` / `DiscoveredDevice.supportsCast: Boolean`, true only when the TXT record carries `cast=1`.
- Produces: `DeviceRow.SupportsCast` / `DeviceRow.supportsCast`, carried through the row rebuild on both apps.

- [ ] **Step 1: Write the failing discovery test**

In `MeshDiscoveryTests`: a service advertised by this build is discovered with `SupportsCast == true`; a TXT record without the key yields `false`.

- [ ] **Step 2: Run it to verify it fails**

- [ ] **Step 3: Add the TXT property, the parsed flag and the row field on both sides**

- [ ] **Step 4: Run it to verify it passes**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(core): announce that a device can take a cast"
```

---

### Task 10: Android cast controls

**Files:**
- Modify: `android/app/src/main/java/com/mesh/ui/DeviceFragment.kt`, `android/app/src/main/java/com/mesh/ui/MainActivity.kt`
- Create: `android/app/src/main/res/layout/fragment_cast_controls.xml`, `android/app/src/main/java/com/mesh/ui/CastControlsFragment.kt`

**Interfaces:**
- Consumes: Tasks 1-6 and 9.
- Produces: `MainActivity.startCast(peerUuid: String)`, `MainActivity.stopCast()`, `MainActivity.updateCastSettings(settings: CastSettings)`, `MainActivity.castSettings: CastSettings?`.

- [ ] **Step 1: Implement the start path**

A Cast control on the device page, shown only when the peer's row has `supportsCast` and the peer is connected. Tapping it sends `CastStart`, launches Android's capture consent, waits for `CastReady`, opens the `CastChannel` and starts the `ScreenCaster`. A `CastStop` from the PC, a denied consent, or the session dropping stops everything and releases the service.

- [ ] **Step 2: Implement the controls**

While a cast runs the device page shows: a quality slider `0..100`, an audio switch, and the placement choice built from the monitor list in the last settings record. Any change sends a full `CastSettingsUpdate`; an incoming one updates the controls without echoing it back.

- [ ] **Step 3: Verify on the real pair**

Cast to the PC, move the slider end to end, toggle audio, move the window between monitors from the phone, lock and unlock the phone, rotate it, and stop from each side in turn.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(cast): start and steer a cast from the phone"
```

---

### Task 11: Windows cast controls

**Files:**
- Modify: `src/windows/Mesh.App/MainWindow.xaml`, `src/windows/Mesh.App/MainWindow.xaml.cs`, `src/windows/Mesh.App/Theme.xaml`

**Interfaces:**
- Consumes: Task 8's `CastSession`, Task 2's `CastSettings`.

- [ ] **Step 1: Implement the controls**

While a cast runs, the device page shows the same three controls as the phone — quality slider, audio switch, placement — and sends a full `CastSettingsUpdate` on any change. An incoming record updates them without echoing. A Stop ends the cast from this side.

- [ ] **Step 2: Verify on the real pair**

Change each setting from the PC and confirm the phone's controls follow, and the picture changes accordingly.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(cast): steer a running cast from the pc"
```

---

### Task 12: Documentation and release notes

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Describe casting in "What you can do" and add a "Screen casting" subsection under "How it works"**

Cover: what it does, the two planes and why, the quality scale, that the PC does not prompt, and what Android does not allow (one sentence, with the same two links the spec carries).

- [ ] **Step 2: Commit**

```bash
git commit -m "docs: describe screen casting in the readme"
```
