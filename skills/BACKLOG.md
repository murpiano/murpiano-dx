# Framework backlog

Open items for the framework itself (not any one project). Referenced
from `skills/DELEGATION-MODEL.md`. Move an item here instead of letting
it live only in a conversation; remove it once it's actually done
(mention the skill/file that resolved it, don't just delete silently).

## Open

- **Frontend domain is not finished.** `frontend-styling-concept` /
  `frontend-web-styles` cover the architecture skeleton (tokens,
  colocation, isolation, baseline reset) but not, e.g.: design-token
  *naming* conventions (prefixing scheme, scale naming like
  `--space-100` vs `--spacing-sm`), component file/folder patterns beyond
  "one `.module.css` per component", a naming convention for the
  components themselves, testing conventions, accessibility specifics
  beyond the constraint row in `project-profile.md`. Treat the domain as
  open, not settled, until these are discussed.
- **Dogfood on a real project before adding more.** `my-world`
  (`/home/bvtrots/projects/my-world`, formerly `cloudpix-platform`) was
  the original source for the styling patterns here — run the new
  `repo-init` "adopting existing conventions" flow on it for real, fill
  its `project-profile.md`, and see what the written rules get wrong or
  miss. Higher priority than inventing further rules from imagination.
- **Backend domain** — do not pre-build; start it (concept →
  implementation → setup, per `DELEGATION-MODEL.md`) only once a real
  backend project is connected or created.
- **Team review process for framework changes.** Right now any change to
  `skills/`/`DELEGATION-MODEL.md`/etc. is just agreed in conversation and
  written. Fine solo; for a team sharing this framework, decide whether
  framework-structure changes need a review step (PR-style) before they
  apply to everyone's sessions.
- **Concurrent edits to one project's `project-profile.md`.** Two
  sessions (or two people) editing the same project's profile/decisions
  at once — `sync.sh`'s existing merge-conflict handling (both sides
  kept, conflict reported) applies at the file level, but there's no
  profile-specific guidance yet (e.g. which section is safe to edit
  concurrently).

## Done

- Cross-platform styling concept + web implementation + guided setup
  (`frontend-styling-concept`, `frontend-web-styles`,
  `frontend-project-setup`).
- Stack-selection entry point (`stack-selection`).
- Project profile table + per-field decision records
  (`project-profile`).
- Delegation model, including the graph-trigger rule
  (`DELEGATION-MODEL.md`).
- Skill revision/retirement rule (`DELEGATION-MODEL.md`).
- Framework self-lint (`framework-lint`).
