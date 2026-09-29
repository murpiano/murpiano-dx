---
name: cloudpix-travel-globe
description: "CloudPix is being rebuilt as a travel-memory globe; design doc and prototype are committed, next step is spec review then implementation plan"
metadata:
  node_type: memory
  type: project
  originSessionId: 49e936ef-b506-4ce0-bd5d-1d95b931ebf9
  modified: 2026-09-29T06:06:46.141Z
---

CloudPix (~/projects/cloudpix-platform) is being rebuilt from the photo sphere into a personal travel archive on a night globe (trips, albums, timeline, plane tours, home base).

State on 2026-09-29:
- Design doc: `docs/design/2026-09-29-travel-globe.md` (commit e103657). Prototype it describes: `docs/design/prototype/flight.html` + `atlas-data.js`.
- Demo assets: `public/demo/photos/` (58 Wikimedia photos), `public/demo/photos.json` (credits), `public/demo/countries-110m.json` (commit 4873eb5).
- Both commits are local, not pushed.
- The user approved the prototype behaviour. The written doc still needs their review.
- Next: the user reviews the doc, then writing-plans produces the implementation plan, then build.
- Backend (murpiano-server cloudpix project) is deliberately later and gets its own design.

**Why:** the user started a new session because the previous context grew too large.

**How to apply:**
- Start by asking the user to review the doc, then plan.
- Keep design docs out of `docs/superpowers` and similar agent-named paths. The user wants no agent traces in repos (see [[repo-cleanup]]).
- Demo server for the prototype: brainstorm server script with `BRAINSTORM_DIR` set to `.superpowers/brainstorm/1562089-1790587256`, port 58424.
