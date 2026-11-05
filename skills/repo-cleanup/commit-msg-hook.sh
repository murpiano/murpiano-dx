#!/usr/bin/env bash
# Installed by murpiano-dx (sync.sh) wrapping this repository's commit-msg hook.
# Scans the commit message text itself for agent-trace mentions -- the one
# thing pre-commit-hook.sh cannot see, since git only finalizes the message
# after pre-commit runs. Fast and local only: the message file git passes in,
# no history, no network. Patterns follow policy.md next to this script.
#
# Usage: commit-msg-hook.sh <path-to-message-file>

set -uo pipefail
export LC_ALL=C.UTF-8

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=patterns.sh
source "$script_dir/patterns.sh"

message_file=$1
findings=$(grep -inE "$TEXT" "$message_file" | cut -c1-200 | head -20)

if [ -z "$findings" ]; then
  exit 0
fi
echo "[murpiano-dx] Commit blocked: agent-trace mention(s) in the commit message." >&2
printf '%s\n' "$findings" >&2
echo "Review: $script_dir/policy.md, section 3." >&2
echo "False positive: commit with --no-verify." >&2
exit 1
