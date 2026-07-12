from __future__ import annotations

import asyncio
import shutil
from urllib.parse import urlparse

import typer
from rich.console import Console

from .crawler import crawl

app = typer.Typer(
    help="Sweep a website for links, screenshots, link data, and broken links."
)


def _check_playwright_browsers() -> None:
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception:
        console = Console()
        playwright_cmd = shutil.which("playwright")
        if playwright_cmd:
            cmd = "playwright install chromium"
        else:
            cmd = "python -m playwright install chromium"
        console.print(
            "\n[bold red]Playwright browsers are not installed.[/bold red]\n"
            "Install the required browser by running:\n\n"
            f"  [bold]{cmd}[/bold]\n"
        )
        raise typer.Exit(code=1)


def _derive_canonical_info(
    url: str, canonical_origin: str | None
) -> tuple[str | None, str]:
    start = urlparse(url)
    start_origin = f"{start.scheme}://{start.netloc}"

    if canonical_origin is None:
        return None, start_origin

    parsed = urlparse(canonical_origin)
    canonical_base = f"{parsed.scheme}://{parsed.netloc}"

    if parsed.hostname == start.hostname:
        return None, start_origin

    return canonical_base, start_origin


def _run_crawl(
    url: str,
    delay: int = 100,
    screenshots: bool = True,
    screenshots_dir: str = "./screenshots",
    sizes: list[str] | None = None,
    links: bool = True,
    links_path: str = "canonical_links.txt",
    canonical: bool = True,
    external: bool = False,
    traverse: bool = True,
    canonical_origin: str | None = None,
) -> None:
    _check_playwright_browsers()

    console = Console()

    canonical_aliases, effective_origin = _derive_canonical_info(url, canonical_origin)

    if canonical_aliases:
        console.print(f"[dim]Canonical origin: {canonical_aliases}[/dim]")
        console.print("[dim]  So pages fetched from[/dim]")
        console.print(f"[dim]    {effective_origin}[/dim]")
        console.print("[dim]  will pass self-referential declarations for[/dim]")
        console.print(f"[dim]    {canonical_aliases}[/dim]")
    else:
        console.print(
            f"[dim]Assuming canonical origin is {effective_origin} — "
            f"canonical tags must match this origin[/dim]"
        )

    console.print(f"\n[bold]Checking internal links starting from[/bold] {url}")

    result = asyncio.run(
        crawl(
            url,
            delay_ms=delay,
            check_canonical=canonical,
            take_screenshots=screenshots,
            screenshots_dir=screenshots_dir,
            sizes=sizes,
            traverse=traverse,
            check_external=external,
            canonical_aliases=[canonical_aliases] if canonical_aliases else None,
        )
    )

    from .display import print_summary

    print_summary(result)

    if links and result.pages:
        from .links import write_internal_links

        all_urls = [pr.url for pr in result.pages.values()]
        path = write_internal_links(all_urls, links_path)
        console.print(f"\n[green]Canonical links written to[/green] {path}")

    if screenshots:
        console.print(f"[green]Screenshots saved to[/green] {screenshots_dir}")


@app.command()
def sweep(
    url: str = typer.Argument(help="The starting URL to sweep"),
    delay: int = typer.Option(100, "--delay", help="Delay between page visits in ms"),
    screenshots: bool = typer.Option(
        True, "--screenshots/--no-screenshots", help="Take screenshots"
    ),
    screenshots_dir: str = typer.Option(
        "./screenshots", "--screenshots-dir", help="Directory for screenshots"
    ),
    size: list[str] = typer.Option(
        None,
        "--size",
        help="Viewport size(s) for screenshots: mobile, tablet, desktop, desktop-lg",
    ),
    links: bool = typer.Option(
        True, "--links/--no-links", help="Write canonical links file"
    ),
    links_path: str = typer.Option(
        "canonical_links.txt", "--links-path", help="Canonical links output path"
    ),
    canonical: bool = typer.Option(
        True, "--canonical/--no-canonical", help="Check canonical tags"
    ),
    external: bool = typer.Option(
        False, "--external/--no-external", help="Check external links for broken URLs"
    ),
    traverse: bool = typer.Option(
        True,
        "--traverse/--single-page",
        help="Traverse all linked pages or check only the given URL",
    ),
    canonical_origin: str = typer.Option(
        None,
        "--canonical-origin",
        help="The production origin for canonical checks (defaults to the crawled URL's origin)",
    ),
) -> None:
    from .screenshots import VIEWPORT_SIZES

    sizes = size or None
    if sizes:
        for s in sizes:
            if s not in VIEWPORT_SIZES:
                from rich.console import Console

                Console().print(
                    f"[red]Unknown size '{s}'. Choose from: "
                    f"{', '.join(VIEWPORT_SIZES.keys())}[/red]"
                )
                raise typer.Exit(code=1)

    _run_crawl(
        url=url,
        delay=delay,
        screenshots=screenshots,
        screenshots_dir=screenshots_dir,
        sizes=sizes,
        links=links,
        links_path=links_path,
        canonical=canonical,
        external=external,
        traverse=traverse,
        canonical_origin=canonical_origin,
    )
