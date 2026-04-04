from __future__ import annotations

import re

from backend.app.core.exceptions import ExternalServiceError, ValidationError
from backend.app.models.schemas import AskResponse, QASections, RetrievedChunk, SourceRecord
from backend.app.services.llm import LLMProvider
from backend.app.services.retrieval import RetrievalService


STRICT_PROMPT = """You are a QA engineer.

Use ONLY the provided Confluence content.
Do NOT assume missing details.

TASK:
1. Extract test scenarios
2. Create structured steps
3. Generate Selenium code if requested

OUTPUT FORMAT:
Test Scenarios:
...

Steps:
...

Expected Results:
...

Selenium Code:
...
"""


class QAService:
    def __init__(self, retrieval: RetrievalService, llm: LLMProvider):
        self.retrieval = retrieval
        self.llm = llm

    def answer(self, query: str, top_k: int, generate_selenium: bool) -> AskResponse:
        if not query.strip():
            raise ValidationError("A query is required.")

        chunks = self.retrieval.retrieve(query=query, top_k=top_k)
        sources = unique_sources(chunks)

        if not chunks:
            sections = QASections(
                answer="No relevant Confluence content was found for this query.",
                assumptions="No assumptions were made because no supporting documentation was retrieved.",
            )
            return AskResponse(
                query=query,
                generate_selenium=generate_selenium,
                sections=sections,
                sources=sources,
                retrieved_chunks=[],
            )

        prompt = build_prompt(query=query, generate_selenium=generate_selenium, chunks=chunks)

        try:
            llm_output = self.llm.generate(prompt)
            sections = parse_sections(llm_output, generate_selenium=generate_selenium)
            sections.raw_output = llm_output
            return AskResponse(
                query=query,
                generate_selenium=generate_selenium,
                sections=sections,
                sources=sources,
                retrieved_chunks=chunks,
            )
        except ExternalServiceError as exc:
            sections = QASections(
                answer="Generation is unavailable right now, but the relevant Confluence sources are still available below.",
                assumptions="The answer was not generated because the local Ollama call failed.",
            )
            return AskResponse(
                query=query,
                generate_selenium=generate_selenium,
                sections=sections,
                sources=sources,
                retrieved_chunks=chunks,
                generation_error=str(exc),
            )


def build_prompt(query: str, generate_selenium: bool, chunks: list[RetrievedChunk]) -> str:
    context_lines = []
    for index, chunk in enumerate(chunks, start=1):
        context_lines.append(
            "\n".join(
                [
                    f"Source {index}:",
                    f"Title: {chunk.title}",
                    f"Page ID: {chunk.page_id}",
                    f"URL: {chunk.url}",
                    f"Snippet: {chunk.snippet}",
                    "Content:",
                    chunk.content,
                ]
            )
        )

    selenium_instruction = "Generate Selenium Python starter code." if generate_selenium else "Write 'Not requested.' under Selenium Code."
    return "\n\n".join(
        [
            STRICT_PROMPT.strip(),
            "Additional rules:",
            "- Answer the user's question using only the provided content.",
            "- Cite sources inline using [Source 1], [Source 2], and so on.",
            "- Explicitly list missing details under Assumptions.",
            "- Do not invent URLs, page titles, selectors, workflows, or test data.",
            f"- {selenium_instruction}",
            "",
            f"USER QUESTION:\n{query}",
            "",
            "OUTPUT FORMAT:",
            "Answer:",
            "...",
            "",
            "Test Scenarios:",
            "...",
            "",
            "Steps:",
            "...",
            "",
            "Expected Results:",
            "...",
            "",
            "Assumptions:",
            "...",
            "",
            "Selenium Code:",
            "...",
            "",
            "CONFLUENCE CONTENT:",
            "\n\n".join(context_lines),
        ]
    )


def parse_sections(raw_output: str, generate_selenium: bool) -> QASections:
    pattern = re.compile(
        r"^(Answer|Test Scenarios|Steps|Expected Results|Assumptions|Selenium Code)\s*:\s*",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(pattern.finditer(raw_output))
    if not matches:
        return QASections(
            answer=raw_output.strip(),
            selenium_code="" if generate_selenium else "Not requested.",
            raw_output=raw_output,
        )

    values: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group(1).strip().lower().replace(" ", "_")
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_output)
        values[heading] = raw_output[start:end].strip()

    selenium_code = values.get("selenium_code", "")
    if not generate_selenium and not selenium_code:
        selenium_code = "Not requested."

    return QASections(
        answer=values.get("answer", ""),
        test_scenarios=values.get("test_scenarios", ""),
        steps=values.get("steps", ""),
        expected_results=values.get("expected_results", ""),
        assumptions=values.get("assumptions", ""),
        selenium_code=selenium_code,
        raw_output=raw_output,
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
