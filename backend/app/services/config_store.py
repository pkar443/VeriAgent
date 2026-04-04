from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from backend.app.core.config import AppSettings
from backend.app.models.schemas import ConfigResponse, RuntimeConfig, UpdateConfigRequest


class ConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read_raw(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError:
            return {}

    def _write_raw(self, payload: dict) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def effective_config(self, settings: AppSettings) -> RuntimeConfig:
        defaults = RuntimeConfig(
            confluence_base_url=settings.confluence_base_url,
            confluence_email=settings.confluence_email,
            confluence_api_token=settings.confluence_api_token,
            ollama_base_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
        )
        with self._lock:
            saved = self._read_raw()
        merged = defaults.model_dump()
        for key, value in saved.items():
            if key in merged and value is not None:
                merged[key] = value
        return RuntimeConfig(**merged)

    def public_config(self, settings: AppSettings) -> ConfigResponse:
        runtime = self.effective_config(settings)
        return ConfigResponse(
            confluence_base_url=runtime.confluence_base_url,
            confluence_email=runtime.confluence_email,
            confluence_api_token_set=bool(runtime.confluence_api_token),
            ollama_base_url=runtime.ollama_base_url,
            ollama_model=runtime.ollama_model,
            mcp_url=settings.resolved_mcp_url(),
            workspace_root=str(settings.workspace_root),
        )

    def update(self, settings: AppSettings, update: UpdateConfigRequest) -> ConfigResponse:
        payload = update.model_dump(exclude_none=True)
        with self._lock:
            current = self._read_raw()
            for key, value in payload.items():
                if key == "confluence_api_token" and value == "":
                    continue
                current[key] = value
            self._write_raw(current)
        return self.public_config(settings)
