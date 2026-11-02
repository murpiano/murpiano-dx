#!/usr/bin/env python3
"""Connect project instructions to the shared store without publishing anything."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
STORE = ROOT / 'projects'
PATHS = ('AGENTS.md', '.agents')
BEGIN = '# >>> murpiano-dx'
END = '# <<< murpiano-dx'


def git(project, *args, check=True):
    result = subprocess.run(['git', '-C', str(project), *args], text=True,
                            capture_output=True, check=False)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Git command failed')
    return result.stdout.strip()


def git_path(project, name):
    path = Path(git(project, 'rev-parse', '--git-path', name))
    return path if path.is_absolute() else project / path


def project_key(url):
    match = re.fullmatch(r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?/?', url)
    if match:
        owner, repo = match.groups()
    else:
        parsed = urlsplit(url)
        if parsed.scheme not in ('https', 'ssh') or parsed.hostname != 'github.com':
            return None
        parts = parsed.path.strip('/').split('/')
        if len(parts) != 2:
            return None
        owner, repo = parts
        repo = repo.removesuffix('.git')
    expected = os.environ['GITHUB_OWNER']
    if (owner.lower() != expected.lower() or
            not re.fullmatch(r'[A-Za-z0-9_.-]+', repo) or repo in ('.', '..')):
        return None
    return f'{expected}/{repo}'


@contextmanager
def store_lock():
    STORE.mkdir(parents=True, exist_ok=True)
    try:
        handle = (STORE / '.sync.lock').open('a')
    except OSError as error:
        raise RuntimeError(f'Не удалось открыть блокировку хранилища: {error}') from error
    with handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('Хранилище занято другой синхронизацией; повтори команду.') from error
        yield


def exclude_agent_files(project):
    path = git_path(project, 'info/exclude')
    text = path.read_text() if path.exists() else ''
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise RuntimeError(f'Повреждены маркеры исключений: {path}')
    if BEGIN in text:
        prefix, rest = text.split(BEGIN, 1)
        _, suffix = rest.split(END, 1)
        text = prefix + suffix
    rules = (ROOT / 'global/gitignore-agents').read_text().rstrip()
    updated = text.rstrip() + '\n\n' + BEGIN + '\n' + rules + '\n' + END + '\n'
    if not path.exists() or path.read_text() != updated:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(updated)


def remove_old_hook(project):
    path = git_path(project, 'hooks') / 'pre-commit'
    if not path.is_file() or path.is_symlink():
        return
    lines = path.read_text().splitlines()
    marker = '# murpiano-dx: agent-trace pre-commit scan (skills/repo-cleanup)'
    if marker not in lines:
        return
    if (len(lines) == 3 and lines[0] == '#!/usr/bin/env bash' and lines[1] == marker
            and lines[2] == f'exec bash "{ROOT}/skills/repo-cleanup/pre-commit-hook.sh"'):
        path.unlink()
        print('Удалён прежний pre-commit murpiano-dx.')
    else:
        print(f'Проверь прежний вызов repo-cleanup в {path}: изменённый хук сохранён.')


def attach(project, key):
    files = STORE / key / 'files'
    files.mkdir(parents=True, exist_ok=True)
    for name in PATHS:
        source, target = project / name, files / name
        if source.is_symlink():
            if source.resolve() != target.resolve():
                print(f'Конфликт ссылки: {source}. Ссылка сохранена.')
            continue
        if git(project, 'ls-files', '--', name):
            print(f'{name} отслеживается проектом; оставлен на месте.')
            continue
        moved = False
        if source.exists():
            if target.exists() or target.is_symlink():
                print(f'Конфликт файлов: {source} и {target}. Объедини вручную.')
                continue
            shutil.move(str(source), str(target))
            moved = True
        elif not target.exists() and not target.is_symlink():
            if name == '.agents':
                target.mkdir()
            else:
                text = (ROOT / 'global/project-rules.md').read_text()
                for token, value in [('{{PROJECT}}', key), ('{{ROOT}}', str(ROOT)),
                                     ('{{STORE}}', str(STORE / key)),
                                     ('{{SYNC}}', 'bash ' + shlex.quote(str(ROOT / 'sync.sh')))]:
                    text = text.replace(token, value)
                target.write_text(text)
        try:
            source.symlink_to(target, target_is_directory=(name == '.agents'))
        except OSError:
            if moved:
                shutil.move(str(target), str(source))
            raise
    print(f'Данные проекта: {STORE / key}')
    memory = STORE / key / 'memory'
    if memory.is_dir():
        print(f'Сохранённая память: {memory}. Прочитай MEMORY.md и нужные заметки.')


def kysaro_gaps(project):
    gaps = []
    if shutil.which('node') is None:
        gaps.append('Node.js')
    binary = project / 'node_modules/.bin/kysaro'
    if not binary.is_file() or not os.access(binary, os.X_OK):
        gaps.append('локальный kysaro')
    for name in ('commit', 'merge', 'request'):
        path = project / f'.kysaro/settings/commits/{name}.json'
        try:
            if not isinstance(json.loads(path.read_text()), dict):
                gaps.append(f'настройки {name}')
        except (OSError, ValueError):
            gaps.append(f'настройки {name}')
    hooks = git_path(project, 'hooks')
    active = hooks / 'commit-msg'
    hooked = active.is_file() and os.access(active, os.X_OK) and 'kysaro' in active.read_text()
    if hooks.name == '_' and hooks.parent.name == '.husky':
        user_hook = hooks.parent / 'commit-msg'
        hooked = (active.is_file() and os.access(active, os.X_OK) and
                  user_hook.is_file() and 'kysaro' in user_hook.read_text())
    if not hooked:
        gaps.append('активный commit-msg')
    workflows = project / '.github/workflows'
    checked_in_ci = workflows.is_dir() and any(
        p.suffix in ('.yml', '.yaml') and 'kysaro ci' in p.read_text()
        for p in workflows.iterdir() if p.is_file())
    if not checked_in_ci:
        gaps.append('CI kysaro')
    return gaps


def load_workflow(key):
    path = STORE / key / 'workflow.json'
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text())
    except (ValueError, UnicodeError) as error:
        raise RuntimeError(f'Некорректное состояние инициализации: {path}') from error
    if not isinstance(state, dict) or state.get('kysaro') not in (
            'pending', 'approved', 'declined', 'enabled'):
        raise RuntimeError(f'Некорректное состояние инициализации: {path}')
    return state


def save_workflow(key, state):
    path = STORE / key / 'workflow.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2) + '\n')
    temporary.replace(path)


def report(project, key, state, initializing=False):
    status = state['kysaro']
    if status == 'enabled':
        gaps = kysaro_gaps(project)
        status = 'настроен' if not gaps else 'восстановить: ' + ', '.join(gaps)
    else:
        status = {'pending': 'решение не принято', 'approved': 'установка согласована, не завершена',
                  'declined': 'отклонён владельцем'}[status]
    branch = git(project, 'branch', '--show-current')
    print(f'{key} | ветка: {branch or "detached HEAD"} | kysaro: {status}')
    print(f'Контекст: {STORE / key}. Правила по задаче: {ROOT}/skills/')
    if any(not (project / name).exists() for name in PATHS):
        print('Инструкции или заметки не подключены в этой копии; восстанови через init по запросу.')
    if initializing and state['kysaro'] == 'pending':
        print('Предложи установить kysaro: локальная зависимость, commit-msg, настройки и CI. '
              'Продолжение: skills/repo-init/SKILL.md.')
    elif initializing and state['kysaro'] == 'approved':
        print('Продолжи согласованную настройку по skills/repo-init/kysaro.md.')


def connect(folder, mode='start', choice=None, quiet=False):
    initialize = mode == 'init'
    root = git(folder, 'rev-parse', '--show-toplevel', check=False)
    if not root:
        if not initialize:
            if not quiet:
                print(f'Нет Git-репозитория. Для подключения: bash '
                      f'{shlex.quote(str(ROOT / "sync.sh"))} init {shlex.quote(str(folder))}')
            return
        git(folder, 'init', '-b', 'main')
        for name, value in [('user.name', os.environ['GIT_NAME']),
                            ('user.email', os.environ['GIT_EMAIL'])]:
            if not git(folder, 'config', '--get', name, check=False):
                git(folder, 'config', '--local', name, value)
        root = str(folder)
    project = Path(root).resolve()
    if project == ROOT:
        if not quiet:
            print('murpiano-dx: используй skills/ как источник общих правил; самоподключение не требуется.')
        return
    url = git(project, 'remote', 'get-url', 'origin', check=False)
    if not url:
        if quiet:
            return
        if not initialize:
            print('Нет origin. По запросу владельца подключи проект через repo-init.')
            return
        exclude_agent_files(project)
        print('Локальный Git готов. Предложи владельцу приватный GitHub-репозиторий.')
        print('После согласия, из папки проекта: gh repo create --private --source=. --remote=origin')
        print('Затем повтори init. Коммиты, создание GitHub-репозитория и push автоматически не выполняются.')
        return
    key = project_key(url)
    if key is None:
        if not quiet:
            print('Origin не относится к настроенному владельцу GitHub; не изменён. Подключение пропущено.')
        return
    if mode == 'start':
        state = load_workflow(key)
        if state is None:
            print(f'{key}: проект не инициализирован. По запросу владельца используй repo-init.')
        else:
            report(project, key, state)
        return
    with store_lock():
        state = load_workflow(key)
        if state is None and not initialize:
            if not quiet:
                print(f'{key}: сначала выполни явную инициализацию через repo-init.')
            return
        state = state or {'kysaro': 'pending'}
        exclude_agent_files(project)
        remove_old_hook(project)
        attach(project, key)
        if initialize:
            if choice == 'enabled':
                gaps = kysaro_gaps(project)
                if gaps:
                    raise RuntimeError('Настройка kysaro не завершена: ' + ', '.join(gaps))
            if choice:
                state['kysaro'] = choice
            elif state['kysaro'] == 'pending' and not kysaro_gaps(project):
                state['kysaro'] = 'enabled'
            save_workflow(key, state)
    if not quiet and initialize:
        report(project, key, state, initializing=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['init', 'start', 'end', 'link'], nargs='?', default='start')
    parser.add_argument('project', type=Path, nargs='?', default=Path.cwd())
    parser.add_argument('--kysaro', choices=['approved', 'declined', 'enabled'],
                        help='Record the owner decision or verify completed setup (init only)')
    args = parser.parse_args()
    if args.kysaro and args.mode != 'init':
        parser.error('--kysaro is only available with init')
    if args.mode == 'link':
        parent = Path(os.environ.get('PROJECTS_DIR', Path.home() / 'projects'))
        if parent.is_dir():
            for folder in sorted(parent.iterdir()):
                if folder.is_dir():
                    connect(folder.resolve(), mode='link', quiet=True)
    else:
        connect(args.project.resolve(), mode=args.mode, choice=args.kysaro)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f'murpiano-dx: {error}', file=sys.stderr)
        sys.exit(1)
