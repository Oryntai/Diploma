# API-контракт

Документ фиксирует backend API для локального engine. Основной пользовательский
интерфейс — PySide6 desktop app; HTML dashboard остается fallback/debug UI.

Важно: это контракт, а не обещание, что все endpoints уже реализованы.

## Принципы API

- API остается небольшим и локальным;
- ответы JSON простые и прозрачные;
- приоритет — поддержка desktop app, fallback dashboard и демо;
- причины алертов человеко-читаемые;
- optional ML не обязателен для API.

## Базовые предпосылки

- backend: FastAPI;
- API возвращает JSON;
- HTML страницы отдаются отдельно (Jinja2);
- timestamps сериализуются в UTC;
- unknown devices не должны молча считаться trusted.

## Минимальный набор endpoint-ов

### `GET /api/system/status`

Назначение: единая сводка для header desktop-приложения.

Возвращает:

- `backend_status`
- `database_url`
- `database_ready`
- `mqtt_enabled`
- `ml_status`
- `summary`

### `POST /api/demo/reset`

Назначение: очистить локальную SQLite БД от demo-данных.

Возвращает количество удаленных устройств, telemetry events и alerts.

### `POST /api/demo/seed`

Назначение: загрузить детерминированный demo dataset для desktop-приложения.

Seed создает 4 ожидаемых устройства, baseline telemetry, rule-based alerts и
ML/anomaly пример, если модель доступна.

### `POST /api/ingest/telemetry`

Назначение: прием telemetry payload от simulator/adapters.

Пример запроса:

```json
{
  "device_id": "temp-001",
  "device_type": "temperature_sensor",
  "timestamp": "2026-03-21T10:00:00Z",
  "temperature": 24.3,
  "battery": 92,
  "firmware_version": "1.0.2",
  "mode": "normal"
}
```

Пример ответа:

```json
{
  "saved_event_id": 1,
  "alerts_created": 1,
  "alert_ids": [1],
  "device_status": "unverified"
}
```

Примечание: при первом появлении `device_id` backend помечает устройство как `unverified`
и создает alert `unknown_device`.

### `GET /health`

Назначение: проверка, что backend жив.

Пример:

```json
{
  "status": "ok",
  "service": "backend"
}
```

### `GET /api/devices`

Назначение: список известных устройств.

Поля элемента:

- `device_id`
- `device_type`
- `status`
- `battery`
- `firmware_version`
- `last_seen_at`
- `risk_score`
- `risk_level`
- `main_issue`
- `recommendation`

### `GET /api/devices/{device_id}`

Назначение: карточка устройства + recent telemetry + recent alerts.

### `GET /api/alerts`

Назначение: список алертов по времени.

Поля:

- `id`
- `device_id`
- `alert_type`
- `severity`
- `risk_score`
- `reason`
- `source`
- `status`
- `created_at`

### `GET /api/alerts/recent`

Назначение: короткая лента последних алертов (обычно 10–20).

### `GET /api/stats/summary`

Назначение: данные для overview-виджетов.

Поля:

- `total_devices`
- `online_devices`
- `active_alerts`
- `alerts_by_severity`
- `alerts_last_hour`

### `POST /api/scan/run`

Назначение: запуск набора demo-сценариев угроз против текущего backend.

Важно: endpoint строит ingest URL из фактического request base URL, поэтому
работает и при auto-start desktop на портах `8000-8010`.

## Правила обработки ошибок

- невалидный input -> понятный client error;
- неизвестный device -> понятный not found;
- внутренние ошибки не раскрывают stack trace пользователю;
- reason в алерте должен оставаться понятным.

## Политика unknown/spoofed identity

- ожидаемые устройства предрегистрированы;
- unknown sender может отображаться в trace events/alerts;
- unknown sender не должен автоматически попадать в trusted devices (в текущей реализации
  устройство получает статус `unverified` и требует ручной верификации);
- spoofing должен подниматься как алерт.

## Связь API и страниц

- desktop header -> `GET /api/system/status`
- overview -> `GET /api/stats/summary`, `GET /api/stats/charts`
- devices -> `GET /api/devices`
- alerts -> `GET /api/alerts`
- device detail -> `GET /api/devices/{device_id}`
- demo controls -> `POST /api/demo/reset`, `POST /api/demo/seed`, `POST /api/scan/run`

## Recommendations по алертам

Подробный каталог рекомендаций по каждому alert_type:

- `docs/recommendations.md`

Как это встраивать в API/UI:

- `Risk Distribution` на overview — текст "что значит класс" и "почему активен";
- `Recent Security Alerts` — быстрый блок `What to do` для конкретного `alert_type`;
- `Device Detail` — чек-лист действий и статус выполнения;
- API (следующий шаг) — добавить `recommendation_steps` в `/api/alerts`
  или отдельный endpoint `GET /api/recommendations?alert_type=...`.

## Критерий готовности API

- реализован минимальный набор endpoint-ов;
- есть ключевые поля в ответах;
- desktop app и fallback dashboard рендерятся на этих данных;
- тесты покрывают критические маршруты;
- документация не расходится с реальным поведением.
