from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RuntimeConfig(BaseModel):
    confluence_base_url: str = ""
    confluence_email: str = ""
    confluence_api_token: str = ""
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "gemma4:e2b"


class ConfigResponse(BaseModel):
    confluence_base_url: str = ""
    confluence_email: str = ""
    confluence_api_token_set: bool = False
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "gemma4:e2b"
    mcp_url: str = ""
    workspace_root: str = ""
    env_file_path: str = ""
    env_file_exists: bool = False


class UpdateConfigRequest(BaseModel):
    confluence_base_url: str | None = None
    confluence_email: str | None = None
    confluence_api_token: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None


class SourceRecord(BaseModel):
    title: str
    page_id: str
    url: str
    snippet: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PageRecord(SourceRecord):
    content: str = ""


class CreatePageRequest(BaseModel):
    title: str
    space: str
    content_markdown: str
    parent_page_id: str | None = None


class CreatePageResponse(BaseModel):
    title: str
    page_id: str
    url: str
    status: str = "created"
    space_id: str
    space_key: str = ""
    space_name: str = ""
    parent_page_id: str | None = None
    content_format: str = "markdown"


StudioTarget = Literal["confluence_page", "jira_ticket", "prd"]


class DraftRecord(BaseModel):
    draft_id: str
    title: str
    target: StudioTarget
    raw_input: str = ""
    structured_markdown: str = ""
    preview_html: str = ""
    source: str = "dashboard"
    status: Literal["draft", "published"] = "draft"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class DraftSaveRequest(BaseModel):
    draft_id: str | None = None
    title: str = ""
    target: StudioTarget = "confluence_page"
    raw_input: str = ""
    structured_markdown: str = ""
    preview_html: str = ""
    source: str = "dashboard"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DraftTransformRequest(BaseModel):
    target: StudioTarget
    raw_input: str
    title: str = ""
    existing_markdown: str = ""
    context_notes: str = ""


class DraftTransformResponse(BaseModel):
    title: str
    target: StudioTarget
    structured_markdown: str
    preview_html: str
    assumptions: str = ""
    suggested_publish_target: Literal["confluence", "jira"] = "confluence"


class DraftPreviewRequest(BaseModel):
    target: StudioTarget
    title: str = ""
    structured_markdown: str


class DraftPreviewResponse(BaseModel):
    target: StudioTarget
    preview_html: str
    title: str = ""
    rendered_format: str = "storage_html"


class CreateJiraIssueRequest(BaseModel):
    summary: str
    project_key: str
    description_markdown: str
    issue_type: str = "Task"
    labels: list[str] = Field(default_factory=list)


class CreateJiraIssueResponse(BaseModel):
    summary: str
    issue_key: str
    url: str
    project_key: str
    issue_type: str
    status: str = "created"


class DraftPublishRequest(BaseModel):
    draft_id: str | None = None
    target: StudioTarget
    title: str
    structured_markdown: str
    confluence_space: str = ""
    parent_page_id: str | None = None
    jira_project_key: str = ""
    jira_issue_type: str = "Task"
    jira_labels: list[str] = Field(default_factory=list)


class DraftPublishResponse(BaseModel):
    target: StudioTarget
    platform: Literal["confluence", "jira"]
    title: str
    external_id: str
    url: str
    status: str = "published"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    chunk_id: str
    title: str
    page_id: str
    url: str
    snippet: str = ""
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class AskRequest(BaseModel):
    query: str
    top_k: int = Field(default=3, ge=1, le=5)
    generate_selenium: bool = False


class ContextRequest(BaseModel):
    query: str
    top_k: int = Field(default=3, ge=1, le=5)


class ContextResponse(BaseModel):
    query: str
    top_k: int
    detail: str = ""
    guidance: list[str] = Field(default_factory=list)
    sources: list[SourceRecord] = Field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)


class QASections(BaseModel):
    answer: str = ""
    test_scenarios: str = ""
    steps: str = ""
    expected_results: str = ""
    assumptions: str = ""
    selenium_code: str = ""
    raw_output: str = ""


class AskResponse(BaseModel):
    query: str
    generate_selenium: bool
    sections: QASections
    sources: list[SourceRecord] = Field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    generation_error: str | None = None


class AskJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    query: str
    top_k: int
    generate_selenium: bool
    submitted_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: AskResponse | None = None
    error: str | None = None


class ServiceStatus(BaseModel):
    name: str
    ok: bool
    detail: str
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    backend: ServiceStatus
    confluence: ServiceStatus
    ollama: ServiceStatus
    mcp: ServiceStatus
    checked_at: datetime


class MCPConfigRequest(BaseModel):
    workspace_path: str
    target: Literal["vscode", "codex", "both"] = "both"
    server_name: str = "veriagent"


class ConfigArtifact(BaseModel):
    path: str
    content: str


class MCPConfigResponse(BaseModel):
    server_name: str
    mcp_url: str
    vscode: ConfigArtifact | None = None
    codex: ConfigArtifact | None = None
    instructions: list[str] = Field(default_factory=list)
    written_files: list[str] = Field(default_factory=list)


class OpenLocationRequest(BaseModel):
    path: str


class TestResult(BaseModel):
    ok: bool
    detail: str
    metadata: dict[str, Any] = Field(default_factory=dict)
