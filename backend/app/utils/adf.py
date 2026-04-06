from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString, Tag
from markdown import markdown


def markdown_to_adf(markdown_text: str) -> dict:
    rendered_html = markdown(
        markdown_text.strip(),
        extensions=["fenced_code", "tables", "sane_lists", "nl2br"],
        output_format="html",
    )
    soup = BeautifulSoup(rendered_html, "html.parser")
    content = []
    for child in soup.contents:
        nodes = _block_nodes(child)
        content.extend(node for node in nodes if node.get("content") or node.get("text"))

    if not content:
        content = [_paragraph_node("No description provided.")]

    return {
        "type": "doc",
        "version": 1,
        "content": content,
    }


def _block_nodes(node: Tag | NavigableString) -> list[dict]:
    if isinstance(node, NavigableString):
        text = str(node).strip()
        return [_paragraph_node(text)] if text else []

    if not isinstance(node, Tag):
        return []

    name = node.name.lower()
    if name in {"p", "div"}:
        return [{"type": "paragraph", "content": _inline_nodes(node)}]
    if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = min(max(int(name[1]), 1), 6)
        return [{"type": "heading", "attrs": {"level": level}, "content": _inline_nodes(node)}]
    if name == "blockquote":
        content = []
        for child in node.children:
            content.extend(_block_nodes(child))
        return [{"type": "blockquote", "content": content or [_paragraph_node(node.get_text(" ", strip=True))]}]
    if name == "pre":
        code = node.get_text("\n", strip=False).rstrip("\n")
        return [{"type": "codeBlock", "attrs": {}, "content": [{"type": "text", "text": code or ""}]}]
    if name == "ul":
        return [{"type": "bulletList", "content": _list_items(node, ordered=False)}]
    if name == "ol":
        return [{"type": "orderedList", "attrs": {"order": 1}, "content": _list_items(node, ordered=True)}]

    blocks = []
    for child in node.children:
        blocks.extend(_block_nodes(child))
    return blocks


def _list_items(node: Tag, ordered: bool) -> list[dict]:
    items = []
    for child in node.find_all("li", recursive=False):
        item_content: list[dict] = []
        inline_buffer = []
        for grandchild in child.children:
            if isinstance(grandchild, NavigableString):
                text = str(grandchild).strip()
                if text:
                    inline_buffer.append({"type": "text", "text": text})
                continue

            if not isinstance(grandchild, Tag):
                continue

            if grandchild.name.lower() in {"ul", "ol"}:
                if inline_buffer:
                    item_content.append({"type": "paragraph", "content": inline_buffer})
                    inline_buffer = []
                nested_type = "orderedList" if grandchild.name.lower() == "ol" else "bulletList"
                nested_items = _list_items(grandchild, ordered=grandchild.name.lower() == "ol")
                list_node: dict = {"type": nested_type, "content": nested_items}
                if nested_type == "orderedList":
                    list_node["attrs"] = {"order": 1}
                item_content.append(list_node)
            elif grandchild.name.lower() in {"p", "div"}:
                if inline_buffer:
                    item_content.append({"type": "paragraph", "content": inline_buffer})
                    inline_buffer = []
                item_content.append({"type": "paragraph", "content": _inline_nodes(grandchild)})
            else:
                inline_buffer.extend(_inline_nodes(grandchild))

        if inline_buffer:
            item_content.append({"type": "paragraph", "content": inline_buffer})
        if not item_content:
            item_content = [_paragraph_node(child.get_text(" ", strip=True))]
        items.append({"type": "listItem", "content": item_content})
    return items


def _inline_nodes(node: Tag) -> list[dict]:
    fragments: list[dict] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if text:
                fragments.append({"type": "text", "text": text})
            continue

        if not isinstance(child, Tag):
            continue

        name = child.name.lower()
        if name == "br":
            fragments.append({"type": "hardBreak"})
            continue

        child_nodes = _inline_nodes(child)
        marks = _marks_for_tag(child)
        if name == "a" and child.get("href"):
            marks.append({"type": "link", "attrs": {"href": child["href"]}})

        if name == "code" and child.parent and child.parent.name and child.parent.name.lower() == "pre":
            continue

        if not child_nodes:
            text = child.get_text(" ", strip=True)
            if text:
                child_nodes = [{"type": "text", "text": text}]

        for item in child_nodes:
            if item.get("type") != "text":
                fragments.append(item)
                continue
            merged = dict(item)
            if marks:
                merged["marks"] = [*item.get("marks", []), *marks]
            fragments.append(merged)

    return _merge_text_fragments(fragments)


def _marks_for_tag(node: Tag) -> list[dict]:
    name = node.name.lower()
    if name in {"strong", "b"}:
        return [{"type": "strong"}]
    if name in {"em", "i"}:
        return [{"type": "em"}]
    if name == "code":
        return [{"type": "code"}]
    return []


def _paragraph_node(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def _merge_text_fragments(fragments: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for item in fragments:
        if item.get("type") != "text":
            merged.append(item)
            continue

        if not item.get("text"):
            continue

        if merged and merged[-1].get("type") == "text" and merged[-1].get("marks") == item.get("marks"):
            merged[-1]["text"] += item["text"]
        else:
            merged.append(item)
    return merged
