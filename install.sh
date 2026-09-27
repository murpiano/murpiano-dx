#!/usr/bin/env bash
# Links every skill from skills/ into the global skill folders of the agents.
# Safe to run again: existing links are updated, real folders are left alone.
set -euo pipefail

root=$(cd "$(dirname "$0")" && pwd)
targets=("$HOME/.claude/skills" "$HOME/.agents/skills")

for target in "${targets[@]}"; do
  mkdir -p "$target"
  for skill in "$root"/skills/*/; do
    name=$(basename "$skill")
    link="$target/$name"
    if [ -e "$link" ] && [ ! -L "$link" ]; then
      echo "skip $link: a real folder is in the way"
      continue
    fi
    ln -sfn "${skill%/}" "$link"
    echo "linked $link"
  done
done
