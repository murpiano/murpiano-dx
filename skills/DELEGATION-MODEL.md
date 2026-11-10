# Delegation model

The user orchestrates; the agent does the work and owns keeping this
framework's knowledge current — the user should not have to re-explain a
decision already made in an earlier session, in this project or any other.
Referenced from `AGENTS.md` → Project rules; read this file whenever
adding, changing, or deciding how to structure a skill, not for routine
task work.

- **State settled conventions, don't re-ask them.** When a skill already
  answers a question the current task raises, say what the convention is and
  apply it. Ask only for a decision this framework genuinely has not made
  yet, or to flag that a better alternative exists than the settled one.
- **Guide step by step when starting new work.** Starting a new project, a
  new domain inside one, or a structural piece of work: walk the user
  through the relevant settled decisions one at a time (state the
  convention, apply it, move on) instead of silently picking an approach or
  dumping the whole decision set on the user at once.
- **Land every substantive discussion back in the framework.** When a
  conversation settles how something should be done — not just for the
  project at hand, but as a reusable rule — propose, before the task ends,
  where that belongs (a new or edited skill under `skills/`, a bullet in
  `AGENTS.md`, a `rules/` override) and write it. Don't wait to be told to
  "save this for next time"; a decision that only lives in this
  conversation's transcript is a decision the user will have to repeat.
- **Keep `skills/BACKLOG.md` current without being told.** The user should
  never have to say "add this to the backlog." Whenever a gap, loose end, or
  deferred piece of work surfaces — in this conversation or while doing
  unrelated work and noticing something else is incomplete — add it to the
  Open section yourself, in the same turn, with enough context to act on it
  later without re-deriving why it matters. Move an item to Done (naming the
  skill/file that resolved it) the moment it's actually finished, not later.
- **Prefer an existing, well-maintained package over inventing the
  mechanism — but never adopt one unilaterally.** Before writing a
  from-scratch implementation for a concern a domain skill governs (a
  linter, a formatter, a scaffolding tool, ...), check whether a
  widely-used package already does it well, and propose it to the user
  with the alternative(s) considered — do not silently pick one and move
  on, even an obvious default. Only once the user confirms it, record its
  name directly in the governing skill (the implementation tier, not just
  this file) so the next project reaches for it immediately instead of the
  question being re-researched. This is itself a "land it back in the
  framework" case — the package name is the reusable fact, not a one-off
  library choice for a single project.
- **Keep the dependency chain explicit.** A domain's knowledge is layered,
  not flat, and each skill should name what it builds on and what reads it
  next so the agent (and the user, skimming `skills/`) never has to guess
  the order:
  1. *Concept* — the platform/technology-agnostic rules for a whole domain
     (e.g. `skills/frontend-styling-concept/SKILL.md`: what must be true
     regardless of which rendering engine is involved).
  2. *Implementation* — one skill per concrete technology/platform that
     satisfies the concept (e.g. `skills/frontend-web-styles/SKILL.md` for
     browser/Electron/Tauri). A domain can have several of these; each
     names which concept it implements. When more than one implementation
     exists for the same platform/row (e.g. CSS Modules today, Tailwind in
     some future project), the concept skill marks exactly one as the
     default — proposed first for new work, not re-decided per project.
     Pick a non-default only when the project states a concrete reason;
     settle it once for that project, don't re-ask on later tasks in it.
     A new technology encountered for the first time gets written up as
     its own implementation skill, the same shape as the existing ones,
     so every later project on that technology is handled identically.
  3. *Guided setup* — a step-by-step walkthrough for starting new work in
     the domain, applying 1 and 2 without re-deciding them (e.g.
     `skills/frontend-project-setup/SKILL.md`).
  4. *Day-to-day* — the implementation skill doubles as the ongoing
     reference once setup is done; no separate tier needed unless a domain
     proves otherwise.
  This shape (concept → implementation → guided setup) is not specific to
  frontend work — it is this framework's standard shape for any domain
  (backend, architecture, infra, testing, ...), sitting below the single
  entry point `skills/stack-selection/SKILL.md`. Build a new domain's
  knowledge the same way once real work in it starts; do not pre-build
  tiers for a domain nothing has touched yet.
- Each skill's own text should say, briefly, what it implements and what
  implements it (as the frontend skills already do), so reading one skill
  in isolation still shows the chain without opening the others first.
- **Graph trigger — mechanical, not optional.** `skills/GRAPH.md` is the
  framework's one shallow overview: top-level domains/entry points only
  (e.g. `stack-selection`, `frontend-styling-concept`, the `repo-*`
  lifecycle group), each linking onward — it changes only when a new
  domain/entry point appears. Below that, the structure is a recursive
  index, not a fixed two-level one: any skill that gains its first child
  (another skill states it implements/extends/is-set-up-by this one) gets
  its own `GRAPH.md`, inside that skill's own folder (`skills/` itself
  stays flat, one directory per skill, grouped only by name prefix — e.g.
  `frontend-*` — never a real subdirectory: `agent_setup.py`'s
  `connect_skills()` scans `skills/` one level deep and symlinks a skill
  only when `SKILL.md` sits directly inside it, so a nested
  `skills/frontend/code-style/SKILL.md` would silently never get
  installed; this is a logical child list, not a filesystem one), listing
  only its direct children. A skill with no children needs no `GRAPH.md`;
  its own "implements / read next" lines are enough. Whenever adding a new
  skill that builds on an existing one:
  1. Check whether that existing skill already has a `GRAPH.md`.
  2. No `GRAPH.md` yet → create one there, listing every current direct
     child (the new one plus any already named in that skill's own text).
  3. `GRAPH.md` already exists → add the new child to it.
  4. If the new skill is itself a new top-level domain/entry point, also
     add one line to `skills/GRAPH.md`.
  Do this in the same change that adds the skill — never leave it for a
  reminder, and never skip it because the addition feels small.
- **Project-level overrides live with the project, not the framework.**
  A specific project may settle on something other than this framework's
  recorded default (a team's existing Tailwind codebase, a pre-existing
  commit-message convention). That choice is recorded once in that
  project's own data (`.agents/` notes — see `global/project-rules.md` and
  `skills/repo-init/SKILL.md`), not by editing the framework's default.
  The framework default stays what most new projects should get; a
  project's override is read first and shadows it for that project only.
- **Revising or retiring a skill — this framework accumulates, but it
  also corrects.** A skill is wrong exactly as often as any other written
  conclusion; nothing here is write-once.
  - **Revise in place** when the core approach is still right and only a
    detail was wrong or incomplete (a missing edge case, a stale version
    number, a breakpoint that should differ) — edit the skill directly,
    no status change, no new file.
  - **Retire and replace** when the core approach itself turned out wrong
    for its stated scope, or a better default should take over for new
    work — the triggers are: real use (e.g. the dogfooding in
    `skills/BACKLOG.md`) contradicted the written rule; the user states
    the default was a mistake after trying it; or the underlying
    technology/platform made the rule moot. Mechanically:
    1. Add a short line near the top of the old skill:
       `Deprecated — superseded by <new-skill>, <date>: <one-line reason>`.
       Keep the file; don't delete it — existing `decisions/*.md` entries
       and project history may still point to it, and the line itself is
       the record of *why* the framework changed its mind.
    2. Write the replacement as its own skill, same shape as the one it
       replaces (per the concept/implementation/setup tiering above).
    3. Update whichever concept skill's "default" table named the old one
       (e.g. `frontend-styling-concept`'s per-platform default row), and
       `project-profile.md`'s "Governed by" column plus every skill's own
       "Governs" line that pointed at the old skill.
    4. Run `skills/framework-lint/SKILL.md`'s check after any of the
       above — a retirement is exactly the kind of change that leaves
       dangling references.
  - A revision or retirement is itself a substantive discussion — land it
    per the "land every substantive discussion back in the framework"
    rule above; don't let a correction live only in the conversation that
    prompted it.
- **Migrating an existing project onto a framework default — alias,
  don't big-bang.** Moving a real project from its own override to this
  framework's default (e.g. SCSS+BEM → CSS Modules) touches many files;
  doing it as one atomic change risks breaking everything unmigrated at
  once, and stalls if interrupted partway.
  - Migrate one unit at a time (one component, one feature), the same
    size as whatever this framework's implementation skill already
    treats as the colocation unit.
  - When the new unit needs something the old shared resource still
    provides to not-yet-migrated units (e.g. a renamed design token),
    add it as a **backward-compatible alias** in the new resource
    pointing at the new name/shape — do not delete the old resource
    until nothing references it anymore. Mark each alias with a comment
    naming what it is and that it's temporary.
  - Track the migration itself as a `skills/BACKLOG.md` entry: what's
    migrated, what's left, and an explicit final step — "remove the
    aliases/legacy file once every unit is migrated and verified." A
    migration is not done while an alias from it still exists; don't
    let that cleanup step get silently forgotten once the visible work
    stops.
  - This is the general shape; the current concrete case is my-world's
    SCSS → CSS Modules move (see `skills/BACKLOG.md`).
- **External justification freshness.** A convention justified by "the
  industry does X" needs an actual, dated external check — not the
  agent's own unaided reasoning, and not a justification that quietly
  goes stale.
  - When a decision rests on external best practice (not a forced or
    trivial choice), record it in the governing skill as its own
    `## Basis (checked YYYY-MM-DD)` section: the sources (as links) and a
    one-line summary of what each says, same shape as
    `frontend-styling-concept`'s "Basis" section.
  - Before deciding a new question in the same area, find the governing
    skill (via `skills/GRAPH.md`'s routing) and check its `Basis` date:
    - **Dated within the current month** — apply it directly, telling
      the user what's being applied and its date; do not re-research
      from scratch.
    - **Missing, or older than about a month** — say so to the user,
      then research it fresh (current sources, not memory) before
      deciding, and write or update the `Basis` section with the new
      date and sources.
  - This sits underneath, not instead of, "never adopt a package/pattern
    unilaterally" above — the freshness check decides *what's current*;
    the user still confirms the resulting choice.
  - `skills/knowledge-refresh/SKILL.md` runs this check systematically:
    for one named topic, or as a full sweep across every skill's `Basis`
    section. Both modes are user-triggered, not an autonomous schedule —
    see that skill for what "stale" means in the sweep and what it does
    with the results.
