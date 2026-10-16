---
name: mesh-dev-workflow
description: "How Mesh is developed and tested — release vs dev apps on phone and PC, where builds run, no binaries in git"
metadata:
  node_type: memory
  type: project
  originSessionId: dedb86d2-f997-494d-ac6b-49c414f0d752
  modified: 2026-10-16T20:31:27.767Z
---

Set up 2026-10-16 (PR #8, branch build/dev-builds).

- Phone (Xiaomi 23127PN0CG, adb serial 5c09bdfd): two apps side by side. "Mesh" `com.mesh` = release from GitHub Releases, user's daily app, never touched by dev work. "Mesh Dev" `com.mesh.debug` = debug build, I update it with `adb install -r` and test on it. Xiaomi asks to confirm each adb install on screen ("Install canceled by user" = nobody tapped), so retry in a loop and tell the user to tap.
- PC: release exe = user's daily app, data `%AppData%\Mesh`. Dev = debug build from sources, data `%AppData%\Mesh Dev`, title "Mesh Dev", name suffix " (dev)". I build and run it from `%LOCALAPPDATA%\Programs\Mesh Dev\Mesh.App.exe` (copy of bin/Debug; never run from the \\wsl path, it hangs; stopping the old instance first, because rebuild cannot overwrite a running exe). The user works in that window; every change means I rebuild and restart it.
- Built files (.exe/.apk) are never committed: they live on GitHub Releases. User asked about keeping the exe in the repo; I explained why not, and they agreed that dev runs from sources.
- Release key: `~/.config/murpiano-dx/mesh-android/` (release.jks + release.properties), secrets ANDROID_KEYSTORE_BASE64 / ANDROID_KEYSTORE_PASSWORD. Losing it breaks APK updates.
- Debug logs before the 2026-10-16 switch saved to `raw/logs/2026-10-16/` (phone + PC) for the PIN bug in [[chat-length-mismatch-bug]].

**Why:** user wants a stable app for daily use and a separate dev app I can update freely, without uninstalling.
**How to apply:** test changes only on Mesh Dev / the dev desktop build; release apps get updates only via GitHub releases.
