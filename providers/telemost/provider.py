import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from providers.telemost.browser import TelemostBrowser
from shared.audio.wav_sink import WavAudioSink
from shared.config.settings import Settings
from shared.contracts.meeting import JoinContext, MeetingEvent, MeetingEventType

logger = logging.getLogger(__name__)

_JOIN_TIMEOUT_MS = 120_000
_POLL_INTERVAL_SEC = 2.0


class TelemostProvider:
    provider_id = "telemost"

    def __init__(self, settings: Settings | None = None) -> None:
        from shared.config.settings import get_settings

        self._settings = settings or get_settings()
        self._browser = TelemostBrowser(self._settings)
        self._sink: WavAudioSink | None = None
        self._ctx: JoinContext | None = None
        self._in_meeting = False
        self._capturing = False

    async def join(self, ctx: JoinContext) -> None:
        self._ctx = ctx
        self._sink = WavAudioSink(ctx.audio_output_path)
        page = await self._browser.start()
        await self._browser.inject_audio_script(page)

        async def on_chunk(samples: list[float]) -> None:
            if self._sink and self._capturing:
                await self._sink.write_float32(samples)

        await page.expose_function("onAudioChunk", on_chunk)
        logger.info("Opening meeting %s", ctx.meeting_url)
        await page.goto(ctx.meeting_url, wait_until="domcontentloaded", timeout=_JOIN_TIMEOUT_MS)

        await self._enter_meeting_ui(page, ctx.bot_display_name)
        self._in_meeting = True
        await self._disable_media(page)
        await page.evaluate("window.__telemostStartCapture && window.__telemostStartCapture()")
        self._capturing = True
        logger.info("Joined meeting, capture started")

    async def _enter_meeting_ui(self, page: Page, display_name: str) -> None:
        name_selectors = [
            'input[placeholder*="имя" i]',
            'input[placeholder*="name" i]',
            "input[type='text']",
        ]
        for sel in name_selectors:
            try:
                field = page.locator(sel).first
                if await field.is_visible(timeout=3000):
                    await field.fill(display_name)
                    break
            except PlaywrightTimeout:
                continue

        join_buttons = [
            page.get_by_role("button", name="Продолжить"),
            page.get_by_role("button", name="Подключиться"),
            page.get_by_role("button", name="Войти"),
            page.get_by_role("button", name="Join"),
            page.locator("button").filter(has_text="Подключ"),
            page.locator("button").filter(has_text="Войти"),
        ]
        for btn in join_buttons:
            try:
                if await btn.first.is_visible(timeout=2000):
                    await btn.first.click()
                    await page.wait_for_timeout(2000)
                    break
            except PlaywrightTimeout:
                continue

        await page.wait_for_timeout(3000)

    async def _disable_media(self, page: Page) -> None:
        for label in ("микрофон", "камер", "microphone", "camera"):
            try:
                btn = page.get_by_role("button", name=label)
                if await btn.first.is_visible(timeout=1500):
                    await btn.first.click()
                    await page.wait_for_timeout(500)
            except PlaywrightTimeout:
                pass

    async def stop_capture(self, ctx: JoinContext) -> Path:
        page = self._browser.page
        if page:
            try:
                await page.evaluate(
                    "window.__telemostStopCapture && window.__telemostStopCapture()"
                )
            except Exception as e:
                logger.warning("stop capture script: %s", e)
        self._capturing = False
        if not self._sink:
            return ctx.audio_output_path
        return await self._sink.finalize()

    async def leave(self, ctx: JoinContext) -> None:
        page = self._browser.page
        if page:
            for label in (
                "Выйти",
                "Отключиться",
                "Покинуть",
                "Leave",
                "Hang up",
            ):
                try:
                    btn = page.get_by_role("button", name=label)
                    if await btn.first.is_visible(timeout=2000):
                        await btn.first.click()
                        await page.wait_for_timeout(1500)
                        break
                except PlaywrightTimeout:
                    continue
        await self._browser.close()
        self._in_meeting = False
        self._capturing = False
        logger.info("Left meeting")

    async def watch_events(self, ctx: JoinContext) -> AsyncIterator[MeetingEvent]:
        page = self._browser.page
        if not page:
            return

        waiting_markers = ("зал ожидания", "ожидает", "waiting room", "подключит")
        meeting_markers = ("в эфире", "участник", "запись", "микрофон", "отключиться", "выйти")
        ended_markers = ("встреча завершена", "звонок окончен", "meeting ended")

        emitted_recording = False
        emitted_waiting = False

        while self._in_meeting and page and not page.is_closed():
            try:
                text = (await page.inner_text("body")).lower()
            except Exception:
                break

            if any(m in text for m in ended_markers):
                yield MeetingEvent(type=MeetingEventType.MEETING_ENDED)
                break

            if any(m in text for m in waiting_markers) and not emitted_waiting:
                emitted_waiting = True
                yield MeetingEvent(type=MeetingEventType.WAITING_ROOM)

            if (
                self._capturing
                or any(m in text for m in meeting_markers)
            ) and not emitted_recording:
                emitted_recording = True
                yield MeetingEvent(type=MeetingEventType.RECORDING)

            await asyncio.sleep(_POLL_INTERVAL_SEC)

    async def close(self) -> None:
        await self._browser.close()
