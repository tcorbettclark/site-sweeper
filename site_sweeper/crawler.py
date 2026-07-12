from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright


@dataclass
class PageResult:
    url: str
    status: int | None = None
    canonical: str | None = None
    canonical_issues: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    broken_links: list[str] = field(default_factory=list)
    screenshot_path: str | None = None


@dataclass
class CrawlResult:
    pages: dict[str, PageResult] = field(default_factory=dict)
    broken_links: dict[str, list[str]] = field(default_factory=dict)


def _same_domain(base_url: str, url: str) -> bool:
    return urlparse(base_url).hostname == urlparse(url).hostname


def _normalize_url(base_url: str, href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return None
    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    return absolute.split("#")[0]


async def crawl(
    start_url: str,
    *,
    delay_ms: int = 100,
    check_broken_links: bool = True,
    check_canonical: bool = True,
    take_screenshots: bool = True,
    screenshots_dir: str = "./screenshots",
) -> CrawlResult:
    from .checks import check_canonical_tag
    from .screenshots import take_screenshot

    result = CrawlResult()
    visited: set[str] = set()
    checked_urls: set[str] = set()
    queue: asyncio.Queue[str] = asyncio.Queue()
    await queue.put(start_url)
    visited.add(start_url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        while not queue.empty():
            url = await queue.get()
            page_result = PageResult(url=url)

            try:
                response = await page.goto(url, wait_until="domcontentloaded")
                page_result.status = response.status if response else None
            except Exception:
                page_result.status = None
                result.pages[url] = page_result
                continue

            await page.wait_for_load_state("networkidle")

            link_hrefs = await page.evaluate(
                """() => {
                    return Array.from(document.querySelectorAll('a[href]'))
                        .map(a => a.href);
                }"""
            )

            normalized_links: list[str] = []
            for href in link_hrefs:
                normalized = _normalize_url(url, href)
                if normalized:
                    normalized_links.append(normalized)
            page_result.links = normalized_links

            if check_canonical:
                (
                    page_result.canonical,
                    page_result.canonical_issues,
                ) = await check_canonical_tag(page, url)

            if check_broken_links:
                for link in normalized_links:
                    if not _same_domain(start_url, link):
                        continue
                    if link in checked_urls:
                        continue
                    checked_urls.add(link)
                    try:
                        resp = await context.request.head(link)
                        if resp.status >= 400:
                            page_result.broken_links.append(link)
                            result.broken_links.setdefault(link, []).append(url)
                    except Exception:
                        page_result.broken_links.append(link)
                        result.broken_links.setdefault(link, []).append(url)
                    await asyncio.sleep(delay_ms / 1000)

            if take_screenshots:
                page_result.screenshot_path = await take_screenshot(
                    page, url, screenshots_dir
                )

            result.pages[url] = page_result

            for link in normalized_links:
                if _same_domain(start_url, link) and link not in visited:
                    visited.add(link)
                    await queue.put(link)

            await asyncio.sleep(delay_ms / 1000)

        await browser.close()

    return result
