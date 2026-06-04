import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from uuid import UUID

from shared.config.settings import Settings
from shared.queues.session_queue import SessionCommand, SessionQueue

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class WorkerManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._queue = SessionQueue(settings.redis_url)
        self._processes: dict[UUID, subprocess.Popen] = {}
        self._capture_events: dict[UUID, asyncio.Event] = {}
        self._leave_events: dict[UUID, asyncio.Event] = {}

    def capture_event(self, session_id: UUID) -> asyncio.Event:
        if session_id not in self._capture_events:
            self._capture_events[session_id] = asyncio.Event()
        return self._capture_events[session_id]

    def leave_event(self, session_id: UUID) -> asyncio.Event:
        if session_id not in self._leave_events:
            self._leave_events[session_id] = asyncio.Event()
        return self._leave_events[session_id]

    def notify_capture_stopped(self, session_id: UUID) -> None:
        self.capture_event(session_id).set()

    def notify_left(self, session_id: UUID) -> None:
        self.leave_event(session_id).set()

    def spawn(self, session_id: UUID) -> None:
        if session_id in self._processes and self._processes[session_id].poll() is None:
            logger.info("Worker already running for %s", session_id)
            return

        cmd = [
            sys.executable,
            "-m",
            "services.meeting_worker",
            "--session-id",
            str(session_id),
        ]
        logger.info("Spawning meeting worker: %s", " ".join(cmd))
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self._processes[session_id] = proc
        self._capture_events[session_id] = asyncio.Event()
        self._leave_events[session_id] = asyncio.Event()

    async def send_stop_capture(self, session_id: UUID, timeout: float = 120.0) -> None:
        self._capture_events[session_id] = asyncio.Event()
        await self._queue.publish_command(
            SessionCommand(session_id=str(session_id), action="STOP_CAPTURE")
        )
        try:
            await asyncio.wait_for(self._capture_events[session_id].wait(), timeout=timeout)
        except TimeoutError as e:
            raise TimeoutError(f"Worker did not stop capture in {timeout}s") from e

    async def send_leave(self, session_id: UUID, timeout: float = 60.0) -> None:
        self._leave_events[session_id] = asyncio.Event()
        await self._queue.publish_command(
            SessionCommand(session_id=str(session_id), action="LEAVE")
        )
        try:
            await asyncio.wait_for(self._leave_events[session_id].wait(), timeout=timeout)
        except TimeoutError as e:
            raise TimeoutError(f"Worker did not leave in {timeout}s") from e

    def stop_process(self, session_id: UUID) -> None:
        proc = self._processes.pop(session_id, None)
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
