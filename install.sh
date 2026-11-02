#!/usr/bin/env bash
# Connect local instructions. Release credentials are a separate explicit action.
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
case "${1:-}" in
  '')
    python3 "$root/configure-codex.py" "$root"
    echo 'Готово. Открой новую сессию Codex. В проекте скажи: «инициализируй проект».'
    ;;
  --release-token)
    token_file="$HOME/.config/murpiano-dx/release-token"
    [ -t 0 ] || { echo 'Введи токен в интерактивном терминале.' >&2; exit 1; }
    read -rs -p 'Release token (Enter сохраняет прежний): ' token
    echo
    if [ -n "$token" ]; then
      mkdir -p "$(dirname "$token_file")"
      (umask 077; printf '%s' "$token" >"$token_file")
      chmod 600 "$token_file"
      unset token
      echo 'Токен сохранён локально. Секрет RELEASE_TOKEN задаётся отдельно в каждом проекте.'
    fi
    ;;
  *) echo 'Usage: bash install.sh [--release-token]' >&2; exit 2 ;;
esac
