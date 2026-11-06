---
name: project-profile
description: Use when connecting an existing project, creating a brand-new one, or whenever the full picture of a project (stack, platforms, infra, workflow) is needed — maintain the one project-profile table. Not for day-to-day coding tasks on an already-profiled project; read the existing profile instead of re-deriving it.
---

# Project profile

Scope: one standing, filled-in table per project describing everything
about it — identity, platform, frontend/backend stack, infra, Git
workflow, constraints. Used two ways:

- **Connecting an existing project** (`skills/repo-init/SKILL.md`): fill
  it from detected signals, confirmed with the owner.
- **Creating a new project** (`skills/stack-selection/SKILL.md` and the
  domain's guided-setup skill, e.g. `frontend-project-setup`): fill it
  top to bottom *as decisions are made* — this table is the checklist
  for building the project, not only a report written after the fact.

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
- When a project's stack changes (a new backend added, a styling
  approach migrated), update the profile in the same change — it should
  never silently drift out of date.
- A profile value that contradicts this framework's recorded default
  (e.g. Tailwind where `frontend-styling-concept` defaults to CSS
  Modules) is exactly the project-level override described in
  `skills/DELEGATION-MODEL.md` — the profile is where that override is
  recorded.
