# API-контракт

Документ фиксирует минимальный backend API для MVP.

Важно: это контракт, а не обещание, что все endpoints уже реализованы.

## Принципы API

- API остается небольшим и локальным;
- ответы JSON простые и прозрачные;
- приоритет — поддержка dashboard и демо;
- причины алертов человеко-читаемые;
- optional ML не обязателен для API.

## Базовые предпосылки

- backend: FastAPI;
- API возвращает JSON;
- HTML страницы отдаются отдельно (Jinja2);
- timestamps сериализуются в UTC;
- unknown devices не должны молча считаться trusted.

## Минимальный набор endpoint-ов

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
- `name`
- `status`
- `firmware_version`
- `last_seen_at`
- `risk_score`

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

### `POST /api/scenarios/start`

Назначение: запуск сценария симуляции.

Пример запроса:

```json
{
  "scenario_name": "message_flood",
  "device_id": "temp-001"
}
```

### `POST /api/scenarios/stop`

Назначение: остановка сценария и возврат в normal mode.

## Правила обработки ошибок

- невалидный input -> понятный client error;
- неизвестный device -> понятный not found;
- внутренние ошибки не раскрывают stack trace пользователю;
- reason в алерте должен оставаться понятным.

## Политика unknown/spoofed identity

- ожидаемые устройства предрегистрированы;
- unknown sender может отображаться в trace events/alerts;
- unknown sender не должен автоматически попадать в trusted devices;
- spoofing должен подниматься как алерт.

## Связь API и страниц

- overview -> `GET /api/stats/summary`
- devices -> `GET /api/devices`
- alerts -> `GET /api/alerts`
- device detail -> `GET /api/devices/{device_id}`

## Критерий готовности API

- реализован минимальный набор endpoint-ов;
- есть ключевые поля в ответах;
- dashboard рендерится на этих данных;
- тесты покрывают критические маршруты;
- документация не расходится с реальным поведением.
