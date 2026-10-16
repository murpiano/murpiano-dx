# Persistent Session & Clipboard Sync — Design Spec

Date: 2026-10-14
Sub-project 2 of "Mesh" (Windows ⇄ Android link app). Builds on sub-project 1
(discovery & pairing, shipped and verified live on real hardware). Scope:
keep the TLS channel open after pairing/reconnect, and use it to sync a
shared, persisted text clipboard history between a paired Windows PC and
Android phone. Out of scope: file transfer (deferred to a later "shared
folders" sub-project — the user explicitly decided clipboard stays
text-only), remote input/screen mirroring (later sub-projects).

## Goals

- After pairing or a trusted reconnect (sub-project 1), the TLS channel
  stays open for the life of the app session instead of closing
  immediately, so it can carry ongoing traffic — starting with clipboard
  sync, extensible to future sub-projects (remote control, etc.).
- If the channel drops (app backgrounded, network blip, peer restart), the
  app automatically reconnects to the last-known-trusted peer in the
  background, with backoff.
- Copying text on either device pushes it to the other device's clipboard
  **history** (not the live system clipboard) over the open channel.
- Each device keeps its own local history of the last 50 clip events
  (own copies and received copies mixed, newest first), auto-evicting the
  oldest when the cap is exceeded.
- The UI gains a tab structure: a "Devices" tab (sub-project 1's existing
  discovery/pairing screen) and a "Clipboard" tab (history list, each
  entry has a "Copy" action that puts that text onto the local system
  clipboard; a connection-status indicator).
- A copy made while disconnected is queued locally and sent once the
  channel reconnects.

## Non-goals

- Files or any non-text clipboard content (explicit user decision — files
  belong to a future shared-folders feature instead).
- Automatically applying a received clip to the local system clipboard
  (avoids feedback loops and matches the user's description: received
  clips sit in a list until the user chooses to copy one).
- Multi-device fan-out (still exactly one paired peer per device, per
  sub-project 1's model).

## Architecture

Both platforms get a new Core layer, `MeshSession`, sitting on top of
sub-project 1's `PairingSession`/`PairingListener`:

1. **Windows (C#/.NET)**
   - `Mesh.Core.MeshSession`: wraps the `SslStream` that pairing/reconnect
     already produced, instead of closing it. Runs a background read loop
     parsing framed messages. Exposes `Send(MeshMessage)` and a
     `MessageReceived` event. Owns reconnect logic (last-known IP + port
     from the paired-device record, retry with exponential backoff capped
     at e.g. 30s, re-resolve via mDNS if direct connect fails a few times).
   - `Mesh.Core.ClipboardHistoryStore`: SQLite (via `Microsoft.Data.Sqlite`)
     at `%APPDATA%/Mesh/clipboard_history.db`, capped at 50 rows (oldest
     deleted on insert past the cap).
   - `Mesh.Core.ClipboardWatcher`: wraps `AddClipboardFormatListener`
     (via a hidden `HwndSource` message hook) to detect local text copies.
   - `Mesh.App`: new "Clipboard" tab (`TabControl`) wired to the history
     store + `MeshSession`.

2. **Android (Kotlin)**
   - `com.mesh.core.MeshSession`: same role, wraps the `SSLSocket` kept
     open after pairing/reconnect.
   - `com.mesh.core.ClipboardHistoryDao`/Room entity, same 50-row cap,
     same SQLite-backed approach via the existing `MeshDatabase`.
   - `com.mesh.core.ClipboardWatcher`: wraps
     `ClipboardManager.OnPrimaryClipChangedListener`.
   - `com.mesh.ui`: tab navigation (two `Fragment`s: Devices, Clipboard)
     hosted in `MainActivity` via a simple `ViewPager2`/`TabLayout` or
     manual fragment-swap (implementer's choice, keep it simple — no
     navigation library needed for two static tabs).

## Wire protocol (shared contract, implemented identically on both sides)

Reuses sub-project 1's `PairingProtocol` framing primitive (4-byte
big-endian length prefix + UTF-8 payload) as the base. On top of the open
post-pairing channel:

- Every message starts with a 1-byte type tag.
  - `0x01` = `ClipboardPush`: followed by an 8-byte big-endian Unix
    millisecond timestamp (the sender's clock, informational only — each
    receiver also stamps its own local receipt time for sorting), then
    the length-prefixed UTF-8 text.
  - `0x02` = `Heartbeat`: no payload. Sent every 20s on an otherwise-idle
    channel so a dead connection is detected within ~45s (if no message,
    including heartbeats, arrives within that window, treat the channel
    as dropped and start reconnecting).
- Messages are independent and unordered-safe (no sequencing needed for
  this sub-project's single message type).

## Reconnect behavior

- On unexpected channel close (read error, heartbeat timeout), `MeshSession`
  transitions to "disconnected", notifies the UI (status indicator), and
  starts a reconnect loop: attempt connect to the paired device's
  `last_ip`/port immediately, then with backoff (1s, 2s, 4s, 8s, capped at
  30s) on repeated failure. On successful reconnect, trust is already
  established (sub-project 1's fingerprint-pinned reconnect — no PIN
  needed), the channel resumes, and any queued outgoing clips are flushed
  in order.
- If `last_ip` no longer responds after a few attempts, fall back to
  mDNS re-discovery (reuse sub-project 1's `MeshDiscovery`) to find the
  peer's current IP, then retry connect.

## Data flow

```
Local text copy (OS clipboard event)
  → ClipboardWatcher fires
  → append to local ClipboardHistoryStore (source: "local")
  → UI (Clipboard tab) updates
  → if MeshSession connected: MeshSession.Send(ClipboardPush)
    else: queue in an outgoing pending list, flushed on reconnect

Incoming ClipboardPush (MeshSession.MessageReceived)
  → append to local ClipboardHistoryStore (source: peer's device name)
  → UI (Clipboard tab) updates
  → (no automatic system-clipboard write)

User taps "Copy" on a history entry
  → write that entry's text to the local OS clipboard
  → (ClipboardWatcher will see this as a new local copy and re-push it —
     see Error Handling below for the dedup this requires)
```

## Error handling

- **Dedup on self-copy-from-history:** tapping "Copy" on a received entry
  writes to the OS clipboard, which `ClipboardWatcher` will detect as a
  new local change and would otherwise re-push the exact same text back
  to the peer, creating a duplicate entry (and if the peer also has
  history forwarding... this sub-project doesn't forward received clips
  again, so it's a single duplicate, not an infinite loop, but still
  undesirable). Fix: `ClipboardWatcher` suppresses the next change
  notification for a very short window (e.g. 500ms) immediately after
  the app itself wrote to the clipboard via the "Copy" action, so it
  doesn't re-trigger a push for its own write.
- **Channel drop mid-send:** `Send` failing (e.g. socket already closed)
  queues the message for the next reconnect instead of dropping it
  silently.
- **History cap race:** inserts and cap-eviction happen inside a single
  transaction (SQLite) so the count never visibly exceeds 50 even under
  concurrent local+remote writes.
- **Large clipboard text:** cap the text length accepted by
  `ClipboardWatcher`/`ClipboardPush` at a sane limit (e.g. 1 MB) — reject
  (don't push, don't store) anything larger, to avoid memory/wire blowups
  from e.g. an accidental huge paste buffer.
- **Reconnect storm:** backoff (above) prevents hammering a genuinely
  offline peer; mDNS re-discovery is only attempted after the direct-IP
  retries are exhausted, not on every attempt.

## Testing

- Unit: wire protocol framing/parsing round-trip for both message types,
  on both platforms.
- Unit: `ClipboardHistoryStore`/Dao cap-and-evict behavior (insert 51,
  assert oldest gone, count stays 50).
- Integration: `MeshSession` over a loopback TLS pair (reusing
  sub-project 1's test harness pattern) — send/receive `ClipboardPush`,
  verify heartbeat keeps the channel alive, verify reconnect after a
  forced socket close picks the session back up and flushes a queued
  message.
- Unit: self-copy dedup window doesn't suppress a genuinely new,
  different local copy made shortly after a "Copy" action.
- Manual: real Windows PC + real Android device, copy text on each side,
  confirm it appears in the other's Clipboard tab; kill Wi-Fi briefly,
  confirm reconnect and that a clip copied while offline arrives once
  connectivity returns.
