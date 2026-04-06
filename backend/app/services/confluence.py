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
from backend.app.models.schemas import CreatePageResponse, PageRecord, RuntimeConfig, SourceRecord, SpaceRecord, TestResult
from backend.app.utils.html import clean_html_content, markdown_to_storage_html
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
        return self._request_json("/rest/api", path, params=params, use_cache=True)

    def _request_v2(
        self,
        path: str,
        *,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        use_cache: bool = True,
        action: str = "access Confluence",
    ) -> dict[str, Any]:
        return self._request_json(
            "/api/v2",
            path,
            method=method,
            params=params,
            payload=payload,
            use_cache=use_cache,
            action=action,
        )

    def _request_json(
        self,
        api_prefix: str,
        path: str,
        *,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        use_cache: bool = False,
        action: str = "access Confluence",
    ) -> dict[str, Any]:
        self._ensure_configured()
        verb = method.upper()
        url = f"{self.base_url}{api_prefix}{path}"
        cache_key = self._cache_key(api_prefix, path, verb, params)
        if verb == "GET" and use_cache:
            cached = self._get_cached_response(cache_key)
            if cached is not None:
                return cached

        try:
            response = httpx.request(
                method=verb,
                url=url,
                params=params,
                json=payload,
                auth=(self.config.confluence_email, self.config.confluence_api_token),
                timeout=30.0,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Unable to reach Confluence: {exc}") from exc

        error_message = self._extract_error_message(response)
        if response.status_code == 401:
            raise ConfigurationError("Confluence credentials were rejected. Check the email or API token.")
        if response.status_code == 403:
            raise ConfigurationError(
                error_message
                or "Confluence denied access. Check that the configured account can view or create pages in this space."
            )
        if response.status_code == 400:
            raise ValidationError(error_message or f"Confluence rejected the request to {action}.")
        if response.status_code == 404:
            raise NotFoundError("The requested Confluence page was not found or is inaccessible.")
        if response.status_code >= 400:
            raise ExternalServiceError(error_message or f"Confluence returned HTTP {response.status_code}.")

        data = response.json()
        if verb == "GET" and use_cache:
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

    def list_spaces(self, limit: int = 50) -> list[SpaceRecord]:
        data = self._request("/space", params={"limit": limit})
        results = []
        for item in data.get("results", []):
            results.append(
                SpaceRecord(
                    space_id=str(item.get("id") or ""),
                    key=str(item.get("key") or ""),
                    name=str(item.get("name") or item.get("key") or "Untitled space"),
                    type=str(item.get("type") or ""),
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

    def create_page(
        self,
        *,
        title: str,
        space: str,
        content_markdown: str,
        parent_page_id: str | None = None,
    ) -> CreatePageResponse:
        clean_title = title.strip()
        clean_space = space.strip()
        content = content_markdown.strip()
        parent_id = (parent_page_id or "").strip() or None

        if not clean_title:
            raise ValidationError("A page title is required.")
        if not clean_space:
            raise ValidationError("A space key or space ID is required.")
        if not content:
            raise ValidationError("Page content is required.")

        resolved_space = self.resolve_space(clean_space)
        storage_value = markdown_to_storage_html(content)
        if not storage_value:
            raise ValidationError("Page content could not be converted into Confluence storage format.")

        payload: dict[str, Any] = {
            "title": clean_title,
            "spaceId": resolved_space["space_id"],
            "status": "current",
            "body": {
                "representation": "storage",
                "value": storage_value,
            },
        }
        if parent_id:
            payload["parentId"] = parent_id

        data = self._request_v2(
            "/pages",
            method="POST",
            payload=payload,
            use_cache=False,
            action="create a Confluence page",
        )
        self._invalidate_cache()

        page_id = str(data.get("id") or "")
        webui_path = ((data.get("_links") or {}).get("webui")) or ""
        page_url = self._build_page_url(webui_path) if webui_path else self._fallback_page_url(page_id)

        return CreatePageResponse(
            title=data.get("title") or clean_title,
            page_id=page_id,
            url=page_url,
            status=str(data.get("status") or "created"),
            space_id=str(data.get("spaceId") or resolved_space["space_id"]),
            space_key=resolved_space["space_key"],
            space_name=resolved_space["space_name"],
            parent_page_id=str(data.get("parentId") or parent_id or "") or None,
            content_format="markdown",
        )

    def resolve_space(self, space_key_or_id: str) -> dict[str, str]:
        target = space_key_or_id.strip()
        if not target:
            raise ValidationError("A Confluence space key or space ID is required.")

        if target.isdigit():
            data = self._request_v2("/spaces/" + target, action="resolve the Confluence space")
            return {
                "space_id": str(data.get("id") or target),
                "space_key": str(data.get("key") or ""),
                "space_name": str(data.get("name") or ""),
            }

        data = self._request_v2(
            "/spaces",
            params={"keys": target, "limit": 1},
            action="resolve the Confluence space",
        )
        results = data.get("results", [])
        if not results:
            raise NotFoundError(f"Confluence space '{target}' was not found or is inaccessible.")

        space = results[0]
        return {
            "space_id": str(space.get("id") or ""),
            "space_key": str(space.get("key") or target),
            "space_name": str(space.get("name") or ""),
        }

    def _build_page_url(self, webui_path: str) -> str:
        if not webui_path:
            return self.base_url
        if webui_path.startswith("http://") or webui_path.startswith("https://"):
            return webui_path
        return f"{self.base_url}{webui_path}"

    def _fallback_page_url(self, page_id: str) -> str:
        if not page_id:
            return self.base_url
        return f"{self.base_url}/pages/viewpage.action?pageId={page_id}"

    def _cache_key(self, api_prefix: str, path: str, method: str, params: dict[str, Any] | None) -> str:
        return json.dumps(
            {
                "base_url": self.base_url,
                "email": self.config.confluence_email,
                "api_prefix": api_prefix,
                "method": method,
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

    def _invalidate_cache(self) -> None:
        with self._cache_lock:
            self._response_cache.clear()

    def _extract_error_message(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text.strip()

        if isinstance(payload, dict):
            direct_fields = ["message", "detail", "error"]
            for field in direct_fields:
                value = payload.get(field)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            errors = payload.get("errors")
            if isinstance(errors, list):
                messages = []
                for item in errors:
                    if isinstance(item, dict) and isinstance(item.get("message"), str):
                        messages.append(item["message"].strip())
                    elif isinstance(item, str):
                        messages.append(item.strip())
                if messages:
                    return "; ".join(message for message in messages if message)

            data = payload.get("data")
            if isinstance(data, dict):
                message = data.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()

        return response.text.strip()


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
