# Дорожная карта

Этот документ превращает `Todo.md` в поэтапный план для команды 3–4 человек.

## Принципы

- соблюдать границы MVP;
- рано получать end-to-end результат;
- каждый этап должен быть демонстрируемым;
- сначала rules-only, потом optional ML;
- документация обновляется вместе с кодом.

## Роли

- **Backend owner**: FastAPI, БД, MQTT ingest, rules.
- **Simulation owner**: профили устройств, сценарии, seed-детерминизм.
- **UI owner**: Jinja2/Chart.js, страницы и интеграция.
- **Docs/QA owner**: README/docs, тесты, demo-script, материалы диплома.

## Фазы

### Phase 0 — Bootstrap

Результат:

- scaffold репозитория;
- backend стартует;
- simulator entrypoint существует;
- базовая инструкция запуска готова.

### Phase 1 — Core Data Flow

Результат:

- один simulator публикует в MQTT;
- backend подписывается и принимает;
- события сохраняются в SQLite.

### Phase 2 — Multi-Device Simulation

Результат:

- 4 разных профиля устройств;
- реалистичный normal mode;
- детерминированный demo mode.

### Phase 3 — Rule-Based Detection

Результат:

- реализовано минимум 5 сценариев детекта;
- алерты содержат type/severity/score/reason;
- normal mode дает меньше алертов, чем attack mode.

### Phase 4 — Dashboard

Результат:

- страницы overview/devices/alerts/device-detail;
- reviewer понимает состояние системы только по UI.

### Phase 5 — Demo Readiness

Результат:

- контролируемые start/stop сценариев;
- воспроизводимый 3–5 минутный демо-проход.

### Phase 6 — Optional Intelligence

Результат:

- optional anomaly interface;
- rules-only режим продолжает работать независимо.

### Phase 7 — Diploma Packaging

Результат:

- полный комплект docs;
- тестовые доказательства;
- скриншоты и сценарий защиты.

## Gate-проверки между фазами

### Gate A (перед multi-device)

- один device уже работает end-to-end;
- есть реальное сохранение в БД;
- health endpoint стабилен.

### Gate B (перед ML)

- rules-only контур стабилен;
- минимум 5 сценариев уже реализованы/почти готовы;
- dashboard показывает алерты и risk context.

### Gate C (перед защитой)

- запуск воспроизводится на чистой машине;
- демо работает без интернета;
- docs и скриншоты соответствуют реальной реализации.

## Критерий выполнения roadmap

- этапы выполняются в указанном порядке;
- на каждом этапе есть проверяемый результат;
- нет ухода в stretch goals до завершения MVP.
