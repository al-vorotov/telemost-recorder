import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from providers.registry import detect_provider
from services.gateway.services.session_fsm import (
    InvalidTransitionError,
    apply_transition,
    status_label,
)
from shared.config.settings import Settings
from shared.contracts.session import SessionStatus
from shared.db.models import SessionRecord, User
from shared.storage.local import LocalStorageAdapter

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(
        self,
        settings: Settings,
        storage: LocalStorageAdapter | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._settings = settings
        self._storage = storage or LocalStorageAdapter(settings)
        self._session_factory = session_factory
        self._simulate_tasks: dict[UUID, asyncio.Task] = {}

    async def get_or_create_user(self, db: AsyncSession, telegram_id: int) -> User:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            return user
        user = User(telegram_id=telegram_id, is_allowed=True)
        db.add(user)
        await db.flush()
        return user

    def _check_acl(self, telegram_id: int) -> None:
        allowed = self._settings.allowed_telegram_id_set
        if allowed and telegram_id not in allowed:
            raise PermissionError("Telegram user not allowed")

    async def _get_session_for_user(
        self, db: AsyncSession, session_id: UUID, telegram_id: int
    ) -> SessionRecord:
        result = await db.execute(
            select(SessionRecord)
            .join(User)
            .where(SessionRecord.id == session_id, User.telegram_id == telegram_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise LookupError("Session not found")
        return record

    async def _transition(
        self, db: AsyncSession, record: SessionRecord, action: str
    ) -> SessionRecord:
        current = SessionStatus(record.status)
        new_status = apply_transition(current, action)
        record.status = new_status.value
        await db.commit()
        await db.refresh(record)
        return record

    def to_response(self, record: SessionRecord) -> dict:
        audio_path = self._storage.audio_path(record.id)
        transcript_path = self._storage.transcript_path(record.id)
        return {
            "id": record.id,
            "status": record.status,
            "status_label": status_label(SessionStatus(record.status)),
            "meeting_url": record.meeting_url,
            "provider": record.provider,
            "audio_ready": audio_path.exists(),
            "transcript_ready": transcript_path.exists(),
            "queue_position": None,
            "error_code": record.error_code,
        }

    async def create_session(
        self,
        db: AsyncSession,
        *,
        meeting_url: str,
        telegram_id: int,
        mode: str,
        scheduled_at: datetime | None = None,
    ) -> SessionRecord:
        self._check_acl(telegram_id)
        provider_id = detect_provider(meeting_url)
        if not provider_id:
            raise ValueError("Unsupported meeting URL")

        active = await db.execute(
            select(SessionRecord)
            .join(User)
            .where(
                User.telegram_id == telegram_id,
                SessionRecord.status.notin_(
                    [
                        SessionStatus.COMPLETED.value,
                        SessionStatus.FAILED.value,
                    ]
                ),
            )
        )
        if active.scalar_one_or_none():
            raise ValueError("You already have an active session")

        user = await self.get_or_create_user(db, telegram_id)
        status = SessionStatus.SCHEDULED if mode == "scheduled" else SessionStatus.QUEUED
        record = SessionRecord(
            user_id=user.id,
            provider=provider_id,
            meeting_url=meeting_url.strip(),
            status=status.value,
            bot_display_name=self._settings.bot_display_name,
            scheduled_at=scheduled_at,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        self._storage.session_dir(record.id)

        if mode == "now":
            await self._transition(db, record, "start_join")
            await db.refresh(record)
            if self._settings.simulate_meeting:
                self._schedule_simulate_join(record.id)

        return record

    def _schedule_simulate_join(self, session_id: UUID) -> None:
        if session_id in self._simulate_tasks:
            self._simulate_tasks[session_id].cancel()

        async def _run() -> None:
            if not self._session_factory:
                return
            await asyncio.sleep(1.5)
            async with self._session_factory() as db:
                record = await db.get(SessionRecord, session_id)
                if not record or record.status != SessionStatus.JOINING.value:
                    return
                try:
                    await self._transition(db, record, "recording")
                except InvalidTransitionError:
                    await self._transition(db, record, "waiting_room")
                    await db.refresh(record)
                    await asyncio.sleep(2)
                    record = await db.get(SessionRecord, session_id)
                    if record and record.status == SessionStatus.WAITING_ROOM.value:
                        await self._transition(db, record, "recording")

        self._simulate_tasks[session_id] = asyncio.create_task(_run())

    async def get_session(
        self, db: AsyncSession, session_id: UUID, telegram_id: int
    ) -> SessionRecord:
        self._check_acl(telegram_id)
        return await self._get_session_for_user(db, session_id, telegram_id)

    async def stop_recording(
        self, db: AsyncSession, session_id: UUID, telegram_id: int
    ) -> SessionRecord:
        record = await self._get_session_for_user(db, session_id, telegram_id)
        record = await self._transition(db, record, "stop_recording")
        audio_path = self._storage.audio_path(session_id)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        if not audio_path.exists():
            audio_path.write_bytes(b"RIFF")  # placeholder until real worker
        record.audio_object_key = str(audio_path)
        record.recorded_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(record)
        return record

    async def leave(self, db: AsyncSession, session_id: UUID, telegram_id: int) -> SessionRecord:
        record = await self._get_session_for_user(db, session_id, telegram_id)
        return await self._transition(db, record, "leave")

    async def decline_leave(
        self, db: AsyncSession, session_id: UUID, telegram_id: int
    ) -> SessionRecord:
        record = await self._get_session_for_user(db, session_id, telegram_id)
        return await self._transition(db, record, "decline_leave")

    async def transcribe(
        self, db: AsyncSession, session_id: UUID, telegram_id: int
    ) -> SessionRecord:
        record = await self._get_session_for_user(db, session_id, telegram_id)
        record = await self._transition(db, record, "confirm_transcribe")
        record.transcription_requested_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(record)
        self._schedule_simulate_transcribe(session_id)
        return record

    async def decline_transcribe(
        self, db: AsyncSession, session_id: UUID, telegram_id: int
    ) -> SessionRecord:
        record = await self._get_session_for_user(db, session_id, telegram_id)
        return await self._transition(db, record, "decline_transcribe")

    def _schedule_simulate_transcribe(self, session_id: UUID) -> None:
        async def _run() -> None:
            if not self._session_factory:
                return
            await asyncio.sleep(0.5)
            async with self._session_factory() as db:
                record = await db.get(SessionRecord, session_id)
                if not record or record.status != SessionStatus.TRANSCRIPTION_QUEUED.value:
                    return
                await self._transition(db, record, "transcribing")
                await asyncio.sleep(2)
                record = await db.get(SessionRecord, session_id)
                if not record:
                    return
                path = self._storage.transcript_path(session_id)
                path.write_text(
                    "# Транскрипт (заглушка)\n\n[00:00] Тестовая транскрибация для dev-режима.\n",
                    encoding="utf-8",
                )
                record.transcript_object_key = str(path)
                record.transcribed_at = datetime.now(UTC)
                await db.commit()
                await self._transition(db, record, "transcript_ready")
                record = await db.get(SessionRecord, session_id)
                if record:
                    await self._transition(db, record, "await_audio_disposal")

        asyncio.create_task(_run())

    async def delete_recording(
        self, db: AsyncSession, session_id: UUID, telegram_id: int
    ) -> SessionRecord:
        record = await self._get_session_for_user(db, session_id, telegram_id)
        await self._storage.delete_audio(session_id)
        record.audio_deleted_at = datetime.now(UTC)
        record = await self._transition(db, record, "delete_audio")
        return record

    async def retain_audio(
        self, db: AsyncSession, session_id: UUID, telegram_id: int
    ) -> SessionRecord:
        record = await self._get_session_for_user(db, session_id, telegram_id)
        record.audio_expires_at = datetime.now(UTC) + timedelta(
            days=self._settings.audio_retention_days
        )
        await db.commit()
        record = await self._transition(db, record, "retain_audio")
        return record

    def read_transcript(self, session_id: UUID) -> str | None:
        path = self._storage.transcript_path(session_id)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def audio_file_path(self, session_id: UUID):
        path = self._storage.audio_path(session_id)
        return path if path.exists() else None

    def transcript_file_path(self, session_id: UUID):
        path = self._storage.transcript_path(session_id)
        return path if path.exists() else None
