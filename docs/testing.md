# Руководство по тестированию

Документ определяет, как проверять систему до уровня professional desktop prototype.

## Философия

Тесты должны доказать:

1. desktop app + local engine работают end-to-end;
2. сценарии угроз действительно детектируются;
3. поведение воспроизводимо для демо;
4. fallback web UI остается рабочим.

## Обязательные уровни тестов

### 1) Unit tests

- rule-engine;
- risk scoring;
- payload validation/parsing;
- desktop API client;
- desktop runtime port selection.

### 2) API tests

Ключевые endpoints:

- `GET /health`
- `GET /api/system/status`
- `POST /api/demo/reset`
- `POST /api/demo/seed`
- `POST /api/ingest/telemetry`
- `GET /api/devices`
- `GET /api/devices/{device_id}`
- `GET /api/alerts`
- `GET /api/stats/summary`
- `GET /api/stats/charts`
- `POST /api/scan/run`

### 3) Integration tests

Проверяют сквозной путь:

`desktop/simulator -> backend engine -> SQLite -> alert query`

### 4) Desktop smoke tests

- desktop API client получает health/devices/alerts;
- backend runtime выбирает свободный порт;
- Reset + Seed Demo наполняет таблицы;
- Run Scan создает новые alerts.

### 5) Fallback dashboard smoke tests

- overview;
- devices;
- alerts;
- device detail.

## Что обязательно покрыть

### Payload validation

- корректные payload принимаются;
- некорректные не ломают систему;
- обязательные поля валидируются;
- timestamps нормализуются.

### Demo controls

- reset очищает `devices`, `telemetry_events`, `alerts`;
- seed создает 4 ожидаемых устройства и воспроизводимый набор событий;
- scan использует фактический base URL backend, а не hardcoded порт.

### Правила детекта

- flood;
- impossible value;
- unknown/spoofed identity;
- low battery;
- firmware mismatch/outdated;
- ML anomaly при доступной модели.

## Acceptance checklist

- [ ] `.\scripts\run_desktop.ps1` запускает desktop app
- [ ] backend стартует из desktop app без ручных фиксов
- [ ] desktop показывает backend/DB/ML status
- [ ] Reset + Seed Demo наполняет устройства и алерты
- [ ] Run Scan создает ожидаемые алерты
- [ ] Export Report сохраняет JSON
- [ ] fallback web-dashboard открывается на выбранном backend-порту
- [ ] `python -m pytest tests/ -q` проходит

## Ручной smoke перед демо

1. Запустить `.\scripts\run_desktop.ps1`.
2. Нажать `Reset + Seed Demo`.
3. Проверить вкладки `Overview`, `Devices`, `Alerts`.
4. Запустить `Run Scan`.
5. Открыть `Device Detail`.
6. Экспортировать отчет.
7. Открыть fallback web UI через меню desktop app.
