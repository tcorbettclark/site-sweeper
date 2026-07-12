from __future__ import annotations

from .crawler import CrawlResult, PageResult


def _invert_by_source(data: dict[str, list[str]]) -> dict[str, list[str]]:
    by_source: dict[str, set[str]] = {}
    for target, sources in data.items():
        for source in sources:
            by_source.setdefault(source, set()).add(target)
    return {k: sorted(v) for k, v in sorted(by_source.items())}


def print_summary(result: CrawlResult) -> None:
    from rich.console import Console

    console = Console()

    pages = list(result.pages.values())
    total = len(pages)

    broken_by_source = _invert_by_source(result.broken_links)
    non_canonical_by_source = _invert_by_source(result.non_canonical_links)
    missing_canonical_by_source = _invert_by_source(result.missing_canonical)

    ok_count = 0
    broken_page_count = 0
    for p in pages:
        has_issues = _page_has_issues(
            p, broken_by_source, non_canonical_by_source, missing_canonical_by_source
        )
        if p.status and 200 <= p.status < 400 and not has_issues:
            ok_count += 1
        if p.status is None or (p.status and p.status >= 400):
            broken_page_count += 1

    canonical_issue_count = sum(1 for p in pages if p.canonical_issues)
    missing_canonical_count = len(result.missing_canonical)
    non_canonical_count = len(result.non_canonical_links)

    console.print(f"\n[bold]Sweep complete![/bold] Visited {total} page(s)\n")

    for p in pages:
        if not _page_has_issues(
            p, broken_by_source, non_canonical_by_source, missing_canonical_by_source
        ):
            continue

        console.print(f"[bold]{p.url}[/bold]")

        if p.status is None:
            console.print("  [red]\u26a0 Failed to load[/red]")
        elif p.status and p.status >= 400:
            console.print(f"  [red]\u26a0 Broken ({p.status})[/red]")

        for issue in p.canonical_issues:
            console.print(f"  [yellow]\u26a0 {issue}[/yellow]")

        if p.url in missing_canonical_by_source:
            targets = missing_canonical_by_source[p.url]
            console.print("  Links to pages missing canonical tags:")
            for target in targets:
                console.print(f"    [yellow]{target}[/yellow]")

        if p.url in non_canonical_by_source:
            targets = non_canonical_by_source[p.url]
            console.print("  Non-canonical links:")
            for target_url in targets:
                target_page = result.pages.get(target_url)
                canonical = target_page.canonical if target_page else "?"
                console.print(
                    f"    [yellow]{target_url}[/yellow] \u2192 should be [green]{canonical}[/green]"
                )

        if p.url in broken_by_source:
            targets = broken_by_source[p.url]
            console.print("  Broken links:")
            for target_url in targets:
                target_page = result.pages.get(target_url)
                if target_page and target_page.status:
                    console.print(f"    [red]{target_url}[/red] ({target_page.status})")
                else:
                    console.print(f"    [red]{target_url}[/red]")

        console.print("")

    console.print(
        f"[green]{ok_count} OK[/green] | [red]{broken_page_count} broken[/red] | "
        f"[yellow]{canonical_issue_count} canonical issues[/yellow] | "
        f"[yellow]{missing_canonical_count} missing canonical[/yellow] | "
        f"[yellow]{non_canonical_count} non-canonical links[/yellow]"
    )


def _page_has_issues(
    p: PageResult,
    broken_by_source: dict[str, list[str]],
    non_canonical_by_source: dict[str, list[str]],
    missing_canonical_by_source: dict[str, list[str]],
) -> bool:
    if p.status is None or (p.status and p.status >= 400):
        return True
    if p.canonical_issues:
        return True
    if p.url in broken_by_source:
        return True
    if p.url in non_canonical_by_source:
        return True
    if p.url in missing_canonical_by_source:
        return True
    return False
