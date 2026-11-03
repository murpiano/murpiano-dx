#!/usr/bin/env python3
"""Compatibility entry point; normal setup detects supported agents automatically."""
from pathlib import Path
import sys
from agent_setup import configure

if __name__ == '__main__':
    try:
        configure(Path(sys.argv[1]).resolve(), only={'codex'})
    except (OSError, RuntimeError) as error:
        print(f'murpiano-dx: {error}', file=sys.stderr)
        sys.exit(1)
