#!/usr/bin/env bash
# Connect local instructions. Release credentials are a separate explicit action.
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
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
case "${1:-}" in
  '')
    setup_config
    python3 "$root/configure-codex.py" "$root"
    echo 'Done. Open a new Codex session. In the project, ask: “initialize the project”.'
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
  *) echo 'Usage: bash install.sh [--release-token]' >&2; exit 2 ;;
esac
