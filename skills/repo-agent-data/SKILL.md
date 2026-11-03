---
name: repo-agent-data
description: Move existing project agent instructions, notes, and settings into murpiano-dx and remove them from future project commits while preserving local access. Use when asked to migrate agent data or clean an existing project for publication.
---

# Centralize existing agent data

Use for an explicit request to move existing agent files out of a project's
published tree. Ordinary development does not run this migration.

1. Run `sync.sh start` and read the returned project data path. If the project is
   not connected, use `repo-init` within the owner's requested setup scope.
2. Preview the migration:
   `python3 <murpiano-dx>/skills/repo-agent-data/scripts/migrate.py <project>`.
   It lists known agent metadata paths, their storage destinations, and tracked
   files that would be removed from the project index. Preview does not write.
3. Inspect the listed paths. Keep product documentation, CI, Kysaro settings, and
   code in the project. Do not copy credentials or access tokens into project
   memory. Split mixed-purpose files before migrating them. Custom notes such as
   `docs/plans` or `memory` require explicit `--path <relative-path>` arguments;
   each `--path` adds to the default candidates.
4. Apply the reviewed plan with `--apply` when the request authorizes migration.
   The helper copies data to `projects/OWNER/REPO/`, checks SHA-256 hashes and file
   modes, replaces local files with excluded links, and removes tracked metadata
   from the Git index. Existing different destination data, staged edits to the
   selected files, or unsafe links stop the operation without overwriting data.
5. Review `git diff --cached --name-status`, the local links, and the migration
   report at `projects/OWNER/REPO/agent-data-migration.json`. Run project checks.
   Search relevant current files for leftover workflow notes and attribution;
   assess matches manually. Legitimate product references to AI stay.

The helper makes no commits, pushes, or history changes. Commit the reviewed
removals with `repo-commit` when authorized. Data in old commits, releases, PRs,
or external copies remains; history cleanup is a separate explicit request.
Do not claim every possible trace was found by scanning known filenames.

## Recovery

The migration report records each source, destination, and original tracked
paths. Verified data stays at the destination. To undo a move, replace only its
generated link with a copy of the stored file or directory. Preserve the stored
copy, then re-add originally tracked paths if the owner wants them published
again. Review the resulting diff before committing.

After verification, run `sync.sh end` only when the configured workspace backup
is appropriate for these files. It may commit and push the workspace. Never run
this migration against the public framework itself to move product instructions.
