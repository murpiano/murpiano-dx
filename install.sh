#!/usr/bin/env bash
# Links every skill from skills/ into the global skill folders of the agents.
# Safe to run again: existing links are updated, real folders are left alone.
set -euo pipefail

root=$(cd "$(dirname "$0")" && pwd)
targets=("$HOME/.claude/skills" "$HOME/.agents/skills")

# Commits in this repository are made only as murpiano (see .githooks/pre-commit).
git -C "$root" config user.name murpiano
git -C "$root" config user.email 159007823+murpiano@users.noreply.github.com
git -C "$root" config core.hooksPath .githooks

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
