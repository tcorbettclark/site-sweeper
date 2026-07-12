from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, ElementTree


def generate_sitemap(urls: list[str], output_path: str = "sitemap.xml") -> str:
    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    for url in sorted(urls):
        url_el = SubElement(urlset, "url")
        loc = SubElement(url_el, "loc")
        loc.text = url

    tree = ElementTree(urlset)
    tree.write(output_path, encoding="unicode", xml_declaration=True)

    return output_path
