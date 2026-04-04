from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    confluence_base_url: str = Field(default="", validation_alias="CONFLUENCE_BASE_URL")
    confluence_email: str = Field(default="", validation_alias="CONFLUENCE_EMAIL")
    confluence_api_token: str = Field(default="", validation_alias="CONFLUENCE_API_TOKEN")
    ollama_base_url: str = Field(default="http://ollama:11434", validation_alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="gemma4:e2b", validation_alias="OLLAMA_MODEL")
    app_port: int = Field(default=8000, validation_alias="APP_PORT")
    mcp_port: int = Field(default=8000, validation_alias="MCP_PORT")
    public_backend_url: str = Field(default="http://localhost:8000", validation_alias="PUBLIC_BACKEND_URL")
    runtime_config_path: Path = Field(
        default_factory=lambda: Path.cwd() / ".veriagent" / "runtime-config.json",
        validation_alias="RUNTIME_CONFIG_PATH",
    )
    workspace_root: Path = Field(default_factory=Path.cwd, validation_alias="WORKSPACE_ROOT")
    retrieval_top_k: int = Field(default=3, validation_alias="RETRIEVAL_TOP_K")
    confluence_search_limit: int = Field(default=8, validation_alias="CONFLUENCE_SEARCH_LIMIT")
    max_page_characters: int = Field(default=25000, validation_alias="MAX_PAGE_CHARACTERS")
    max_chunk_characters: int = Field(default=1800, validation_alias="MAX_CHUNK_CHARACTERS")
    ollama_timeout_seconds: int = Field(default=120, validation_alias="OLLAMA_TIMEOUT_SECONDS")
    ollama_retries: int = Field(default=2, validation_alias="OLLAMA_RETRIES")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def resolved_mcp_url(self) -> str:
        base_url = self.public_backend_url.strip().rstrip("/")
        if base_url:
            parsed = urlparse(base_url)
            if parsed.hostname in {"localhost", "127.0.0.1"} and self.mcp_port:
                netloc = f"{parsed.hostname}:{self.mcp_port}"
                parsed = parsed._replace(netloc=netloc)
                base_url = urlunparse(parsed).rstrip("/")
            return f"{base_url}/mcp"
        return f"http://localhost:{self.mcp_port}/mcp"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
