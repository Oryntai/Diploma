# Интеллектуальная система мониторинга безопасности IoT

Дипломный проект — локальный прототип системы мониторинга безопасности IoT-устройств с двухуровневым детектом угроз (правила + ML).

## Возможности

- Симуляция 4 типов IoT-устройств (термометр, розетка, камера, замок)
- Приём телеметрии по HTTP и MQTT
- Rule-based детект: 5 сценариев угроз (impossible_value, low_battery, message_flood, firmware_mismatch, unknown_device)
- ML-детект: PyTorch autoencoder на CICIoT2023 (SYN flood, port scan, ARP spoofing, DNS tunnel, DDoS)
- Web-dashboard с KPI, таблицами, Chart.js графиками, тёмной темой
- Экспорт отчётов в JSON
- Запуск сканирования из UI (кнопка Run Scan)
- Демо-сценарии для защиты

## Архитектура

```
simulator → MQTT broker (optional) → FastAPI backend → SQLite → dashboard
                                          ↓
                                    Rule Engine + ML Model
                                          ↓
                                       Alerts
```

## Стек

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Pydantic
- **ML**: PyTorch (autoencoder), CICIoT2023
- **DB**: SQLite
- **UI**: Jinja2, Chart.js, vanilla CSS/JS
- **Messaging**: MQTT (paho-mqtt, Mosquitto)
- **Тесты**: pytest, httpx

## Быстрый запуск

### 1. Установить зависимости

```bash
cd backend
pip install -r requirements.txt
```

### 2. Запустить backend

```bash
cd backend
python -m uvicorn app.main:app --reload
```

### 3. Открыть dashboard

```
http://127.0.0.1:8000/
```

### 4. Отправить нормальную телеметрию

```bash
python simulator/main.py --once --seed 42 --ingest-url http://127.0.0.1:8000/api/ingest/telemetry
```

### 5. Запустить сценарии угроз

```bash
python simulator/scenarios/run_scenario.py --scenario all --ingest-url http://127.0.0.1:8000/api/ingest/telemetry
```

### 6. Запустить тесты

```bash
cd backend
python -m pytest tests/ -v
```

## Или одной командой (PowerShell)

```powershell
.\scripts\run_local.ps1
```

## Типы устройств

| Тип | Поля | Аномалии |
|-----|------|----------|
| Temperature Sensor | temperature, battery, firmware | 70–80°C, батарея 10–25% |
| Smart Plug | power_watts, voltage, is_on | 500–2000W, напряжение 180–280V |
| IP Camera | fps, resolution, bandwidth | fps 1–8, bandwidth 8–15K kbps |
| Smart Door Lock | lock_state, access_attempts | 10–50 попыток доступа |

## Детектируемые угрозы

### Rule Engine (5 правил)
1. `impossible_value` — температура вне [-20, 60]°C
2. `low_battery` — батарея < 20%
3. `message_flood` — >20 сообщений за 60 сек
4. `firmware_mismatch` — смена прошивки
5. `unknown_device` — неизвестное устройство

### ML Model (5 типов атак)
1. SYN Flood — завалить соединениями
2. Port Scan — сканирование портов
3. ARP Spoofing — подмена адреса
4. DNS Tunnel — скрытый канал
5. DDoS — массированная атака

## API

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/health` | Health check |
| GET | `/` | Dashboard overview |
| GET | `/dashboard/devices` | Список устройств |
| GET | `/dashboard/alerts` | Список алертов |
| GET | `/dashboard/devices/{id}` | Детали устройства |
| POST | `/api/ingest/telemetry` | Приём телеметрии |
| GET | `/api/devices` | JSON список устройств |
| GET | `/api/alerts` | JSON список алертов |
| GET | `/api/stats/summary` | Сводка |
| GET | `/api/stats/charts` | Данные для графиков |
| GET | `/api/ml/status` | Статус ML-модели |
| POST | `/api/ml/predict` | ML-инференс |
| GET | `/api/export/report` | Экспорт отчёта |
| POST | `/api/scan/run` | Запуск сканирования |

## Структура проекта

```
backend/
  app/
    main.py              # FastAPI app, routes, rule engine
    models/              # SQLAlchemy ORM (Device, Alert, TelemetryEvent)
    services/
      ml_runtime.py      # ML model loader & inference
      traffic_features.py # CICIoT2023 feature generator
      mqtt_subscriber.py # MQTT listener
    templates/           # Jinja2 HTML pages
    static/              # CSS
  tests/                 # pytest tests
  models/                # ML model artifacts

simulator/
  devices/               # 4 device type simulators
  scenarios/             # 5 threat scenarios
  main.py                # CLI entry point

docs/                    # Architecture, API, threat model, demo script
```

## Документация

- [docs/architecture.md](docs/architecture.md) — архитектура
- [docs/api.md](docs/api.md) — API контракт
- [docs/threat-model.md](docs/threat-model.md) — модель угроз
- [docs/demo-script.md](docs/demo-script.md) — сценарий демо
- [docs/ml-integration.md](docs/ml-integration.md) — ML интеграция
