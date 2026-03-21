# Руководство по локальному запуску

Документ описывает, как подготовить окружение и с чего начать реализацию по `Todo.md`.

## Цель

Используйте этот документ, когда:

- студент впервые поднимает проект;
- coding-agent начинает реализацию с нуля;
- команде нужен единый checklist запуска на «чистой» машине.

## Базовые решения для MVP

- Python: `3.11+`
- Backend: `FastAPI`
- Broker: `Eclipse Mosquitto`
- База: `SQLite`
- UI: `Jinja2`
- Графики: `Chart.js`
- Тесты: `pytest`, `httpx`

## Предусловия

Нужно установить:

- Python 3.11+
- pip
- Git
- Mosquitto (локально или через Docker)
- современный браузер

Опционально:

- Docker Desktop
- DB Browser for SQLite
- VS Code

## Минимальная структура

```text
backend/
  app/
  tests/
simulator/
  devices/
  scenarios/
docs/
scripts/
docker/
```

## Минимальные зависимости backend

Runtime:

- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `pydantic`
- `paho-mqtt`
- `jinja2`

Тесты:

- `pytest`
- `httpx`

После стабилизации rules-only пути можно добавить:

- `scikit-learn`
- `pandas`

## Рекомендуемые переменные окружения

```env
APP_ENV=local
APP_HOST=127.0.0.1
APP_PORT=8000
DATABASE_URL=sqlite:///./iot_monitor.db
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_TOPIC_ROOT=iot/devices
DEFAULT_TIMEZONE=UTC
ENABLE_ANOMALY_DETECTION=false
SIMULATOR_SEED=42
```

Правила:

- timestamps хранить в UTC;
- anomaly detection выключен по умолчанию;
- без скрытых «магических» значений в коде.

## Путь запуска (native)

1. Установить Python 3.11+.
2. Создать venv и активировать.
3. Установить backend зависимости.
4. Поднять Mosquitto.
5. Убедиться, что broker доступен на `127.0.0.1:1883`.
6. Запустить FastAPI.
7. Запустить simulator.

## Путь запуска (минимум Docker)

Используйте Docker только если он **упрощает** запуск.

Рекомендованный компромисс:

- Mosquitto в Docker (опционально);
- FastAPI и simulator — локально в первый цикл.

## Первый успешный bring-up

1. Запустить Mosquitto.
2. Запустить backend.
3. Проверить `GET /health`.
4. Запустить один temperature simulator.
5. Отправить telemetry в MQTT topic.
6. Проверить, что backend принял и сохранил событие.

## Критерий готовности setup-этапа

Этап считается завершенным, когда:

- новый участник может поднять проект по инструкции;
- backend и simulator стартуют без ad-hoc фиксов;
- broker/API/DB endpoints задокументированы явно;
- последовательность воспроизводится минимум на двух ноутбуках.
