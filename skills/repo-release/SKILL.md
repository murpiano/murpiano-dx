---
name: repo-release
description: Use when the user asks to start, pause, resume or remove automatic releases of a repository, to preview the next release, or to rewrite the notes of a GitHub release.
---

# Релизы

Релизы выпускаются сами после каждого зелёного CI в `main`. Агент только управляет ими по
командам пользователя.

Правила: [rules.md](rules.md). Файлы для проекта: [release.yml](release.yml),
[release.sh](release.sh).

## Команды

### «Начни релизы»

1. Проверить: репозиторий на GitHub, в `main` есть workflow с `name: CI` и он зелёный.
   Если CI нет, сначала настроить его по скиллу `repo-readme`.
2. Проверить, что файл `~/.config/murpiano-dx/release-token` есть и не пустой. Если нет,
   попросить пользователя запустить `bash install.sh` из `murpiano-dx` и ввести токен
   (раздел 4 `rules.md`). Токен не читать и не выводить.
3. Скопировать `release.yml` в `.github/workflows/release.yml` и `release.sh` в
   `.github/scripts/release.sh`.
4. Если бейджа Release нет и репозиторий публичный, добавить его в README
   (раздел 6 `rules.md`).
5. Закоммитить: `ci: release on every push to main`. Push.
6. `gh secret set RELEASE_TOKEN -R OWNER/REPO < ~/.config/murpiano-dx/release-token`.
7. Если тегов `v*` ещё нет, выпустить первый релиз вручную: версия `v1.0.0` (или версия
   из `package.json`, если она не ниже и ещё не выпущена), заметки по разделу 5,
   `gh release create vX.Y.Z --target main --title vX.Y.Z --notes-file notes.md`.
8. `gh variable set RELEASES --body on -R OWNER/REPO`.

### «Приостанови релизы»

`gh variable set RELEASES --body paused -R OWNER/REPO`.

### «Возобнови релизы»

`gh variable set RELEASES --body on -R OWNER/REPO`. Коммиты, накопленные за паузу, войдут в
следующий релиз.

### «Убери релизы»

Необратимо. Перед выполнением показать список релизов и тегов и получить подтверждение.

1. `gh variable set RELEASES --body off -R OWNER/REPO`.
2. Для каждого релиза: `gh release delete <tag> --cleanup-tag --yes -R OWNER/REPO`.
3. Удалить `.github/workflows/release.yml`, `.github/scripts/release.sh`, бейдж Release.
4. Закоммитить: `ci: stop publishing releases`. Push.
5. `gh secret delete RELEASE_TOKEN -R OWNER/REPO`.

### «Покажи следующий релиз»

`bash .github/scripts/release.sh --dry-run` в проекте. Показать версию и заметки.

### «Перепиши заметки релиза vX.Y.Z»

Прочитать коммиты релиза (`git log <прошлый тег>..vX.Y.Z`) и их изменения, написать
заметки вручную по разделу 5, показать пользователю, после подтверждения
`gh release edit vX.Y.Z --notes-file notes.md`.

## Нельзя

- Выводить или копировать токен куда-либо, кроме `gh secret set`.
- Менять `version` в `package.json` ради релиза.
- Выпускать релиз, если CI на этом коммите не зелёный.

## Готово, когда

- «Начни»: `release.yml` и `release.sh` в `main`, секрет и `RELEASES=on` заданы, тег `v*`
  есть, бейдж в README (для публичного репозитория).
- «Приостанови», «Возобнови»: `gh variable get RELEASES` показывает новое значение.
- «Убери»: релизов и тегов нет, файлов релиза и бейджа нет, `RELEASES=off`.
