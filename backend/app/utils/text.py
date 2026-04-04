from __future__ import annotations

import hashlib
import re


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "what",
    "when",
    "with",
}


def tokenize_query(query: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9_]+", query.lower())
    return [token for token in tokens if len(token) > 2 and token not in STOPWORDS]


def split_text_into_chunks(text: str, max_chars: int = 1800, overlap_chars: int = 200) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", cleaned) if paragraph.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            overlap = current[-overlap_chars:] if overlap_chars else ""
            current = f"{overlap}\n\n{paragraph}".strip()
        else:
            chunks.extend(_split_long_paragraph(paragraph, max_chars=max_chars, overlap_chars=overlap_chars))
            current = ""

    if current:
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


def _split_long_paragraph(paragraph: str, max_chars: int, overlap_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    parts: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = sentence if not current else f"{current} {sentence}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            parts.append(current.strip())
            overlap = current[-overlap_chars:] if overlap_chars else ""
            current = f"{overlap} {sentence}".strip()
        else:
            for index in range(0, len(sentence), max_chars):
                parts.append(sentence[index : index + max_chars].strip())
            current = ""

    if current:
        parts.append(current.strip())
    return [part for part in parts if part]


def build_snippet(text: str, query: str = "", max_length: int = 280) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return ""
    tokens = tokenize_query(query)
    if not tokens:
        return normalized[:max_length].strip()

    lowered = normalized.lower()
    positions = [lowered.find(token) for token in tokens if lowered.find(token) >= 0]
    if not positions:
        return normalized[:max_length].strip()

    start = max(min(positions) - 60, 0)
    end = min(start + max_length, len(normalized))
    snippet = normalized[start:end].strip()
    if start > 0:
        snippet = f"... {snippet}"
    if end < len(normalized):
        snippet = f"{snippet} ..."
    return snippet


def score_chunk(query: str, title: str, content: str, snippet: str, search_rank: int) -> float:
    terms = tokenize_query(query)
    query_lower = query.lower().strip()
    title_lower = title.lower()
    content_lower = content.lower()
    snippet_lower = snippet.lower()

    score = 0.0
    if query_lower and query_lower in title_lower:
        score += 6.0
    if query_lower and query_lower in content_lower:
        score += 4.0

    for term in terms:
        score += title_lower.count(term) * 3.0
        score += snippet_lower.count(term) * 2.0
        score += content_lower.count(term) * 1.0

    score += max(0, 4 - search_rank) * 0.75
    score += min(len(content) / 500.0, 2.0)
    return score


def stable_chunk_id(page_id: str, content: str) -> str:
    digest = hashlib.sha1(f"{page_id}:{content}".encode("utf-8")).hexdigest()
    return digest[:12]
