from __future__ import annotations

from backend.app.core.exceptions import VeriAgentError
from backend.app.models.schemas import AskResponse, MCPConfigRequest
from backend.app.services.hub import ServiceContainer
from mcp.server.fastmcp import FastMCP


def build_mcp_server(container: ServiceContainer) -> FastMCP:
    server = FastMCP(
        "VeriAgent",
        instructions=(
            "Ground all answers in Confluence content, return URLs, and use the shared VeriAgent services "
            "for retrieval, QA output, and Selenium generation."
        ),
    )

    @server.tool()
    def search_confluence(query: str, limit: int = 5) -> dict:
        """Search Confluence pages and return structured results with links."""
        try:
            results = container.confluence().search_pages(query=query, limit=limit)
            return {"ok": True, "query": query, "results": [item.model_dump() for item in results]}
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def get_confluence_page(id: str) -> dict:
        """Fetch a Confluence page by ID with cleaned content and metadata."""
        try:
            page = container.confluence().get_page(id)
            return {"ok": True, "page": page.model_dump()}
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def answer_from_confluence(query: str, top_k: int = 3) -> dict:
        """Answer a documentation question using the shared grounded QA flow."""
        try:
            answer = container.qa().answer(query=query, top_k=top_k, generate_selenium=False)
            return serialize_answer(answer)
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def generate_selenium_test_plan(query: str, top_k: int = 3) -> dict:
        """Generate grounded QA scenarios, steps, and expected results."""
        try:
            answer = container.qa().answer(query=query, top_k=top_k, generate_selenium=False)
            return serialize_answer(answer)
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def generate_selenium_code(query: str, top_k: int = 3) -> dict:
        """Generate grounded Selenium starter code alongside the QA plan."""
        try:
            answer = container.qa().answer(query=query, top_k=top_k, generate_selenium=True)
            return serialize_answer(answer)
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def list_pages(query: str = "", limit: int = 10) -> dict:
        """List recent Confluence pages or search pages by keyword."""
        try:
            pages = container.confluence().list_pages(query=query, limit=limit)
            return {"ok": True, "query": query, "results": [page.model_dump() for page in pages]}
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def get_mcp_config(workspace_path: str, target: str = "both") -> dict:
        """Generate VS Code and Codex MCP config snippets for a workspace."""
        try:
            config = container.integration().generate_config(
                MCPConfigRequest(workspace_path=workspace_path, target=target)
            )
            return {"ok": True, "config": config.model_dump()}
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    return server


def serialize_answer(answer: AskResponse) -> dict:
    return {
        "ok": answer.generation_error is None,
        "query": answer.query,
        "generate_selenium": answer.generate_selenium,
        "answer": answer.sections.answer,
        "test_scenarios": answer.sections.test_scenarios,
        "steps": answer.sections.steps,
        "expected_results": answer.sections.expected_results,
        "assumptions": answer.sections.assumptions,
        "selenium_code": answer.sections.selenium_code,
        "generation_error": answer.generation_error,
        "sources": [source.model_dump() for source in answer.sources],
        "retrieved_chunks": [chunk.model_dump() for chunk in answer.retrieved_chunks],
        "raw_output": answer.sections.raw_output,
    }
