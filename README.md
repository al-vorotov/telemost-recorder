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

### Docker (рекомендуется для VM)

```bash
cp .env.example .env
# TELEGRAM_BOT_TOKEN, ALLOWED_TELEGRAM_IDS, BOT_API_SECRET

docker compose up -d --build
```

Сервисы: `gateway` :8000, `tg-bot`, `transcriber`, `postgres`, `redis`.  
Данные сессий: volume `appdata`.

### Локально без Docker

```bash
cp .env.example .env
docker compose up -d redis   # или redis + postgres

python -m services.gateway
python -m services.tg_bot
python -m services.transcriber
```

### Режимы

| `SIMULATE_MEETING` | Поведение |
|--------------------|-----------|
| `true` | Без браузера: fake `recording` и заглушка транскрипта |
| `false` | Redis + subprocess `meeting_worker` + Playwright (Телемост) |

| `SIMULATE_TRANSCRIPTION` | Поведение |
|--------------------------|-----------|
| `true` | Заглушка `transcript.txt` через 2 сек |
| `false` | Сервис `transcriber` + faster-whisper |

Для реального звонка:

```bash
docker compose up -d redis   # postgres опционально
./scripts/install-playwright.sh
# .env: SIMULATE_MEETING=false
```

Полный диалог в боте: ссылка → подключиться / **запланировать** → стоп записи → выход → транскрибация → удаление аудио.

- **Запланировать** — формат `ДД.ММ.ГГГГ ЧЧ:ММ` (МСК), APScheduler в gateway
- **/status** — активная сессия
- **retention sweeper** — автоудаление аудио по `audio_expires_at` (каждый час)
