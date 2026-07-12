from __future__ import annotations

from urllib.parse import urlparse


def _canonicalize(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path

    if path.endswith("/index.html"):
        path = path[: -len("index.html")]
    elif path == "/index.html":
        path = "/"
    elif path.endswith(".html"):
        pass
    else:
        segments = [s for s in path.split("/") if s]
        if segments and "." not in segments[-1]:
            path = "/" + "/".join(segments) + "/"
        elif not segments:
            path = "/"
        else:
            path = "/" + "/".join(segments)

    if not path.startswith("/"):
        path = "/" + path

    return path


def write_internal_links(
    urls: list[str], output_path: str = "canonical_links.txt"
) -> str:
    paths: set[str] = set()
    for url in sorted(urls):
        paths.add(_canonicalize(url))

    with open(output_path, "w") as f:
        for path in sorted(paths):
            f.write(path + "\n")

    return output_path
