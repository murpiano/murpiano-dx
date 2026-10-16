#!/usr/bin/env bash
# Installed by murpiano-dx (sync.sh) as this repository's pre-commit hook.
# Blocks a commit that stages an agent file, an agent mention or a secret.
# Fast and local only: staged files and the staged diff, no history, no network.
# Patterns follow policy.md in this folder. Edit there, not per project.

set -uo pipefail
export LC_ALL=C.UTF-8

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
