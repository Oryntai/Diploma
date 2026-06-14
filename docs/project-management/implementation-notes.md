# Заметки по реализации

## Что уже построено

- FastAPI отвечает на `GET /health` и основные API endpoints.
- FastAPI отдает Jinja2 dashboard как основной пользовательский интерфейс.
- База данных создает ядро таблиц в SQLite.
- Зарегистрированы пять демо IoT-устройств.
- `/api/network/sample`, `/api/demo/scenario` и `/api/scan/run` проходят через CICIoT feature adapter и PyTorch autoencoder.
- Dashboard показывает overview, devices, device detail, alerts, charts и ML status.
- Старый monolithic desktop-код удален.
- Добавлен легкий desktop device simulator, который отправляет presets в FastAPI `/api/network/sample`.
- Основной runtime теперь: FastAPI backend + web dashboard + desktop simulator sender.

## Почему это важно

- Проект запускается как обычное FastAPI web-приложение.
- Демо можно проводить через dashboard scan или вручную через desktop simulator.
- Детерминированный scan упрощает защиту, тесты и скриншоты.

## Что пока можно улучшить

- Разнести helper-функции из `backend/app/main.py` по роутерам и сервисам.
- Добавить browser-level screenshot smoke tests.
- Расширить экспорт отчета с plain text до HTML/JSON artifacts.

Это не блокирует текущий FastAPI web prototype.
