from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    meeting_url: str
    telegram_id: int
    mode: str = Field(pattern="^(now|scheduled)$")
    scheduled_at: datetime | None = None


class SessionResponse(BaseModel):
    id: UUID
    status: str
    status_label: str
    meeting_url: str
    provider: str
    audio_ready: bool = False
    transcript_ready: bool = False
    queue_position: int | None = None
    error_code: str | None = None
    scheduled_at: datetime | None = None

    model_config = {"from_attributes": True}


class TelegramAuthMixin(BaseModel):
    telegram_id: int
