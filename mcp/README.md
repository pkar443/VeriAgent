# VeriAgent MCP

This folder documents the workspace-facing MCP integration that is mounted by the FastAPI backend at `http://localhost:8000/mcp`.

The runtime implementation lives in `veriagent_mcp/server.py` so it does not shadow the official Python `mcp` package used by the backend.
