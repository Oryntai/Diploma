# Руководство по тестированию

Документ определяет, как проверять систему от первого коммита до готовности к защите.

## Философия

Тесты должны доказать:

1. система работает end-to-end;
2. сценарии угроз действительно детектируются;
3. поведение воспроизводимо для демо.

## Обязательные уровни тестов

### 1) Unit tests

Проверяют изолированно:

- rule-engine;
- risk scoring;
- payload validation/parsing.

### 2) API tests

Проверяют ключевые endpoints:

- `GET /health`
- `GET /api/devices`
- `GET /api/devices/{device_id}`
- `GET /api/alerts`
- `GET /api/alerts/recent`
- `GET /api/stats/summary`

### 3) Integration tests

Проверяют сквозной путь:

`simulator -> MQTT -> backend -> SQLite -> alert query`

### 4) Dashboard smoke tests

Проверяют рендер страниц:

- overview;
- devices;
- alerts;
- device detail.

### 5) Visual layout checks (по референс-скринам)

Для страницы overview дополнительно проверяем:

- наличие header с двумя кнопками (`Export Report`, `Run Scan`);
- наличие 4 KPI-карточек в первой строке;
- наличие таблицы `Device Overview` с 7 колонками;
- наличие блока `Risk Distribution` с уровнями `Critical/High/Medium/Low`;
- наличие блока `Recommendations`;
- наличие блока `Recent Security Alerts`;
- наличие блока `System Flow` на 5 шагов.

## Что обязательно покрыть

### Payload validation

- корректные payload принимаются;
- некорректные не ломают систему;
- обязательные поля валидируются;
- timestamps нормализуются.

### Device upsert

- новые устройства создаются;
- повторные сообщения обновляют `last_seen_at`;
- firmware сохраняется корректно.

### Правила детекта

Минимум:

- flood;
- impossible value;
- unknown/spoofed identity;
- repeated auth failures;
- firmware mismatch/outdated.

### Risk scoring

- severity добавляет ожидаемые баллы;
- итог ограничен 100;
- normal mode < attack mode по риску.

## Acceptance checklist

- [ ] backend стартует без ручных фиксов
- [ ] simulator стартует без ручных фиксов
- [ ] таблицы БД создаются корректно
- [ ] локальный запуск воспроизводим
- [ ] минимум 5 сценариев дают ожидаемые алерты
- [ ] normal mode дает меньше алертов, чем attack mode
- [ ] dashboard страницы открываются
- [ ] причины алертов читаемы человеком
- [ ] overview визуально совпадает с целевым референсом по блокам
- [ ] severity-бейджи и статусы устройств различимы по цвету

## Матрица сценариев (шаблон)

| Сценарий | Триггер | Ожидаемый алерт | Severity | Доказательство |
| --- | --- | --- | --- | --- |
| Flood | очень частая публикация | flood alert | medium/high | API + скриншот |
| Impossible value | значение вне диапазона | anomaly/value alert | medium | event + alert |
| Spoofed/unknown | неизвестный `device_id` | spoofing alert | high | logs + API |
| Auth failures | серия неудачных auth | brute-force alert | high | reason text |
| Firmware mismatch | неподдерживаемая версия | firmware alert | medium | device detail |

## Ручной smoke перед демо

1. Поднять broker/backend/simulator.
2. Проверить `/health`.
3. Убедиться, что устройства видны.
4. Запустить normal mode.
5. Запустить подозрительный сценарий.
6. Проверить алерт в API и UI.

## Критерий готовности тестирования

Тестирование достаточно для MVP, если:

- есть все обязательные уровни проверок;
- 5+ сценариев детекта подтверждены;
- есть доказательства (скриншоты, API ответы, отчеты);
- результаты воспроизводимы на защите.
