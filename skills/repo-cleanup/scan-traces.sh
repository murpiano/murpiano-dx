#!/usr/bin/env bash
# Read-only scan of a git repository and its GitHub remote for traces of AI-agent tooling
# and for committed secrets.
# Patterns follow policy.md next to this script.
#
# Usage: bash scan-traces.sh [repo-dir] [--no-github] [--published]
#        --published  scan only remote branches and tags, not local-only refs
# Exit:  0 no findings, 1 findings to review, 2 usage error.

set -uo pipefail
export LC_ALL=C.UTF-8

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=.
github=1
refs=--all
for arg in "$@"; do
  case "$arg" in
    --no-github) github=0 ;;
    --published) refs='--remotes --tags' ;;
    -h | --help) sed -n 2,9p "$0"; exit 0 ;;
    *) repo=$arg ;;
  esac
done

cd "$repo" 2>/dev/null || { echo "cannot open $repo"; exit 2; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repository: $repo"; exit 2; }

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

section 'Tracked agent files' "$(git ls-files | grep -E "$FILES")"
section 'Agent files anywhere in history' \
  "$(git log $refs --format= --name-only | sort -u | grep -E "$FILES")"
section 'Agent mentions in tracked text files' \
  "$(git grep -nIiE "$TEXT" -- . "${LOCKS[@]}" | cut -c1-200 | head -100)"
section 'Agent mentions in commit messages' \
  "$(git log $refs --format='%x00%h%x09%s %b' | tr '\n\0' ' \n' | grep -iE "$TEXT" | cut -c1-200)"
section 'Emoji in commit subjects' "$(git log $refs --format='%h %s' | grep -P "$EMOJI")"
section 'Agent or bot identities in authors and committers' \
  "$(git log $refs --format='%an <%ae>%n%cn <%ce>' | sort -u | grep -iE "$IDENTITY")"
section 'Agent-style branch names' \
  "$(git branch $([ "$refs" = --all ] && echo -a || echo -r) --format='%(refname:short)' | grep -iE "$BRANCH")"

identities=$(git log $refs --format='%an <%ae>%n%cn <%ce>' | sort -u)
printf '== Author and committer identities (review: should be one)\n%s\n\n' "$identities"
[ "$(printf '%s\n' "$identities" | wc -l)" -gt 1 ] && findings=$((findings + 1))

# Secrets. Output names the place only, never the matched value.
section 'Secret files tracked or in history' \
  "$(git log $refs --format= --name-only | sort -u | grep -E "$SECRET_FILES" | grep -vE "$SECRET_FILES_OK")"
section 'Secrets in tracked text files (path:line)' \
  "$(git grep -nIiE -e "$SECRET_TEXT" -- . "${LOCKS[@]}" | cut -d: -f1,2 | head -100)"
section 'Secrets anywhere in history (commits adding or removing them)' \
  "$(git log $refs -i -G "$SECRET_TEXT" --format='%h %s' -- . "${LOCKS[@]}" | cut -c1-200)"

remote=$(git remote get-url origin 2>/dev/null || true)
if [ "$github" = 1 ] && [[ "$remote" == *github.com* ]] && command -v gh >/dev/null; then
  slug=$(printf '%s' "$remote" | sed -E 's#(\.git)?$##; s#.*github\.com[:/]##')
  section 'Pull requests: title, body or branch' \
    "$(gh api "repos/$slug/pulls?state=all&per_page=100" --paginate \
      -q '.[] | "#\(.number)\t\(.head.ref)\t\(.title)\t\((.body // "") | gsub("\n"; " "))"' 2>/dev/null |
      grep -iP "$TEXT|$EMOJI|\t(claude|copilot|codex|cursor|devin|ai|agent)[/-]" | cut -c1-200)"
  section 'Releases: name or notes' \
    "$(gh api "repos/$slug/releases?per_page=100" --paginate \
      -q '.[] | "\(.tag_name)\t\(.name)\t\((.body // "") | gsub("\n"; " "))"' 2>/dev/null |
      grep -iP "$TEXT|$EMOJI" | cut -c1-200)"
  section 'Comments by bots' \
    "$(gh api "repos/$slug/issues/comments?per_page=100" --paginate \
      -q '.[] | select(.user.type == "Bot") | "\(.user.login)\t\(.html_url)"' 2>/dev/null)"
  heads=$(git ls-remote origin 'refs/pull/*/head' 2>/dev/null | wc -l)
  [ "$heads" -gt 0 ] && printf '== Note\nGitHub keeps %s pull request heads with their original commits. Only GitHub Support can remove them.\n\n' "$heads"
fi

if [ "$findings" -eq 0 ]; then
  echo 'No agent traces or secrets found.'
  exit 0
fi
echo "Findings to review: $findings"
exit 1
