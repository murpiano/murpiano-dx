#!/usr/bin/env bash
# Scans arbitrary text (a PR/release-notes body, not a file in the repo) for
# agent-trace mentions. scan-traces.sh and the commit hooks only see files and
# commit messages -- a PR description passed straight to `gh pr create --body`
# or `gh pr edit --body` never touches a git hook at all, so nothing else
# catches it. Patterns follow policy.md next to this script.
#
# Usage: check-text.sh <file>   (read text from a file)
#        check-text.sh -        (read text from stdin)
# Exit:  0 no findings, 1 findings to review, 2 usage error.

set -uo pipefail
export LC_ALL=C.UTF-8

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=patterns.sh
source "$script_dir/patterns.sh"

input=${1:-}
if [ -z "$input" ]; then
  echo "usage: check-text.sh <file>|-" >&2
  exit 2
fi

if [ "$input" = "-" ]; then
  findings=$(grep -inE "$TEXT")
else
  [ -f "$input" ] || { echo "no such file: $input" >&2; exit 2; }
  findings=$(grep -inE "$TEXT" "$input")
fi

if [ -z "$findings" ]; then
  exit 0
fi
echo "[murpiano-dx] Agent-trace mention(s) found:" >&2
printf '%s\n' "$findings" | cut -c1-200 >&2
echo "Review: $script_dir/policy.md, section 3." >&2
exit 1
