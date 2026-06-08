from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./data/telemost.db"
    redis_url: str = "redis://localhost:6379/0"
    data_dir: Path = Path("./data")

    telegram_bot_token: str = ""
    allowed_telegram_ids: str = ""  # comma-separated
    bot_api_secret: str = "change-me"

    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    bot_display_name: str = "Recorder Bot"
    max_concurrent_sessions: int = 1
    audio_retention_days: int = 7

    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str = "ru"

    meeting_worker_headless: bool = False
    simulate_meeting: bool = False  # true = без Playwright; false = meeting_worker + Redis
    simulate_transcription: bool = False  # true = заглушка txt; false = transcriber + Whisper
    schedule_timezone: str = "Europe/Moscow"
    retention_sweep_interval_hours: int = 1
    gateway_base_url: str = "http://127.0.0.1:8000"

    @property
    def allowed_telegram_id_set(self) -> set[int]:
        if not self.allowed_telegram_ids.strip():
            return set()
        return {int(x.strip()) for x in self.allowed_telegram_ids.split(",") if x.strip()}

    @property
    def sessions_data_path(self) -> Path:
        return self.data_dir / "sessions"


@lru_cache
def get_settings() -> Settings:
    return Settings()
