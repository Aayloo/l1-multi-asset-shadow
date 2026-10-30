from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.images: list[str] = []
        self.local_paths: list[str] = []
        self.fragments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "img":
            self.images.append(values.get("src") or "")
            assert values.get("alt"), "All images need alternative text."
        for attribute in ("src", "href"):
            value = values.get(attribute)
            if not value:
                continue
            parsed = urlparse(value)
            if value.startswith("#"):
                self.fragments.append(value[1:])
            elif not parsed.scheme and not parsed.netloc:
                self.local_paths.append(parsed.path)


def test_static_site_assets_and_anchors():
    parser = PageParser()
    parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    assert len(parser.ids) == len(set(parser.ids))
    for fragment in parser.fragments:
        assert fragment in parser.ids
    for resource in parser.local_paths:
        assert (ROOT / resource).resolve().exists(), resource
    assert len(parser.images) == 5


def test_latest_weights_are_long_only_and_fully_invested():
    results = json.loads((ROOT / "assets" / "data" / "results.json").read_text(encoding="utf-8"))
    weights = list(results["latest_weights"].values())
    assert abs(sum(weights) - 1) < 1e-3
    assert min(weights) >= 0
    assert results["metrics"]["L1 TAA"]["months"] == 221


def test_research_disclaimer_is_visible():
    html = (ROOT / "index.html").read_text(encoding="utf-8").lower()
    assert "not investment advice" in html
    assert "no real money" in (ROOT / "reports" / "2026-10.md").read_text(encoding="utf-8").lower()
