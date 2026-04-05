from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request

from backend.app.models.schemas import (
    AskRequest,
    AskResponse,
    ConfigResponse,
    ContextRequest,
    ContextResponse,
    HealthResponse,
    MCPConfigRequest,
    MCPConfigResponse,
    OpenLocationRequest,
    PageRecord,
    ServiceStatus,
    SourceRecord,
    TestResult,
    UpdateConfigRequest,
)
from backend.app.services.hub import ServiceContainer


router = APIRouter(prefix="/api", tags=["veriagent"])


def get_container(request: Request) -> ServiceContainer:
    return request.app.state.container


@router.get("/config", response_model=ConfigResponse)
def get_config(request: Request) -> ConfigResponse:
    return get_container(request).public_config()


@router.post("/config", response_model=ConfigResponse)
def update_config(payload: UpdateConfigRequest, request: Request) -> ConfigResponse:
    return get_container(request).update_config(payload)


@router.post("/confluence/test", response_model=TestResult)
def test_confluence(request: Request) -> TestResult:
    return get_container(request).confluence().test_connection()


@router.post("/ollama/test", response_model=TestResult)
def test_ollama(request: Request) -> TestResult:
    return get_container(request).ollama().test_connection()


@router.get("/confluence/pages", response_model=list[SourceRecord])
def list_pages(request: Request, limit: int = 25, query: str = "") -> list[SourceRecord]:
    return get_container(request).confluence().list_pages(limit=limit, query=query)


@router.get("/confluence/pages/{page_id}", response_model=PageRecord)
def get_page(page_id: str, request: Request) -> PageRecord:
    return get_container(request).confluence().get_page(page_id)


@router.post("/qa/ask", response_model=AskResponse)
def ask_from_confluence(payload: AskRequest, request: Request) -> AskResponse:
    return get_container(request).qa().answer(
        query=payload.query,
        top_k=payload.top_k,
        generate_selenium=payload.generate_selenium,
    )


@router.post("/qa/context", response_model=ContextResponse)
def retrieve_confluence_context(payload: ContextRequest, request: Request) -> ContextResponse:
    return get_container(request).retrieval().retrieve_context(
        query=payload.query,
        top_k=payload.top_k,
        guidance=[
            "Answer only from the retrieved Confluence chunks.",
            "If the requested detail is missing, say it is not documented.",
            "Cite sources as Markdown links when the calling client supports it.",
        ],
    )


@router.post("/integration/config", response_model=MCPConfigResponse)
def generate_integration_config(payload: MCPConfigRequest, request: Request) -> MCPConfigResponse:
    return get_container(request).integration().generate_config(payload)


@router.post("/integration/enable", response_model=MCPConfigResponse)
def enable_integration(payload: MCPConfigRequest, request: Request) -> MCPConfigResponse:
    return get_container(request).integration().enable_integration(payload)


@router.post("/integration/open-location")
def open_location(payload: OpenLocationRequest, request: Request) -> dict[str, str]:
    resolved = get_container(request).integration().open_location(payload.path)
    return {"path": resolved}


@router.get("/integration/info")
def integration_info(request: Request) -> dict[str, str]:
    container = get_container(request)
    return {
        "mcp_url": container.settings.resolved_mcp_url(),
        "workspace_root": str(container.settings.workspace_root),
        "host_workspace_path": container.settings.host_workspace_path,
        "running_in_docker": str(container.settings.running_in_docker).lower(),
    }


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    container = get_container(request)
    backend_status = ServiceStatus(
        name="backend",
        ok=True,
        detail="Backend is running.",
        url=container.settings.public_backend_url,
    )

    try:
        confluence_test = container.confluence().test_connection()
        confluence_status = ServiceStatus(
            name="confluence",
            ok=confluence_test.ok,
            detail=confluence_test.detail,
            metadata=confluence_test.metadata,
        )
    except Exception as exc:  # noqa: BLE001
        confluence_status = ServiceStatus(name="confluence", ok=False, detail=str(exc))

    try:
        ollama_test = container.ollama().test_connection()
        ollama_status = ServiceStatus(
            name="ollama",
            ok=ollama_test.ok,
            detail=ollama_test.detail,
            url=container.runtime_config().ollama_base_url,
            metadata=ollama_test.metadata,
        )
    except Exception as exc:  # noqa: BLE001
        ollama_status = ServiceStatus(name="ollama", ok=False, detail=str(exc))

    mcp_status = ServiceStatus(
        name="mcp",
        ok=True,
        detail="Mounted on the backend and ready for local editor connections.",
        url=container.settings.resolved_mcp_url(),
    )

    return HealthResponse(
        backend=backend_status,
        confluence=confluence_status,
        ollama=ollama_status,
        mcp=mcp_status,
        checked_at=datetime.now(timezone.utc),
    )
