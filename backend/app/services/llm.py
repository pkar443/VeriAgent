from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

import httpx

from backend.app.core.exceptions import ConfigurationError, ExternalServiceError
from backend.app.models.schemas import TestResult

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int = 120,
        retries: int = 2,
        thinking_enabled: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.thinking_enabled = thinking_enabled

    def generate(self, prompt: str) -> str:
        if not self.base_url:
            raise ConfigurationError("Ollama base URL is not configured.")
        if not self.model:
            raise ConfigurationError("Ollama model is not configured.")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": self.thinking_enabled,
        }
        last_error: Exception | None = None

        for attempt in range(1, self.retries + 2):
            try:
                response = httpx.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                if response.status_code == 404:
                    raise ExternalServiceError(
                        f"Ollama does not have model '{self.model}' loaded. Pull the model and try again."
                    )
                if response.status_code >= 400:
                    raise ExternalServiceError(f"Ollama returned HTTP {response.status_code}.")

                data = response.json()
                text = (data.get("response") or "").strip()
                if not text:
                    raise ExternalServiceError("Ollama returned an empty response.")
                logger.info(
                    (
                        "Ollama generation completed model=%s thinking_enabled=%s prompt_chars=%s response_chars=%s "
                        "prompt_eval_count=%s eval_count=%s load_ms=%s prompt_eval_ms=%s eval_ms=%s total_ms=%s"
                    ),
                    self.model,
                    self.thinking_enabled,
                    len(prompt),
                    len(text),
                    data.get("prompt_eval_count"),
                    data.get("eval_count"),
                    _ns_to_ms(data.get("load_duration")),
                    _ns_to_ms(data.get("prompt_eval_duration")),
                    _ns_to_ms(data.get("eval_duration")),
                    _ns_to_ms(data.get("total_duration")),
                )
                return text
            except (httpx.HTTPError, ExternalServiceError) as exc:
                last_error = exc
                if attempt > self.retries:
                    break
                time.sleep(min(attempt * 1.5, 5.0))

        raise ExternalServiceError(f"Ollama generation failed: {last_error}")

    def test_connection(self) -> TestResult:
        if not self.base_url:
            raise ConfigurationError("Ollama base URL is not configured.")

        try:
            version_response = httpx.get(f"{self.base_url}/api/version", timeout=15.0)
            tags_response = httpx.get(f"{self.base_url}/api/tags", timeout=15.0)
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Unable to reach Ollama: {exc}") from exc

        if version_response.status_code >= 400:
            raise ExternalServiceError(f"Ollama version check failed with HTTP {version_response.status_code}.")
        if tags_response.status_code >= 400:
            raise ExternalServiceError(f"Ollama tags check failed with HTTP {tags_response.status_code}.")

        tags = tags_response.json().get("models", [])
        model_loaded = any(model.get("name") == self.model for model in tags)
        detail = "Ollama is reachable and the model is loaded." if model_loaded else "Ollama is reachable, but the model is not loaded yet."
        return TestResult(
            ok=model_loaded,
            detail=detail,
            metadata={
                "version": version_response.json().get("version"),
                "model_loaded": model_loaded,
                "model_name": self.model,
                "thinking_enabled": self.thinking_enabled,
            },
        )


def _ns_to_ms(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / 1_000_000, 2)
