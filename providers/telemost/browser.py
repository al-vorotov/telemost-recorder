import logging
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from shared.config.settings import Settings

logger = logging.getLogger(__name__)

_CHROMIUM_ARGS = [
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    "--autoplay-policy=no-user-gesture-required",
    "--disable-features=IsolateOrigins,site-per-process",
]


class TelemostBrowser:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page | None:
        return self._page

    async def start(self) -> Page:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._settings.meeting_worker_headless,
            args=_CHROMIUM_ARGS,
        )
        self._context = await self._browser.new_context(
            permissions=["microphone", "camera"],
            locale="ru-RU",
        )
        self._page = await self._context.new_page()
        return self._page

    async def inject_audio_script(self, page: Page) -> None:
        script_path = Path(__file__).parent / "audio_inject.js"
        await page.add_init_script(path=str(script_path))

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
