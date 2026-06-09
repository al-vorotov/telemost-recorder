from pathlib import Path
from uuid import UUID

from shared.config.settings import Settings


class LocalStorageAdapter:
    """Файловое хранилище артефактов сессии на диске VM."""

    def __init__(self, settings: Settings | None = None) -> None:
        from shared.config.settings import get_settings

        self._settings = settings or get_settings()

    def session_dir(self, session_id: UUID) -> Path:
        path = self._settings.sessions_data_path / str(session_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def audio_path(self, session_id: UUID) -> Path:
        return self.session_dir(session_id) / "audio.wav"

    def transcript_path(self, session_id: UUID) -> Path:
        return self.session_dir(session_id) / "transcript.txt"

    def summary_path(self, session_id: UUID) -> Path:
        return self.session_dir(session_id) / "summary.md"

    async def delete_audio(self, session_id: UUID) -> None:
        path = self.audio_path(session_id)
        if path.exists():
            path.unlink()

    async def delete_session_dir(self, session_id: UUID) -> None:
        import shutil

        path = self._settings.sessions_data_path / str(session_id)
        if path.exists():
            shutil.rmtree(path)
