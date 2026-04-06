from __future__ import annotations

from backend.app.core.config import AppSettings
from backend.app.models.schemas import ConfigResponse, RuntimeConfig, UpdateConfigRequest
from backend.app.services.config_store import ConfigStore
from backend.app.services.confluence import ConfluenceClient
from backend.app.services.integration import IntegrationService
from backend.app.services.llm import OllamaProvider
from backend.app.services.qa import QAService
from backend.app.services.retrieval import RetrievalService


class ServiceContainer:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.config_store = ConfigStore(settings.runtime_config_path)

    def runtime_config(self) -> RuntimeConfig:
        return self.config_store.effective_config(self.settings)

    def public_config(self) -> ConfigResponse:
        return self.config_store.public_config(self.settings)

    def update_config(self, update: UpdateConfigRequest) -> ConfigResponse:
        return self.config_store.update(self.settings, update)

    def confluence(self) -> ConfluenceClient:
        return ConfluenceClient(self.runtime_config(), self.settings)

    def ollama(self) -> OllamaProvider:
        runtime = self.runtime_config()
        return OllamaProvider(
            base_url=runtime.ollama_base_url,
            model=runtime.ollama_model,
            timeout_seconds=self.settings.ollama_timeout_seconds,
            retries=self.settings.ollama_retries,
            thinking_enabled=self.settings.ollama_thinking_enabled,
        )

    def retrieval(self) -> RetrievalService:
        return RetrievalService(self.confluence(), self.settings)

    def qa(self) -> QAService:
        return QAService(self.retrieval(), self.ollama())

    def integration(self) -> IntegrationService:
        return IntegrationService(self.settings)
