# Статус реализации

Документ отражает текущее состояние проекта после перехода к FastAPI web prototype.

## Выполнено

- [x] Создана базовая структура папок (`backend`, `simulator`, `scripts`, `docker/mosquitto`).
- [x] Добавлен FastAPI backend-скелет с `GET /health`.
- [x] Добавлен SQLite слой и первые модели (`Device`, `TelemetryEvent`, `Alert`).
- [x] Добавлен temperature simulator с режимом `--once` и seed-детерминизмом.
- [x] Обновлен `README.md` с инструкцией запуска текущего этапа.
- [x] Добавлены минимальные smoke-тесты.
- [x] FastAPI стал основной пользовательской точкой входа.
- [x] Добавлен черный минимальный web-dashboard.
- [x] Добавлены API `system/status`, `demo/scenario`, `scan/run`.
- [x] Добавлен запуск `.\scripts\run_local.ps1`.
- [x] Старый desktop-код удален; проект поддерживает FastAPI web dashboard.

## Проверки качества

- [x] Архитектурная согласованность.
- [x] Smoke-проверка backend и БД.
- [x] Проверка simulator и документации.
- [x] Регрессионная проверка scope.
- [x] Dashboard routes проверены smoke-тестом.
- [x] Scan запускается через FastAPI endpoint `/api/scan/run`.
