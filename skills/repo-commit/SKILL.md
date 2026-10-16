---
name: repo-commit
description: Use whenever making a git commit — picks type, scope and subject, writes a body for feat and fix that explains what changed and why, and follows this project's kysaro settings if it has any. Not for deciding when to release: that is repo-release.
---

# Коммиты

Пишет сообщение каждого коммита: тип, scope, subject и, для `feat`/`fix`, тело с тем, что
изменилось и зачем. Отдельно от того, когда делать релиз — это `repo-release`, он только
читает готовую историю, сам коммитов не пишет.

Правила: [rules.md](rules.md).

## Шаги

1. Если в проекте есть `.kysaro/settings/commits/commit.json` (или `merge.json`/`request.json`
   для своего типа сообщения) — прочитать его: допустимые `type`, `scope`, регистр subject,
   обязательность тела, footer. Нет файла, но `kysaro` в `package.json` — пресет kysaro по
   умолчанию. Нет kysaro вовсе — тот же дефолт, без хука на выходе.
2. Определить тип по изменению (таблица в `rules.md`). Scope — по затронутой части проекта,
   если список scope задан в `.kysaro/settings/resources/scopes.json`, брать из него.
3. Subject: что сделано, повелительное наклонение, без точки, в регистре из пресета.
4. `feat`/`fix`: первый абзац тела — что изменилось и зачем, 1-3 предложения, без деталей
   реализации. Это пойдёт в заметки релиза как есть (`repo-release`, раздел 5 его `rules.md`).
   Детали реализации — вторым абзацем, если нужны, не в первом.
5. Закоммитить. Если kysaro отклонил сообщение — прочитать его вывод (называет правило и
   предложенный заголовок) и исправить, не `--no-verify`. `--no-verify` — только по прямой
   просьбе автора.

## Нельзя

- `--no-verify` без просьбы автора.
- Коммит `feat`/`fix` без тела, если `kysaro` требует его (`body.required`) или изменение
  нетривиальное.
- Переносить в первый абзац тела детали реализации — `repo-release` берёт из тела только его.

## Готово, когда

- Коммит прошёл через хук kysaro, если он стоит, без `--no-verify`.
- У `feat`/`fix` есть тело, первый абзац которого можно взять как пункт заметок релиза.
