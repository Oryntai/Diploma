# Руководство по локальному запуску

Документ описывает актуальный запуск проекта после перехода к FastAPI web
dashboard и отдельному desktop device simulator.

## Цель

Используйте этот документ, когда:

- студент впервые поднимает проект;
- нужно быстро проверить backend, dashboard и simulator;
- команде нужен единый checklist запуска на чистой машине.

## Базовые решения MVP

- Python: `3.11+`
- Backend: `FastAPI`
- UI: `Jinja2` dashboard
- Desktop simulator: `tkinter`
- База: `SQLite`
- ML: `PyTorch` autoencoder
- Feature space: `CICIoT2023`, 46 network features
- Тесты: `pytest`, `httpx`

## Предусловия

Нужно установить:

- Python 3.11+
- pip
- Git
- современный браузер

Опционально:

- DB Browser for SQLite
- VS Code
- Docker Desktop, если отдельно нужен Mosquitto для экспериментов

## Минимальная структура

```text
backend/             FastAPI app, templates, services, models, tests
desktop_simulator/   desktop sender for FastAPI network samples
simulator/           CLI/device scenario helpers
docs/                documentation
scripts/             launch scripts
docker/              optional Mosquitto config
```

## Установка зависимостей

```powershell
python -m pip install -r backend\requirements.txt
```

`tkinter` используется для desktop simulator и обычно поставляется вместе с
Python на Windows.

## Запуск backend и dashboard

```powershell
.\scripts\run_local.ps1
```

Или вручную:

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Открыть dashboard:

```text
http://127.0.0.1:8000/
```

## Запуск desktop device simulator

Backend должен быть уже запущен.

```powershell
.\scripts\run_desktop_simulator.ps1
```

В окне simulator:

1. Проверить `FastAPI URL`: `http://127.0.0.1:8000`.
2. Нажать `Health`.
3. Выбрать тип устройства, например `temperature_sensor`.
4. Отправить `normal` preset через `Send Preset`.
5. Изменить поля в `Custom Sample` и нажать `Send Custom`.
6. Нажать `Send Random Sample` или запустить `Start Device Stream`.
7. Проверить alerts в dashboard.

`Start Device Stream` имитирует выбранный device type: сначала идут штатные
samples, затем редкий короткий incident burst, после чего поток возвращается к
штатной работе.

Simulator отправляет JSON напрямую в:

```text
POST /api/network/sample
```

## Проверка

```powershell
python -m pytest backend\tests -q
python -m compileall backend desktop_simulator simulator
```

## Runtime data

- SQLite хранит registered devices и generated alert rows.
- Активный backend процесс держит alerts в памяти для live dashboard refresh.
- `logs/network_samples.log` содержит evidence по принятым samples.
- `reports/` зарезервирован под экспортированные artifacts.

## Первый успешный bring-up

1. Запустить `.\scripts\run_local.ps1`.
2. Проверить `GET /health`.
3. Открыть dashboard.
4. Запустить `.\scripts\run_desktop_simulator.ps1`.
5. Отправить normal sample: alerts должны быть пустыми.
6. Отправить flood sample: должен появиться `ml_autoencoder` alert.
7. Открыть `Alerts` и `Devices`.
