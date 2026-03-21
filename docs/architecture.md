# Архитектура проекта

Документ переводит `Todo.md` в практичную архитектуру, которую легко реализовать и объяснить на защите.

## Цели архитектуры

- локальный запуск на одном ноутбуке;
- понятность для студентов;
- модульность без переусложнения;
- объяснимые алерты и решения.

## Контекст системы

Базовый поток данных:

```text
simulator -> MQTT broker -> FastAPI backend -> SQLite -> dashboard
```

Роли компонентов:

- `simulator` генерирует телеметрию устройств;
- `Mosquitto` доставляет сообщения по MQTT;
- `backend` валидирует, анализирует и сохраняет данные;
- `SQLite` хранит состояние, события и алерты;
- `dashboard` показывает состояние и риски.

## Компоненты

### 1) Simulator

- минимум 4 профиля устройств;
- normal/abnormal режимы;
- детерминированные seed для воспроизводимого демо.

### 2) MQTT broker

- локальный Mosquitto;
- простая маршрутизация сообщений от simulator к backend.

### 3) FastAPI backend

- подписка на топики;
- валидация payload;
- upsert устройств;
- rule-engine и risk scoring;
- создание алертов;
- API + HTML страницы.

### 4) SQLite

- хранение `devices`, `telemetry_events`, `alerts` и связанных сущностей;
- легкий локальный дебаг.

### 5) Dashboard

- overview;
- список устройств;
- список алертов;
- детальная страница устройства.

### Целевая композиция страницы Overview

Для первого демонстрационного экрана фиксируем структуру (по утвержденному референсу):

1. Header: заголовок + action-кнопки `Export Report` и `Run Scan`.
2. KPI row: 4 карточки (`Total Devices`, `Active Alerts`, `High/Critical Risk`, `Avg. Security Score`).
3. Main content row:
   - слева `Device Overview` (таблица устройств и текущих проблем);
   - справа `Risk Distribution` (severity bars) + `Recommendations`.
4. Bottom row:
   - слева `Recent Security Alerts`;
   - справа `System Flow` (этапы работы системы).

Это целевой baseline для MVP dashboard. Дополнительные визуальные улучшения допускаются только если не ломают эту иерархию и читаемость.

## Ключевые решения

1. **Monolith first**: один FastAPI-сервис, без microservices.
2. **Rules before ML**: сначала стабильный rules-only контур.
3. **SQLite first**: быстрый локальный старт, потом возможна миграция.
4. **Server-rendered UI**: Jinja2 + Chart.js, без тяжелого frontend.

## Рекомендуемая структура

```text
backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
    templates/
    static/
    main.py
  tests/

simulator/
  devices/
  scenarios/
  main.py
```

## Поток обработки telemetry

1. Simulator формирует payload.
2. Публикация в MQTT topic.
3. Backend получает сообщение.
4. Payload валидируется.
5. Обновляется/создается запись устройства.
6. Событие сохраняется в БД.
7. Rule-engine вычисляет срабатывания.
8. Считается risk score.
9. Создаются алерты.
10. Данные отдаются в API/UI.

## MQTT topics

- `iot/devices/{device_type}/{device_id}/telemetry`
- `iot/devices/{device_type}/{device_id}/status`
- `iot/devices/{device_type}/{device_id}/security`

Правила:

- lowercase сегменты;
- в topic и payload присутствуют `device_type` и `device_id`;
- payload self-describing (`device_id`, `device_type`, `timestamp`).

## Политика идентичности устройства

- ожидаемые устройства предрегистрированы;
- unknown sender сохраняется как событие + алерт;
- unknown sender не добавляется автоматически в trusted-реестр;
- mismatch между topic identity и payload identity -> high severity spoofing alert.

## Минимальный набор API

- `GET /health`
- `GET /api/devices`
- `GET /api/devices/{device_id}`
- `GET /api/alerts`
- `GET /api/alerts/recent`
- `GET /api/stats/summary`
- `POST /api/scenarios/start`
- `POST /api/scenarios/stop`

## Критерий следования архитектуре

Архитектура соблюдается, когда:

- ingest/analysis/API/UI реализованы в одном backend процессе;
- broker локальный и воспроизводимый;
- правила изолированы от транспорта и рендеринга;
- ML остается опциональным слоем;
- ключевые компоненты объясняются за 1–2 минуты на защите.
