from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from .crawler import crawl

app = typer.Typer(
    help="Sweep a website for links, screenshots, link data, and broken links."
)


def _run_crawl(
    url: str,
    delay: int = 100,
    screenshots: bool = True,
    screenshots_dir: str = "./screenshots",
    links: bool = True,
    links_path: str = "canonical_links.txt",
    canonical: bool = True,
    traverse: bool = True,
    canonical_aliases: list[str] | None = None,
) -> None:
    console = Console()
    console.print(f"[bold]Checking[/bold] {url} ...\n")

    result = asyncio.run(
        crawl(
            url,
            delay_ms=delay,
            check_canonical=canonical,
            take_screenshots=screenshots,
            screenshots_dir=screenshots_dir,
            traverse=traverse,
            canonical_aliases=canonical_aliases,
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
    links: bool = typer.Option(
        True, "--links/--no-links", help="Write canonical links file"
    ),
    links_path: str = typer.Option(
        "canonical_links.txt", "--links-path", help="Canonical links output path"
    ),
    canonical: bool = typer.Option(
        True, "--canonical/--no-canonical", help="Check canonical tags"
    ),
    traverse: bool = typer.Option(
        True,
        "--traverse/--single-page",
        help="Traverse all linked pages or check only the given URL",
    ),
    canonical_alias: list[str] = typer.Option(
        [],
        "--canonical-alias",
        help="Treat this URL's domain as equivalent to the crawled domain for canonical checks",
    ),
) -> None:
    _run_crawl(
        url=url,
        delay=delay,
        screenshots=screenshots,
        screenshots_dir=screenshots_dir,
        links=links,
        links_path=links_path,
        canonical=canonical,
        traverse=traverse,
        canonical_aliases=canonical_alias or None,
    )
