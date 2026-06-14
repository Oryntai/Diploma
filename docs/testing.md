# Руководство по тестированию

Документ определяет, как проверять систему как FastAPI web prototype.

## Философия

Тесты должны доказать:

1. FastAPI app работает end-to-end;
2. desktop device simulator отправляет samples в FastAPI;
3. сетевые сценарии угроз действительно создают ML alerts;
4. поведение воспроизводимо для демо.

## Обязательные уровни тестов

### 1) API tests

- `GET /health`
- `GET /api/system/status`
- `GET /api/registered-devices`
- `POST /api/network/sample`
- `POST /api/demo/scenario`
- `POST /api/demo/device-tests`
- `POST /api/scan/run`
- `GET /api/stats/summary`
- `GET /api/stats/charts`
- `GET /api/devices`
- `GET /api/alerts`

### 2) Dashboard smoke tests

- `GET /`
- `GET /dashboard/devices`
- `GET /dashboard/devices/{device_id}`
- `GET /dashboard/alerts`

### 3) Integration tests

Проверяют сквозной путь:

`desktop simulator payload -> FastAPI endpoint -> CICIoT adapter -> PyTorch autoencoder -> alert row -> dashboard JSON`.

## Acceptance checklist

- [ ] `.\scripts\run_local.ps1` запускает FastAPI dashboard.
- [ ] `.\scripts\run_desktop_simulator.ps1` запускает desktop device simulator.
- [ ] `http://127.0.0.1:8000/` открывается без desktop-клиента.
- [ ] Desktop simulator отправляет normal и flood samples в `/api/network/sample`.
- [ ] `Run Scan` создает ожидаемые ML alerts.
- [ ] `Devices` показывает пять зарегистрированных устройств.
- [ ] `Alerts` показывает причины, severity, source и timestamp.
- [ ] `Export Report` отдает текстовый отчет текущей сессии.
- [ ] `python -m pytest backend\tests -q` проходит.
- [ ] `python -m compileall backend desktop_simulator simulator` проходит.

## Ручной smoke перед демо

1. Запустить `.\scripts\run_local.ps1`.
2. Открыть `http://127.0.0.1:8000/`.
3. Нажать `Run Scan`.
4. Проверить `Overview`, `Devices`, `Alerts`.
5. Открыть карточку одного устройства.
6. Скачать отчет через `Export Report`.
