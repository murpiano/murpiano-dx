#!/usr/bin/env bash
# Local project connection. No automatic commits or network operations.
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
source "$root/config.env"
export GITHUB_OWNER GIT_NAME GIT_EMAIL
exec python3 "$root/sync.py" "$@"
