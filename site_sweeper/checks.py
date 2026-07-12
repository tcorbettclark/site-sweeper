from __future__ import annotations

from urllib.parse import urlparse

from playwright.async_api import Page


async def check_canonical_tag(
    page: Page, page_url: str
) -> tuple[str | None, list[str]]:
    issues: list[str] = []

    canonical = await page.evaluate(
        """() => {
            const el = document.querySelector('link[rel="canonical"]');
            return el ? el.href : null;
        }"""
    )

    if canonical is None:
        issues.append("Missing canonical tag")
        return None, issues

    parsed = urlparse(canonical)
    path = parsed.path

    if path.endswith("/index.html"):
        issues.append(f"Canonical contains index.html: {canonical}")
    elif "index.html" in path:
        issues.append(f"Canonical contains index.html: {canonical}")

    if path != "/" and not path.endswith("/") and not path.endswith(".html"):
        issues.append(f"Canonical missing trailing slash: {canonical}")

    if canonical != page_url:
        issues.append(f"Canonical mismatch: page={page_url}, canonical={canonical}")

    return canonical, issues
