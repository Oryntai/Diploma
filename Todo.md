# Todo проекта: Интеллектуальный мониторинг безопасности IoT

Этот файл — главный бриф для команды и coding-agents. Он задает границы MVP и порядок разработки.

> Актуальное позиционирование: проект развивается выше уровня дипломного MVP.
> Основной продуктовый интерфейс — desktop app на PySide6, FastAPI остается
> локальным engine, web-dashboard сохранен как fallback/debug UI.

## 1) Миссия

Собрать реалистичный дипломный прототип системы, которая:

- симулирует IoT-устройства;
- принимает телеметрию по MQTT;
- анализирует поведение и выявляет подозрительные события;
- хранит состояние устройств, события и алерты;
- показывает результат в desktop-приложении;
- сохраняет web-dashboard как fallback/debug интерфейс;
- запускается локально на одном ноутбуке.

## 2) Позиционирование

Это **не** enterprise SIEM и не cloud-платформа.

MVP строится на:

- rule-based детекте;
- прозрачной логике алертов;
- простой архитектуре, понятной на защите.

ML допускается только как опциональный слой после стабильного rules-only контура.

## 3) Результат MVP

К завершению MVP в репозитории должна быть рабочая локальная система, где:

1. Симулятор публикует телеметрию минимум 4 типов устройств.
2. Backend получает сообщения из MQTT.
3. Backend сохраняет данные в БД.
4. Детектируется минимум 5 сценариев угроз.
5. Dashboard показывает устройства, состояние, алерты и события.
6. Проект воспроизводимо запускается по инструкции.
7. Есть детерминированный демо-сценарий на защиту.

## 4) Что не делать в первом цикле

- Kubernetes, микросервисы, облака;
- сложный IAM/role-based auth;
- heavy frontend;
- обязательный ML/LLM;
- интеграция с большим количеством реального железа.

## 5) Рекомендуемый стек

Backend:

- Python 3.11+
- FastAPI
- SQLAlchemy
- Pydantic

Messaging:

- MQTT
- Eclipse Mosquitto

DB:

- SQLite (MVP)

UI:

- PySide6 desktop app
- Jinja2
- Chart.js
- plain CSS/JS

Тесты:

- pytest
- httpx

## 6) Архитектура верхнего уровня

```text
simulator -> MQTT broker -> FastAPI backend -> SQLite -> dashboard
```

Backend отвечает за:

- подписку на MQTT-топики;
- валидацию payload;
- upsert устройств;
- rule-check + risk score;
- создание алертов;
- сохранение и выдачу данных через API/UI.

## 7) Типы устройств для симуляции

Минимум 4 профиля:

1. Temperature sensor
2. Smart plug
3. IP camera
4. Smart door lock

Для каждого профиля:

- normal/abnormal режим;
- настраиваемый интервал публикации;
- поддержка seed для детерминированного демо.

## 8) Сценарии угроз (минимум 5)

Приоритетные:

1. Message flood
2. Impossible values
3. Unknown/spoofed device_id
4. Repeated auth failures
5. Firmware mismatch/outdated firmware

Дополнительно:

- frequent reboot/unstable transitions;
- behavior deviation.

## 9) Стратегия детекта

### Фаза 1 (обязательная)

Rule-based detection + risk score (0–100).

Пример начисления:

- low: +15
- medium: +30
- high: +50
- потолок: 100

### Фаза 2 (опциональная)

Легкий anomaly слой (например, Isolation Forest), не ломающий работу системы при отключении.

## 10) Модель данных (ядро)

Таблицы:

- `devices`
- `telemetry_events`
- `device_metrics`
- `alerts`
- `scenarios`

Правило идентичности:

- ожидаемые устройства предрегистрированы;
- неизвестный sender логируется и алертится;
- unknown sender не должен молча попадать в trusted-реестр.

## 11) MQTT topics

Рекомендуемая схема:

- `iot/devices/{device_type}/{device_id}/telemetry`
- `iot/devices/{device_type}/{device_id}/status`
- `iot/devices/{device_type}/{device_id}/security`

## 12) Целевая структура репозитория

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
  requirements.txt or pyproject.toml

simulator/
  devices/
  scenarios/
  main.py

docs/
  architecture.md
  threat-model.md
  api.md
  demo-script.md
  diploma-notes.md

scripts/
  run_local.ps1
  seed_demo_data.py

docker/
  mosquitto/

README.md
Todo.md
```

## 13) Минимальные backend-фичи

- MQTT subscriber lifecycle
- payload validation
- device upsert
- rule engine
- alert service
- summary service
- HTML routes
- JSON API routes

Базовые endpoints:

- `GET /health`
- `GET /api/devices`
- `GET /api/devices/{device_id}`
- `GET /api/alerts`
- `GET /api/alerts/recent`
- `GET /api/stats/summary`
- `POST /api/scenarios/start`
- `POST /api/scenarios/stop`

## 14) Требования к dashboard

Нужны страницы:

1. Overview
2. Devices
3. Alerts
4. Device detail

UI должен работать на ноутбуке и показывать человеко-понятные причины алертов.

## 15) Фазы работ

### Phase 0 — Bootstrap

- структура репозитория;
- skeleton backend;
- skeleton simulator;
- базовая README-инструкция.

### Phase 1 — Core Data Flow

- локальный broker;
- публикация из симулятора;
- ingest в backend;
- запись в БД.

### Phase 2 — Multi-device Simulation

- 4 профиля устройств;
- normal behavior;
- детерминированный demo mode.

### Phase 3 — Rule-Based Detection

- rule engine;
- severity + risk;
- создание алертов;
- выдача алертов в API/UI.

### Phase 4 — Dashboard

- все 4 обязательные страницы.

### Phase 5 — Demo readiness

- запуск/остановка сценариев;
- 3–5 минутный воспроизводимый демо-поток.

### Phase 6 — Optional intelligence

- опциональный anomaly слой.

### Phase 7 — Diploma packaging

- документы, скриншоты, отчет, заметки для защиты.

## 16) Тестирование

Обязательные типы:

- unit tests (rules, validation);
- API tests;
- integration MQTT ingest test;
- dashboard smoke tests.

Базовый checklist:

- backend стартует без ручных фиксов;
- simulator стартует без ручных фиксов;
- таблицы БД создаются корректно;
- стек поднимается воспроизводимо;
- normal mode дает меньше алертов, чем attack mode.

## 17) Демо-сценарий

Минимальная последовательность:

1. Поднять broker + backend.
2. Запустить simulator normal mode.
3. Показать baseline в dashboard.
4. Включить flood.
5. Включить spoofed device.
6. Включить impossible value.
7. Показать алерты и объяснение причины на device detail.

## 18) Обязательные документы

В `docs/` должны поддерживаться в актуальном состоянии:

- `architecture.md`
- `threat-model.md`
- `api.md`
- `demo-script.md`
- `testing.md`
- `diploma-notes.md`

## 19) Значения по умолчанию

- backend: FastAPI
- DB: SQLite
- broker: Mosquitto
- UI: Jinja2 + Chart.js
- timestamps: UTC
- scope: локальный лабораторный прототип

## 20) Правила исполнения

1. Сначала smallest working end-to-end.
2. Никакого обязательного ML до rules-only контура.
3. Не переусложнять архитектуру.
4. Код и документы должны быть понятны студентам.
5. Причины алертов — всегда явные и читаемые.

## 21) Ближайшие задачи

- scaffold репозитория;
- health endpoint;
- SQLite + первые модели;
- один temperature simulator;
- MQTT publish/ingest;
- минимальный dashboard;
- первые 2 правила (impossible value + flood);
- локальная инструкция запуска.

## 22) Критерий готовности проекта

Проект готов, когда:

- все ключевые этапы запускаются по документации;
- есть минимум 4 типа устройств;
- есть минимум 5 сценариев детекта;
- алерты видны в UI и содержат понятные причины;
- есть тесты и пакет документов для защиты;
- есть воспроизводимый демо-проход.

## 23) Stretch goals после MVP

- optional anomaly mode;
- экспорт отчетов;
- исторические графики здоровья устройств;
- PostgreSQL;
- интеграция с одним реальным устройством.

## 24) Что считается успехом

Успех — это целостная, объяснимая система (а не набор разрозненных скриптов), где видно полный путь: телеметрия -> анализ -> алерт -> визуализация.
