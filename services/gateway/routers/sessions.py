from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from services.gateway.auth import verify_api_secret
from services.gateway.deps import get_session_factory, get_session_service
from services.gateway.schemas import CreateSessionRequest, SessionResponse
from services.gateway.services.session_fsm import InvalidTransitionError
from services.gateway.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"], dependencies=[Depends(verify_api_secret)])


async def get_db() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, InvalidTransitionError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=SessionResponse)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        record = await svc.create_session(
            db,
            meeting_url=body.meeting_url,
            telegram_id=body.telegram_id,
            mode=body.mode,
            scheduled_at=body.scheduled_at,
        )
        return SessionResponse(**svc.to_response(record))
    except Exception as e:
        raise _http_error(e) from e


@router.get("/active/current", response_model=SessionResponse)
async def get_active_session(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        record = await svc.get_active_session(db, telegram_id)
        if record is None:
            raise HTTPException(status_code=404, detail="No active session")
        return SessionResponse(**svc.to_response(record))
    except Exception as e:
        raise _http_error(e) from e


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        record = await svc.get_session(db, session_id, telegram_id)
        return SessionResponse(**svc.to_response(record))
    except Exception as e:
        raise _http_error(e) from e


@router.post("/{session_id}/stop-recording", response_model=SessionResponse)
async def stop_recording(
    session_id: UUID,
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        record = await svc.stop_recording(db, session_id, telegram_id)
        return SessionResponse(**svc.to_response(record))
    except Exception as e:
        raise _http_error(e) from e


@router.post("/{session_id}/leave", response_model=SessionResponse)
async def leave_call(
    session_id: UUID,
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        record = await svc.leave(db, session_id, telegram_id)
        return SessionResponse(**svc.to_response(record))
    except Exception as e:
        raise _http_error(e) from e


@router.post("/{session_id}/decline-leave", response_model=SessionResponse)
async def decline_leave(
    session_id: UUID,
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        record = await svc.decline_leave(db, session_id, telegram_id)
        return SessionResponse(**svc.to_response(record))
    except Exception as e:
        raise _http_error(e) from e


@router.post("/{session_id}/transcribe", response_model=SessionResponse)
async def start_transcribe(
    session_id: UUID,
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        record = await svc.transcribe(db, session_id, telegram_id)
        return SessionResponse(**svc.to_response(record))
    except Exception as e:
        raise _http_error(e) from e


@router.post("/{session_id}/cancel", response_model=SessionResponse)
async def cancel_scheduled(
    session_id: UUID,
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        record = await svc.cancel_scheduled(db, session_id, telegram_id)
        return SessionResponse(**svc.to_response(record))
    except Exception as e:
        raise _http_error(e) from e


@router.post("/{session_id}/summarize")
async def summarize_session(
    session_id: UUID,
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
):
    try:
        summary = await svc.summarize(db, session_id, telegram_id)
        path = svc.summary_file_path(session_id)
        if not path:
            raise HTTPException(status_code=500, detail="Summary file missing")
        return FileResponse(path, filename="summary.md", media_type="text/markdown")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise _http_error(e) from e


@router.post("/{session_id}/decline-transcribe", response_model=SessionResponse)
async def decline_transcribe(
    session_id: UUID,
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        record = await svc.decline_transcribe(db, session_id, telegram_id)
        return SessionResponse(**svc.to_response(record))
    except Exception as e:
        raise _http_error(e) from e


@router.delete("/{session_id}/recording", response_model=SessionResponse)
async def delete_recording(
    session_id: UUID,
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        record = await svc.delete_recording(db, session_id, telegram_id)
        return SessionResponse(**svc.to_response(record))
    except Exception as e:
        raise _http_error(e) from e


@router.post("/{session_id}/retain-audio", response_model=SessionResponse)
async def retain_audio(
    session_id: UUID,
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    svc: SessionService = Depends(get_session_service),
) -> SessionResponse:
    try:
        record = await svc.retain_audio(db, session_id, telegram_id)
        return SessionResponse(**svc.to_response(record))
    except Exception as e:
        raise _http_error(e) from e


@router.get("/{session_id}/transcript")
async def download_transcript(
    session_id: UUID,
    telegram_id: int,
    svc: SessionService = Depends(get_session_service),
    db: AsyncSession = Depends(get_db),
):
    try:
        await svc.get_session(db, session_id, telegram_id)
        text = svc.read_transcript(session_id)
        if not text:
            raise HTTPException(status_code=404, detail="Transcript not ready")
        path = svc.transcript_file_path(session_id)
        if not path:
            raise HTTPException(status_code=404, detail="Transcript file missing")
        return FileResponse(path, filename="transcript.txt", media_type="text/plain")
    except Exception as e:
        raise _http_error(e) from e


@router.get("/{session_id}/recording/download")
async def download_recording(
    session_id: UUID,
    telegram_id: int,
    svc: SessionService = Depends(get_session_service),
    db: AsyncSession = Depends(get_db),
):
    try:
        await svc.get_session(db, session_id, telegram_id)
        path = svc.audio_file_path(session_id)
        if not path:
            raise HTTPException(status_code=404, detail="Recording not found")
        return FileResponse(path, filename="recording.wav", media_type="audio/wav")
    except Exception as e:
        raise _http_error(e) from e
