from __future__ import annotations

from backend.app.core.exceptions import ValidationError
from backend.app.core.config import AppSettings
from backend.app.models.schemas import ContextResponse, RetrievedChunk, SourceRecord
from backend.app.services.confluence import ConfluenceClient
from backend.app.utils.text import build_snippet, score_chunk, split_text_into_chunks, stable_chunk_id


class RetrievalService:
    def __init__(self, confluence: ConfluenceClient, settings: AppSettings):
        self.confluence = confluence
        self.settings = settings

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        if not query.strip():
            raise ValidationError("A query is required.")

        limit = top_k or self.settings.retrieval_top_k
        search_results = self.confluence.search_pages(
            query=query,
            limit=max(limit * 2, self.settings.confluence_search_limit),
        )
        if not search_results:
            return []

        chunks: list[RetrievedChunk] = []
        pages_to_fetch = min(
            len(search_results),
            min(self.settings.max_pages_per_query, max(2, limit)),
        )
        for rank, result in enumerate(search_results[:pages_to_fetch], start=1):
            page = self.confluence.get_page(result.page_id)
            for chunk_text in split_text_into_chunks(page.content, max_chars=self.settings.max_chunk_characters):
                score = score_chunk(query, page.title, chunk_text, result.snippet, rank)
                if score <= 0:
                    continue
                chunks.append(
                    RetrievedChunk(
                        chunk_id=stable_chunk_id(page.page_id, chunk_text),
                        title=page.title,
                        page_id=page.page_id,
                        url=page.url,
                        snippet=build_snippet(chunk_text, query=query),
                        content=chunk_text,
                        score=score,
                        metadata=page.metadata,
                    )
                )

        deduped: dict[str, RetrievedChunk] = {}
        for chunk in sorted(chunks, key=lambda item: item.score, reverse=True):
            key = f"{chunk.page_id}:{chunk.chunk_id}"
            if key not in deduped:
                deduped[key] = chunk

        ranked = list(deduped.values())[:limit]
        if ranked:
            return ranked

        return [
            RetrievedChunk(
                chunk_id=f"{result.page_id}-snippet",
                title=result.title,
                page_id=result.page_id,
                url=result.url,
                snippet=result.snippet,
                content=result.snippet,
                score=1.0,
                metadata=result.metadata,
            )
            for result in search_results[:limit]
        ]

    def retrieve_context(self, query: str, top_k: int | None = None, guidance: list[str] | None = None) -> ContextResponse:
        limit = top_k or self.settings.retrieval_top_k
        chunks = self.retrieve(query=query, top_k=limit)
        sources = unique_sources(chunks)
        if chunks:
            detail = f"Retrieved {len(chunks)} grounded chunk(s) from {len(sources)} Confluence page(s)."
        else:
            detail = "No relevant Confluence content was found for this query."

        return ContextResponse(
            query=query,
            top_k=limit,
            detail=detail,
            guidance=guidance or [],
            sources=sources,
            retrieved_chunks=chunks,
        )


def unique_sources(chunks: list[RetrievedChunk]) -> list[SourceRecord]:
    seen: set[str] = set()
    sources: list[SourceRecord] = []
    for chunk in chunks:
        if chunk.page_id in seen:
            continue
        seen.add(chunk.page_id)
        sources.append(
            SourceRecord(
                title=chunk.title,
                page_id=chunk.page_id,
                url=chunk.url,
                snippet=chunk.snippet,
                metadata=chunk.metadata,
            )
        )
    return sources
