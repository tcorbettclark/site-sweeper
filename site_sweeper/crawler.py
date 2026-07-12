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
    screenshot_path: str | None = None
    is_html: bool = False


@dataclass
class CrawlResult:
    pages: dict[str, PageResult] = field(default_factory=dict)
    broken_links: dict[str, list[str]] = field(default_factory=dict)
    non_canonical_links: dict[str, list[str]] = field(default_factory=dict)
    missing_canonical: dict[str, list[str]] = field(default_factory=dict)


def _resolve_alias(url: str, start_url: str, canonical_aliases: list[str]) -> str:
    parsed = urlparse(url)
    start_hostname = urlparse(start_url).hostname
    for alias in canonical_aliases:
        alias_parsed = urlparse(alias)
        if parsed.hostname in (start_hostname, alias_parsed.hostname):
            return f"{alias_parsed.scheme}://{alias_parsed.netloc}{parsed.path}"
    return url


def _same_domain(
    base_url: str, url: str, canonical_aliases: list[str] | None = None
) -> bool:
    if canonical_aliases:
        hostnames = {urlparse(base_url).hostname}
        hostnames.update(urlparse(a).hostname for a in canonical_aliases)
        return urlparse(url).hostname in hostnames
    return urlparse(base_url).hostname == urlparse(url).hostname


def _is_html(content_type: str) -> bool:
    return "text/html" in content_type.lower()


def _normalize_url(base_url: str, href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return None
    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    return absolute.split("#")[0]


def _compute_broken_links(
    pages: dict[str, PageResult],
    start_url: str,
    canonical_aliases: list[str] | None = None,
) -> dict[str, list[str]]:
    broken: dict[str, list[str]] = {}
    for url, page_result in pages.items():
        for link in page_result.links:
            if not _same_domain(start_url, link, canonical_aliases):
                continue
            target = pages.get(link)
            if target is None:
                continue
            if target.status is None or (target.status and target.status >= 400):
                broken.setdefault(link, []).append(url)
    return broken


def _compute_non_canonical_links(
    pages: dict[str, PageResult],
    start_url: str,
    canonical_aliases: list[str] | None = None,
) -> dict[str, list[str]]:
    non_canonical: dict[str, list[str]] = {}
    for url, page_result in pages.items():
        if page_result.canonical is None:
            continue
        for link in page_result.links:
            if not _same_domain(start_url, link, canonical_aliases):
                continue
            target = pages.get(link)
            if target is None:
                continue
            if target.canonical is None:
                continue
            resolved = _resolve_alias(link, start_url, canonical_aliases or [])
            if resolved != target.canonical:
                non_canonical.setdefault(link, []).append(url)
    return non_canonical


def _compute_missing_canonical(
    pages: dict[str, PageResult], start_url: str
) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for url, page_result in pages.items():
        if not page_result.is_html:
            continue
        if page_result.canonical is not None:
            continue
        for source_url, source_result in pages.items():
            if url in source_result.links:
                missing.setdefault(url, []).append(source_url)
    return missing


async def crawl(
    start_url: str,
    *,
    delay_ms: int = 100,
    check_canonical: bool = True,
    take_screenshots: bool = True,
    screenshots_dir: str = "./screenshots",
    traverse: bool = True,
    canonical_aliases: list[str] | None = None,
) -> CrawlResult:
    from .checks import check_canonical_tag
    from .screenshots import take_screenshot

    from rich.console import Console

    console = Console()

    result = CrawlResult()
    visited: set[str] = set()
    queue: asyncio.Queue[str] = asyncio.Queue()
    await queue.put(start_url)
    visited.add(start_url)
    total_visited = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720}, ignore_https_errors=True
        )
        page = await context.new_page()

        while not queue.empty():
            url = await queue.get()
            total_visited += 1
            console.print(f"[dim][{total_visited}] {url}[/dim]")
            page_result = PageResult(url=url)

            try:
                response = await page.goto(url, wait_until="domcontentloaded")
                page_result.status = response.status if response else None
                content_type = (
                    response.headers.get("content-type", "") if response else ""
                )
            except Exception:
                try:
                    resp = await context.request.get(url)
                    page_result.status = resp.status
                    content_type = resp.headers.get("content-type", "")
                except Exception:
                    page_result.status = None
                    content_type = ""
                page_result.is_html = _is_html(content_type)
                result.pages[url] = page_result
                await asyncio.sleep(delay_ms / 1000)
                continue

            page_result.is_html = _is_html(content_type)

            if not page_result.is_html:
                result.pages[url] = page_result
                await asyncio.sleep(delay_ms / 1000)
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
                ) = await check_canonical_tag(page, url, start_url, canonical_aliases)

            if take_screenshots:
                page_result.screenshot_path = await take_screenshot(
                    page, url, screenshots_dir
                )

            result.pages[url] = page_result

            if traverse:
                for link in normalized_links:
                    if (
                        _same_domain(start_url, link, canonical_aliases)
                        and link not in visited
                    ):
                        visited.add(link)
                        await queue.put(link)

            await asyncio.sleep(delay_ms / 1000)

        await browser.close()

    result.broken_links = _compute_broken_links(
        result.pages, start_url, canonical_aliases
    )
    result.non_canonical_links = _compute_non_canonical_links(
        result.pages, start_url, canonical_aliases
    )
    result.missing_canonical = _compute_missing_canonical(result.pages, start_url)

    return result
