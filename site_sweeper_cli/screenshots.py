from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Page

VIEWPORT_SIZES: dict[str, dict[str, int]] = {
    "mobile": {"width": 375, "height": 667},
    "tablet": {"width": 768, "height": 1024},
    "desktop": {"width": 1280, "height": 720},
    "desktop-lg": {"width": 1440, "height": 900},
}


async def take_screenshot(
    page: Page, url: str, screenshots_dir: str, size: str = "desktop"
) -> str:
    output_dir = Path(screenshots_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(url)
    safe_path = f"{parsed.hostname}_{parsed.path.strip('/').replace('/', '_') or 'index'}_{size}.png"
    filepath = output_dir / safe_path

    await page.screenshot(path=str(filepath), full_page=False)

    return str(filepath)
