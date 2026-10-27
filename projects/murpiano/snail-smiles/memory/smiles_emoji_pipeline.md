---
name: smiles-emoji-pipeline
description: "ongoing project converting raw/ pixel-art smiley GIFs into smooth transparent Telegram custom emoji webm, plus a manual сборка/ assembly workflow"
metadata:
  node_type: memory
  type: project
  originSessionId: c978a862-2a02-401d-8b22-aea47879aec2
  modified: 2026-10-19T13:09:06.824Z
---

Project in `/home/bvtrots/projects/smiles/`. Goal: turn `raw/` (90 animated 32x32 pixel-art smiley GIFs, Cyrillic filenames like "[Smiles] - Улыбка.gif") into Telegram **custom emoji** (not stickers) — small inline animated emoji added via `/newemojipack` on @Stickers bot, which requires Telegram Premium to create.

**Pipeline** (script: scratchpad `batch_upscale.py`, venv at scratchpad `venv/`):
1. Erode each frame's native 32x32 alpha mask by 1px — the source art has a baked-in near-white AA fringe on fully-opaque edge pixels (artifact of flattening onto a white canvas at export) that gets amplified into a halo if not stripped first.
2. distance_transform edge-extend fill for transparent pixels (so the AI model gets coherent context), then upscale with Real-ESRGAN (`RealESRGAN_x4plus_anime_6B.pth`, CPU, ~0.2-0.4s/frame on this 16-core box) for smooth (non-pixelated) results.
3. Build final alpha via a HARD binary mask (no soft gradient) + premultiplied-alpha downscale (BOX resize of premultiplied RGB and of the mask separately, then unpremultiply) — this was the fix for widespread near-white "ghost" semi-transparent pixels bleeding around 80/90 files' silhouettes. A naive blurred/thresholded alpha or plain RGBA Lanczos resize both reintroduce this.
4. Encode webm: `libvpx-vp9 -pix_fmt yuva420p ... -auto-alt-ref 0 -lag-in-frames 0` — see [[ffmpeg-vp9-alpha-fix]], mandatory or transparency silently breaks in real players despite looking fine under ffmpeg's own verification.
5. Output targets 100x100 (Telegram custom-emoji spec), 30fps, ≤3s.

Current outputs: `telegram_emoji_webm_smooth/` (90 animated webm) and `telegram_emoji_png_smooth/` (90 static PNG fallback).

**Manual touch-up workflow**: user separately hand-cleans individual frames in an image editor and drops them as numbered PNGs (`00.png`, `02.png`, `04.png`, ...) into a `сборка/` folder, then asks to "собери" (assemble) them — task is to ffmpeg-encode whatever PNGs currently sit in that folder into one webm using the same validated settings (100x100, 30fps via `-vf fps=30` after an arbitrary input `-framerate`, `yuva420p`, `-auto-alt-ref 0 -lag-in-frames 0`). The folder's contents change between asks (files get replaced/added), so always re-`ls` it fresh before assembling rather than assuming prior state.

User confirmed (2026-10-19) this whole approach now works correctly end-to-end in real Telegram — continue the same method for future additions.
