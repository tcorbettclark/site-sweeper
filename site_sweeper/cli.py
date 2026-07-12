from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from .crawler import crawl

app = typer.Typer(
    help="Sweep a website for links, screenshots, sitemap data, and broken links."
)


def _run_crawl(
    url: str,
    delay: int = 100,
    screenshots: bool = True,
    screenshots_dir: str = "./screenshots",
    sitemap: bool = True,
    sitemap_path: str = "sitemap.xml",
    broken_links: bool = True,
    canonical: bool = True,
) -> None:
    console = Console()
    console.print(f"[bold]Sweeping[/bold] {url} ...\n")

    result = asyncio.run(
        crawl(
            url,
            delay_ms=delay,
            check_broken_links=broken_links,
            check_canonical=canonical,
            take_screenshots=screenshots,
            screenshots_dir=screenshots_dir,
        )
    )

    from .display import print_summary

    print_summary(result)

    if sitemap and result.pages:
        from .sitemap import generate_sitemap

        urls = list(result.pages.keys())
        path = generate_sitemap(urls, sitemap_path)
        console.print(f"\n[green]Sitemap written to[/green] {path}")

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
    sitemap: bool = typer.Option(
        True, "--sitemap/--no-sitemap", help="Generate sitemap.xml"
    ),
    sitemap_path: str = typer.Option(
        "sitemap.xml", "--sitemap-path", help="Sitemap output path"
    ),
    broken_links: bool = typer.Option(
        True, "--broken-links/--no-broken-links", help="Check broken links"
    ),
    canonical: bool = typer.Option(
        True, "--canonical/--no-canonical", help="Check canonical tags"
    ),
) -> None:
    _run_crawl(
        url=url,
        delay=delay,
        screenshots=screenshots,
        screenshots_dir=screenshots_dir,
        sitemap=sitemap,
        sitemap_path=sitemap_path,
        broken_links=broken_links,
        canonical=canonical,
    )
