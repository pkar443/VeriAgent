from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from backend.app.core.config import AppSettings
from backend.app.core.exceptions import ConfigurationError, ExternalServiceError, ValidationError
from backend.app.models.schemas import CreateJiraIssueResponse, IssueTypeRecord, ProjectRecord, RuntimeConfig
from backend.app.utils.adf import markdown_to_adf
from backend.app.services.confluence import normalize_confluence_base_url


class JiraClient:
    def __init__(self, config: RuntimeConfig, settings: AppSettings):
        self.config = config
        self.settings = settings
        self.site_url = derive_atlassian_site_url(config.confluence_base_url)

    def create_issue(
        self,
        *,
        summary: str,
        project_key: str,
        description_markdown: str,
        issue_type: str = "Task",
        labels: list[str] | None = None,
    ) -> CreateJiraIssueResponse:
        clean_summary = " ".join(summary.strip().split())
        clean_project = project_key.strip().upper()
        clean_issue_type = issue_type.strip() or "Task"
        clean_description = description_markdown.strip()

        if not clean_summary:
            raise ValidationError("A Jira summary is required.")
        if not clean_project:
            raise ValidationError("A Jira project key is required.")
        if not clean_description:
            raise ValidationError("A Jira description is required.")

        payload = {
            "fields": {
                "project": {"key": clean_project},
                "summary": clean_summary,
                "issuetype": {"name": clean_issue_type},
                "description": markdown_to_adf(clean_description),
                "labels": labels or [],
            }
        }
        data = self._request(
            "/rest/api/3/issue",
            method="POST",
            payload=payload,
            action="create a Jira issue",
        )
        issue_key = str(data.get("key") or "")
        return CreateJiraIssueResponse(
            summary=clean_summary,
            issue_key=issue_key,
            url=f"{self.site_url}/browse/{issue_key}" if issue_key else self.site_url,
            project_key=clean_project,
            issue_type=clean_issue_type,
            status="created",
        )

    def list_projects(self, limit: int = 100) -> list[ProjectRecord]:
        data = self._request(
            "/rest/api/3/project/search",
            method="GET",
            params={"maxResults": limit, "orderBy": "key"},
            action="list Jira projects",
        )
        results = []
        for item in data.get("values", []):
            results.append(
                ProjectRecord(
                    project_id=str(item.get("id") or ""),
                    key=str(item.get("key") or ""),
                    name=str(item.get("name") or item.get("key") or "Untitled project"),
                    project_type=str(item.get("projectTypeKey") or ""),
                )
            )
        return results

    def list_issue_types(self, project_key: str) -> list[IssueTypeRecord]:
        clean_project = project_key.strip()
        if not clean_project:
            raise ValidationError("A Jira project key is required.")

        data = self._request(
            f"/rest/api/3/issue/createmeta/{clean_project}/issuetypes",
            method="GET",
            action="list Jira issue types",
        )
        raw_items: list[dict[str, Any]]
        if isinstance(data, list):
            raw_items = [item for item in data if isinstance(item, dict)]
        else:
            raw_items = []
            for key in ("issueTypes", "values"):
                value = data.get(key)
                if isinstance(value, list):
                    raw_items = [item for item in value if isinstance(item, dict)]
                    break

        results = []
        for item in raw_items:
            results.append(
                IssueTypeRecord(
                    issue_type_id=str(item.get("id") or ""),
                    name=str(item.get("name") or "Untitled issue type"),
                    description=str(item.get("description") or ""),
                    subtask=bool(item.get("subtask")),
                    hierarchy_level=item.get("hierarchyLevel"),
                )
            )
        return results

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        action: str = "access Jira",
    ) -> dict[str, Any]:
        self._ensure_configured()
        try:
            response = httpx.request(
                method=method.upper(),
                url=f"{self.site_url}{path}",
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
            raise ExternalServiceError(f"Unable to reach Jira: {exc}") from exc

        if response.status_code == 401:
            raise ConfigurationError("Jira credentials were rejected. Check the Atlassian email or API token.")
        if response.status_code == 403:
            raise ConfigurationError("Jira denied access. Check project permissions for the configured account.")
        if response.status_code == 400:
            raise ValidationError(_extract_error_message(response) or f"Jira rejected the request to {action}.")
        if response.status_code >= 400:
            raise ExternalServiceError(_extract_error_message(response) or f"Jira returned HTTP {response.status_code}.")

        return response.json()

    def _ensure_configured(self) -> None:
        if not self.site_url:
            raise ConfigurationError("Atlassian site URL is not configured.")
        if not self.config.confluence_email:
            raise ConfigurationError("Atlassian email is not configured.")
        if not self.config.confluence_api_token:
            raise ConfigurationError("Atlassian API token is not configured.")


def derive_atlassian_site_url(confluence_base_url: str) -> str:
    normalized = normalize_confluence_base_url(confluence_base_url)
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    path = parsed.path.rstrip("/")
    if path.endswith("/wiki"):
        path = path[: -len("/wiki")]
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", "")).rstrip("/")


def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip()

    messages: list[str] = []
    if isinstance(payload, dict):
        for key in ("errorMessages", "errors", "message"):
            value = payload.get(key)
            if isinstance(value, list):
                messages.extend(str(item).strip() for item in value if str(item).strip())
            elif isinstance(value, dict):
                messages.extend(f"{field}: {detail}" for field, detail in value.items() if str(detail).strip())
            elif isinstance(value, str) and value.strip():
                messages.append(value.strip())
    return "; ".join(messages)
