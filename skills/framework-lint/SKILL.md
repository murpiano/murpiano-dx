---
name: framework-lint
description: Use after adding, renaming, or editing any skill under skills/, or before considering a framework-structure change finished — verify skills/ has no broken links, no orphaned skills, and no mismatch between a skill's "Governs" line and project-profile.md's "Governed by" column. Not for linting project code; this only checks murpiano-dx's own skills/.
---

# Framework self-lint

Scope: catches drift in murpiano-dx's own cross-references — the ones
built by hand across `GRAPH.md` files, `[links](...)`, and the
`project-profile.md` ↔ skill "Governs" pairing. Written because those
references are maintained manually and will silently rot as skills are
renamed, split, or retired (see `skills/DELEGATION-MODEL.md` and
`skills/BACKLOG.md` → skill revision/retirement).

## Running it

```sh
python3 skills/framework-lint/scripts/lint.py
```

Run from the `murpiano-dx` checkout; `--skills-root <path>` points it at
a different `skills/` directory (mainly for testing the linter itself).
Exit code `0` and a pass message mean clean; exit code `1` prints each
problem to stderr.

## What it checks

1. **Frontmatter** — every `skills/<name>/SKILL.md` has a `name:` field
   matching its directory name, and a non-empty `description:`.
2. **Relative links** — every `[text](path)` or `![alt](path)` inside a
   `.md` file under `skills/` resolves to a real file, except:
   - links to `http(s)://` or `mailto:` (external, not checked),
   - links inside anything under a `templates/` directory (those
     describe a future *project's* structure, not this framework's —
     see `skills/project-profile/templates/`, `skills/repo-readme/templates/`),
   - a target containing `<` or `>` (a `<placeholder>` path, not a real
     file).
3. **Orphan skills** — every skill directory's name must appear
   backtick-quoted (`` `name` ``) in at least one `GRAPH.md` somewhere
   under `skills/`. A skill nobody's `GRAPH.md` mentions is unreachable
   from the overview graph — see `skills/GRAPH.md`'s own graph-trigger
   rule in `DELEGATION-MODEL.md`.
4. **Governs cross-reference** — a skill's `SKILL.md` "Governs
   `project-profile.md` fields: ..." line and
   `project-profile/templates/project-profile.md`'s "Governed by" column
   must name each other for the same field, in both directions.

## What it does not check (yet)

Semantic correctness of a skill's content, whether a concept's "default"
marking is still right, or whether `.agents/project-profile.md` files in
actual connected projects match the current template shape. These stay
manual review for now — see `skills/BACKLOG.md`.

## When to run it

- After adding a skill, splitting one, or renaming/moving a `SKILL.md`.
- After editing any `GRAPH.md` or a "Governs" line.
- Before telling the user a framework-structure change is complete —
  this is the automatic half of that check, the same way
  `superpowers:verification-before-completion` asks for evidence before
  claiming project code works.
