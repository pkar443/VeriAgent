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
