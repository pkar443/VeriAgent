# VeriAgent MCP

This folder documents the workspace-facing MCP integration that is mounted by the FastAPI backend at `http://localhost:8000/mcp`.

The runtime implementation lives in `veriagent_mcp/server.py` so it does not shadow the official Python `mcp` package used by the backend.

Current behavior:

- Dashboard calls still use local Ollama generation through the backend REST API.
- MCP tools default to retrieval-only Confluence context so Codex can produce the final answer in the editor.
- Set `use_local_llm=true` on supported MCP tools if you explicitly want the backend to generate the final answer with Ollama instead.
