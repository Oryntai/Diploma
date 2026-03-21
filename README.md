# Интеллектуальная система мониторинга безопасности IoT

Этот репозиторий содержит план, архитектурные документы и текущую реализацию дипломного прототипа локальной системы мониторинга безопасности IoT.

## Текущий статус (скелет)

Сейчас реализован **минимальный рабочий скелет**, а не полный MVP:

- backend на FastAPI с endpoint `GET /health`;
- базовый слой SQLite и первые модели;
- симулятор одного температурного датчика с детерминированным режимом;
- минимальные автотесты для smoke-проверки.

Еще не реализовано на этом этапе:

- MQTT ingest в backend;
- rule-engine и генерация алертов;
- страницы dashboard.

## Быстрый запуск текущего скелета

1. Установить зависимости backend:

```bash
pip install -r backend/requirements.txt
```

2. Запустить backend из корня репозитория:

```bash
python -m uvicorn app.main:app --app-dir backend --reload
```

3. В другом терминале проверить health:

```bash
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
```

Ожидаемый ответ:

```json
{"status":"ok","service":"backend"}
```

4. Запустить симулятор один раз:

```bash
python simulator/main.py --once --seed 42
```

Команда печатает один детерминированный JSON payload и завершает работу.

## Как логировать данные с реального пылесоса (STYTJ02YM)

Для модели `Mi Robot Vacuum-Mop P (STYTJ02YM)` мы используем схему:

```text
Vacuum (STYTJ02YM) -> Python adapter (python-miio) -> FastAPI ingest endpoint -> SQLite
```

### Почему именно так

- `python-miio` поддерживает Viomi-линейку (в том числе `viomi.vacuum.v8`, к которой относится STYTJ02YM).
- Можно опрашивать устройство в локальной сети без обязательной cloud-интеграции в runtime.
- Поля статуса и ошибок доступны в структурированном виде (`ViomiVacuumStatus`).

### Что нужно для подключения

1. IP пылесоса в локальной сети.
2. Токен устройства (32 hex символа) — обычно извлекается через MiToolkit/HA guide.
3. Python-адаптер, который раз в N секунд читает статус и отправляет JSON в backend.

### Какие поля реально логируем в backend

Минимальный набор для security-monitoring:

- `device_id` (например `vacuum-stytj02ym-01`)
- `device_type` (`robot_vacuum`)
- `timestamp` (UTC)
- `battery`
- `charging`
- `vacuum_state` (idle/cleaning/returning/docked/paused/...)
- `error_code`
- `error`
- `clean_area`
- `clean_time`
- `fanspeed`
- `water_grade`
- `has_map`

Расширенный набор (зависит от прошивки):

- `bin_type`, `mop_attached`, `route_pattern`, `map_number`, `current_map_id`, `water_percent`.

### Как именно отправляем в наш backend

Адаптер делает polling и шлет payload в endpoint (план):

`POST /api/ingest/vacuum`

Пример payload:

```json
{
  "device_id": "vacuum-stytj02ym-01",
  "device_type": "robot_vacuum",
  "model": "STYTJ02YM",
  "timestamp": "2026-03-21T10:15:00Z",
  "battery": 66,
  "charging": false,
  "vacuum_state": "cleaning",
  "error_code": 0,
  "error": "No error",
  "clean_area": 37.2,
  "clean_time": 2520,
  "fanspeed": "standard",
  "water_grade": "medium",
  "has_map": true,
  "source": "python-miio-adapter"
}
```

### Ограничения, которые учитываем

- Для отдельных EU-прошивок STYTJ02YM часть свойств может не возвращаться.
- Поэтому backend должен поддерживать частично заполненный payload (nullable поля).
- Cloud-вариант (через Home Assistant Xiaomi Cloud Map Extractor) оставляем как fallback, но основной путь — локальный адаптер.

### Источники ресерча

- `python-miio` (репозиторий): https://github.com/rytilahti/python-miio
- API docs Viomi vacuum (`ViomiVacuumStatus`): https://python-miio.readthedocs.io/en/latest/api/miio.integrations.viomi.vacuum.html
- Known issue для STYTJ02YM/EU firmware: https://github.com/rytilahti/python-miio/issues/1003
- Cloud fallback (HA Xiaomi Cloud Map Extractor): https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor

## Цель проекта

Собрать локальный прототип, который:

- симулирует несколько типов IoT-устройств;
- передает телеметрию через MQTT;
- принимает сообщения в backend (FastAPI);
- хранит состояние устройств, телеметрию и алерты в SQLite;
- обнаруживает подозрительное поведение (в первую очередь правилами);
- показывает состояние системы в веб-интерфейсе.

Проект должен оставаться «дипломным»:

- без обязательной облачной инфраструктуры;
- без тяжелого frontend-фреймворка;
- без обязательного ML в MVP;
- с запуском на одном ноутбуке.

## Обязательные границы MVP

Обязательно:

- Python 3.11+;
- FastAPI;
- MQTT + Mosquitto;
- SQLite;
- Jinja2 + Chart.js;
- минимум 4 типа устройств;
- минимум 5 детектируемых сценариев угроз.

Опционально после MVP:

- Isolation Forest или аналог;
- pandas для офлайн-анализа;
- путь миграции на PostgreSQL.

Не входит в первый цикл:

- microservices;
- Kubernetes;
- cloud deployment;
- сложная аутентификация;
- mobile app;
- deep learning;
- обязательные LLM-фичи.

## Базовая архитектура

```text
simulator -> MQTT broker -> FastAPI backend -> SQLite -> dashboard
```

## Целевой вид dashboard (по референс-скринам)

Ниже зафиксирован ожидаемый результат интерфейса, к которому идем в реализации.

### Верхняя зона

- Заголовок: `IoT Security Monitoring Platform`.
- Кнопки справа: `Export Report` и `Run Scan`.
- 4 KPI-карточки:
  - `Total Devices`
  - `Active Alerts`
  - `High/Critical Risk`
  - `Avg. Security Score`

### Средняя зона

- Слева большой блок `Device Overview` (таблица):
  - колонки `Device`, `Type`, `Status`, `Battery`, `Firmware`, `Risk`, `Main Issue`;
  - цветные бейджи риска (`Low`, `Medium`, `High`, `Critical`);
  - индикация online/offline.
- Справа блок `Risk Distribution`:
  - горизонтальные бары по уровням `Critical`, `High`, `Medium`, `Low`;
  - справа число инцидентов по каждому уровню.
- Под `Risk Distribution` блок `Recommendations`:
  - список конкретных действий (обновить прошивку, сменить креды, ограничить доступ и т.д.).

### Нижняя зона

- Слева `Recent Security Alerts`:
  - карточки последних алертов с устройством, временем и severity-бейджем.
- Справа `System Flow`:
  - 5 шагов пайплайна от получения telemetry до отображения алертов в админ-панели.

### UX-правила для этого макета

- layout в стиле clean admin panel;
- светлая тема, аккуратные карточки и мягкие границы;
- без перегрузки графиками, основной акцент на читаемости статуса и алертов;
- UI должен быть одинаково читаем на ноутбуке и на проекционном экране при защите.

## Порядок чтения документов

1. `Todo.md` — мастер-бриф проекта.
2. `README.md` — точка входа и правила работы.
3. `docs/setup.md` — локальная подготовка и старт.
4. `docs/architecture.md` — архитектура и поток данных.
5. `docs/roadmap.md` — фазы реализации.
6. `docs/testing.md` — стратегия тестирования.
7. `docs/api.md` — API-контракт.
8. `docs/demo-script.md` — сценарий защиты.
9. `docs/threat-model.md` — модель угроз.
10. `docs/team-workflow.md` — командный процесс.
11. `docs/diploma-outline.md` — структура диплома.
12. `docs/diploma-notes.md` — заметки для защиты.

## Документы по управлению реализацией

Папка `docs/project-management/`:

- `implementation-status.md` — что уже сделано;
- `implementation-notes.md` — что именно построено простыми словами;
- `technical-decisions.md` — ключевые технические решения и причины;
- `open-items.md` — следующие шаги.

## Что считается готовностью всего проекта

Проект можно считать готовым, когда:

- система поднимается локально по документации на «чистой» машине;
- симулируются минимум 4 типа устройств;
- детектируются минимум 5 сценариев;
- алерты сохраняются и видны в UI;
- у каждого алерта есть причина, severity и риск-оценка;
- есть тестовое покрытие ключевых контуров;
- есть воспроизводимый 3–5 минутный демо-сценарий;
- команда может уверенно объяснить архитектуру и решения.
