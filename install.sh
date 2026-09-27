#!/usr/bin/env bash
# Sets up this computer for development with agents. Safe to run again.
#
#   1. Links every skill from skills/ into the global skill folders of the agents.
#   2. Sets the global git author from config.env.
#   3. Adds agent tooling files to the global git ignore file.
#   4. Turns off commit and pull request attribution in Claude Code.
set -euo pipefail

root=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=config.env
source "$root/config.env"

echo "== Skills"
for target in "$HOME/.claude/skills" "$HOME/.agents/skills"; do
  mkdir -p "$target"
  for skill in "$root"/skills/*/; do
    link="$target/$(basename "$skill")"
    if [ -e "$link" ] && [ ! -L "$link" ]; then
      echo "skip $link: a real folder is in the way"
      continue
    fi
    ln -sfn "${skill%/}" "$link"
    echo "linked $link"
  done
done

echo "== Git author"
git config --global user.name "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"
echo "$(git config --global user.name) <$(git config --global user.email)>"

echo "== Global git ignore"
ignore=$(git config --global core.excludesfile || true)
ignore=${ignore:-${XDG_CONFIG_HOME:-$HOME/.config}/git/ignore}
ignore=${ignore/#\~/$HOME}
mkdir -p "$(dirname "$ignore")"
touch "$ignore"
begin='# >>> murpiano-dx'
end='# <<< murpiano-dx'
sed -i "/^$begin\$/,/^$end\$/d" "$ignore"
{
  echo "$begin"
  grep -v '^#' "$root/skills/repo-cleanup/gitignore-agents"
  echo "$end"
} >>"$ignore"
echo "updated $ignore"

echo "== Claude Code attribution"
settings="$HOME/.claude/settings.json"
mkdir -p "$(dirname "$settings")"
[ -f "$settings" ] || echo '{}' >"$settings"
python3 - "$settings" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data["attribution"] = {"commit": "", "pr": "", "sessionUrl": False}
with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
echo "updated $settings"
