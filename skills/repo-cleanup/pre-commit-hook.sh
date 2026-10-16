#!/usr/bin/env bash
# Installed by murpiano-dx (sync.sh) as this repository's pre-commit hook.
# Blocks a commit on main or master: work goes to a topic branch (skill repo-commit).
# Blocks a commit that stages an agent file, an agent mention or a secret.
# Fast and local only: staged files and the staged diff, no history, no network.
# Patterns follow policy.md in this folder. Edit there, not per project.

set -uo pipefail
export LC_ALL=C.UTF-8

# Commits on the default branch. Allowed: the first commit of a repository, the commit that
# concludes a merge, and MURPIANO_ON_MAIN=1 when the user asked for this commit on main.
branch=$(git branch --show-current 2>/dev/null)
if { [ "$branch" = main ] || [ "$branch" = master ]; } &&
  git rev-parse -q --verify HEAD >/dev/null &&
  [ ! -e "$(git rev-parse --git-path MERGE_HEAD)" ] &&
  [ "${MURPIANO_ON_MAIN:-}" != 1 ]; then
  cat >&2 <<EOF
[murpiano-dx] Commit blocked: you are on $branch. Work goes to a topic branch.
Look at the staged and unstaged changes and propose a branch to the user:
<type>/<short-name>, for example feat/dark-theme or fix/login-timeout
(skill repo-commit, section 6 of its rules.md). If the changes cover several
topics, propose one branch per topic. After the user agrees:
  git switch -c <branch>    # uncommitted changes move along
and commit again. Commit on $branch only if the user asked for it:
  MURPIANO_ON_MAIN=1 git commit ...
EOF
  exit 1
fi

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=patterns.sh
source "$script_dir/patterns.sh"

findings=0
section() {
  local title=$1 output=$2
  if [ -n "$output" ]; then
    findings=$((findings + $(printf '%s\n' "$output" | wc -l)))
    printf '== %s\n%s\n\n' "$title" "$output"
  fi
}

staged_files=$(git diff --cached --name-only --diff-filter=ACMR)

section 'Staged agent files' "$(printf '%s\n' "$staged_files" | grep -E "$FILES")"
section 'Staged secret files' \
  "$(printf '%s\n' "$staged_files" | grep -E "$SECRET_FILES" | grep -vE "$SECRET_FILES_OK")"
section 'Agent mentions in the staged diff (path:line)' \
  "$(git diff --cached -U0 -- . "${LOCKS[@]}" | awk '
    /^\+\+\+ b\// { file = substr($0, 7); next }
    /^@@/ { match($0, /\+[0-9]+/); line = substr($0, RSTART + 1, RLENGTH - 1) + 0; next }
    /^\+/ { print file ":" line ": " substr($0, 2); line++ }
  ' | grep -iE "$TEXT" | cut -c1-200 | head -100)"
section 'Secrets in the staged diff (path only, value withheld)' \
  "$(git diff --cached --name-only -G "$SECRET_TEXT" -- . "${LOCKS[@]}")"

if [ "$findings" -eq 0 ]; then
  exit 0
fi
echo "[murpiano-dx] Commit blocked: $findings agent-trace or secret finding(s)." >&2
echo "Review with: bash $script_dir/scan-traces.sh . --no-github" >&2
echo "False positive: commit with --no-verify." >&2
exit 1
