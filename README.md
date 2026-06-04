# telemost-recorder

Бот для записи звонков в Яндекс Телемост с управлением через Telegram и транскрибацией (faster-whisper).

## Модули

| Пакет | Назначение |
|-------|------------|
| `shared` | Контракты, модели БД, конфиг, storage |
| `providers` | Адаптеры источников встреч (`telemost`) |
| `services.tg_bot` | Telegram UI |
| `services.gateway` | Оркестрация, API, очереди |
| `services.meeting_worker` | Playwright: join, запись аудио |
| `services.transcriber` | Whisper worker |

## Быстрый старт (скелет)

```bash
cd telemost-recorder
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Структура

```
telemost-recorder/
├── shared/           # общая библиотека
├── providers/        # MeetingProvider implementations
├── services/         # deployable сервисы
├── scripts/          # утилиты
├── docker-compose.yml
└── tests/
```

Документация по FSM сессий: `shared/contracts/session.py`.

### Запуск сервисов (заглушки)

```bash
python -m services.gateway      # http://127.0.0.1:8000/health
python -m services.tg_bot       # нужен TELEGRAM_BOT_TOKEN
python -m services.transcriber
python -m services.meeting_worker --session-id <uuid>
```
