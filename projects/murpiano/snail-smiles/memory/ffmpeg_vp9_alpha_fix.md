---
name: ffmpeg-vp9-alpha-fix
description: ffmpeg libvpx-vp9 webm alpha channel requires -auto-alt-ref 0 -lag-in-frames 0 or it silently breaks in real players
metadata:
  node_type: memory
  type: project
  originSessionId: c978a862-2a02-401d-8b22-aea47879aec2
  modified: 2026-10-19T13:08:50.863Z
---

Encoding transparent webm (VP9 + alpha, e.g. for Telegram custom emoji/video stickers) with `ffmpeg -c:v libvpx-vp9 -pix_fmt yuva420p` alone produces a file that LOOKS correct (ffprobe/encoder log shows yuva420p, and even `ffmpeg -c:v libvpx-vp9` forced-decode round-trip shows real 0-255 alpha values) but renders as fully opaque with a white/solid background in Telegram, browsers, and standalone video players (VLC/mpv-class decoders).

Root cause: VP9 alt-ref (alternate-reference, non-displayed lookahead) frames desync the alpha side-stream from the color stream. Standards-compliant decoders then reject/ignore the alpha track entirely and fall back to opaque. ffmpeg's own forced-decoder verification is not a reliable check — it can read back "valid-looking" alpha even when the file is non-conformant for everyone else.

**Fix**: always add `-auto-alt-ref 0 -lag-in-frames 0` to the libvpx-vp9 encode command when the output needs real alpha transparency:

```
ffmpeg -y -framerate <fps> -i frames/f%03d.png -vf "fps=30" \
  -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 30 \
  -auto-alt-ref 0 -lag-in-frames 0 -an output.webm
```

**How to verify for real** (ffprobe/ffmpeg self-decode is not trustworthy): render the file in an actual standards-compliant engine. This session used a locally-installed `playwright-core` + Playwright's bundled Chromium (`~/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome`, launched with `--no-sandbox`, since the Playwright MCP tool itself requires a system "chrome" channel that needs sudo to install and wasn't available) to load an HTML page with a `<video>` tag over a bright solid-color background (e.g. magenta) and screenshot it — if the background color shows through around the subject, alpha is genuinely working.

Context: project is [[smiles-emoji-pipeline]] — converting a folder of 32x32 pixel-art animated GIF smileys into smooth AI-upscaled Telegram custom emoji (100x100 VP9 webm with alpha). This fix must be applied to every future batch/regeneration in that pipeline, and to any one-off manual assembly (e.g. the `сборка/` folder workflow where the user drops cleaned PNG frames in and asks for them assembled into a webm).
