from __future__ import annotations

from backend.app.core.exceptions import VeriAgentError
from backend.app.models.schemas import AskResponse, ContextResponse, DraftSaveRequest, MCPConfigRequest
from backend.app.services.hub import ServiceContainer
from mcp.server.fastmcp import FastMCP


def build_mcp_server(container: ServiceContainer) -> FastMCP:
    server = FastMCP(
        "VeriAgent",
        instructions=(
            "Ground all answers in Confluence content and return URLs. Prefer retrieval-first tools so the calling "
            "agent can summarize from Confluence context directly. Use local Ollama generation only when explicitly requested. "
            "When publishing content, use the dedicated publishing tools and return the created URL. When a user wants to review "
            "or edit content in the dashboard first, save it as a dashboard draft instead of publishing immediately."
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
    def retrieve_confluence_context(query: str, top_k: int = 3) -> dict:
        """Retrieve grounded Confluence chunks for the agent to summarize without using the local LLM."""
        try:
            context = container.retrieval().retrieve_context(
                query=query,
                top_k=top_k,
                guidance=answer_guidance(),
            )
            return serialize_context(context, task="answer")
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def answer_from_confluence(query: str, top_k: int = 3, use_local_llm: bool = False) -> dict:
        """Get grounded support for a documentation question. By default this returns Confluence context for the agent to summarize; set use_local_llm=true to force the local Ollama QA flow."""
        try:
            if not use_local_llm:
                context = container.retrieval().retrieve_context(
                    query=query,
                    top_k=top_k,
                    guidance=answer_guidance(),
                )
                return serialize_context(context, task="answer")
            answer = container.qa().answer(query=query, top_k=top_k, generate_selenium=False)
            return serialize_answer(answer)
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def generate_selenium_test_plan(query: str, top_k: int = 3, use_local_llm: bool = False) -> dict:
        """Get grounded Confluence context for a QA test plan. By default the agent should generate the final plan from the returned sources; set use_local_llm=true to force local Ollama generation."""
        try:
            if not use_local_llm:
                context = container.retrieval().retrieve_context(
                    query=query,
                    top_k=top_k,
                    guidance=test_plan_guidance(),
                )
                return serialize_context(context, task="selenium_test_plan")
            answer = container.qa().answer(query=query, top_k=top_k, generate_selenium=False)
            return serialize_answer(answer)
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def generate_selenium_code(query: str, top_k: int = 3, use_local_llm: bool = False) -> dict:
        """Get grounded Confluence context for Selenium code generation. By default the agent should generate the final code from the returned sources; set use_local_llm=true to force local Ollama generation."""
        try:
            if not use_local_llm:
                context = container.retrieval().retrieve_context(
                    query=query,
                    top_k=top_k,
                    guidance=selenium_code_guidance(),
                )
                return serialize_context(context, task="selenium_code")
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
    def create_confluence_page(title: str, space: str, content_markdown: str, parent_page_id: str = "") -> dict:
        """Create a Confluence page from Markdown or plain-text content and return the created page URL."""
        try:
            created = container.confluence().create_page(
                title=title,
                space=space,
                content_markdown=content_markdown,
                parent_page_id=parent_page_id or None,
            )
            return {
                "ok": True,
                "mode": "publish",
                "page": created.model_dump(),
                "message": f"Created Confluence page '{created.title}'.",
            }
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def create_jira_ticket(
        summary: str,
        project_key: str,
        description_markdown: str,
        issue_type: str = "Task",
        labels: list[str] | None = None,
    ) -> dict:
        """Create a Jira issue from Markdown content and return the created issue URL."""
        try:
            created = container.jira().create_issue(
                summary=summary,
                project_key=project_key,
                description_markdown=description_markdown,
                issue_type=issue_type,
                labels=labels or [],
            )
            return {
                "ok": True,
                "mode": "publish",
                "issue": created.model_dump(),
                "message": f"Created Jira issue '{created.issue_key}'.",
            }
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def save_dashboard_draft(
        title: str,
        target: str,
        raw_input: str = "",
        structured_markdown: str = "",
        source: str = "codex",
    ) -> dict:
        """Save a draft into the dashboard studio so a human can preview, edit, and publish it later."""
        try:
            saved = container.studio().save_draft(
                DraftSaveRequest(
                    title=title,
                    target=target,
                    raw_input=raw_input,
                    structured_markdown=structured_markdown,
                    source=source,
                )
            )
            return {
                "ok": True,
                "draft": saved.model_dump(),
                "message": f"Saved dashboard draft '{saved.title}'.",
            }
        except VeriAgentError as exc:
            return {"ok": False, "error": {"code": exc.code, "message": exc.message}}

    @server.tool()
    def list_dashboard_drafts(limit: int = 10) -> dict:
        """List recent dashboard drafts so the agent can reference or update them."""
        try:
            drafts = container.studio().list_drafts(limit=limit)
            return {"ok": True, "results": [draft.model_dump() for draft in drafts]}
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
        "mode": "local_llm",
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


def serialize_context(context: ContextResponse, task: str) -> dict:
    return {
        "ok": True,
        "mode": "agent_summary",
        "task": task,
        "query": context.query,
        "top_k": context.top_k,
        "detail": context.detail,
        "guidance": context.guidance,
        "sources": [source.model_dump() for source in context.sources],
        "retrieved_chunks": [chunk.model_dump() for chunk in context.retrieved_chunks],
    }


def answer_guidance() -> list[str]:
    return [
        "Answer only from the retrieved Confluence chunks.",
        "If the requested detail is missing, say it is not documented.",
        "Keep the answer concise and include a Sources section.",
        "Format each source as a Markdown link like [Title](https://...).",
    ]


def test_plan_guidance() -> list[str]:
    return [
        "Generate the QA plan only from the retrieved Confluence chunks.",
        "Return Test Scenarios, Steps, Expected Results, Assumptions, and Sources.",
        "If details are missing, list them under Assumptions instead of inventing them.",
        "Format each source as a Markdown link like [Title](https://...).",
    ]


def selenium_code_guidance() -> list[str]:
    return [
        "Generate Selenium starter code only from the retrieved Confluence chunks.",
        "Also include test scenarios, assumptions, and source links.",
        "Do not invent locators, workflows, or test data that are not grounded in the retrieved content.",
        "Format each source as a Markdown link like [Title](https://...).",
    ]
