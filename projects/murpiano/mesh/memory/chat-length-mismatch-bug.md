---
name: chat-length-mismatch-bug
description: "Open bug, fix later on user request — phone chat limit 4x bigger than PC, long phone messages silently lost on PC"
metadata:
  node_type: memory
  type: project
  originSessionId: dedb86d2-f997-494d-ac6b-49c414f0d752
  modified: 2026-10-16T20:12:10.043Z
---

Open bug, user said "запомни, потом исправим" (2026-10-16). Not fixed in v1.0.0.

Android `MainActivity.kt` `MAX_CHAT_TEXT_LENGTH = 4 * 1_048_576`, Windows `MainWindow.xaml.cs` `MaxChatTextLength = 1_048_576`. Wire limit `MaxTextBytes = 4 * 1_048_576` on both sides. Phone message over 1,048,576 chars never shows on PC (dropped silently). Listed in README "Rough edges" and v1.0.0 notes — remove those lines when fixed.

**Why:** user postponed it, wants it remembered.
**How to apply:** when user says to fix bugs, fix in branch `fix/<name>`, make limits equal on both apps, update README rough edges.

Also open: PIN asked again on reconnect of Trusted device — waiting for both debug.log files from user. See [[mesh-dev-workflow]].
