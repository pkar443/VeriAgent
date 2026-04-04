from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from backend.app.core.config import AppSettings
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.schemas import ConfigArtifact, MCPConfigRequest, MCPConfigResponse


class IntegrationService:
    def __init__(self, settings: AppSettings):
        self.settings = settings

    def generate_config(self, request: MCPConfigRequest) -> MCPConfigResponse:
        workspace_path = self._resolve_workspace_path(request.workspace_path)
        mcp_url = self.settings.resolved_mcp_url()
        vscode_path = workspace_path / ".vscode" / "mcp.json"
        codex_path = workspace_path / ".codex" / "config.toml"

        response = MCPConfigResponse(
            server_name=request.server_name,
            mcp_url=mcp_url,
            instructions=[
                "Restart VS Code after writing the config.",
                "Open Copilot Agent mode or Codex and enable the VeriAgent MCP server.",
                "If workspace-local Codex config is ignored in your setup, copy the snippet into ~/.codex/config.toml manually.",
            ],
        )

        if request.target in {"vscode", "both"}:
            response.vscode = ConfigArtifact(
                path=str(vscode_path),
                content=self._merge_vscode_content(existing_path=vscode_path, server_name=request.server_name, mcp_url=mcp_url),
            )
        if request.target in {"codex", "both"}:
            response.codex = ConfigArtifact(
                path=str(codex_path),
                content=self._merge_codex_content(existing_path=codex_path, server_name=request.server_name, mcp_url=mcp_url),
            )
        return response

    def enable_integration(self, request: MCPConfigRequest) -> MCPConfigResponse:
        response = self.generate_config(request)
        written_files: list[str] = []

        for artifact in [response.vscode, response.codex]:
            if artifact is None:
                continue
            path = Path(artifact.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(artifact.content, encoding="utf-8")
            written_files.append(str(path))

        response.written_files = written_files
        return response

    def open_location(self, raw_path: str) -> str:
        path = self._resolve_workspace_path(raw_path)
        if not path.exists():
            raise NotFoundError(f"Path does not exist: {path}")

        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"Unable to open the location automatically: {exc}") from exc
        return str(path)

    def _resolve_workspace_path(self, raw_path: str) -> Path:
        if not raw_path.strip():
            raise ValidationError("A workspace path is required.")
        return Path(raw_path).expanduser().resolve()

    def _merge_vscode_content(self, existing_path: Path, server_name: str, mcp_url: str) -> str:
        payload = {"servers": {}}
        if existing_path.exists():
            try:
                payload = json.loads(existing_path.read_text(encoding="utf-8") or "{}")
            except json.JSONDecodeError:
                payload = {"servers": {}}
        payload.setdefault("servers", {})
        payload["servers"][server_name] = {"type": "http", "url": mcp_url}
        return json.dumps(payload, indent=2)

    def _merge_codex_content(self, existing_path: Path, server_name: str, mcp_url: str) -> str:
        block = f'[mcp_servers.{server_name}]\nurl = "{mcp_url}"\n'
        if not existing_path.exists():
            return block

        existing = existing_path.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"(?ms)^\[mcp_servers\.{re.escape(server_name)}\]\s*(?:.+?\n)*(?=^\[|\Z)"
        )
        if pattern.search(existing):
            merged = pattern.sub(block + "\n", existing)
            return merged.strip() + "\n"

        existing = existing.rstrip() + "\n\n"
        return existing + block
