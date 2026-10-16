# Discovery & Pairing — Design Spec

Date: 2026-10-13
Sub-project 1 of "Mesh" (Windows ⇄ Android link app). Scope: devices find
each other on the same LAN, pair once via PIN confirmation, and remember
each other for future connections. Out of scope: WAN/manual-IP connection,
clipboard sync, file transfer, screen mirroring, input control — those are
later sub-projects that build on the secure channel this one establishes.

## Goals

- Windows app (C#/.NET, native — not MAUI shared UI) and Android app
  (Kotlin, native) discover each other automatically on the same LAN.
- First-time connection requires human confirmation via a PIN shown on
  both screens (prevents silent/accidental pairing).
- Once paired, devices are remembered; reconnecting does not require the
  PIN again, only certificate-fingerprint verification.
- Establish a TLS-secured TCP channel that later sub-projects (clipboard,
  files, remote control) will reuse.

## Non-goals

- NAT traversal / internet relay / manual IP entry (future sub-project).
- Any feature beyond discovery, pairing, and the secured channel itself.

## Architecture

Two independent native apps sharing only a protocol definition (documented
here), not code:

1. **Windows app (C#/.NET)**
   - mDNS advertise + browse (library: `Makaretu.Dns` or equivalent).
   - Identity: self-signed cert + key pair generated on first run, stored
     at `%APPDATA%/Mesh/identity.pfx`.
   - TCP+TLS listener/connector.
   - Paired-device store: `%APPDATA%/Mesh/paired_devices.json`.

2. **Android app (Kotlin)**
   - mDNS via `NsdManager`.
   - Identity: key pair in Android Keystore, self-signed cert alongside.
   - TCP+TLS listener/connector.
   - Paired-device store: Room table `paired_devices`.

## mDNS service definition

- Service type: `_meshlink._tcp`
- TXT records: `id=<device-uuid>`, `name=<device-name>`, `platform=windows|android`
- Port: dynamically chosen, advertised in the SRV record (standard mDNS behavior).

## Pairing protocol

1. On first run, each app generates a key pair + self-signed certificate
   if none exists yet.
2. Each app advertises itself via mDNS as above, and browses for peers.
3. User picks a discovered device and taps/clicks "Connect".
4. Initiator opens TCP, performs TLS handshake. At this stage both sides
   accept any peer certificate (no trust established yet).
5. After handshake, both sides compute the SHA-256 fingerprint of the
   peer's certificate, then derive a 6-digit PIN deterministically from
   both fingerprints combined (order-independent — e.g. sort fingerprints
   before hashing) so both screens show the same PIN.
6. User visually compares the PIN on both screens and confirms "Match" on
   each.
7. On mutual confirm, each side stores the peer as trusted: `{uuid, name,
   fingerprint, last_ip, paired_at}` in its paired-device store.
8. On any future reconnect to a known `uuid`/`fingerprint`, TLS handshake
   is validated against the pinned fingerprint — no PIN step.

## Data flow

```
mDNS browse → candidate list (UI)
  → user selects "Connect"
  → TCP connect + TLS handshake (untrusted)
  → fingerprint → PIN derivation → user confirms on both screens
  → paired-device store write
  → secured session channel ready (handed off to future sub-projects)
```

## Error handling

- mDNS unavailable / blocked by firewall: UI shows "mDNS unreachable —
  check firewall settings" plus a manual refresh button.
- PIN mismatch: user taps "Not matching" → connection closed, both sides
  shown "Pairing failed".
- Known device's fingerprint changed (e.g. reinstalled app): TLS/pin
  validation rejects silently-trusting it; UI shows "Certificate changed
  for <name> — re-pair?" and requires going through the PIN flow again.
- Handshake timeout: 10 seconds, then "Connection failed" shown.

## Testing

- Unit: PIN derivation is deterministic and order-independent given the
  same two fingerprints.
- Unit: paired-device store serialize/deserialize round-trip (JSON on
  Windows, Room entity on Android).
- Integration: full pairing flow between two local loopback processes/
  emulated peers.
- Manual: real Windows PC + real Android device on the same Wi-Fi network.
