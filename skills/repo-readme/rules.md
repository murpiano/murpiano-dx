# Правила витринного README

Посетитель за минуту понимает, что это, видит результат, может запустить проект и знает его
ограничения. Все README выглядят как одна серия и читаются как написанные автором вручную.

Эталон: `murpiano/murpiano-server`.

## 1. Факты

- Каждое число, лимит, путь, команда и URL берутся из кода, конфигов, CI или живого сервиса.
- Ничего не придумывать: ни мотивацию, ни метрики, ни пользователей, ни планы.
- Каждую внешнюю ссылку открыть до того, как вписать.
- README описывает сам репозиторий, а не тех, кто им пользуется. У общего сервера или
  библиотеки нет списка приложений-потребителей и их отдельных ручек. Описывается общее
  поведение и где писать специфичный код.

## 2. Структура

Порядок и названия фиксированы. Блок без содержания пропускается. Своих секций нет.

| Блок | Обязателен | Что внутри |
| --- | --- | --- |
| Картинка | да | первая строка файла, до заголовка |
| `# Name` и одно предложение | да | что это и на чём построено |
| Бейджи | да | CI, и Release, если релизы включены |
| Строка навигации | да | 2–3 ссылки через ` · ` |
| Предупреждение | нет | что знать до клика по демо |
| `## What you can do` | да | абзац глаголами пользователя, при желании пример |
| `## How it works` | да | 2–6 подразделов `###` |
| `## Run locally` | да | блок `bash`, требования, env, тесты и CI |
| `## Where things live` | если папок больше трёх | дерево и 1–2 предложения |
| `## API` / `## CLI` / `## Usage` | по типу проекта | эндпоинты, help или примеры кода |
| `## Rough edges` | да | 2–6 реальных ограничений |
| `---` и подпись в `<sub>` | да | строка из шаблона дословно, меняется только лицензия |

Картинка:

- Веб-приложение: реальный интерфейс, без рамок устройств и коллажей.
- Бэкенд, CLI, библиотека: обложка, которая передаёт суть.
- Файл в репозитории, ширина около 1440 px, JPEG до 300 KB, alt-текст — имя проекта.
- Пример (`curl` с ответом, команда с выводом, 5–10 строк кода) идёт блоком `text` в
  `What you can do`, а не вместо картинки.

Бейджи отдельными строками под описанием, в этом порядке: CI, затем Release, если релизы
включены (скилл `repo-release`). Бейдж ставится, только когда он уже показывает реальный
статус.

```markdown
[![CI](https://github.com/murpiano/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/murpiano/<repo>/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/murpiano/<repo>?color=informational)](https://github.com/murpiano/<repo>/releases/latest)
```

Навигация: первая ссылка на демо, npm или живой API, дальше `#how-it-works` и
`#run-locally`.

## 3. Голос

- Английский, если автор не просит другой. Простые слова, как объяснение коллеге.
- Настоящее время, активный залог, одна мысль в предложении.
- Длина предложений, абзацев и подразделов разная.
- Подраздел `How it works`: что сделано, почему так, чем за это заплачено. Файлы в `code`,
  константы с реальными значениями.
- `Rough edges`: факты из кода («Likes are stored in the browser»), а не «Room for
  improvement».
- Первое лицо только для решений, видимых в коде.

## 4. Запрещено

Оформление:

- Эмодзи где угодно. `align`, центрирование.
- Бейджи кроме CI и Release.
- Горизонтальные линии между секциями. Одна `---` только перед подписью.
- Жирный внутри абзацев. Пункты вида `**Лид.** текст` или `**Лид**: текст`.
- Таблицы для стека и фич. Таблица допустима для API, опций CLI, скриптов и env.
- Заглушки, `TODO`, `Coming soon`.

Секции: `Features`, `Key features`, `Highlights`, `Overview`, `Tech stack`, `Why`,
`Engineering commentary`, `Acknowledgements`, `Contributing`, `Author`, `License`,
описание конвенции коммитов.

Язык:

- Длинное тире. Вместо него точка, двоеточие, запятая или скобки.
- Приёмы `not X, but Y`, `X, not Y`, `unlike other...`, `without X` ради эффекта.
- Тройки: три прилагательных, три одинаковых пункта.
- Слова: `seamless`, `robust`, `powerful`, `scalable`, `highly`, `leverage`, `utilize`,
  `blazing`, `effortless`, `elegant`, `showcase`, `delve`, `crafted`, `cutting-edge`,
  `modern`, `intuitive`, `comprehensive`, `ecosystem`, `orchestrate`, `unlock`, `empower`,
  `streamline`, `under the hood`, `out of the box`, `best practices`, `clean architecture`,
  `separation of concerns`.
- Вступления и концовки: `This project is...`, `Welcome to`, `In summary`, `Feel free to`,
  `Contributions are welcome`, `Happy coding`, `Made with love`.
- `portfolio`, `pet project`, `test task` в README, description и topics.
- Любые следы агентов: см. скилл `repo-cleanup`.

## 5. Тесты и CI

- В каждом проекте есть тесты. Хотя бы несколько простых: главная логика и то, что
  приложение собирается и отвечает.
- Раннер `vitest`. Тест лежит рядом с кодом: `foo.ts` и `foo.test.ts`. Тесты исключены из
  сборки через `exclude` в `tsconfig.json`.
- Тесты не трогают рабочие данные, прод и сеть: временные папки, фикстуры, моки.
- Скрипты одинаковые во всех проектах (линтер, если есть, тоже входит в `check`):

  ```json
  "test": "vitest run",
  "check": "tsc --noEmit && vitest run"
  ```

- `.github/workflows/ci.yml`: `name: CI`, одна джоба `test`, запуск на push в `main` и на
  pull request, шаги `npm ci`, `npm run check`, `npm run build`. Деплой в отдельном
  workflow.
- В README, в `Run locally`: строки `npm test` и `npm run check` и одно-два предложения о
  том, где лежат тесты, что они не трогают и что запускает CI.

## 6. Релизы

Релизы, версии, заметки и бейдж Release описаны в скилле `repo-release`. Релизы выпускает
GitHub Actions после зелёного CI, поэтому CI из раздела 5 обязателен.

## 7. Метаданные репозитория

- Description: одно предложение до 100 символов, без эмодзи и длинного тире. Совпадает с
  `description` в `package.json`.
- Website: демо или живой API.
- Topics: 4–7, технологии и предметная область.
- Лицензия в подписи совпадает с `LICENSE` и полем `license` в `package.json`.

```bash
gh repo edit OWNER/REPO --description "..." --homepage "..." --add-topic typescript
```

`gh pr edit` может падать на устаревших полях Projects. Тогда править через
`gh api -X PATCH repos/OWNER/REPO/pulls/N -f title=...`.

## 8. Проверка

Эти команды ничего не должны выводить:

```bash
grep -nP '—|\*\*[^*]+[.:]\*\*|[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]|align=|<!--' README.md
grep -niE 'seamless|robust|powerful|scalable|highly|leverage|utiliz|showcase|delve|crafted|cutting-edge|intuitive|comprehensive|ecosystem|orchestrat|empower|streamline|under the hood|out of the box|best practice|portfolio|feel free|welcome' README.md
```

Затем:

- `npx prettier --check README.md`.
- `npm ci && npm run check && npm run build` на чистом клоне.
- Открыть каждую ссылку и каждый якорь.
- Прочитать `How it works` вслух. Фразу, которую автор не сказал бы коллеге, переписать.
