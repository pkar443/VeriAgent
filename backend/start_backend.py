from __future__ import annotations

import time

import httpx
import uvicorn

from backend.app.core.config import get_settings


def wait_for_ollama(base_url: str, model: str, timeout_seconds: int = 300) -> None:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=10.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if any(item.get("name") == model for item in models):
                    return
                pull_response = httpx.post(
                    f"{base_url.rstrip('/')}/api/pull",
                    json={"model": model, "stream": False},
                    timeout=600.0,
                )
                if pull_response.status_code < 400:
                    return
        except httpx.HTTPError:
            pass
        time.sleep(3)

    raise RuntimeError(f"Ollama was not ready within {timeout_seconds} seconds.")


if __name__ == "__main__":
    settings = get_settings()
    wait_for_ollama(settings.ollama_base_url, settings.ollama_model)
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        log_level=settings.log_level.lower(),
    )
