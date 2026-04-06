from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup
from markdown import markdown


def clean_html_content(raw_html: str) -> str:
    if not raw_html:
        return ""

    soup = BeautifulSoup(raw_html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    for block in soup.find_all(["br", "p", "div", "section", "article", "li", "ul", "ol", "tr", "table"]):
        block.append("\n")

    for header in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        header.insert_before("\n")
        header.append("\n")

    text = soup.get_text(" ", strip=False)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def markdown_to_storage_html(markdown_text: str) -> str:
    content = markdown_text.strip()
    if not content:
        return ""

    rendered = markdown(
        content,
        extensions=["fenced_code", "tables", "sane_lists", "nl2br"],
        output_format="html",
    )
    return rendered.strip()
