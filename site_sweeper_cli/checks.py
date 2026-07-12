from __future__ import annotations

from urllib.parse import urlparse

from playwright.async_api import Page


def _urls_match_ignoring_alias(
    url_a: str, url_b: str, start_url: str, canonical_aliases: list[str]
) -> bool:
    if url_a == url_b:
        return True
    parsed_a = urlparse(url_a)
    parsed_b = urlparse(url_b)
    if parsed_a.path != parsed_b.path:
        return False
    hostnames = {urlparse(start_url).hostname}
    for alias in canonical_aliases:
        hostnames.add(urlparse(alias).hostname)
    if parsed_a.hostname in hostnames and parsed_b.hostname in hostnames:
        return True
    return False


async def check_canonical_tag(
    page: Page,
    page_url: str,
    start_url: str,
    canonical_aliases: list[str] | None = None,
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

    aliases = canonical_aliases or []
    if not _urls_match_ignoring_alias(page_url, canonical, start_url, aliases):
        issues.append(f"Canonical mismatch: page={page_url}, canonical={canonical}")

    return canonical, issues
