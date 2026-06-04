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

### Запуск (gateway + Telegram)

```bash
cp .env.example .env
# Заполните TELEGRAM_BOT_TOKEN, ALLOWED_TELEGRAM_IDS, BOT_API_SECRET

# Терминал 1
python -m services.gateway

# Терминал 2
python -m services.tg_bot
```

### Режимы

| `SIMULATE_MEETING` | Поведение |
|--------------------|-----------|
| `true` | Без браузера: fake `recording` и заглушка транскрипта |
| `false` | Redis + subprocess `meeting_worker` + Playwright (Телемост) |

Для реального звонка:

```bash
docker compose up -d redis   # postgres опционально
./scripts/install-playwright.sh
# .env: SIMULATE_MEETING=false
```

Полный диалог в боте: ссылка → подключиться → стоп записи → выход из звонка → транскрибация → удаление аудио.
