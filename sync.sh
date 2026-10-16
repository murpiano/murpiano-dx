#!/usr/bin/env bash
# Keeps project agent files and Claude Code memory in murpiano-dx and in the cloud.
#
# Usage:
#   bash sync.sh start   SessionStart hook: pull, link the session's project, push leftovers
#   bash sync.sh end     SessionEnd hook: adopt new agent files of the session's project, push
#   bash sync.sh link    link every project under PROJECTS_DIR, no network
#   bash sync.sh         pull, adopt and link the project in the current folder, push
#
# The hooks pass JSON with "cwd" on stdin. Without it the current folder is used.
# The script never blocks a session: it always exits 0 and reports problems on stderr.

set -uo pipefail

dx=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=config.env
source "$dx/config.env"
projects_dir=${PROJECTS_DIR:-$HOME/projects}
store="$dx/projects"
patterns="$dx/skills/repo-cleanup/gitignore-agents"
mode=${1:-manual}
notes=()

say() { echo "murpiano-dx: $*" >&2; }

# Project key: owner/repo from the origin remote. A project without origin is not synced,
# so an unrelated folder with the same name never picks up another project's files.
project_key() {
  local url
  url=$(git -C "$1" remote get-url origin 2>/dev/null) || return 1
  url=${url%/}
  url=${url%.git}
  url=${url/#*@*:/x/} # git@host:owner/repo -> x/owner/repo
  local repo owner
  repo=$(basename "$url")
  owner=$(basename "$(dirname "$url")")
  [ -n "$repo" ] && [ -n "$owner" ] || return 1
  printf '%s/%s' "$owner" "$repo"
}

# Claude Code keeps memory in ~/.claude/projects/<path with every non-alphanumeric as ->/memory.
memory_dir() {
  printf '%s/.claude/projects/%s/memory' "$HOME" "$(printf '%s' "$1" | sed 's/[^A-Za-z0-9]/-/g')"
}

# Agent file paths present in a project, one per line, relative to its root.
agent_paths() {
  local root=$1 pattern
  while IFS= read -r pattern; do
    [[ -z "$pattern" || "$pattern" == \#* ]] && continue
    pattern=${pattern%/}
    (cd "$root" && compgen -G "$pattern") || true
  done <"$patterns"
}

# Move untracked agent files of a project into the store and leave symlinks behind.
adopt() {
  local root=$1 key=$2 path target
  while IFS= read -r path; do
    [ -L "$root/$path" ] && continue
    if [ -n "$(git -C "$root" ls-files -- "$path" 2>/dev/null)" ]; then
      continue # committed on purpose, leave it in the project
    fi
    target="$store/$key/files/$path"
    if [ -e "$target" ]; then
      say "$key: $path exists in the project and in murpiano-dx; left as is, merge by hand"
      continue
    fi
    mkdir -p "$(dirname "$target")"
    mv "$root/$path" "$target" && ln -s "$target" "$root/$path"
    notes+=("$key: moved $path into murpiano-dx")
  done < <(agent_paths "$root")

  local memory
  memory=$(memory_dir "$root")
  if [ -d "$memory" ] && [ ! -L "$memory" ]; then
    target="$store/$key/memory"
    if [ -e "$target" ]; then
      say "$key: memory exists locally and in murpiano-dx; left as is, merge by hand"
    else
      mkdir -p "$store/$key"
      mv "$memory" "$target" && ln -s "$target" "$memory"
    fi
  fi
}

# Create symlinks in a project for every agent path the store holds for it.
link() {
  local root=$1 key=$2 path file link_path linked=0
  [ -d "$store/$key" ] || return 0
  if [ -d "$store/$key/files" ]; then
    while IFS= read -r path; do
      file="$store/$key/files/$path"
      link_path="$root/$path"
      if [ -L "$link_path" ]; then
        [ "$(readlink "$link_path")" = "$file" ] && continue
        rm "$link_path"
      elif [ -e "$link_path" ]; then
        say "$key: $path already exists in the project; not replaced"
        continue
      fi
      mkdir -p "$(dirname "$link_path")"
      ln -s "$file" "$link_path"
      linked=1
    done < <(agent_paths "$store/$key/files")
  fi
  if [ -d "$store/$key/memory" ]; then
    local memory
    memory=$(memory_dir "$root")
    if [ ! -e "$memory" ]; then
      mkdir -p "$(dirname "$memory")"
      ln -s "$store/$key/memory" "$memory"
    fi
  fi
  [ "$linked" = 1 ] && notes+=("$key: project agent files linked from murpiano-dx. Read CLAUDE.md and .agents/ of this project before starting.")
  return 0
}

# This repo's hooks directory: plain .git/hooks, or husky's folder if core.hooksPath is set.
hooks_dir() {
  local root=$1 rel
  rel=$(git -C "$root" rev-parse --git-path hooks 2>/dev/null) || return 1
  case "$rel" in
    /*) printf '%s' "$rel" ;;
    *) printf '%s/%s' "$root" "$rel" ;;
  esac
}

precommit_marker='# murpiano-dx: agent-trace pre-commit scan (skills/repo-cleanup)'

# Install the agent-trace pre-commit scanner for a tracked project. Idempotent: skipped if
# already installed, left alone if the project has its own unrelated pre-commit hook.
install_precommit_hook() {
  local root=$1 key=$2 dir target
  dir=$(hooks_dir "$root") || return 0
  target="$dir/pre-commit"
  if [ -e "$target" ]; then
    grep -qF "$precommit_marker" "$target" 2>/dev/null && return 0
    say "$key: pre-commit hook already exists; not replaced. Agent-trace scan: bash $dx/skills/repo-cleanup/pre-commit-hook.sh"
    return 0
  fi
  mkdir -p "$dir"
  { echo '#!/usr/bin/env bash'; echo "$precommit_marker"; echo "exec bash \"$dx/skills/repo-cleanup/pre-commit-hook.sh\""; } >"$target"
  chmod +x "$target"
  notes+=("$key: pre-commit hook installed. Every commit is scanned for agent traces and secrets before it is made (skills/repo-cleanup/policy.md); a false positive commits with --no-verify.")
}

# Note if the project depends on kysaro but this machine has no commit-msg hook for it.
check_kysaro_hook() {
  local root=$1 key=$2 dir
  [ -f "$root/package.json" ] || return 0
  grep -q '"kysaro"' "$root/package.json" 2>/dev/null || return 0
  dir=$(hooks_dir "$root") || return 0
  [ -e "$dir/commit-msg" ] && return 0
  notes+=("$key: package.json lists kysaro, but this machine has no commit-msg hook for it. Run \`npx kysaro init\` here; a bad commit message currently would not be blocked. If the hook should survive a fresh clone, set up husky first: \`npx husky init\`.")
}

pull() {
  git -C "$dx" diff --quiet && git -C "$dx" diff --cached --quiet || commit
  if ! timeout 20 git -C "$dx" pull --quiet --rebase --autostash >/dev/null 2>&1; then
    git -C "$dx" rebase --abort 2>/dev/null
    say "pull failed (offline or conflict); working with the local copy"
  fi
}

commit() {
  git -C "$dx" add -A projects
  git -C "$dx" diff --cached --quiet && return 0
  local keys
  keys=$(git -C "$dx" diff --cached --name-only | awk -F/ 'NF > 3 {print $2 "/" $3}' | sort -u | paste -sd, - | sed 's/,/, /g')
  git -C "$dx" commit --quiet -m "chore(sync): update ${keys:-project store} from $(hostname)" || say "commit failed"
}

push() {
  commit
  [ -z "$(git -C "$dx" log --oneline '@{u}..' 2>/dev/null)" ] && return 0
  timeout 20 git -C "$dx" push --quiet 2>/dev/null || say "push failed; it will be retried at the next session start"
}

# The session folder from the hook's stdin JSON, or $PWD without it.
session_cwd() {
  local cwd=""
  if [ ! -t 0 ]; then
    cwd=$(python3 -c 'import json, sys
try: print(json.load(sys.stdin).get("cwd", ""))
except Exception: pass' 2>/dev/null)
  fi
  printf '%s' "${cwd:-$PWD}"
}

# The project of this run: git root of the session folder, never murpiano-dx itself.
session_root() {
  local root
  root=$(git -C "$(session_cwd)" rev-parse --show-toplevel 2>/dev/null) || return 1
  [ "$root" = "$dx" ] && return 1
  printf '%s' "$root"
}

exec 9>"$dx/.git/murpiano-dx.lock"
flock -w 30 9 || { say "another sync is running"; exit 0; }

case "$mode" in
  start)
    pull
    cwd=$(session_cwd)
    root=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null)
    if [ -n "$root" ] && [ "$root" != "$dx" ]; then
      if key=$(project_key "$root"); then
        link "$root" "$key"
        adopt "$root" "$key"
        install_precommit_hook "$root" "$key"
        check_kysaro_hook "$root" "$key"
      else
        notes+=("This project has a git repository but no GitHub origin, so murpiano-dx does not track it yet: no agent-trace cleanup, no releases (commit convention is kysaro's job, set up per project). Ask the user whether to create a GitHub repository for it (private by default, so the history stays but isn't public: \`gh repo create --private --source=. --remote=origin\`), then run \`bash $dx/sync.sh\` once to link it.")
      fi
    elif [ -z "$root" ]; then
      notes+=("This folder has no git repository, so murpiano-dx does not track it: no commit history, no agent-trace cleanup, no releases. Ask the user whether to start one now, before more work piles up: \`git init\`, a first commit, then a GitHub repository (private by default: \`gh repo create --private --source=. --remote=origin --push\`), then run \`bash $dx/sync.sh\` once to link it.")
    fi
    push
    ;;
  end)
    if root=$(session_root) && key=$(project_key "$root"); then
      adopt "$root" "$key"
    fi
    push
    ;;
  link)
    for root in "$projects_dir"/*/; do
      root=${root%/}
      if [ -d "$root/.git" ] && [ "$root" != "$dx" ] && key=$(project_key "$root"); then
        link "$root" "$key"
        install_precommit_hook "$root" "$key"
        check_kysaro_hook "$root" "$key"
      fi
    done
    ;;
  *)
    pull
    if root=$(session_root) && key=$(project_key "$root"); then
      adopt "$root" "$key"
      link "$root" "$key"
      install_precommit_hook "$root" "$key"
      check_kysaro_hook "$root" "$key"
    fi
    push
    ;;
esac

for note in "${notes[@]}"; do
  echo "$note"
done
exit 0
