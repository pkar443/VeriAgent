from __future__ import annotations

import copy
import json
import time
from threading import Lock
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from backend.app.core.config import AppSettings
from backend.app.core.exceptions import ConfigurationError, ExternalServiceError, NotFoundError, ValidationError
from backend.app.models.schemas import PageRecord, RuntimeConfig, SourceRecord, TestResult
from backend.app.utils.html import clean_html_content
from backend.app.utils.text import build_snippet


class ConfluenceClient:
    _response_cache: dict[str, tuple[float, dict[str, Any]]] = {}
    _cache_lock = Lock()

    def __init__(self, config: RuntimeConfig, settings: AppSettings):
        self.config = config
        self.settings = settings
        self.base_url = normalize_confluence_base_url(config.confluence_base_url)

    def _ensure_configured(self) -> None:
        if not self.base_url:
            raise ConfigurationError("Confluence base URL is not configured.")
        if not self.config.confluence_email:
            raise ConfigurationError("Confluence email is not configured.")
        if not self.config.confluence_api_token:
            raise ConfigurationError("Confluence API token is not configured.")

    def _request(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_configured()
        url = f"{self.base_url}/rest/api{path}"
        cache_key = self._cache_key(path, params)
        cached = self._get_cached_response(cache_key)
        if cached is not None:
            return cached

        try:
            response = httpx.get(
                url,
                params=params,
                auth=(self.config.confluence_email, self.config.confluence_api_token),
                timeout=30.0,
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Unable to reach Confluence: {exc}") from exc

        if response.status_code in (401, 403):
            raise ConfigurationError("Confluence credentials were rejected. Check the email or API token.")
        if response.status_code == 404:
            raise NotFoundError("The requested Confluence page was not found or is inaccessible.")
        if response.status_code >= 400:
            raise ExternalServiceError(f"Confluence returned HTTP {response.status_code}.")

        data = response.json()
        self._set_cached_response(cache_key, data)
        return data

    def test_connection(self) -> TestResult:
        data = self._request("/space", params={"limit": 1})
        return TestResult(ok=True, detail="Confluence connection succeeded.", metadata={"sample_count": data.get("size", 0)})

    def search_pages(self, query: str, limit: int = 10) -> list[SourceRecord]:
        if not query.strip():
            raise ValidationError("A search query is required.")

        cql = f'type=page and siteSearch ~ "{escape_cql(query)}"'
        data = self._request(
            "/search",
            params={"cql": cql, "limit": limit, "expand": "content.space,content.version"},
        )
        results = []
        for item in data.get("results", []):
            content = item.get("content", {})
            page_id = str(content.get("id") or item.get("id") or "")
            if not page_id:
                continue
            results.append(
                SourceRecord(
                    title=content.get("title") or item.get("title") or "Untitled",
                    page_id=page_id,
                    url=self._build_page_url(content.get("_links", {}).get("webui") or item.get("url") or ""),
                    snippet=clean_html_content(item.get("excerpt", "")) or "No excerpt available.",
                    metadata={
                        "space_key": (content.get("space") or {}).get("key"),
                        "last_updated": (content.get("version") or {}).get("when"),
                    },
                )
            )
        return results

    def list_pages(self, limit: int = 25, query: str = "") -> list[SourceRecord]:
        if query.strip():
            return self.search_pages(query=query, limit=limit)

        data = self._request(
            "/content/search",
            params={"cql": "type=page order by lastmodified desc", "limit": limit, "expand": "space,version"},
        )
        results = []
        for item in data.get("results", []):
            page_id = str(item.get("id") or "")
            if not page_id:
                continue
            results.append(
                SourceRecord(
                    title=item.get("title") or "Untitled",
                    page_id=page_id,
                    url=self._build_page_url(item.get("_links", {}).get("webui") or ""),
                    snippet="Recent Confluence page.",
                    metadata={
                        "space_key": (item.get("space") or {}).get("key"),
                        "last_updated": (item.get("version") or {}).get("when"),
                    },
                )
            )
        return results

    def get_page(self, page_id: str) -> PageRecord:
        if not page_id.strip():
            raise ValidationError("A page ID is required.")

        data = self._request(f"/content/{page_id}", params={"expand": "body.storage,space,version"})
        raw_html = ((data.get("body") or {}).get("storage") or {}).get("value", "")
        content = clean_html_content(raw_html)
        if len(content) > self.settings.max_page_characters:
            content = content[: self.settings.max_page_characters].rstrip() + "\n\n[Content truncated for retrieval safety.]"

        return PageRecord(
            title=data.get("title") or "Untitled",
            page_id=str(data.get("id") or page_id),
            url=self._build_page_url((data.get("_links") or {}).get("webui") or ""),
            snippet=build_snippet(content, max_length=280),
            content=content,
            metadata={
                "space_key": ((data.get("space") or {}).get("key")),
                "space_name": ((data.get("space") or {}).get("name")),
                "last_updated": ((data.get("version") or {}).get("when")),
            },
        )

    def _build_page_url(self, webui_path: str) -> str:
        if not webui_path:
            return self.base_url
        if webui_path.startswith("http://") or webui_path.startswith("https://"):
            return webui_path
        return f"{self.base_url}{webui_path}"

    def _cache_key(self, path: str, params: dict[str, Any] | None) -> str:
        return json.dumps(
            {
                "base_url": self.base_url,
                "email": self.config.confluence_email,
                "path": path,
                "params": params or {},
            },
            sort_keys=True,
        )

    def _get_cached_response(self, cache_key: str) -> dict[str, Any] | None:
        ttl_seconds = self.settings.confluence_cache_ttl_seconds
        if ttl_seconds <= 0:
            return None

        now = time.monotonic()
        with self._cache_lock:
            entry = self._response_cache.get(cache_key)
            if entry is None:
                return None
            expires_at, payload = entry
            if expires_at <= now:
                self._response_cache.pop(cache_key, None)
                return None
            return copy.deepcopy(payload)

    def _set_cached_response(self, cache_key: str, payload: dict[str, Any]) -> None:
        ttl_seconds = self.settings.confluence_cache_ttl_seconds
        if ttl_seconds <= 0:
            return

        expires_at = time.monotonic() + ttl_seconds
        with self._cache_lock:
            self._response_cache[cache_key] = (expires_at, copy.deepcopy(payload))


def escape_cql(query: str) -> str:
    return query.replace('"', '\\"')


def normalize_confluence_base_url(base_url: str) -> str:
    raw = base_url.strip().rstrip("/")
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    path = parsed.path.rstrip("/")
    if not path.endswith("/wiki"):
        path = f"{path}/wiki" if path else "/wiki"
    return urlunparse((parsed.scheme or "https", parsed.netloc, path, "", "", ""))
