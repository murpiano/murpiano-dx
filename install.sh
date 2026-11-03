#!/usr/bin/env bash
# Connect local instructions. Release credentials are a separate explicit action.
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
bin_home="${XDG_BIN_HOME:-$HOME/.local/bin}"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}/murpiano-dx"
config_file="$config_home/config.env"

gh_value() {
  command -v gh >/dev/null 2>&1 || return 0
  gh api user --jq "$1" 2>/dev/null || true
}

setup_config() {
  [ -t 0 ] || return 0
  if [ -f "$config_file" ]; then
    return 0
  fi
  local gh_login gh_name gh_id default_name default_email default_owner name email owner
  gh_login="$(gh_value '.login')"
  gh_name="$(gh_value '.name')"
  gh_id="$(gh_value '.id')"
  default_owner="${gh_login:-}"
  default_name="${gh_name:-$gh_login}"
  default_email="$(git config --global user.email 2>/dev/null || true)"
  if [ -z "$default_email" ] && [ -n "$gh_id" ] && [ -n "$gh_login" ]; then
    default_email="${gh_id}+${gh_login}@users.noreply.github.com"
  fi
  echo 'Initial murpiano-dx setup. Values are stored locally only.'
  read -r -p "Git name [${default_name}]: " name
  read -r -p "Email Git [${default_email}]: " email
  read -r -p "GitHub owner [${default_owner}]: " owner
  name="${name:-$default_name}"
  email="${email:-$default_email}"
  owner="${owner:-$default_owner}"
  [ -n "$name" ] && [ -n "$email" ] && [ -n "$owner" ] || {
    echo 'Name, email, and GitHub owner are required.' >&2
    return 1
  }
  mkdir -p "$config_home"
  (umask 077; {
    printf 'GIT_NAME=%q\n' "$name"
    printf 'GIT_EMAIL=%q\n' "$email"
    printf 'GITHUB_OWNER=%q\n' "$owner"
  } >"$config_file")
  chmod 600 "$config_file"
  echo "Local settings saved: $config_file"
}
install_command() {
  local workspace="$1"
  mkdir -p "$bin_home"
  ln -sfn "$workspace/murpiano-dx" "$bin_home/murpiano-dx"
  echo "Command installed: $bin_home/murpiano-dx"
}

workspace_path() {
  if [ -n "${MURPIANO_DX_DATA_DIR:-}" ]; then
    printf '%s\n' "$MURPIANO_DX_DATA_DIR"
  elif [ -f "$root/config/machine.json" ]; then
    printf '%s\n' "$root"
  else
    printf '%s\n' "$HOME/.murpiano-dx"
  fi
}

restore_workspace() {
  local remote="${1:-}" target="${2:-$(workspace_path)}" owner
  if [ -z "$remote" ]; then
    command -v gh >/dev/null 2>&1 || {
      echo 'GitHub CLI (gh) is required for restore.' >&2
      exit 1
    }
    owner="${GITHUB_OWNER:-$(gh api user --jq '.login' 2>/dev/null || true)}"
    [ -n "$owner" ] || {
      echo 'Could not determine the GitHub owner. Set GITHUB_OWNER or pass a repository URL.' >&2
      exit 1
    }
    if gh repo view "$owner/murpiano-dx-workspace" --json name >/dev/null 2>&1; then
      remote="git@github.com:$owner/murpiano-dx-workspace.git"
    else
      remote="git@github.com:$owner/murpiano-dx-private.git"
    fi
  fi
  [ ! -e "$target" ] || { echo "Workspace already exists: $target" >&2; exit 1; }
  git clone "$remote" "$target"
  MURPIANO_DX_DATA_DIR="$target" bash "$target/install.sh"
}
case "${1:-}" in
  '')
    setup_config
    if [ -f "$config_file" ]; then
      # shellcheck disable=SC1090
      source "$config_file"
    elif [ -z "${GIT_NAME:-}" ] && [ -z "${GIT_EMAIL:-}" ] && [ -z "${GITHUB_OWNER:-}" ]; then
      # shellcheck disable=SC1091
      source "$root/config.env"
    fi
    export GITHUB_OWNER GIT_NAME GIT_EMAIL
    workspace="$(workspace_path)"
    export MURPIANO_DX_DATA_DIR="$workspace"
    MURPIANO_DX_DATA_DIR="$workspace" python3 "$root/sync.py" workspace
    install_command "$workspace"
    python3 "$workspace/agent_setup.py" "$workspace" "$root"
    python3 "$workspace/workspace_sync.py" --configure-remote "$workspace"
    echo "Done. Ask your coding agent to read $workspace/AGENTS.md and initialize the project."
    ;;
  --restore)
    shift
    restore_workspace "$@"
    ;;
  --release-token)
    token_file="$HOME/.config/murpiano-dx/release-token"
    [ -t 0 ] || { echo 'Enter the token in an interactive terminal.' >&2; exit 1; }
    read -rs -p 'Release token (Enter keeps the previous value): ' token
    echo
    if [ -n "$token" ]; then
      mkdir -p "$(dirname "$token_file")"
      (umask 077; printf '%s' "$token" >"$token_file")
      chmod 600 "$token_file"
      unset token
      echo 'Token saved locally. The RELEASE_TOKEN secret is configured separately for each project.'
    fi
    ;;
  *) echo 'Usage: bash install.sh [--restore [url] [path] | --release-token]' >&2; exit 2 ;;
esac
