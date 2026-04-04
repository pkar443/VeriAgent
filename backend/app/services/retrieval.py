from __future__ import annotations

from backend.app.core.config import AppSettings
from backend.app.models.schemas import RetrievedChunk
from backend.app.services.confluence import ConfluenceClient
from backend.app.utils.text import build_snippet, score_chunk, split_text_into_chunks, stable_chunk_id


class RetrievalService:
    def __init__(self, confluence: ConfluenceClient, settings: AppSettings):
        self.confluence = confluence
        self.settings = settings

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        limit = top_k or self.settings.retrieval_top_k
        search_results = self.confluence.search_pages(
            query=query,
            limit=max(limit * 2, self.settings.confluence_search_limit),
        )
        if not search_results:
            return []

        chunks: list[RetrievedChunk] = []
        for rank, result in enumerate(search_results[:5], start=1):
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
