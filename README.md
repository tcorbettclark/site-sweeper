# Site Sweeper

A command-line tool to sweep a website for all internal links, take screenshots, generate sitemap data, and check for broken links and canonical tag issues.

Uses [Playwright](https://playwright.dev/python/) (headless Chromium) to render pages, extract links, verify canonical tags, and capture screenshots.

## Features

- **Crawl & traverse** — recursively follows all internal links from a starting URL
- **Broken link detection** — identifies internal pages returning 4xx/5xx status codes
- **Canonical tag validation** — checks for missing, mismatched, or malformed `<link rel="canonical">` tags
- **Non-canonical link detection** — flags internal links that point to non-canonical URLs (e.g. linking to `/page` when the canonical is `/page/`)
- **External link checking** — optionally verifies that external links are reachable
- **Screenshots** — captures page screenshots at configurable viewport sizes (mobile, tablet, desktop, desktop-lg)
- **Canonical links file** — writes a list of canonicalised internal paths for sitemap generation

## Installation

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/) (or pip).

```bash
# Clone the repository
git clone https://github.com/tcorbettclark/site-sweeper.git
cd site-sweeper

# Install dependencies
uv sync

# Install the Playwright browser
uv run playwright install chromium
```

Or with pip:

```bash
pip install -e .
playwright install chromium
```

## Usage

```bash
site-sweeper <URL>
```

### Examples

Sweep a local site:

```bash
site-sweeper http://localhost:8000
```

Sweep a production site, treating `localhost` as an alias for the canonical origin:

```bash
site-sweeper http://localhost:8000 --canonical-origin https://example.com
```

Check only a single page (don't follow links):

```bash
site-sweeper http://localhost:8000 --single-page
```

Take screenshots at mobile and desktop sizes:

```bash
site-sweeper http://localhost:8000 --size mobile --size desktop
```

Skip screenshots and only check links:

```bash
site-sweeper http://localhost:8000 --no-screenshots
```

Check external links for broken URLs:

```bash
site-sweeper http://localhost:8000 --external
```

### Options

| Option | Default | Description |
| --- | --- | --- |
| `--delay` | `100` | Delay between page visits in milliseconds |
| `--screenshots` / `--no-screenshots` | `--screenshots` | Whether to take screenshots |
| `--screenshots-dir` | `./screenshots` | Directory to save screenshots |
| `--size` | `desktop` | Viewport size(s): `mobile`, `tablet`, `desktop`, `desktop-lg`. Can be specified multiple times |
| `--links` / `--no-links` | `--links` | Whether to write the canonical links file |
| `--links-path` | `canonical_links.txt` | Output path for the canonical links file |
| `--canonical` / `--no-canonical` | `--canonical` | Whether to check canonical tags |
| `--external` / `--no-external` | `--no-external` | Whether to check external links for broken URLs |
| `--traverse` / `--single-page` | `--traverse` | Traverse all linked pages, or check only the given URL |
| `--canonical-origin` | *(auto)* | The production origin for canonical checks (defaults to the crawled URL's origin) |

### Output

The tool prints a summary to the terminal showing:

- Pages that failed to load or returned error status codes
- Canonical tag issues (missing, mismatched, malformed)
- Non-canonical internal links and what the correct canonical URL should be
- Broken internal and external links

It also writes:

- **Screenshots** to `./screenshots/` (or the configured directory), named `<hostname>_<path>_<size>.png`
- **Canonical links** to `canonical_links.txt` (or the configured path), containing one normalised path per line — suitable for sitemap generation

## Demo

A small static site is included in `demo/site/` that exercises all of site-sweeper's checks — broken links, missing canonicals, canonical mismatches, and non-canonical links.

To run the demo:

```bash
bash demo/demo.sh
```

This starts a local server on port 8765, runs site-sweeper against it (including `--external`), and saves screenshots and canonical links to `demo/`.

### What the demo checks

| Page | Issue |
| --- | --- |
| `/` | Proper canonical; links to everything including a broken page and an external link |
| `/about/` | Proper canonical |
| `/contact/` | Missing canonical tag |
| `/blog/post-one/` | Canonical mismatch (points to `/blog/post-two/`) |
| `/blog/post-two/` | Home links to `/blog/post-two` (no trailing slash) — non-canonical link |
| `/broken-page/` | 404 — broken link |

### Recording a demo video

To record a terminal demo and generate a GIF (requires [agg](https://github.com/asciinema/agg), `brew install agg`):

```bash
bash demo/record-demo.sh
```

This records with [asciinema](https://asciinema.org/) and converts to `demo/demo.gif` automatically.

## License

[MIT](LICENSE)