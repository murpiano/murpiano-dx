# Screen casting between paired devices — design

## Intent

Mesh already pairs a phone and a PC and keeps a live session between them. This adds the
other thing the author wants from that pair: putting one device's screen on another device's
screen, over the local network, with Mesh installed everywhere.

The first case that pushed it: sheet music opened in a PDF viewer on the phone, read from a
big screen while playing. The long-term intent is general — any Mesh device can hand its
picture to any other Mesh device it is paired with.

This document covers the first slice: **the phone sends, the PC receives.** The pieces are
shaped so the later directions (phone to TV, PC to phone) reuse them, but they are not built
here.

## Goals

- A cast runs between two already-paired, currently-connected devices, started from the
  device page.
- The PC shows the picture in its own window, separate from the main Mesh window, which can
  be moved to any monitor, made full screen, or stretched across all monitors.
- Every setting of a running cast has **two control points**: the phone and the PC. A change
  made on either side applies to the cast and shows on both.
- The settings are: picture quality (a scale from smooth motion to sharp detail), audio on or
  off, and where the PC window sits. All three change while the cast runs, with no restart.
- The quality scale has to make small static text — sheet music, code, documents — readable
  at one end of it.
- Either side can end the cast.

## Non-goals (not in this slice)

- The TV build (Android TV) and the PC-sends direction. The protocol and the session model
  are designed to take them later; nothing here is to be written in a way that blocks them.
- Casting to more than one receiver at once.
- Input going back the other way: this is a picture, not remote control. No touch, no mouse,
  no keyboard from the PC to the phone.
- A PDF viewer of our own on any device. It was discussed and dropped.
- Recording a cast to a file.

## Anti-goals

- **Do not** make the PC window a second desktop for the phone. Android does not allow it
  (see Constraints), and faking it halfway would be worse than not having it.
- **Do not** let a cast run without the receiving device's user being able to see it and stop
  it. The receiver does not approve a cast before it starts (see Starting), but the window is
  unmissable and closing it ends the cast.
- **Do not** block the chat, the pairing or the heartbeat behind video traffic. A cast that
  makes the rest of Mesh unresponsive is a failure even if the picture is perfect.
- **Do not** grow the desktop release past a reasonable download because of a decoder. The
  release is a single self-contained `.exe`; a +100 MB decoder bundle is not acceptable.

## Constraints

### What Android does not allow

A normal app, without system privileges or root, cannot run one app on an external screen
while the phone goes on being used for something else:

- `MediaProjection` captures what is on the phone's screen. Android 14 (API 34) can capture a
  single app's window instead of the whole screen, but it is still the window of the app the
  user is looking at.
  (<https://developer.android.com/about/versions/14/features/app-screen-sharing>)
- An app may launch only **its own** activities on a `VirtualDisplay` it created. Launching
  another app's activity on a display needs `INTERNAL_SYSTEM_WINDOW` (system components) or
  the narrow `ACTIVITY_EMBEDDING` case.
  (<https://source.android.com/docs/core/display/multi_display/activity-launch>)

So: the phone mirrors what it is showing. The author knows this and accepted it. On the PC
side the same restriction does not exist — Windows can capture a single window or a single
monitor — which is where "send this window there, that window elsewhere" will become possible
when the PC-sends direction is built.

### Other platform facts

- Starting a capture always shows Android's own consent dialog. It cannot be suppressed, and
  it appears every time a cast starts.
- The capture must run under a foreground service declaring `mediaProjection`, with the
  notification Android puts up.
- Audio capture (`AudioPlaybackCapture`, API 29+) only gets the audio of apps that allow
  being captured. Apps that opt out, and most DRM playback, come through silent. This is a
  property of Android, not a bug to fix: it has to be visible in the UI, not hidden.
- Only one `MediaProjection` is active at a time in a process.

## How it works

### Two planes

The existing `MeshSession` (the single TLS connection that carries chat) becomes the
**control plane** for casting. It carries small messages only: start, stop, settings changed,
the receiver's monitor list. It must never carry frames.

The **media plane** is a second TLS connection, opened for the cast and closed with it, to
the same peer, authenticated the same way the pairing connection is (both certificates
checked against the stored fingerprints — a cast connection must not be a way around
pairing). It carries only encoded video and audio frames. A separate connection is what keeps
a 20 Mbit/s picture from delaying a heartbeat or a chat message, and what lets the cast die
without taking the session with it.

### Session state and the two control points

One record describes a running cast: who sends, who receives, the quality value, audio on or
off, and the window placement. It lives on both devices and is kept identical by sending the
whole record on every change, from whichever side made the change, over the control plane.
Last change wins; there is no merge. The record is small and changes are rare (a human moving
a slider), so there is nothing to be clever about.

Each side applies the record to what it owns: the phone applies quality and audio to its
encoder, the PC applies the placement to its window. A side that receives a record it cannot
satisfy (a monitor that no longer exists) applies the nearest thing it can and sends back the
corrected record.

### The sending side (Android)

- `MediaProjection` -> `VirtualDisplay` -> the input surface of a `MediaCodec` H.264 encoder,
  which is hardware-backed on any phone this runs on.
- The encoder output goes to the media plane as length-prefixed frames with a type byte and a
  presentation timestamp. Codec configuration (SPS/PPS) is sent first and re-sent on every
  settings change that restarts the encoder.
- Audio, when on: `AudioPlaybackCapture` -> AAC in the same `MediaCodec` style, interleaved on
  the same connection with its own frame type.
- A foreground service owns the projection for the life of the cast, as
  `MeshConnectionService` already does for the session.

### The receiving side (Windows)

- A separate WPF window, one per cast, owning its own decoder.
- The decoder is Windows' built-in H.264 decoder (Media Foundation Transform), reached through
  managed interop. This keeps the single-file release small; bundling FFmpeg would add tens of
  megabytes to a download that is 73 MB today. **This is the designer's call, not the author's
  requirement**: if the Media Foundation path proves unworkable during implementation, falling
  back to a bundled decoder is allowed, and the size cost goes in the release notes.
- Decoded frames are drawn in the window, scaled to fit, letterboxed, with the aspect ratio of
  the phone's screen kept.
- Audio, when on, plays through the default output device.
- The window shows the state when there is no picture: connecting, reconnecting after a drop,
  and why a cast ended.

### The quality control

One value, 0 to 100, from "smooth" to "sharp". The sender maps it to frame rate, bitrate,
resolution scale and keyframe interval. Anchors:

- **Smooth end**: full frame rate (up to 60 fps if the phone allows), resolution scaled down
  to about 1080p wide, bitrate spent on keeping up with motion.
- **Sharp end**: low frame rate (10 fps or less), native resolution, bitrate spent on detail,
  keyframes often enough that a static page settles quickly and stays clean.

A change applies without tearing the cast down: bitrate and frame rate change on the running
encoder where the device supports it, and a resolution change restarts the encoder and re-sends
its configuration. The receiver handles both.

### Starting, stopping, failing

- Start: from the device page of a connected peer. Android's consent dialog follows. The PC
  does not ask: the devices are paired and connected, the person starting the cast is at the
  phone, and Android has already made them confirm. The PC opens the window as soon as the
  first frame arrives, in the foreground — the window appearing is the receiver's notice that
  a cast started, and closing it ends the cast. (The author chose this over a per-cast or
  first-time prompt on the PC.)
- Stop: from either device, and from the PC by closing the window. A stop goes over the
  control plane so the other side ends cleanly.
- The media plane dropping does not end the session: the receiver shows "Reconnecting" and the
  sender re-dials the media connection with the same backoff policy the session already uses.
  If the control session itself drops, the cast ends with it.
- Blacklisting or unpairing a device ends a cast with it, as it already ends the session.

### Interruptions on the phone

The cast survives the phone's screen locking, the user switching apps and the screen
rotating. None of these end it:

- **Screen off / lock.** The projection keeps running; frames may stop or arrive black. The
  receiver window keeps the last frame and says "Phone screen is off" over it. When the
  screen comes back the picture resumes without a new consent dialog.
- **Switching apps.** Nothing special: the picture is whatever the phone shows, which is the
  point.
- **Rotation.** The encoder restarts at the new size and re-sends its configuration, exactly
  as a resolution change from the quality slider does. The receiver window re-letterboxes to
  the new aspect ratio.

**Designer's call, not the author's requirement**, in all three cases.

### Latency

The target is "feels immediate on a LAN": under 150 ms from the phone's screen to the PC's,
at the smooth end of the quality scale. The receiver draws each frame as it decodes it and
does not buffer to smooth jitter; audio plays through a small buffer and is not resynced to
video, since the picture is the subject and a few tens of milliseconds of drift on a sheet of
music is nothing. Where the sharp end's low frame rate makes a frame old by the time it
arrives, the frame is still drawn rather than dropped. **Designer's call.**

### The placement record

Placement is three fields: a mode (`window`, `fullscreen`, `all monitors`), the id of the
monitor it applies to, and the window's rectangle when the mode is `window`. The PC is the
authority on what monitors exist: it sends the list (id, name, resolution, which is primary)
in the settings record, and the phone shows those names. A record naming a monitor that is
gone falls back to the primary one, and the PC sends the corrected record back.
**Designer's call.**

### Older peers

Both apps throw on an unknown message tag today, so sending cast messages to a peer that
predates them would drop its session. The two apps are released together, but a release app
and a dev app of different ages do get paired (that is what the dev build is for).

So support is announced out of band, in the mDNS TXT record the discovery already publishes
(`cast=1`). An older peer ignores a TXT key it does not know, and a peer that does not
announce it never gets a cast message: the Cast control is simply not offered for that
device. No new pairing step, which would break pairing with old builds outright.
**Designer's call.**

## Testing

- Core, both platforms: the frame format (type, length, timestamp) round-trips, including a
  frame at the size limit, and the settings record survives a round-trip with every field
  changed.
- Android: the quality mapping produces a monotonic fps/bitrate curve across 0..100, and the
  encoder restart path re-sends codec configuration.
- Windows: the receiver window applies a placement record for a monitor that no longer exists
  by falling back and reporting the corrected record.
- The protocol copies stay in step by hand, as the rest of the protocol does — the frame
  format and the settings record are mirrored byte for byte in both codebases.

Live checks on the real pair are part of the work: a static page of sheet music at the sharp
end, a moving video at the smooth end, and a cast surviving the phone's screen locking and
unlocking.

## Left to the builder

- The exact wire tags and field order of the cast messages, consistent with the existing
  `MeshMessage` style on both sides.
- The port and discovery of the media plane: a port the receiver announces in the start
  message is the obvious shape, but the builder decides.
- Whether audio rides the same connection as video (assumed here) or its own.
- The Media Foundation interop details, and the decision to fall back to a bundled decoder if
  that path fails.
- The exact numbers behind the quality anchors, tuned on the real pair rather than guessed
  here.
- Where the cast controls sit on each screen, within the existing dark UI.
