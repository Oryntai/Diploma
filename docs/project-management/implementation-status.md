# Статус реализации

Документ отражает текущее состояние проекта после перехода к desktop prototype.

## Выполнено

- [x] Создана базовая структура папок (`backend`, `simulator`, `scripts`, `docker/mosquitto`).
- [x] Добавлен FastAPI backend-скелет с `GET /health`.
- [x] Добавлен SQLite слой и первые модели (`Device`, `TelemetryEvent`, `Alert`).
- [x] Добавлен temperature simulator с режимом `--once` и seed-детерминизмом.
- [x] Обновлен `README.md` с инструкцией запуска текущего этапа.
- [x] Добавлены минимальные smoke-тесты.
- [x] Добавлен PySide6 desktop-клиент как основной интерфейс.
- [x] Desktop app умеет запускать локальный backend на свободном порту.
- [x] Добавлены API `system/status`, `demo/reset`, `demo/seed`.
- [x] Web-dashboard сохранен как fallback/debug UI.
- [x] Добавлен запуск `.\scripts\run_desktop.ps1`.

## Проверки качества

- [x] Архитектурная согласованность.
- [x] Smoke-проверка backend и БД.
- [x] Проверка simulator и документации.
- [x] Регрессионная проверка scope.
- [x] Desktop API client покрыт unit-тестом.
- [x] Scan больше не зависит от hardcoded порта `8000`.
