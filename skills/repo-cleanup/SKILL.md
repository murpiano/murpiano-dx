---
name: repo-cleanup
description: Use when a repository is about to be pushed or published, or when its files, commit history, authors, branches, pull requests or releases may show that AI agents or assistants were used (CLAUDE.md, AGENTS.md, Co-Authored-By trailers, emoji commits, bot identities), or when it may contain committed secrets (.env files, keys, tokens).
---

# Очистка от следов агентов

Найти и убрать следы агентной разработки из всего, что видит посетитель репозитория.
Даты коммитов, содержимое файлов и структура merge-коммитов сохраняются.

Заодно найти секреты, попавшие в репозиторий.

Что считается следом и секретом: [policy.md](policy.md). Сканер:
[scan-traces.sh](scan-traces.sh), только читает, ничего не меняет.

## Шаги

1. Просканировать локальное состояние и то, что видно на GitHub:

   ```bash
   bash scan-traces.sh <repo>
   bash scan-traces.sh <repo> --published
   ```

2. Разобрать каждую находку: след или ложное срабатывание (например, CSS `cursor`). Если
   неясно, спросить автора. Найденный секрет сразу показать автору по разделу 8
   `policy.md`, значение не выводить.
3. Рабочее дерево: убрать файлы агентов из индекса (`git rm --cached -r <path>`), убрать
   упоминания из текста, закоммитить в ветке `chore/remove-agent-traces` и влить в `main`
   по разделу «Merge» `repo-commit/rules.md`.
4. История, только после подтверждения:
   1. Ветка-копия `backup/original-history` на текущем HEAD.
   2. Новые сообщения в файлы, названные по старому хешу. Проверить линтером. Kysaro
      запускать вне репозитория kysaro, чтобы работал пресет по умолчанию.
   3. `git filter-branch` сохраняет даты автора и коммиттера:
      - сообщения: `--msg-filter`, который печатает файл по `$GIT_COMMIT` или исходное
        сообщение;
      - автор: `--env-filter` с `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`,
        `GIT_COMMITTER_EMAIL`;
      - файлы: `--index-filter 'git rm -r --cached --ignore-unmatch <paths>'`.
   4. Удалить `.git/refs/original`.
   5. Сверить: `git diff --stat backup/original-history HEAD` показывает только задуманное,
      число коммитов и merge-коммитов то же, сканер чистый.
   6. Задать автора в репозитории: `git config user.name` и `git config user.email`.
5. Публикация, только после подтверждения:
   `git push --force-with-lease=main:<старый-sha-на-remote> origin main`. Удалить удалённые
   ветки со старой историей.
6. GitHub, только после подтверждения:
   - PR: `gh api -X PATCH repos/OWNER/REPO/pulls/N -f title=... -f body=...`
     (`gh pr edit` может падать на устаревших полях Projects);
   - релизы: `gh release edit <tag> --notes-file <file>`;
   - комментарии ботов: удалять только те, что подтвердил автор.
7. Повторить `scan-traces.sh <repo> --published`. Сообщить автору всё, что осталось, и
   раздел 7 `policy.md`.
8. Проверить профилактику из раздела 6 `policy.md`. Глобальные настройки менять только
   после подтверждения.

## Спросить автора

- Любое переписывание истории и любой push, особенно force.
- Удаление веток, тегов, комментариев на GitHub. Правка PR и релизов.
- Упоминание, которое может быть частью продукта.
- Найденный секрет: отозван ли он и надо ли чистить историю.
- Переписывать ли старые сообщения, в которых нет следов, но есть нарушения конвенции.

## Нельзя

- `--force` без lease.
- Переписывать историю без ветки-копии.
- Менять что-то за пределами зоны из `policy.md`.
- Выводить значение найденного секрета.

## Готово, когда

- `scan-traces.sh <repo> --published` показывает только принятые автором находки.
- Каждое переписывание подтверждено и сверено с `backup/original-history`.
- Автору сообщено, что осталось и почему.
