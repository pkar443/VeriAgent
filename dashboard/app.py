from __future__ import annotations

import html as html_lib
import json
import os
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components


BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
DEFAULT_WORKSPACE_PATH = os.environ.get("DEFAULT_WORKSPACE_PATH", os.getcwd())
PAGES = ["Overview", "Ask", "Studio", "Setup", "Integration"]

TARGET_OPTIONS = {
    "Confluence Page": "confluence_page",
    "Jira Ticket": "jira_ticket",
    "PRD": "prd",
}
TARGET_LABELS = {value: label for label, value in TARGET_OPTIONS.items()}
GROUNDING_OPTIONS = {"Fast": 1, "Balanced": 3, "Deep": 5}


st.set_page_config(
    page_title="VeriAgent",
    page_icon="V",
    layout="wide",
    initial_sidebar_state="expanded",
)


CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --bg: #07111f;
  --panel: rgba(10, 19, 34, 0.76);
  --panel-strong: rgba(13, 24, 44, 0.92);
  --panel-soft: rgba(255, 255, 255, 0.05);
  --ink: #edf4ff;
  --muted: #97a7c2;
  --line: rgba(148, 163, 184, 0.16);
  --accent: #5eead4;
  --accent-strong: #14b8a6;
  --gold: #fbbf24;
  --blue: #60a5fa;
  --danger: #f87171;
  --ok: #5eead4;
}

.stApp {
  background:
    radial-gradient(circle at top left, rgba(20, 184, 166, 0.28), transparent 26%),
    radial-gradient(circle at 78% 8%, rgba(96, 165, 250, 0.20), transparent 24%),
    radial-gradient(circle at bottom right, rgba(251, 191, 36, 0.16), transparent 22%),
    linear-gradient(180deg, #09101c 0%, #07111f 100%);
  color: var(--ink);
  font-family: 'Manrope', sans-serif;
}

section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(7,17,31,0.96), rgba(9,20,37,0.98));
  border-right: 1px solid var(--line);
}

h1, h2, h3, h4 {
  color: var(--ink);
  font-family: 'Manrope', sans-serif;
  letter-spacing: -0.03em;
}

p, label, [data-testid="stMarkdownContainer"] {
  color: var(--ink);
}

.hero {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(8, 15, 28, 0.94), rgba(9, 28, 45, 0.86)),
    linear-gradient(120deg, rgba(94,234,212,0.10), rgba(96,165,250,0.10));
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 28px;
  padding: 28px 30px;
  box-shadow: 0 20px 70px rgba(2, 8, 23, 0.34);
  margin-bottom: 18px;
}

.hero::after {
  content: "";
  position: absolute;
  right: -20px;
  top: -30px;
  width: 180px;
  height: 180px;
  background: radial-gradient(circle, rgba(94, 234, 212, 0.18), transparent 62%);
}

.eyebrow {
  color: var(--accent);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.hero-title {
  font-size: 2.5rem;
  font-weight: 800;
  line-height: 1.02;
  max-width: 12ch;
  margin: 10px 0 12px 0;
}

.hero-copy {
  color: var(--muted);
  max-width: 58rem;
  line-height: 1.65;
  font-size: 1rem;
}

.glass-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 18px 18px 16px 18px;
  box-shadow: 0 16px 48px rgba(2, 8, 23, 0.28);
  backdrop-filter: blur(14px);
}

.glass-card-tight {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 14px 14px 12px 14px;
  box-shadow: 0 14px 40px rgba(2, 8, 23, 0.22);
  backdrop-filter: blur(12px);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 10px 0 20px 0;
}

.metric-card {
  background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 16px 16px 14px 16px;
}

.metric-label {
  font-size: 0.75rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 800;
}

.metric-value {
  font-size: 1rem;
  font-weight: 700;
  margin-top: 10px;
}

.status-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.status-title {
  font-size: 0.78rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.11em;
  font-weight: 800;
}

.status-pill {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 800;
}

.pill-ok {
  background: rgba(94,234,212,0.12);
  color: var(--ok);
}

.pill-warn {
  background: rgba(251,191,36,0.16);
  color: var(--gold);
}

.status-detail {
  color: var(--ink);
  margin-top: 14px;
  line-height: 1.55;
}

.status-meta {
  color: var(--muted);
  font-size: 0.86rem;
  line-height: 1.55;
  margin-top: 12px;
}

.section-kicker {
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 0.74rem;
  font-weight: 800;
  margin-bottom: 8px;
}

.section-title {
  font-size: 1.4rem;
  font-weight: 800;
  margin-bottom: 4px;
}

.section-copy {
  color: var(--muted);
  line-height: 1.55;
}

.note-card {
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 14px 16px;
  color: var(--muted);
  line-height: 1.6;
}

.source-card {
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 16px;
  margin-bottom: 10px;
}

.source-title {
  font-weight: 800;
  margin-bottom: 6px;
}

.source-meta {
  color: var(--muted);
  font-size: 0.86rem;
  line-height: 1.55;
}

.source-snippet {
  color: #d9e4f4;
  line-height: 1.6;
  margin-top: 12px;
}

.brand {
  padding: 10px 0 4px 0;
}

.brand-name {
  font-size: 1.6rem;
  font-weight: 900;
  letter-spacing: -0.04em;
}

.brand-copy {
  color: var(--muted);
  font-size: 0.93rem;
  line-height: 1.55;
  margin-top: 8px;
}

.nav-note {
  color: var(--muted);
  font-size: 0.84rem;
  margin-top: 12px;
  line-height: 1.5;
}

.draft-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(96,165,250,0.14);
  color: #bfdbfe;
  font-size: 0.72rem;
  font-weight: 800;
  margin-right: 8px;
}

.draft-badge-published {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(94,234,212,0.14);
  color: var(--ok);
  font-size: 0.72rem;
  font-weight: 800;
  margin-right: 8px;
}

.inline-heading {
  font-size: 1.05rem;
  font-weight: 800;
  margin-bottom: 10px;
}

code, pre {
  font-family: 'IBM Plex Mono', monospace !important;
}

div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input {
  background: rgba(255,255,255,0.04);
  color: var(--ink);
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.20);
}

div[data-testid="stRadio"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stSlider"] label {
  color: var(--muted);
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
  background: rgba(255,255,255,0.04);
  border-color: rgba(148, 163, 184, 0.18);
}

button[kind="secondary"],
button[kind="primary"] {
  border-radius: 999px !important;
  font-weight: 800 !important;
}

@media (max-width: 960px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .hero-title {
    font-size: 2rem;
  }
}
</style>
"""


def api_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 240,
) -> tuple[Any | None, str | None]:
    try:
        response = requests.request(
            method=method,
            url=f"{BACKEND_URL}{path}",
            params=params,
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        return None, f"Unable to reach the backend at {BACKEND_URL}: {exc}"

    data: Any = None
    if "application/json" in response.headers.get("content-type", ""):
        try:
            data = response.json()
        except ValueError:
            data = None

    if response.ok:
        return data, None

    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict) and error.get("message"):
            return None, str(error["message"])
    return None, f"Request failed with HTTP {response.status_code}."


def api_get(path: str, *, params: dict[str, Any] | None = None, timeout: int = 240) -> tuple[Any | None, str | None]:
    return api_request("GET", path, params=params, timeout=timeout)


def api_post(path: str, payload: dict[str, Any] | None = None, timeout: int = 240) -> tuple[Any | None, str | None]:
    return api_request("POST", path, payload=payload, timeout=timeout)


def hero(title: str, copy: str, eyebrow: str = "VeriAgent") -> None:
    st.markdown(
        f"""
        <div class="hero">
          <div class="eyebrow">{html_lib.escape(eyebrow)}</div>
          <div class="hero-title">{html_lib.escape(title)}</div>
          <div class="hero-copy">{html_lib.escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_intro(kicker: str, title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div style="margin-bottom:12px;">
          <div class="section-kicker">{html_lib.escape(kicker)}</div>
          <div class="section-title">{html_lib.escape(title)}</div>
          <div class="section-copy">{html_lib.escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_copy_button(text: str, label: str, key: str) -> None:
    key_id = f"copy-{key}".replace(" ", "-")
    components.html(
        f"""
        <div style="margin:0.15rem 0 0.6rem 0;">
          <button
            style="background:linear-gradient(135deg,#14b8a6,#0f766e);color:white;border:none;border-radius:999px;padding:0.62rem 1rem;font-weight:800;cursor:pointer;font-family:Manrope,sans-serif;"
            onclick='navigator.clipboard.writeText({json.dumps(text)}); document.getElementById("{key_id}").innerText = "Copied";'
          >
            {html_lib.escape(label)}
          </button>
          <span id="{key_id}" style="margin-left:0.7rem;color:#97a7c2;font-family:Manrope,sans-serif;"></span>
        </div>
        """,
        height=52,
    )


def render_status_card(label: str, status: dict[str, Any]) -> None:
    ok = bool(status.get("ok"))
    pill_class = "pill-ok" if ok else "pill-warn"
    pill_label = "Ready" if ok else "Attention"
    detail = status.get("detail", "Unknown")
    meta = status.get("metadata") or {}
    lines = []
    if status.get("url"):
        lines.append(f"url: {status['url']}")
    for key, value in meta.items():
        lines.append(f"{key}: {value}")

    st.markdown(
        f"""
        <div class="glass-card-tight">
          <div class="status-head">
            <div class="status-title">{html_lib.escape(label)}</div>
            <div class="status-pill {pill_class}">{pill_label}</div>
          </div>
          <div class="status-detail">{html_lib.escape(detail)}</div>
          <div class="status-meta">{'<br>'.join(html_lib.escape(line) for line in lines)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source_card(source: dict[str, Any]) -> None:
    meta = source.get("metadata") or {}
    meta_parts = [f"Page ID {source.get('page_id', '')}"]
    if meta.get("space_key"):
        meta_parts.append(f"Space {meta['space_key']}")
    if meta.get("last_updated"):
        meta_parts.append(f"Updated {meta['last_updated']}")
    st.markdown(
        f"""
        <div class="source-card">
          <div class="source-title">{html_lib.escape(source.get("title", "Untitled"))}</div>
          <div class="source-meta">{html_lib.escape(' • '.join(meta_parts))}</div>
          <div class="source-snippet">{html_lib.escape(source.get("snippet", ""))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if source.get("url"):
        st.link_button("Open source", source["url"], use_container_width=False)


def render_draft_card(draft: dict[str, Any]) -> None:
    badge_class = "draft-badge-published" if draft.get("status") == "published" else "draft-badge"
    badge_label = draft.get("status", "draft").title()
    target = TARGET_LABELS.get(draft.get("target", ""), draft.get("target", "Draft"))
    source = draft.get("source", "dashboard")
    st.markdown(
        f"""
        <div class="glass-card-tight">
          <div style="margin-bottom:8px;">
            <span class="{badge_class}">{html_lib.escape(badge_label)}</span>
            <span class="draft-badge">{html_lib.escape(target)}</span>
          </div>
          <div style="font-weight:800;font-size:1.02rem;margin-bottom:4px;">{html_lib.escape(draft.get("title", "Untitled Draft"))}</div>
          <div class="status-meta">Source {html_lib.escape(source)} • Updated {html_lib.escape(str(draft.get("updated_at", "")))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_preview(preview_html: str) -> None:
    if not preview_html.strip():
        st.info("Generate or refresh the formatted draft to see the polished preview here.")
        return
    components.html(preview_html, height=760, scrolling=True)


def navigate_to(page: str) -> None:
    st.session_state["_pending_page_nav"] = page
    st.rerun()


def studio_queue_update(payload: dict[str, Any], page: str | None = None) -> None:
    st.session_state["_pending_studio_update"] = payload
    if page:
        st.session_state["_pending_page_nav"] = page
    st.rerun()


def apply_pending_studio_update() -> None:
    pending = st.session_state.pop("_pending_studio_update", None)
    if not pending:
        return
    for key, value in pending.items():
        st.session_state[key] = value


def current_health() -> dict[str, Any] | None:
    data, error = api_get("/api/health", timeout=30)
    if error:
        st.error(error)
        return None
    return data


def current_config() -> dict[str, Any] | None:
    data, error = api_get("/api/config", timeout=30)
    if error:
        st.error(error)
        return None
    return data


def current_integration_info() -> dict[str, Any] | None:
    data, error = api_get("/api/integration/info", timeout=30)
    if error:
        st.error(error)
        return None
    return data


def fetch_recent_drafts(limit: int = 12) -> list[dict[str, Any]]:
    data, error = api_get("/api/studio/drafts", params={"limit": limit}, timeout=60)
    if error:
        st.warning(error)
        return []
    return data or []


def get_page_preview(page_id: str) -> tuple[dict[str, Any] | None, str | None]:
    cache = st.session_state.setdefault("page_preview_cache", {})
    if page_id in cache:
        return cache[page_id], None
    data, error = api_get(f"/api/confluence/pages/{page_id}")
    if error:
        return None, error
    cache[page_id] = data
    return data, None


def sync_active_ask_job() -> None:
    job_id = st.session_state.get("ask_job_id")
    if not job_id:
        return

    data, error = api_get(f"/api/qa/jobs/{job_id}", timeout=30)
    if error:
        st.session_state["ask_job_error"] = error
        return

    st.session_state["ask_job_state"] = data
    st.session_state["ask_job_error"] = None
    status = data.get("status")
    if status == "completed" and data.get("result"):
        st.session_state["ask_result"] = data["result"]
        st.session_state["page_preview_cache"] = {}
        st.session_state["ask_job_id"] = None
    elif status == "failed":
        st.session_state["ask_job_id"] = None


def seed_studio_from_ask(result: dict[str, Any]) -> None:
    sections = result.get("sections", {})
    lines = [f"# {result.get('query', 'VeriAgent Draft')}", ""]
    if sections.get("answer"):
        lines.extend(["## Answer", sections["answer"], ""])
    if sections.get("assumptions"):
        lines.extend(["## Assumptions", sections["assumptions"], ""])
    if sections.get("test_scenarios"):
        lines.extend(["## Test Scenarios", sections["test_scenarios"], ""])
    if sections.get("steps"):
        lines.extend(["## Steps", sections["steps"], ""])
    if sections.get("expected_results"):
        lines.extend(["## Expected Results", sections["expected_results"], ""])
    if sections.get("selenium_code") and sections["selenium_code"] != "Not requested.":
        lines.extend(["## Selenium Starter Code", "```python", sections["selenium_code"], "```", ""])
    if result.get("sources"):
        lines.append("## Sources")
        for source in result["sources"]:
            title = source.get("title", "Untitled")
            url = source.get("url", "")
            lines.append(f"- [{title}]({url})" if url else f"- {title}")
        lines.append("")

    studio_queue_update(
        {
            "studio_draft_id": "",
            "studio_title": f"QA Draft - {result.get('query', 'VeriAgent')[:68].strip()}",
            "studio_target": "confluence_page",
            "studio_target_picker": "Confluence Page",
            "studio_raw_input": sections.get("raw_output", "") or sections.get("answer", "") or result.get("query", ""),
            "studio_markdown": "\n".join(lines).strip(),
            "studio_preview_html": "",
            "studio_assumptions": sections.get("assumptions", ""),
            "studio_source": "dashboard-ask",
            "studio_publish_result": None,
        },
        page="Studio",
    )


def load_draft_into_studio(draft: dict[str, Any]) -> None:
    studio_queue_update(
        {
            "studio_draft_id": draft.get("draft_id", ""),
            "studio_title": draft.get("title", ""),
            "studio_target": draft.get("target", "confluence_page"),
            "studio_target_picker": TARGET_LABELS.get(draft.get("target", "confluence_page"), "Confluence Page"),
            "studio_raw_input": draft.get("raw_input", ""),
            "studio_markdown": draft.get("structured_markdown", ""),
            "studio_preview_html": draft.get("preview_html", ""),
            "studio_assumptions": draft.get("metadata", {}).get("assumptions", ""),
            "studio_source": draft.get("source", "dashboard"),
            "studio_publish_result": None,
        },
        page="Studio",
    )


def parse_label_csv(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def home_page() -> None:
    hero(
        "A sharper QA hub for docs, drafts, and publish flows",
        "VeriAgent v2 turns the dashboard into a real workbench: grounded Q&A, Gemma-shaped document drafts, Codex handoff, and direct publishing into Confluence or Jira.",
        eyebrow="Overview",
    )

    health = current_health()
    if health is None:
        return

    recent_drafts = fetch_recent_drafts(limit=6)
    st.markdown(
        f"""
        <div class="metric-grid">
          <div class="metric-card">
            <div class="metric-label">Model</div>
            <div class="metric-value">{html_lib.escape(str(health.get('ollama', {}).get('metadata', {}).get('model_name', 'gemma4:e2b')))}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Confluence</div>
            <div class="metric-value">{'Connected' if health.get('confluence', {}).get('ok') else 'Needs setup'}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Active Drafts</div>
            <div class="metric-value">{len(recent_drafts)}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">MCP URL</div>
            <div class="metric-value">{html_lib.escape(health.get('mcp', {}).get('url', ''))}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_cols = st.columns(4)
    with action_cols[0]:
        if st.button("Open Ask", use_container_width=True):
            navigate_to("Ask")
    with action_cols[1]:
        if st.button("Open Studio", use_container_width=True):
            navigate_to("Studio")
    with action_cols[2]:
        if st.button("Setup Sources", use_container_width=True):
            navigate_to("Setup")
    with action_cols[3]:
        if st.button("MCP Config", use_container_width=True):
            navigate_to("Integration")

    status_cols = st.columns(4)
    for column, label, key in zip(status_cols, ["Backend", "Confluence", "Ollama", "MCP"], ["backend", "confluence", "ollama", "mcp"]):
        with column:
            render_status_card(label, health.get(key, {}))

    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        section_intro("Recent Drafts", "Work waiting for review or publish", "Codex and the dashboard now share a single draft queue. Use the Studio to refine, preview, and publish.")
        if not recent_drafts:
            st.markdown('<div class="note-card">No drafts yet. Start in Studio or send a draft from Codex with <code>save_dashboard_draft</code>.</div>', unsafe_allow_html=True)
        for draft in recent_drafts[:4]:
            render_draft_card(draft)
            if st.button("Open in Studio", key=f"open-home-draft-{draft['draft_id']}", use_container_width=True):
                load_draft_into_studio(draft)

    with right:
        section_intro("How v2 flows", "One hub for AI drafting and human approval", "Use Ask for grounded answers, Studio for document shaping, and Integration for Codex handoff. Confluence and Jira publishing now sit behind the same approval surface.")
        st.markdown(
            """
            <div class="note-card">
              <strong>Dashboard path</strong><br>
              Paste rough notes, click Preview, let Gemma turn them into a polished artifact, then edit and publish.<br><br>
              <strong>Codex path</strong><br>
              Let Codex draft from repo context, save the draft into VeriAgent, review it in Studio, then publish without re-copying content.
            </div>
            """,
            unsafe_allow_html=True,
        )
        config = current_config()
        if config:
            st.caption(f"Workspace .env: {config.get('env_file_path', '.env')}")
            st.caption(f"Token saved: {'Yes' if config.get('confluence_api_token_set') else 'No'}")


def ask_page() -> None:
    hero(
        "Ground a question, then turn the answer into a draft",
        "Ask stays focused on retrieval-backed QA. When the answer is useful, send it straight into Studio and turn it into a Confluence page, PRD, or Jira-ready artifact.",
        eyebrow="Ask",
    )

    with st.container(border=True):
        col_query, col_mode = st.columns([1.4, 0.6], gap="large")
        with col_query:
            query = st.text_area(
                "Question",
                value=st.session_state.get("ask_query", ""),
                key="ask_query",
                height=140,
                placeholder="What do you want to verify?",
            )
        with col_mode:
            grounding_label = st.radio("Grounding", list(GROUNDING_OPTIONS.keys()), horizontal=True, key="ask_grounding")
            generate_selenium = st.toggle("Include Selenium starter code", value=st.session_state.get("ask_selenium", False), key="ask_selenium")
            st.markdown('<div class="note-card">Balanced is best for most documentation questions. Deep is useful when the page is broad or noisy.</div>', unsafe_allow_html=True)

        action_cols = st.columns([0.6, 0.2, 0.2])
        run_ask = action_cols[0].button("Run grounded QA", type="primary", use_container_width=True)
        refresh = action_cols[1].button("Refresh", use_container_width=True)
        clear = action_cols[2].button("Clear", use_container_width=True)

        if run_ask:
            data, error = api_post(
                "/api/qa/jobs",
                {
                    "query": query,
                    "top_k": GROUNDING_OPTIONS[grounding_label],
                    "generate_selenium": generate_selenium,
                },
            )
            if error:
                st.error(error)
            else:
                st.session_state["ask_job_id"] = data.get("job_id")
                st.session_state["ask_job_state"] = data
                st.session_state["ask_job_error"] = None
                st.session_state.pop("ask_result", None)
                st.success("Gemma job started in the backend.")

        if refresh:
            sync_active_ask_job()
            st.rerun()

        if clear:
            for key in ["ask_job_id", "ask_job_state", "ask_job_error", "ask_result"]:
                st.session_state.pop(key, None)
            st.rerun()

    active_job = st.session_state.get("ask_job_state")
    if active_job and active_job.get("status") in {"queued", "running"}:
        st.info(f"Background QA job is {active_job.get('status')}. You can switch pages and come back.")
    if st.session_state.get("ask_job_error"):
        st.warning(st.session_state["ask_job_error"])

    result = st.session_state.get("ask_result")
    if not result:
        return

    sections = result.get("sections", {})
    summary_cols = st.columns(4)
    with summary_cols[0]:
        st.metric("Sources", len(result.get("sources", [])))
    with summary_cols[1]:
        st.metric("Chunks", len(result.get("retrieved_chunks", [])))
    with summary_cols[2]:
        st.metric("Mode", "Sources only" if result.get("generation_error") else "QA")
    with summary_cols[3]:
        if st.button("Send to Studio", use_container_width=True):
            seed_studio_from_ask(result)

    left, right = st.columns([1.12, 0.88], gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<div class="inline-heading">Answer</div>', unsafe_allow_html=True)
            st.write(sections.get("answer") or "No answer returned.")
            if sections.get("assumptions"):
                st.markdown('<div class="inline-heading" style="margin-top:18px;">Assumptions</div>', unsafe_allow_html=True)
                st.write(sections.get("assumptions"))

        qa_tabs = st.tabs(["QA Assets", "Selenium", "Raw"])
        with qa_tabs[0]:
            st.write("### Test Scenarios")
            st.write(sections.get("test_scenarios") or "No scenarios returned.")
            st.write("### Steps")
            st.write(sections.get("steps") or "No steps returned.")
            st.write("### Expected Results")
            st.write(sections.get("expected_results") or "No expected results returned.")
        with qa_tabs[1]:
            st.code(sections.get("selenium_code") or "Not requested.", language="python")
        with qa_tabs[2]:
            st.code(sections.get("raw_output") or "", language="markdown")

    with right:
        with st.container(border=True):
            st.markdown('<div class="inline-heading">Matched Sources</div>', unsafe_allow_html=True)
            sources = result.get("sources", [])
            if not sources:
                st.info("No Confluence pages matched this question.")
            else:
                source_lookup = {source["page_id"]: source for source in sources}
                source_ids = list(source_lookup.keys())
                selected = st.radio(
                    "Pages",
                    source_ids,
                    horizontal=False,
                    key="ask_selected_source_page",
                    format_func=lambda page_id: source_lookup[page_id]["title"],
                )
                render_source_card(source_lookup[selected])
                preview, error = get_page_preview(selected)
                if error:
                    st.warning(error)
                elif preview:
                    st.text_area("Page preview", preview.get("content", ""), height=220, disabled=True, key=f"ask-preview-{selected}")
                chunks = [item for item in result.get("retrieved_chunks", []) if item.get("page_id") == selected]
                if chunks:
                    st.markdown("**Grounding excerpts**")
                    for chunk in chunks[:3]:
                        st.markdown(f"- {chunk.get('snippet') or chunk.get('content', '')[:180]}")


def studio_page() -> None:
    section_intro("Studio", "Shape raw notes into polished publishable artifacts", "Preview drives the formatting flow: paste rough text or open a Codex draft, let Gemma structure it, then refine and publish.")

    st.session_state.setdefault("studio_draft_id", "")
    st.session_state.setdefault("studio_title", "")
    st.session_state.setdefault("studio_target", "confluence_page")
    st.session_state.setdefault("studio_target_picker", TARGET_LABELS[st.session_state["studio_target"]])
    st.session_state.setdefault("studio_raw_input", "")
    st.session_state.setdefault("studio_markdown", "")
    st.session_state.setdefault("studio_preview_html", "")
    st.session_state.setdefault("studio_assumptions", "")
    st.session_state.setdefault("studio_source", "dashboard")
    st.session_state.setdefault("studio_space", "")
    st.session_state.setdefault("studio_parent_page_id", "")
    st.session_state.setdefault("studio_jira_project", "")
    st.session_state.setdefault("studio_jira_issue_type", "Task")
    st.session_state.setdefault("studio_jira_labels", "")
    st.session_state.setdefault("studio_publish_result", None)

    left, right = st.columns([0.34, 0.66], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<div class="inline-heading">Draft Inbox</div>', unsafe_allow_html=True)
            inbox_cols = st.columns([0.7, 0.3])
            with inbox_cols[0]:
                st.caption("Saved by Codex or the dashboard")
            refresh_drafts = inbox_cols[1].button("Refresh", use_container_width=True, key="studio-refresh-drafts")

            drafts = fetch_recent_drafts(limit=12)
            if refresh_drafts:
                drafts = fetch_recent_drafts(limit=12)

            if not drafts:
                st.markdown('<div class="note-card">No drafts yet. Use the editor on the right, or from Codex call <code>save_dashboard_draft</code>.</div>', unsafe_allow_html=True)

            for draft in drafts[:8]:
                render_draft_card(draft)
                if st.button("Open draft", key=f"studio-open-{draft['draft_id']}", use_container_width=True):
                    load_draft_into_studio(draft)

        latest_ask = st.session_state.get("ask_result")
        with st.container(border=True):
            st.markdown('<div class="inline-heading">Quick Intake</div>', unsafe_allow_html=True)
            st.markdown('<div class="note-card">Use the latest grounded answer, paste rough notes, or open a Codex draft. Studio keeps the human in the loop before anything is published.</div>', unsafe_allow_html=True)
            if latest_ask and st.button("Use latest Ask result", use_container_width=True, key="studio-use-ask"):
                seed_studio_from_ask(latest_ask)
            if st.button("Start fresh draft", use_container_width=True, key="studio-start-fresh"):
                studio_queue_update(
                    {
                        "studio_draft_id": "",
                        "studio_title": "",
                        "studio_target": "confluence_page",
                        "studio_target_picker": "Confluence Page",
                        "studio_raw_input": "",
                        "studio_markdown": "",
                        "studio_preview_html": "",
                        "studio_assumptions": "",
                        "studio_source": "dashboard",
                        "studio_publish_result": None,
                    },
                    page="Studio",
                )

    with right:
        hero(
            "Draft, preview, refine, publish",
            "The Studio is built for rough notes first. Preview uses Gemma to structure raw text into a proper artifact, then shows the styled output you are about to publish.",
            eyebrow="Document Studio",
        )
        target_choice = st.radio(
            "Artifact",
            list(TARGET_OPTIONS.keys()),
            horizontal=True,
            index=list(TARGET_OPTIONS.values()).index(st.session_state.get("studio_target", "confluence_page")),
            key="studio_target_picker",
        )
        target_value = TARGET_OPTIONS[target_choice]
        if target_value != st.session_state.get("studio_target"):
            studio_queue_update({"studio_target": target_value, "studio_target_picker": target_choice}, page="Studio")

        editor_cols = st.columns([0.56, 0.44], gap="large")
        with editor_cols[0]:
            with st.container(border=True):
                title = st.text_input("Title", key="studio_title")
                raw_input = st.text_area(
                    "Raw input",
                    key="studio_raw_input",
                    height=220,
                    placeholder="Paste rough notes, ticket details, repo summaries, or copied content here.",
                )
                markdown_body = st.text_area(
                    "Formatted draft",
                    key="studio_markdown",
                    height=280,
                    placeholder="Gemma will place the structured Markdown here.",
                )

                tool_cols = st.columns(4)
                preview_clicked = tool_cols[0].button("Preview", type="primary", use_container_width=True)
                save_clicked = tool_cols[1].button("Save draft", use_container_width=True)
                beautify_clicked = tool_cols[2].button("Refine", use_container_width=True)
                copy_clicked = tool_cols[3].button("Copy draft", use_container_width=True)

                if copy_clicked and markdown_body.strip():
                    render_copy_button(markdown_body, "Copy formatted draft", "studio-markdown")

                if preview_clicked or beautify_clicked:
                    if raw_input.strip():
                        data, error = api_post(
                            "/api/studio/transform",
                            {
                                "target": st.session_state["studio_target"],
                                "raw_input": raw_input,
                                "title": title,
                                "existing_markdown": markdown_body if beautify_clicked else "",
                                "context_notes": f"Draft source: {st.session_state.get('studio_source', 'dashboard')}",
                            },
                            timeout=300,
                        )
                        if error:
                            st.error(error)
                        else:
                            studio_queue_update(
                                {
                                    "studio_title": data.get("title", title),
                                    "studio_markdown": data.get("structured_markdown", ""),
                                    "studio_preview_html": data.get("preview_html", ""),
                                    "studio_assumptions": data.get("assumptions", ""),
                                },
                                page="Studio",
                            )
                    elif markdown_body.strip():
                        data, error = api_post(
                            "/api/studio/preview",
                            {
                                "target": st.session_state["studio_target"],
                                "title": title,
                                "structured_markdown": markdown_body,
                            },
                        )
                        if error:
                            st.error(error)
                        else:
                            studio_queue_update({"studio_preview_html": data.get("preview_html", "")}, page="Studio")
                    else:
                        st.warning("Add raw input or a formatted draft before previewing.")

                if save_clicked:
                    data, error = api_post(
                        "/api/studio/drafts",
                        {
                            "draft_id": st.session_state.get("studio_draft_id") or None,
                            "title": title,
                            "target": st.session_state["studio_target"],
                            "raw_input": raw_input,
                            "structured_markdown": markdown_body,
                            "preview_html": st.session_state.get("studio_preview_html", ""),
                            "source": st.session_state.get("studio_source", "dashboard"),
                            "metadata": {"assumptions": st.session_state.get("studio_assumptions", "")},
                        },
                    )
                    if error:
                        st.error(error)
                    else:
                        studio_queue_update(
                            {
                                "studio_draft_id": data.get("draft_id", ""),
                                "studio_preview_html": data.get("preview_html", st.session_state.get("studio_preview_html", "")),
                            },
                            page="Studio",
                        )

                if st.session_state.get("studio_assumptions"):
                    st.markdown("**Assumptions**")
                    st.write(st.session_state["studio_assumptions"])
                st.caption(f"Draft source: {st.session_state.get('studio_source', 'dashboard')}")

        with editor_cols[1]:
            with st.container(border=True):
                st.markdown('<div class="inline-heading">Publish target</div>', unsafe_allow_html=True)
                st.text_input("Draft title snapshot", value=st.session_state.get("studio_title", ""), disabled=True)
                if st.session_state["studio_target"] in {"confluence_page", "prd"}:
                    st.text_input("Confluence space", key="studio_space", placeholder="SD")
                    st.text_input("Parent page ID", key="studio_parent_page_id", placeholder="Optional")
                    publish_caption = "Publishes to Confluence as a new page."
                else:
                    st.text_input("Jira project key", key="studio_jira_project", placeholder="SD")
                    st.selectbox("Issue type", ["Task", "Story", "Bug", "Epic"], key="studio_jira_issue_type")
                    st.text_input("Labels", key="studio_jira_labels", placeholder="qa, veriagent")
                    publish_caption = "Publishes to Jira as a new issue."
                st.caption(publish_caption)
                publish_clicked = st.button("Publish now", use_container_width=True)

                if publish_clicked:
                    payload = {
                        "draft_id": st.session_state.get("studio_draft_id") or None,
                        "target": st.session_state["studio_target"],
                        "title": st.session_state.get("studio_title", ""),
                        "structured_markdown": st.session_state.get("studio_markdown", ""),
                        "confluence_space": st.session_state.get("studio_space", ""),
                        "parent_page_id": st.session_state.get("studio_parent_page_id") or None,
                        "jira_project_key": st.session_state.get("studio_jira_project", ""),
                        "jira_issue_type": st.session_state.get("studio_jira_issue_type", "Task"),
                        "jira_labels": parse_label_csv(st.session_state.get("studio_jira_labels", "")),
                    }
                    data, error = api_post("/api/studio/publish", payload, timeout=120)
                    if error:
                        st.error(error)
                    else:
                        st.session_state["studio_publish_result"] = data
                        st.success(f"Published to {data.get('platform', 'destination')}.")

                result = st.session_state.get("studio_publish_result")
                if result:
                    st.metric("Published ID", result.get("external_id", ""))
                    st.metric("Platform", result.get("platform", ""))
                    if result.get("url"):
                        st.link_button("Open published item", result["url"], use_container_width=True)

            with st.container(border=True):
                st.markdown('<div class="inline-heading">Preview</div>', unsafe_allow_html=True)
                render_preview(st.session_state.get("studio_preview_html", ""))


def setup_page() -> None:
    hero(
        "Connect sources and tune the local runtime",
        "Setup is intentionally compact now: save the Atlassian and Ollama settings once, then let the rest of the product focus on drafting and publish flows.",
        eyebrow="Setup",
    )
    config = current_config()
    if config is None:
        return

    with st.container(border=True):
        left, right = st.columns([1.0, 0.72], gap="large")
        with left:
            confluence_base_url = st.text_input("Confluence URL", value=config.get("confluence_base_url", ""), placeholder="https://your-domain.atlassian.net/wiki")
            confluence_email = st.text_input("Atlassian email", value=config.get("confluence_email", ""))
            confluence_api_token = st.text_input("API token", value="", type="password", help="Leave blank to keep the current token.")
        with right:
            ollama_base_url = st.text_input("Ollama base URL", value=config.get("ollama_base_url", "http://ollama:11434"))
            ollama_model = st.text_input("Model name", value=config.get("ollama_model", "gemma4:e2b"))
            st.markdown(
                f"""
                <div class="note-card">
                  .env path<br>
                  <strong>{html_lib.escape(config.get('env_file_path', '.env'))}</strong><br><br>
                  Token saved<br>
                  <strong>{'Yes' if config.get('confluence_api_token_set') else 'No'}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

        action_cols = st.columns(3)
        save = action_cols[0].button("Save configuration", type="primary", use_container_width=True)
        test_confluence = action_cols[1].button("Test Confluence", use_container_width=True)
        test_ollama = action_cols[2].button("Test Ollama", use_container_width=True)

        if save:
            data, error = api_post(
                "/api/config",
                {
                    "confluence_base_url": confluence_base_url,
                    "confluence_email": confluence_email,
                    "confluence_api_token": confluence_api_token,
                    "ollama_base_url": ollama_base_url,
                    "ollama_model": ollama_model,
                },
                timeout=60,
            )
            if error:
                st.error(error)
            else:
                st.success(f"Saved. Updated .env at {data.get('env_file_path', '.env')}.")

        if test_confluence:
            data, error = api_post("/api/confluence/test", timeout=60)
            if error:
                st.error(error)
            else:
                st.success(data.get("detail", "Confluence looks good."))
                if data.get("metadata"):
                    st.json(data["metadata"])

        if test_ollama:
            data, error = api_post("/api/ollama/test", timeout=60)
            if error:
                st.error(error)
            else:
                if data.get("ok"):
                    st.success(data.get("detail", "Ollama looks good."))
                else:
                    st.warning(data.get("detail", "Ollama is reachable but not fully ready."))
                if data.get("metadata"):
                    st.json(data["metadata"])


def integration_page() -> None:
    hero(
        "Connect Codex and keep drafts flowing back into the dashboard",
        "Integration now matters more than simple config generation. Codex can retrieve grounded Confluence context, save drafts into Studio, and publish through the same backend.",
        eyebrow="Integration",
    )
    info = current_integration_info()
    if info is None:
        return

    running_in_docker = str(info.get("running_in_docker", "false")).lower() == "true"
    host_workspace_path = info.get("host_workspace_path", "").strip()
    display_workspace_path = host_workspace_path or info.get("workspace_root", DEFAULT_WORKSPACE_PATH)

    with st.container(border=True):
        workspace_path = st.text_input("Workspace path", value=st.session_state.get("workspace_path", display_workspace_path))
        target_label = st.radio("Config target", ["Both", "VS Code", "Codex"], horizontal=True)
        target = {"Both": "both", "VS Code": "vscode", "Codex": "codex"}[target_label]

        action_cols = st.columns(3)
        generate = action_cols[0].button("Generate config", use_container_width=True)
        enable = action_cols[1].button("Write config", type="primary", use_container_width=True)
        open_location = action_cols[2].button("Open workspace", use_container_width=True)

        if generate:
            data, error = api_post("/api/integration/config", {"workspace_path": workspace_path, "target": target}, timeout=60)
            if error:
                st.error(error)
            else:
                st.session_state["mcp_config"] = data

        if enable:
            data, error = api_post("/api/integration/enable", {"workspace_path": workspace_path, "target": target}, timeout=60)
            if error:
                st.error(error)
            else:
                st.session_state["mcp_config"] = data
                st.success("Workspace config written.")

        if open_location:
            if running_in_docker:
                render_copy_button(display_workspace_path, "Copy workspace path", "integration-workspace")
                st.info(f"Open this folder on your host machine: {display_workspace_path}")
            else:
                _, error = api_post("/api/integration/open-location", {"path": workspace_path}, timeout=30)
                if error:
                    st.warning(error)
                else:
                    st.success("Opened the workspace path.")

    st.markdown(
        """
        <div class="note-card">
          <strong>Codex v2 flow</strong><br>
          1. Use retrieval-first tools for grounded context.<br>
          2. Draft the content in Codex or ask Codex to save it with <code>save_dashboard_draft</code>.<br>
          3. Open the draft in Studio, preview, edit, and publish to Confluence or Jira.
        </div>
        """,
        unsafe_allow_html=True,
    )

    config = st.session_state.get("mcp_config")
    if not config:
        return

    for instruction in config.get("instructions", []):
        st.caption(instruction)
    if config.get("written_files"):
        st.success("Written files: " + ", ".join(config["written_files"]))

    col_vscode, col_codex = st.columns(2, gap="large")
    vscode_config = config.get("vscode")
    codex_config = config.get("codex")
    with col_vscode:
        if vscode_config:
            with st.container(border=True):
                st.markdown("**.vscode/mcp.json**")
                render_copy_button(vscode_config["content"], "Copy VS Code config", "vscode-config")
                st.code(vscode_config["content"], language="json")
    with col_codex:
        if codex_config:
            with st.container(border=True):
                st.markdown("**.codex/config.toml**")
                render_copy_button(codex_config["content"], "Copy Codex config", "codex-config")
                st.code(codex_config["content"], language="toml")


def sidebar() -> None:
    st.sidebar.markdown(
        """
        <div class="brand">
          <div class="brand-name">VeriAgent</div>
          <div class="brand-copy">
            A local-first quality engineering studio for grounded answers, premium drafts, and human-approved publishing.
          </div>
          <div class="nav-note">
            Confluence and Jira publishing now live behind the same shared backend and draft queue.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.radio("Navigate", PAGES, key="page_nav")
    active_job = st.session_state.get("ask_job_state")
    if active_job and active_job.get("status") in {"queued", "running"}:
        st.sidebar.info(f"Gemma job {active_job.get('status')}: {active_job.get('query', '')[:38]}")
    st.sidebar.caption(f"Backend: {BACKEND_URL}")


def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    sync_active_ask_job()
    apply_pending_studio_update()

    pending_page = st.session_state.pop("_pending_page_nav", None)
    if pending_page is not None:
        st.session_state["page_nav"] = pending_page
    if "page_nav" not in st.session_state:
        st.session_state["page_nav"] = "Overview"

    sidebar()

    page = st.session_state["page_nav"]
    if page == "Overview":
        home_page()
    elif page == "Ask":
        ask_page()
    elif page == "Studio":
        studio_page()
    elif page == "Setup":
        setup_page()
    elif page == "Integration":
        integration_page()
    else:
        home_page()


if __name__ == "__main__":
    main()
