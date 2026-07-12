from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright
from rich.console import Console


@dataclass
class PageResult:
    url: str
    status: int | None = None
    canonical: str | None = None
    canonical_issues: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    screenshot_paths: dict[str, str] = field(default_factory=dict)
    is_html: bool = False


@dataclass
class CrawlResult:
    pages: dict[str, PageResult] = field(default_factory=dict)
    broken_links: dict[str, list[str]] = field(default_factory=dict)
    broken_external_links: dict[str, list[str]] = field(default_factory=dict)
    blocked_external_links: dict[str, list[str]] = field(default_factory=dict)
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


_BLOCKED_CODES = {403, 429, 999}


def _classify_external(status: int | None) -> str | None:
    if status is None:
        return "broken"
    if status < 400:
        return None
    if status in _BLOCKED_CODES:
        return "blocked"
    if status >= 500:
        return "broken"
    if status in (401, 402, 407):
        return "blocked"
    return "broken"


async def _check_external_links(
    context,
    external_links: dict[str, set[str]],
    delay_ms: int,
    console,
    total_visited: int,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    broken: dict[str, list[str]] = {}
    blocked: dict[str, list[str]] = {}
    checked: dict[str, int | None] = {}
    for url in sorted(external_links):
        total_visited += 1
        console.print(f"[dim][{total_visited}] {url}[/dim]")
        try:
            resp = await context.request.get(url)
            checked[url] = resp.status
        except Exception:
            try:
                resp = await context.request.head(url)
                checked[url] = resp.status
            except Exception:
                checked[url] = None
        await asyncio.sleep(delay_ms / 1000)

    for url, sources in external_links.items():
        status = checked.get(url)
        classification = _classify_external(status)
        if classification == "broken":
            for source in sources:
                broken.setdefault(url, []).append(source)
        elif classification == "blocked":
            for source in sources:
                blocked.setdefault(url, []).append(source)
    return broken, blocked


async def crawl(
    start_url: str,
    *,
    delay_ms: int = 100,
    check_canonical: bool = True,
    check_external: bool = False,
    take_screenshots: bool = True,
    screenshots_dir: str = "./screenshots",
    sizes: list[str] | None = None,
    traverse: bool = True,
    canonical_aliases: list[str] | None = None,
    console: Console | None = None,
) -> CrawlResult:
    from .checks import check_canonical_tag
    from .screenshots import VIEWPORT_SIZES, take_screenshot

    if console is None:
        console = Console()

    resolved_sizes = sizes or ["desktop"]

    result = CrawlResult()
    external_links: dict[str, set[str]] = {}
    total_visited = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for size_name in resolved_sizes:
            viewport = VIEWPORT_SIZES[size_name]
            context = await browser.new_context(
                viewport=viewport, ignore_https_errors=True
            )
            page = await context.new_page()

            visited_sizes: set[str] = set()
            queue: asyncio.Queue[str] = asyncio.Queue()
            await queue.put(start_url)
            visited_sizes.add(start_url)

            while not queue.empty():
                url = await queue.get()
                total_visited += 1
                console.print(f"[dim][{total_visited}] {url} ({size_name})[/dim]")

                existing = result.pages.get(url)
                page_result = existing if existing else PageResult(url=url)

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

                if not page_result.links:
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

                if check_canonical and not page_result.canonical_issues and page_result.canonical is None:
                    (
                        page_result.canonical,
                        page_result.canonical_issues,
                    ) = await check_canonical_tag(page, url, start_url, canonical_aliases)

                if take_screenshots:
                    page_result.screenshot_paths[size_name] = await take_screenshot(
                        page, url, screenshots_dir, size_name
                    )

                result.pages[url] = page_result

                for link in page_result.links:
                    if _same_domain(start_url, link, canonical_aliases):
                        if traverse and link not in visited_sizes:
                            visited_sizes.add(link)
                            if link not in result.pages:
                                await queue.put(link)
                    elif check_external:
                        external_links.setdefault(link, set()).add(url)

                await asyncio.sleep(delay_ms / 1000)

            await context.close()

        if check_external and external_links:
            context = await browser.new_context(ignore_https_errors=True)
            console.print("[bold]Checking all external links[/bold]")
            (
                result.broken_external_links,
                result.blocked_external_links,
            ) = await _check_external_links(
                context, external_links, delay_ms, console, total_visited
            )
            await context.close()

        await browser.close()

    result.broken_links = _compute_broken_links(
        result.pages, start_url, canonical_aliases
    )
    result.non_canonical_links = _compute_non_canonical_links(
        result.pages, start_url, canonical_aliases
    )
    result.missing_canonical = _compute_missing_canonical(result.pages, start_url)

    return result
