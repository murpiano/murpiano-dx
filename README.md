# murpiano-dx

Конфиг компьютера для разработки с агентами. Один запуск `install.sh` приводит агентов и git
к одному стандарту. В сами проекты ничего не устанавливается.

## Что делает установка

```bash
bash install.sh
```

1. Подключает скиллы из `skills/` к Claude Code (`~/.claude/skills`) и к Codex и другим
   агентам (`~/.agents/skills`) симлинками. Правка скилла здесь сразу видна всем агентам.
2. Ставит глобального автора git из [config.env](config.env).
3. Добавляет файлы агентов в глобальный git ignore, блоком между `# >>> murpiano-dx` и
   `# <<< murpiano-dx`. Список: [gitignore-agents](skills/repo-cleanup/gitignore-agents).
4. Выключает автоматическую подпись коммитов и PR в Claude Code
   (`attribution` в `~/.claude/settings.json`).

Повторный запуск ничего не дублирует. После правки `config.env`, списка или скиллов
запустить ещё раз.

## Скиллы

| Скилл | Когда |
| --- | --- |
| [`repo-readme`](skills/repo-readme/SKILL.md) | README, description и topics репозитория, тесты, CI и релиз для бейджей |
| [`repo-cleanup`](skills/repo-cleanup/SKILL.md) | перед push или публикацией: следы агентов в файлах, истории, PR и релизах |

Агент выбирает скилл сам по полю `description` в `SKILL.md`. Вручную: `/repo-readme`,
`/repo-cleanup`.

Одна папка на скилл: `SKILL.md` с шагами, рядом правила, шаблоны и скрипты этого скилла.
Ссылок между папками нет, поэтому скилл работает и через симлинк.

Сканер следов работает и без агента:

```bash
bash skills/repo-cleanup/scan-traces.sh <repo> --published
```
