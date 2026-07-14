from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs):
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif tag in {"br", "p", "div", "li", "section", "article", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str):
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag in {"p", "div", "li", "section", "article", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str):
        if not self._ignored_depth:
            self.parts.append(data)


def preprocess_text(text: str) -> str:
    """Strip HTML and normalize Unicode and whitespace."""
    if not text:
        return ""

    parser = _HTMLTextExtractor()
    parser.feed(text)
    parser.close()
    normalized = unicodedata.normalize("NFKC", "".join(parser.parts))
    normalized = normalized.replace("\u00a0", " ").replace("\u3000", " ")
    normalized = re.sub(r"[^\S\n]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = re.sub(r"\n{2,}", "\n", normalized)
    return normalized.strip()


def preprocess_samples(samples: list[str]) -> list[str]:
    cleaned = [preprocess_text(sample) for sample in samples]
    return [sample for sample in cleaned if sample]
