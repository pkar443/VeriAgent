from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.core.exceptions import ValidationError
from backend.app.models.schemas import (
    CreatePageResponse,
    CreateJiraIssueResponse,
    DraftPreviewResponse,
    DraftPublishRequest,
    DraftPublishResponse,
    DraftRecord,
    DraftSaveRequest,
    DraftTransformRequest,
    DraftTransformResponse,
    StudioTarget,
)
from backend.app.services.confluence import ConfluenceClient
from backend.app.services.drafts import DraftStore
from backend.app.services.jira import JiraClient
from backend.app.services.llm import LLMProvider
from backend.app.utils.html import markdown_to_storage_html


DOCUMENT_PROMPT = """You are a documentation operations assistant.

Use ONLY the provided source material.
Do NOT invent missing details.
Preserve URLs, identifiers, dates, and names exactly when they appear in the input.
If important details are missing, capture them under Assumptions instead of fabricating them.

Return concise, polished Markdown for the requested artifact.
"""


@dataclass
class PublishResult:
    platform: str
    external_id: str
    url: str
    title: str
    metadata: dict


class StudioService:
    def __init__(
        self,
        llm: LLMProvider,
        drafts: DraftStore,
        confluence: ConfluenceClient,
        jira: JiraClient,
    ):
        self.llm = llm
        self.drafts = drafts
        self.confluence = confluence
        self.jira = jira

    def list_drafts(self, limit: int = 20) -> list[DraftRecord]:
        return self.drafts.list(limit=limit)

    def get_draft(self, draft_id: str) -> DraftRecord:
        return self.drafts.get(draft_id)

    def save_draft(self, request: DraftSaveRequest) -> DraftRecord:
        preview_html = request.preview_html
        if request.structured_markdown.strip() and not preview_html:
            preview_html = self.render_preview(request.target, request.title, request.structured_markdown).preview_html
        draft_request = request.model_copy(update={"preview_html": preview_html})
        return self.drafts.save(draft_request)

    def transform(self, request: DraftTransformRequest) -> DraftTransformResponse:
        raw_input = request.raw_input.strip()
        if not raw_input:
            raise ValidationError("Raw input is required before VeriAgent can structure the document.")

        prompt = build_document_prompt(
            target=request.target,
            raw_input=raw_input,
            title=request.title,
            existing_markdown=request.existing_markdown,
            context_notes=request.context_notes,
        )
        llm_output = self.llm.generate(prompt)
        parsed = parse_document_output(llm_output)
        title = request.title.strip() or parsed.title or fallback_title_for_target(request.target)
        preview = self.render_preview(request.target, title, parsed.body_markdown)
        return DraftTransformResponse(
            title=title,
            target=request.target,
            structured_markdown=parsed.body_markdown,
            preview_html=preview.preview_html,
            assumptions=parsed.assumptions,
            suggested_publish_target=suggested_publish_target(request.target),
        )

    def render_preview(self, target: StudioTarget, title: str, structured_markdown: str) -> DraftPreviewResponse:
        body_html = markdown_to_storage_html(structured_markdown)
        preview_html = build_preview_html(
            title=title.strip() or fallback_title_for_target(target),
            body_html=body_html,
            target=target,
        )
        return DraftPreviewResponse(
            target=target,
            title=title.strip() or fallback_title_for_target(target),
            preview_html=preview_html,
            rendered_format="storage_html",
        )

    def publish(self, request: DraftPublishRequest) -> DraftPublishResponse:
        title = request.title.strip()
        body = request.structured_markdown.strip()
        if not title:
            raise ValidationError("A title is required before publishing.")
        if not body:
            raise ValidationError("Structured content is required before publishing.")

        if request.target in {"confluence_page", "prd"}:
            if not request.confluence_space.strip():
                raise ValidationError("A Confluence space is required to publish this artifact.")
            created = self.confluence.create_page(
                title=title,
                space=request.confluence_space,
                content_markdown=body,
                parent_page_id=request.parent_page_id,
            )
            result = publish_result_from_confluence(created)
        else:
            if not request.jira_project_key.strip():
                raise ValidationError("A Jira project key is required to publish a Jira ticket.")
            created_issue = self.jira.create_issue(
                summary=title,
                project_key=request.jira_project_key,
                description_markdown=body,
                issue_type=request.jira_issue_type,
                labels=request.jira_labels,
            )
            result = publish_result_from_jira(created_issue)

        if request.draft_id:
            self.drafts.mark_published(
                request.draft_id,
                metadata={
                    "published_platform": result.platform,
                    "published_url": result.url,
                    "external_id": result.external_id,
                    **result.metadata,
                },
            )

        return DraftPublishResponse(
            target=request.target,
            platform=result.platform,  # type: ignore[arg-type]
            title=result.title,
            external_id=result.external_id,
            url=result.url,
            status="published",
            metadata=result.metadata,
        )


def build_document_prompt(
    *,
    target: StudioTarget,
    raw_input: str,
    title: str,
    existing_markdown: str,
    context_notes: str,
) -> str:
    target_instructions = {
        "confluence_page": (
            "Turn the input into a polished Confluence page in Markdown with sections such as Summary, Context, Details, "
            "Risks, Next Steps, and Sources when available."
        ),
        "jira_ticket": (
            "Turn the input into a polished Jira ticket in Markdown with sections such as Problem, Background, "
            "Acceptance Criteria, Risks, and Links when available."
        ),
        "prd": (
            "Turn the input into a concise product requirements document in Markdown with sections such as Problem Statement, "
            "Goals, Non-goals, Users, Requirements, Constraints, Open Questions, and Sources when available."
        ),
    }
    title_hint = title.strip() or "Create a concise, useful title from the input."
    existing_hint = existing_markdown.strip() or "No existing markdown draft is available."
    notes_hint = context_notes.strip() or "No extra context notes were supplied."
    return "\n\n".join(
        [
            DOCUMENT_PROMPT.strip(),
            f"TARGET ARTIFACT: {human_target_name(target)}",
            target_instructions[target],
            "OUTPUT FORMAT:",
            "Title:",
            "...",
            "",
            "Body Markdown:",
            "...",
            "",
            "Assumptions:",
            "...",
            "",
            f"TITLE HINT:\n{title_hint}",
            "",
            f"EXISTING MARKDOWN:\n{existing_hint}",
            "",
            f"CONTEXT NOTES:\n{notes_hint}",
            "",
            f"SOURCE MATERIAL:\n{raw_input}",
        ]
    )


def parse_document_output(raw_output: str) -> "ParsedDocument":
    pattern = re.compile(r"^(Title|Body Markdown|Assumptions)\s*:\s*", re.IGNORECASE | re.MULTILINE)
    matches = list(pattern.finditer(raw_output))
    if not matches:
        markdown = raw_output.strip()
        return ParsedDocument(title="", body_markdown=markdown, assumptions="")

    values: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group(1).strip().lower().replace(" ", "_")
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_output)
        values[heading] = raw_output[start:end].strip()

    body = values.get("body_markdown", "").strip() or raw_output.strip()
    return ParsedDocument(
        title=values.get("title", "").strip(),
        body_markdown=body,
        assumptions=values.get("assumptions", "").strip(),
    )


def build_preview_html(*, title: str, body_html: str, target: StudioTarget) -> str:
    eyebrow = {
        "confluence_page": "Confluence Page Preview",
        "jira_ticket": "Jira Ticket Preview",
        "prd": "PRD Preview",
    }[target]
    return f"""
    <html>
      <head>
        <style>
          body {{
            margin: 0;
            padding: 0;
            background: #f8fafc;
            font-family: Inter, Arial, sans-serif;
            color: #142033;
          }}
          .frame {{
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            border: 1px solid rgba(15, 23, 42, 0.09);
            border-radius: 22px;
            padding: 28px;
            box-sizing: border-box;
            min-height: 480px;
          }}
          .eyebrow {{
            color: #0f766e;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-size: 12px;
            font-weight: 800;
            margin-bottom: 10px;
          }}
          .title {{
            font-size: 31px;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 22px;
          }}
          .body {{
            font-size: 15px;
            line-height: 1.7;
            color: #243244;
          }}
          .body h1, .body h2, .body h3, .body h4 {{
            color: #132238;
            line-height: 1.2;
            margin-top: 26px;
            margin-bottom: 12px;
          }}
          .body h1 {{ font-size: 28px; }}
          .body h2 {{ font-size: 22px; }}
          .body h3 {{ font-size: 18px; }}
          .body p {{ margin: 0 0 12px 0; }}
          .body ul, .body ol {{ margin: 0 0 16px 20px; padding: 0; }}
          .body li {{ margin: 0 0 6px 0; }}
          .body pre {{
            background: #0f172a;
            color: #e2e8f0;
            border-radius: 14px;
            padding: 16px;
            overflow-x: auto;
          }}
          .body code {{
            font-family: Consolas, monospace;
            background: rgba(15, 23, 42, 0.06);
            padding: 2px 6px;
            border-radius: 8px;
          }}
          .body pre code {{
            background: transparent;
            padding: 0;
          }}
          .body blockquote {{
            margin: 18px 0;
            padding: 4px 0 4px 16px;
            border-left: 4px solid #60a5fa;
            color: #334155;
            background: rgba(96, 165, 250, 0.08);
            border-radius: 0 12px 12px 0;
          }}
          .body table {{
            border-collapse: collapse;
            width: 100%;
            margin: 18px 0;
          }}
          .body th, .body td {{
            border: 1px solid rgba(15, 23, 42, 0.10);
            padding: 10px 12px;
            text-align: left;
          }}
          .body th {{
            background: rgba(15, 118, 110, 0.08);
          }}
          .body a {{
            color: #1d4ed8;
            text-decoration: none;
          }}
        </style>
      </head>
      <body>
        <div class="frame">
          <div class="eyebrow">{eyebrow}</div>
          <div class="title">{title}</div>
          <div class="body">{body_html}</div>
        </div>
      </body>
    </html>
    """


def suggested_publish_target(target: StudioTarget) -> str:
    return "jira" if target == "jira_ticket" else "confluence"


def fallback_title_for_target(target: StudioTarget) -> str:
    return {
        "confluence_page": "Confluence Draft",
        "jira_ticket": "Jira Ticket Draft",
        "prd": "Product Requirements Draft",
    }[target]


def human_target_name(target: StudioTarget) -> str:
    return {
        "confluence_page": "Confluence Page",
        "jira_ticket": "Jira Ticket",
        "prd": "Product Requirements Document",
    }[target]


def publish_result_from_confluence(result: CreatePageResponse) -> PublishResult:
    return PublishResult(
        platform="confluence",
        external_id=result.page_id,
        url=result.url,
        title=result.title,
        metadata={
            "space_key": result.space_key,
            "space_id": result.space_id,
            "parent_page_id": result.parent_page_id,
        },
    )


def publish_result_from_jira(result: CreateJiraIssueResponse) -> PublishResult:
    return PublishResult(
        platform="jira",
        external_id=result.issue_key,
        url=result.url,
        title=result.summary,
        metadata={
            "project_key": result.project_key,
            "issue_type": result.issue_type,
        },
    )


@dataclass
class ParsedDocument:
    title: str
    body_markdown: str
    assumptions: str
