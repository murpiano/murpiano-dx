#!/usr/bin/env python3
"""Exchange saved workspace files on agent session events, without a timer."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from workspace_sync import is_workspace, prepare_local_files, synchronize

ROOT = Path(__file__).resolve().parent


def exchange():
    try:
        completed = synchronize(ROOT)
        message = 'Workspace synchronized.' if completed else 'Workspace sync already running.'
        success = True
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        message = f'Workspace sync pending; saved data remains local: {error}'
        success = False
    with (ROOT / 'logs/session-sync.log').open('a') as log:
        log.write(f'{datetime.now(timezone.utc).isoformat()} {message}\n')
    return success, message


def main():
    event = sys.argv[1] if len(sys.argv) == 2 else ''
    if event not in ('start', 'end', 'send'):
        raise RuntimeError('Usage: session_hook.py start|end|send')
    # Hooks never install a workspace, initialize a project, or save raw transcripts.
    if not is_workspace(ROOT):
        return
    prepare_local_files(ROOT)
    if event == 'end':
        # Codex allows SessionEnd only three seconds. Start one bounded exchange,
        # independent of the closing client, and exit the hook immediately.
        with (ROOT / 'logs/session-sync.log').open('a') as log:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'send'],
                             stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                             start_new_session=True, close_fds=True)
        return
    success, message = exchange()
    if event == 'start':
        # Both supported agents accept this SessionStart context shape.
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': 'SessionStart',
            'additionalContext': 'murpiano-dx: ' + message
                + ' Run the instructed start command with --local to check project state '
                  'without repeating network synchronization.'}}))
    elif not success:
        print(message, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'murpiano-dx session hook: {error}', file=sys.stderr)
        sys.exit(1)
