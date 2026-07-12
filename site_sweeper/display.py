from __future__ import annotations

from .crawler import CrawlResult


def print_summary(result: CrawlResult) -> None:
    from rich.console import Console
    from rich.table import Table

    console = Console()

    pages = list(result.pages.values())
    total = len(pages)
    ok = sum(1 for p in pages if p.status and 200 <= p.status < 400)
    broken_count = len(result.broken_links)
    canonical_issues = sum(1 for p in pages if p.canonical_issues)

    console.print(f"\n[bold]Sweep complete![/bold] Visited {total} page(s)\n")

    table = Table(title="Pages")
    table.add_column("URL", style="cyan", no_wrap=True)
    table.add_column("Status", justify="right")
    table.add_column("Canonical Issues")
    table.add_column("Broken Links", justify="right")

    for p in pages:
        status_str = str(p.status) if p.status else "[red]FAILED[/red]"
        if p.status and p.status >= 400:
            status_str = f"[red]{status_str}[/red]"
        elif p.status and 200 <= p.status < 300:
            status_str = f"[green]{status_str}[/green]"

        canonical_str = (
            ", ".join(p.canonical_issues) if p.canonical_issues else "[green]OK[/green]"
        )
        broken_str = str(len(p.broken_links)) if p.broken_links else "-"

        table.add_row(p.url, status_str, canonical_str, broken_str)

    console.print(table)

    if result.broken_links:
        console.print("\n[bold red]Broken Links[/bold red]")
        for broken_url, sources in result.broken_links.items():
            console.print(f"  [red]{broken_url}[/red] <- {', '.join(sources)}")

    console.print(
        f"\n[green]{ok} OK[/green] | [red]{total - ok} failed[/red] | "
        f"[yellow]{canonical_issues} canonical issues[/yellow] | "
        f"[red]{broken_count} broken links[/red]"
    )
