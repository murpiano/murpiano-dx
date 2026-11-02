> Agent entry point: read [AGENTS.md](https://github.com/murpiano/murpiano-dx/blob/main/AGENTS.md) and stop reading this README. It contains the concise workflow for Codex. This page is for humans.

![murpiano Developer Experience](resources/logo.png)

# murpiano-dx

An agentic development framework: project memory, shared Git rules, consistent
repository standards, CI, and releases for projects managed by Codex.

[![CI](https://github.com/murpiano/murpiano-dx/actions/workflows/ci.yml/badge.svg)](https://github.com/murpiano/murpiano-dx/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/murpiano/murpiano-dx?color=informational)](https://github.com/murpiano/murpiano-dx/releases/latest)


[How it works](#how-it-works) · [Installation](#installation) · [Commands](#commands)

## What it does

Connect new and existing projects while keeping agent data and project memory
separate from product code. The agent reads the shared rules and applies them to
branches, commits, PRs, README files, releases, and CI. A normal request such as
“write the README”, “set up CI”, or “start releases” is enough; no special
“follow murpiano-dx rules” phrase is required.

## How it works

### Separation of responsibilities

| Participant | Responsibility |
| --- | --- |
| murpiano-dx | Shared rules, templates, project connection, and context storage |
| Project agent | Reads relevant rules, performs the task, and checks code and intent |
| Kysaro in the project | Checks commit messages through commit-msg and commits/PRs through CI |
| Project CI | Runs tests, checks, and builds; releases can require a successful run |

Kysaro does not choose branches or assess code. The agent makes those decisions
through `repo-commit`. The project’s `.kysaro/settings/` define the machine format
for messages; the shared process remains in murpiano-dx.

### Подключение проекта

После установки скажи агенту «инициализируй проект». Он использует `repo-init`.
Локальный Git создаётся при отсутствии. Если origin нет, агент предлагает
приватный GitHub-репозиторий и создаёт его после согласия. Существующий origin
сохраняется. Владелец GitHub берётся из локального конфига машины.

Kysaro настраивается отдельно в каждом проекте через его `init`: настройки,
commit-msg и workflow. Агент предлагает установку и после согласия проводит её
по шагам: зависимость, настройки, активный hook, CI и проверка сообщений.
Локальная синхронизация сама пакеты не скачивает. Существующие хуки сохраняются.
Для проекта другого стека Node.js остаётся инструментом разработки: минимальный
package.json с `private: true` и lock-файл закрепляют локальную зависимость kysaro.

Решение и этап хранятся в `workflow.json`: `pending` (решение не принято),
`approved` (согласовано, ещё не завершено), `declined` (отказ), `enabled`
(компоненты проверены). После сбоя инициализация продолжается с сохранённого этапа.
Отказ не вызывает повторных предложений в обычных задачах. Уже настроенный kysaro
не устанавливается заново.

### Данные проекта

```text
projects/OWNER/REPO/
├── workflow.json     решение по kysaro и состояние настройки
├── files/
│   ├── AGENTS.md
│   └── .agents/       решения, команды проверок, заметки задач
└── memory/           ранее сохранённая память
```

В проекте `AGENTS.md` и `.agents/` ссылаются на хранилище. Новые проекты получают
короткие инструкции с указателями на общие правила. Уже существующие инструкции
и заметки сохраняются; отслеживаемые Git файлы не перемещаются. Конфликтующие
файлы и ссылки остаются на месте с сообщением для ручного разбора.

Локальные исключения в `.git/info/exclude` скрывают служебные файлы от Git
продукта. Переносятся только `AGENTS.md` и `.agents/`. Старые `.claude`,
`.superpowers`, планы и память в хранилище сохранены; новые временные каталоги
не собираются. Секреты хранятся вне проектной памяти.

### Навыки

| Навык | Когда применяется |
| --- | --- |
| `repo-init` | Подключение проекта, GitHub origin и проверки kysaro |
| `repo-commit` | Ветки задач, коммиты, PR и merge |
| `repo-readme` | README по шаблону, description, website и topics |
| `repo-release` | Тесты, CI, включение и управление релизами |

Общие инструкции подключаются через `AGENTS.md`, навыки выбираются по задаче.
Механизм описан в [официальной документации Codex](https://learn.chatgpt.com/docs/customization/overview).
Вызовы `start` и `end` поручены агенту инструкциями; фонового сервиса и
гарантированного события начала/окончания сессии здесь нет.

### Оформление репозитория

`repo-readme` задаёт единый шаблон README: назначение проекта, способы запуска,
структура, ограничения и только подтверждённые факты. Тот же навык описывает
GitHub `description`, `website` и `topics`. Бейдж CI добавляется только при
рабочем `.github/workflows/ci.yml`, бейдж Release только после включения релизов.
Подробные правила и шаблон находятся в
[`skills/repo-readme/rules.md`](skills/repo-readme/rules.md) и
[`skills/repo-readme/template.md`](skills/repo-readme/template.md).

### Что получает агент

До явного запроса инициализации проект не меняется. `start` выводит короткий
статус без установки, переноса файлов и повторного опроса. После подключения
`AGENTS.md` содержит указатели на murpiano-dx. Агент читает только навык текущей
задачи, нужные правила и предметные заметки; общие инструкции в проекты не копируются.
Подробная настройка kysaro вынесена из обычного рабочего контекста и читается
только при установке или восстановлении. Команды и результаты начальной проверки
агент сохраняет в `.agents/setup.md`.

## Установка

Нужны Linux или WSL, Bash, Git и Python 3.11+. GitHub CLI нужен для операций
на GitHub; Node.js/npm нужны kysaro. Настройки владельца и резервного автора
новых репозиториев находятся в `~/.config/murpiano-dx/config.env`.
При первом запуске `install.sh` имя, email и GitHub owner запрашиваются пошагово.
Значения по умолчанию берутся из активной учётной записи `gh` и настроек Git.
Файл `config.env` в репозитории содержит только публичный шаблон.

```bash
bash install.sh
```

Установка подключает четыре навыка в `~/.agents/skills` и обновляет только блок
murpiano-dx в `~/.codex/AGENTS.md`. Существующая ссылка инструкций на Windows-файл
сохраняется. Другие правила и одноимённые сторонние навыки не перезаписываются.
После установки открой новую сессию Codex.

Глобальная Git-идентичность, настройки Claude, токены и соседние проекты при
установке не меняются. Прежняя ссылка на навык repo-cleanup удаляется, если
принадлежит этой установке. Штатный старый pre-commit убирается при подключении
проекта; изменённый или сторонний хук сохраняется с сообщением. Установщик также
убирает точный прежний блок murpiano-dx из глобального Husky init, сохраняя чужой код.

Проверки пакета:

```bash
python3 -B -m unittest discover -s tests -v
bash -n install.sh
bash -n sync.sh
bash -n skills/repo-release/release.sh
```

Тесты работают во временных HOME и Git-репозиториях, без GitHub и рабочих
данных. `.github/workflows/ci.yml` выполняет их на PR и push в main;
отдельный workflow kysaro проверяет сообщения.

## Где что лежит

```text
global/             общие инструкции, шаблон проекта, локальные исключения
skills/             правила и шаблоны рабочих процессов
projects/           данные подключённых проектов
tests/              интеграционные проверки
configure-codex.py  подключение инструкций и навыков
install.sh          установка; отдельный режим сохранения токена релизов
sync.sh, sync.py    локальное подключение и синхронизация
```

## Команды

Из папки проекта, с фактическим путём к murpiano-dx:

```bash
bash /path/to/murpiano-dx/sync.sh init
bash /path/to/murpiano-dx/sync.sh start
bash /path/to/murpiano-dx/sync.sh end
```

| Команда | Действие |
| --- | --- |
| `init [папка]` | Подключить проект; показать этап настройки и предложение kysaro, если решение ещё не принято |
| `init --kysaro approved` | Сохранить согласие; установку продолжает агент по шагам repo-init |
| `init --kysaro declined` | Сохранить отказ от kysaro |
| `init --kysaro enabled` | Проверить локальную зависимость, настройки, активный hook и workflow перед сохранением завершённого этапа |
| `start [папка]` | Только прочитать состояние и показать путь контекста; никаких установок и переноса файлов |
| `end [папка]` | Подхватить новые инструкции и заметки уже инициализированного проекта |
| `link` | Восстановить подключение уже инициализированных проектов в подпапках `PROJECTS_DIR`, по умолчанию `~/projects` |

`enabled` проверяет наличие локальных компонентов. Проверку корректных и
некорректных сообщений выполняет агент до этой команды. Запуск GitHub Actions
подтверждается отдельно после согласованной публикации.

Коммиты, push и PR выполняются агентом по `repo-commit` в рамках задачи.
Данные самого хранилища публикуются по тому же процессу; автоматической команды
`publish` больше нет. Repo-cleanup и сканер истории удалены.

Для релизов от своего имени сохрани токен отдельной командой:

```bash
bash install.sh --release-token
```

Токен хранится в `~/.config/murpiano-dx/release-token` с правами `600`.
При включении релизов агент задаёт `RELEASE_TOKEN` только в выбранном репозитории.
Workflow выпускает релиз после зелёного CI в main при `RELEASES=on`.

## Ограничения

- Рабочие ссылки требуют доступного каталога murpiano-dx. Codex должен иметь
  право записи в центральное хранилище, когда меняет проектную память.
- После нового клонирования проекта нужно подключить его снова. Локальные
  Git-хуки также требуют восстановления; CI хранится в репозитории.
- Подключение без origin останавливается после подготовки локального Git.
  Центральное хранилище определяется по origin, а не по имени локальной папки.
- Старые заметки Claude сохранены, но их актуальность проверяется по мере работы.
