---
name: project-profile
description: Use when connecting an existing project, creating a brand-new one, or whenever the full picture of a project (stack, platforms, infra, workflow) is needed — maintain the one project-profile table. Not for day-to-day coding tasks on an already-profiled project; read the existing profile instead of re-deriving it.
---

# Project profile

Governs `project-profile.md` fields: Identity → Interaction mode.

Scope: one standing, filled-in table per project describing everything
about it — identity, platform, frontend/backend stack, infra, Git
workflow, constraints. Used three ways:

- **Connecting an existing project** (`skills/repo-init/SKILL.md`): fill
  it from detected signals, confirmed with the owner.
- **Creating a new project** (`skills/stack-selection/SKILL.md` and the
  domain's guided-setup skill, e.g. `frontend-project-setup`): fill it
  top to bottom *as decisions are made* — this table is the checklist
  for building the project, not only a report written after the fact.
- **Worked by hand, no agent**: the table's own `Governed by` column
  names the skill file that is the knowledge base for that row — open
  `skills/<name>/SKILL.md` directly to read its default, real
  alternatives, and dated `Basis` sources, and write the decision into
  the table yourself. An agent walks this table as a convenience; it is
  not a gate on reading the knowledge base behind any one row.

Master templates: [templates/project-profile.md](templates/project-profile.md)
(the table) and [templates/decision.md](templates/decision.md) (one
field's detail — why this value, what else was considered, what it used
to be).

## Where it lives

Copy the table template to `.agents/project-profile.md` inside the
project's own data (`{{STORE}}`, per `global/project-rules.md`) — not
committed into the project's own repository unless the owner explicitly
asks for that. One file per project; this skill's own `templates/` copy
never gets project-specific values written into it.

A field whose value had real alternatives or a non-obvious reason gets
its own decision file next to the profile, at
`.agents/decisions/<field-slug>.md` (copied from `templates/decision.md`),
and the profile cell links to it: `Value — [why](decisions/<field-slug>.md)`.
Create one only when there is an actual "why" worth keeping — a forced
or trivial choice (e.g. "Visibility: private" with no discussion) stays
a plain value; a decision file created just to have one for every row is
noise, not knowledge.

## Opening a cell's detail

When working on a field and a "why is it this way / what was it before /
what else was possible" question comes up:

1. Check whether the profile cell already links a decision file; if so,
   open and read it before asking the owner or guessing.
2. If none exists and the question's answer is worth keeping, create
   `.agents/decisions/<field-slug>.md` from the template, fill it from
   whatever is known (ask the owner for what isn't), and link it from
   the profile cell.
3. If the value changes later, add a row to that file's "History" table
   instead of overwriting the old value's story — the point is to keep
   *why it changed*, not just the new state (the table already has that).

## Changing a governed cell is a trigger, not cosmetics

A row with a **Governed by** skill (see the template) is not free text —
its value names a technology the framework can act on. Editing one is
four steps, not one:

1. **Resolve the skill.** The new value names a technology; find its
   implementation skill by the owning domain's naming convention (e.g.
   `frontend-web-styles-<technology>` under `frontend-styling-concept`).
   None exists yet → say so and propose drafting it together, per
   `skills/DELEGATION-MODEL.md`'s tiering — do not write the new value in
   and move on as if the work were done.
2. **Do the actual work the change implies** — a styling-approach change
   is a real migration (rewriting components, not just the cell), not a
   documentation edit. The cell reflects the project's actual state; it
   never leads it.
3. **Record the history.** Add a row to that field's
   `decisions/<field-slug>.md` (create one from `templates/decision.md`
   if none existed) — old value, new value, why.
4. **Leave the framework's own default alone.** A project choosing a
   non-default implementation does not change which implementation
   `frontend-styling-concept` (or any concept skill) marks as default for
   new projects — that is a separate, explicit framework-level decision,
   never a side effect of one project's override.

One skill can touch several cells in the same run (e.g. `repo-init`
setting up Kysaro writes `Commit convention`, `PR requirements`, and
`Merge strategy` together) — the relationship is many-cells-per-skill,
not one dedicated skill per cell. A skill's own `SKILL.md` should name
which profile field(s) it governs, mirroring the table's own column.

## Interaction mode — read it before walking any table

Before running `stack-selection`, a domain's `*-stack-selection`, a
`*-project-setup`, or `repo-init`'s confirmation pass, check the
Identity → Interaction mode row. No value yet → ask once (learning /
co-pilot / autonomous, see `DELEGATION-MODEL.md` → "Interaction mode"
for what each means) and write the answer in. A value already there →
use it without re-asking; the owner switches it by saying so, not by
being asked again each session.

## Reading it before anything else

Before asking the owner a question this table already answers for the
current project, read `.agents/project-profile.md` first. If it exists
and has a value for the field in question, state it and move on — this
is the same "state settled conventions, don't re-ask" rule as everywhere
else in this framework (`skills/DELEGATION-MODEL.md`).

## Keeping it current

- A detected-but-unconfirmed value (see the template's "Provenance"
  section) is not settled; confirm it with the owner before relying on
  it elsewhere.
- **Absence of a signal is not the same as a decision.** "No i18n
  library in `package.json`" tells you the project doesn't have
  multi-language support *yet* — it does not tell you whether the
  owner ever considered needing one. Writing "no" into a field from
  silence, without surfacing the question, turns an unopened question
  into a false settled fact; the owner can't correct what they were
  never asked. The template marks a short list of fields this way
  (**"ask explicitly"**) — for those, `repo-init`'s scan step must put
  the question to the owner directly even when nothing was detected,
  and record their actual answer (including a real "no, don't need
  it") as the confirmed value, not an inferred one. Don't expand this
  list casually — it's for decisions that are easy to silently skip
  and expensive to discover missing later, not every blank row.
- When a project's stack changes (a new backend added, a styling
  approach migrated), update the profile in the same change — it should
  never silently drift out of date.
- A profile value that contradicts this framework's recorded default
  (e.g. Tailwind where `frontend-styling-concept` defaults to CSS
  Modules) is exactly the project-level override described in
  `skills/DELEGATION-MODEL.md` — the profile is where that override is
  recorded.

## Concurrent edits

Two sessions (or two people) can end up editing the same project's
`project-profile.md` inside the same `sync.sh start`/`end` window. What
happens depends on *what* overlapped, not just *that* it overlapped —
`sync_workspace()` runs a real `git merge` over the personal workspace
repo (`workspace_sync.py`), so this is an ordinary text-merge, not a
table-aware one:

- **Different rows, or a row plus its own `decisions/<field-slug>.md`**
  merge cleanly on their own — each row is one line, each field's
  decision file is its own path, so non-overlapping edits never
  conflict regardless of how close together in time they happened.
- **The same row (or the same decision file) edited by both** is a real
  Git conflict. `sync_workspace()` does not resolve it for you: on
  `merge --no-edit` failure it aborts the merge, raises, and leaves
  *both* commits intact and unmerged — "Workspace remote changes could
  not be merged... Resolve the conflict, then automatic sync will
  retry." Do not pick a side to make the error go away. Read both
  versions, find out from the owner (or the other session's own record,
  if it left one) which is now true, write the resolved value with its
  own `decisions/<field-slug>.md` entry if the two versions disagreed
  for a real reason, then resolve the Git conflict and re-run sync.
- A detected-but-unconfirmed value (previous bullet) is especially
  exposed here: two sessions independently "confirming" the same blank
  field from two different guesses in the same window is the concurrent
  version of the single-session problem above — the fix is the same,
  surface it and ask, don't silently keep whichever commit happened to
  sync first.
