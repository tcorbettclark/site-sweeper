from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Page


async def take_screenshot(page: Page, url: str, screenshots_dir: str) -> str:
    output_dir = Path(screenshots_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(url)
    filename = hashlib.md5(url.encode()).hexdigest()[:12]
    safe_path = f"{parsed.hostname}_{parsed.path.strip('/').replace('/', '_') or 'index'}_{filename}.png"
    filepath = output_dir / safe_path

    await page.screenshot(path=str(filepath), full_page=False)

    return str(filepath)
