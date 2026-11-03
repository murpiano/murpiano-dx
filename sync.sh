#!/usr/bin/env bash
# Local project connection. No automatic commits or network operations.
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
config_home="${XDG_CONFIG_HOME:-$HOME/.config}/murpiano-dx"
config_file="${MURPIANO_DX_CONFIG:-$config_home/config.env}"
if [ -f "$config_file" ]; then
  source "$config_file"
else
  source "$root/config.env"
fi
export GITHUB_OWNER GIT_NAME GIT_EMAIL
if [ -z "${MURPIANO_DX_DATA_DIR:-}" ] && [ -f "$root/config/machine.json" ]; then
  export MURPIANO_DX_DATA_DIR="$root"
fi
exec python3 "$root/sync.py" "$@"
