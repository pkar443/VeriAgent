from __future__ import annotations

import html
import json
import os
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components


BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
DEFAULT_WORKSPACE_PATH = os.environ.get("DEFAULT_WORKSPACE_PATH", os.getcwd())
PAGES = ["Home", "Setup", "Ask", "VS Code Integration"]


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
  --bg: #f7f5ef;
  --panel: rgba(255, 255, 255, 0.82);
  --panel-strong: rgba(255, 255, 255, 0.92);
  --ink: #15222b;
  --muted: #53626f;
  --line: rgba(21, 34, 43, 0.10);
  --accent: #0f766e;
  --accent-soft: rgba(15, 118, 110, 0.12);
  --warn: #b45309;
  --danger: #b91c1c;
  --ok: #1d4ed8;
}

.stApp {
  background:
    radial-gradient(circle at top left, rgba(15, 118, 110, 0.18), transparent 22%),
    radial-gradient(circle at top right, rgba(234, 179, 8, 0.18), transparent 20%),
    linear-gradient(180deg, #fbfaf6 0%, var(--bg) 100%);
  color: var(--ink);
  font-family: 'Manrope', sans-serif;
}

section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(247,245,239,0.96));
  border-right: 1px solid var(--line);
}

h1, h2, h3 {
  color: var(--ink);
  font-family: 'Manrope', sans-serif;
  letter-spacing: -0.02em;
}

.hero {
  background: linear-gradient(135deg, rgba(255,255,255,0.94), rgba(223, 247, 239, 0.88));
  border: 1px solid rgba(15, 118, 110, 0.14);
  border-radius: 22px;
  padding: 1.5rem;
  box-shadow: 0 18px 45px rgba(21, 34, 43, 0.08);
  margin-bottom: 1rem;
}

.hero-eyebrow {
  color: var(--accent);
  font-size: 0.85rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero-title {
  font-size: 2.1rem;
  font-weight: 800;
  margin: 0.2rem 0 0.6rem 0;
}

.hero-copy {
  color: var(--muted);
  max-width: 52rem;
  line-height: 1.6;
}

.status-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 1rem;
  min-height: 152px;
  backdrop-filter: blur(8px);
}

.status-label {
  color: var(--muted);
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
}

.status-pill {
  display: inline-block;
  margin-top: 0.7rem;
  padding: 0.28rem 0.6rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 800;
}

.status-ok {
  background: rgba(29, 78, 216, 0.10);
  color: var(--ok);
}

.status-warn {
  background: rgba(180, 83, 9, 0.12);
  color: var(--warn);
}

.status-detail {
  margin-top: 0.7rem;
  color: var(--ink);
  line-height: 1.5;
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
  margin: 1rem 0 0.2rem 0;
}

.metric-chip {
  padding: 1rem;
  border-radius: 16px;
  background: rgba(255,255,255,0.66);
  border: 1px solid var(--line);
}

.metric-kicker {
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.09em;
  font-size: 0.75rem;
  font-weight: 800;
}

.metric-value {
  font-size: 1rem;
  font-weight: 700;
  margin-top: 0.35rem;
}

.block-note {
  background: var(--panel-strong);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1rem 1.1rem;
  color: var(--muted);
  line-height: 1.55;
}

.source-card {
  background: rgba(255,255,255,0.84);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1rem;
  margin-bottom: 0.8rem;
}

.source-title {
  font-weight: 800;
  margin-bottom: 0.2rem;
}

.source-meta {
  color: var(--muted);
  font-size: 0.88rem;
  margin-bottom: 0.5rem;
}

.source-snippet {
  color: var(--ink);
  line-height: 1.55;
}

.brand-lockup {
  padding: 0.85rem 0 0.35rem 0;
}

.brand-name {
  font-weight: 900;
  font-size: 1.35rem;
  letter-spacing: -0.03em;
}

.brand-copy {
  color: var(--muted);
  font-size: 0.92rem;
  line-height: 1.5;
}

code, pre {
  font-family: 'IBM Plex Mono', monospace !important;
}

@media (max-width: 960px) {
  .metric-strip {
    grid-template-columns: 1fr;
  }

  .hero-title {
    font-size: 1.55rem;
  }
}
</style>
"""


def api_request(method: str, path: str, *, params: dict[str, Any] | None = None, payload: dict[str, Any] | None = None) -> tuple[Any | None, str | None]:
    try:
        response = requests.request(
            method=method,
            url=f"{BACKEND_URL}{path}",
            params=params,
            json=payload,
            timeout=240,
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


def api_get(path: str, *, params: dict[str, Any] | None = None) -> tuple[Any | None, str | None]:
    return api_request("GET", path, params=params)


def api_post(path: str, payload: dict[str, Any] | None = None) -> tuple[Any | None, str | None]:
    return api_request("POST", path, payload=payload)


def render_copy_button(text: str, label: str, key: str) -> None:
    escaped_label = html.escape(label)
    key_id = f"copy-{key}".replace(" ", "-")
    js_text = json.dumps(text)
    components.html(
        f"""
        <div style="margin:0.25rem 0 0.75rem 0;">
          <button
            style="background:#0f766e;color:white;border:none;border-radius:999px;padding:0.55rem 0.95rem;font-weight:700;cursor:pointer;"
            onclick='navigator.clipboard.writeText({js_text}); document.getElementById("{key_id}").innerText = "Copied to clipboard";'
          >
            {escaped_label}
          </button>
          <span id="{key_id}" style="margin-left:0.75rem;color:#53626f;font-family:Manrope,sans-serif;"></span>
        </div>
        """,
        height=52,
    )


def hero(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-eyebrow">VeriAgent</div>
          <div class="hero-title">{html.escape(title)}</div>
          <div class="hero-copy">{html.escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_card(label: str, status: dict[str, Any]) -> None:
    ok = bool(status.get("ok"))
    pill_class = "status-ok" if ok else "status-warn"
    pill_text = "Ready" if ok else "Needs attention"
    detail = html.escape(status.get("detail", "Unknown"))
    url = status.get("url")
    meta = status.get("metadata") or {}
    meta_lines = [f"{key}: {value}" for key, value in meta.items()]
    if url:
        meta_lines.append(f"url: {url}")
    meta_html = "<br>".join(html.escape(line) for line in meta_lines)
    st.markdown(
        f"""
        <div class="status-card">
          <div class="status-label">{html.escape(label)}</div>
          <div class="status-pill {pill_class}">{pill_text}</div>
          <div class="status-detail">{detail}</div>
          <div class="source-meta" style="margin-top:0.7rem;">{meta_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def source_card(source: dict[str, Any]) -> None:
    meta = source.get("metadata") or {}
    meta_parts = [f"Page ID: {source.get('page_id', '')}"]
    if meta.get("space_key"):
        meta_parts.append(f"Space: {meta['space_key']}")
    if meta.get("last_updated"):
        meta_parts.append(f"Updated: {meta['last_updated']}")

    st.markdown(
        f"""
        <div class="source-card">
          <div class="source-title">{html.escape(source.get("title", "Untitled"))}</div>
          <div class="source-meta">{html.escape(" | ".join(meta_parts))}</div>
          <div class="source-snippet">{html.escape(source.get("snippet", ""))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if source.get("url"):
        st.link_button(
            "Open in Confluence",
            source["url"],
            key=f"source-link-{source.get('page_id', 'unknown')}",
            use_container_width=False,
        )


def get_page_preview(page_id: str) -> tuple[dict[str, Any] | None, str | None]:
    cache = st.session_state.setdefault("page_preview_cache", {})
    if page_id in cache:
        return cache[page_id], None

    data, error = api_get(f"/api/confluence/pages/{page_id}")
    if error:
        return None, error
    cache[page_id] = data
    return data, None


def render_matched_sources(result: dict[str, Any]) -> None:
    sources = result.get("sources", [])
    if not sources:
        st.info("No Confluence pages matched this question.")
        return

    source_lookup = {source["page_id"]: source for source in sources}
    source_ids = list(source_lookup.keys())

    if st.session_state.get("ask_selected_source_page") not in source_lookup:
        st.session_state["ask_selected_source_page"] = source_ids[0]

    st.caption("Live Confluence matches for this query. This MVP searches Confluence at runtime; it does not use a persistent local page index yet.")
    selected_page_id = st.radio(
        "Matched pages",
        source_ids,
        key="ask_selected_source_page",
        format_func=lambda page_id: source_lookup[page_id]["title"],
    )

    selected_source = source_lookup[selected_page_id]
    source_card(selected_source)

    preview, error = get_page_preview(selected_page_id)
    if error:
        st.error(error)
        return

    if preview:
        st.text_area(
            "Page preview",
            value=preview.get("content", ""),
            height=260,
            key=f"preview-{selected_page_id}",
            disabled=True,
        )

    matched_chunks = [chunk for chunk in result.get("retrieved_chunks", []) if chunk.get("page_id") == selected_page_id]
    if matched_chunks:
        st.markdown("**Matched excerpts used for grounding**")
        for chunk in matched_chunks[:3]:
            st.markdown(f"- {chunk.get('snippet') or chunk.get('content', '')[:200]}")


def show_api_error(error: str | None) -> None:
    if error:
        st.error(error)


def navigate_to(page: str) -> None:
    st.session_state["_pending_page_nav"] = page
    st.rerun()


def current_health() -> dict[str, Any] | None:
    data, error = api_get("/api/health")
    if error:
        st.error(error)
        return None
    return data


def current_config() -> dict[str, Any] | None:
    data, error = api_get("/api/config")
    if error:
        st.error(error)
        return None
    return data


def setup_page() -> None:
    hero("Connect your sources and local model", "Save the runtime configuration used by both the dashboard and the MCP tools, and write a workspace .env file for sharing.")
    config = current_config()
    if config is None:
        return

    st.caption(
        f"Dashboard saves will write `.env` at `{config.get('env_file_path', '.env')}`. "
        f"Current state: {'present' if config.get('env_file_exists') else 'not created yet'}."
    )

    with st.form("setup-form", clear_on_submit=False):
        confluence_base_url = st.text_input("Confluence URL", value=config.get("confluence_base_url", ""), placeholder="https://your-domain.atlassian.net/wiki")
        confluence_email = st.text_input("Email", value=config.get("confluence_email", ""))
        confluence_api_token = st.text_input(
            "API Token",
            value="",
            type="password",
            help="Leave blank to keep the currently saved token.",
        )
        ollama_base_url = st.text_input("Ollama Base URL", value=config.get("ollama_base_url", "http://ollama:11434"))
        ollama_model = st.text_input("Model Name", value=config.get("ollama_model", "gemma4:e2b"))
        save = st.form_submit_button("Save", use_container_width=True)

    if config.get("confluence_api_token_set"):
        st.caption("A Confluence API token is already stored for this workspace.")

    if save:
        payload = {
            "confluence_base_url": confluence_base_url,
            "confluence_email": confluence_email,
            "confluence_api_token": confluence_api_token,
            "ollama_base_url": ollama_base_url,
            "ollama_model": ollama_model,
        }
        data, error = api_post("/api/config", payload)
        if error:
            st.error(error)
        else:
            st.success(f"Configuration saved and `.env` updated at `{data.get('env_file_path', '.env')}`.")
            st.session_state["config_cache"] = data

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Test Confluence", use_container_width=True):
            data, error = api_post("/api/confluence/test")
            if error:
                st.error(error)
            else:
                st.success(data.get("detail", "Confluence looks good."))
                if data.get("metadata"):
                    st.json(data["metadata"])
    with col2:
        if st.button("Test Ollama", use_container_width=True):
            data, error = api_post("/api/ollama/test")
            if error:
                st.error(error)
            else:
                if data.get("ok"):
                    st.success(data.get("detail", "Ollama looks good."))
                else:
                    st.warning(data.get("detail", "Ollama is reachable but not fully ready."))
                if data.get("metadata"):
                    st.json(data["metadata"])
    with col3:
        if st.button("Enable VS Code Integration", use_container_width=True):
            navigate_to("VS Code Integration")


def home_page() -> None:
    hero(
        "An agentic quality engineering hub for local teams",
        "Read Confluence, ground answers in documentation, generate QA assets with Ollama, and expose the same capabilities to editor agents through MCP.",
    )
    health = current_health()
    if health is None:
        return

    st.markdown(
        f"""
        <div class="metric-strip">
          <div class="metric-chip">
            <div class="metric-kicker">Model</div>
            <div class="metric-value">{html.escape(str(health.get("ollama", {}).get("metadata", {}).get("model_name", "gemma4:e2b")))}</div>
          </div>
          <div class="metric-chip">
            <div class="metric-kicker">Model Loaded</div>
            <div class="metric-value">{'Yes' if health.get('ollama', {}).get('metadata', {}).get('model_loaded') else 'No'}</div>
          </div>
          <div class="metric-chip">
            <div class="metric-kicker">Advertised MCP URL</div>
            <div class="metric-value">{html.escape(health.get("mcp", {}).get("url", ""))}</div>
          </div>
          <div class="metric-chip">
            <div class="metric-kicker">Confluence State</div>
            <div class="metric-value">{'Connected' if health.get('confluence', {}).get('ok') else 'Not ready'}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    labels = ["Backend", "Confluence", "Ollama", "MCP"]
    keys = ["backend", "confluence", "ollama", "mcp"]
    for column, label, key in zip(cols, labels, keys):
        with column:
            status_card(label, health.get(key, {}))

    st.markdown(
        """
        <div class="block-note">
          The backend exposes both REST endpoints and the mounted MCP server. The dashboard and editor tools share the same Confluence and retrieval logic, while the final generation path can differ: the dashboard uses local Ollama and Codex can summarize directly from retrieved MCP context.
        </div>
        """,
        unsafe_allow_html=True,
    )


def ask_page() -> None:
    hero(
        "Ask grounded questions with live source context",
        "Run one query and inspect the matched Confluence pages beside the answer. VeriAgent searches Confluence live and only sends the top-ranked chunks to Ollama.",
    )
    st.markdown(
        """
        <div class="block-note">
          <strong>How retrieval works:</strong> your question is sent to Confluence search first, VeriAgent fetches the best matching pages, ranks their chunks, and only forwards a small grounded subset to the model. The control below changes grounding depth, not the total number of pages in Confluence.
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("ask-form"):
        query = st.text_area("What do you want to verify?", placeholder="Example: Generate login test scenarios for the release approval workflow.")
        top_k = st.slider(
            "Grounding depth",
            min_value=1,
            max_value=5,
            value=3,
            help="How many top-ranked chunks VeriAgent sends to Ollama for this answer.",
        )
        generate_selenium = st.toggle("Generate Selenium starter code", value=False)
        submit = st.form_submit_button("Run grounded QA", use_container_width=True)

    if submit:
        data, error = api_post(
            "/api/qa/ask",
            {"query": query, "top_k": top_k, "generate_selenium": generate_selenium},
        )
        if error:
            st.error(error)
        else:
            st.session_state["ask_result"] = data
            st.session_state["page_preview_cache"] = {}
            sources = data.get("sources", [])
            if sources:
                st.session_state["ask_selected_source_page"] = sources[0].get("page_id")

    result = st.session_state.get("ask_result")
    if not result:
        return

    if result.get("generation_error"):
        st.warning(result["generation_error"])

    summary_cols = st.columns(3)
    with summary_cols[0]:
        st.metric("Matched pages", len(result.get("sources", [])))
    with summary_cols[1]:
        st.metric("Grounding chunks", len(result.get("retrieved_chunks", [])))
    with summary_cols[2]:
        st.metric("Mode", "QA + sources" if not result.get("generation_error") else "Sources only")

    left, right = st.columns([1.25, 0.85], gap="large")
    sections = result.get("sections", {})

    with left:
        tabs = st.tabs(["Answer", "QA Assets", "Selenium"])

        with tabs[0]:
            st.subheader("Answer")
            st.write(sections.get("answer") or "No answer text returned.")
            st.subheader("Assumptions")
            st.write(sections.get("assumptions") or "No assumptions listed.")

        with tabs[1]:
            st.subheader("Test Scenarios")
            st.write(sections.get("test_scenarios") or "No scenarios returned.")
            st.subheader("Steps")
            st.write(sections.get("steps") or "No steps returned.")
            st.subheader("Expected Results")
            st.write(sections.get("expected_results") or "No expected results returned.")

        with tabs[2]:
            code = sections.get("selenium_code") or "Not requested."
            st.code(code, language="python")

    with right:
        st.subheader("Matched Sources")
        render_matched_sources(result)


def vscode_page() -> None:
    hero("Enable editor agents through MCP", "Generate a workspace config, write it into the repo, and point VS Code or Codex at the backend-hosted MCP endpoint.")
    info, error = api_get("/api/integration/info")
    if error:
        st.error(error)
        return

    running_in_docker = str(info.get("running_in_docker", "false")).lower() == "true"
    host_workspace_path = info.get("host_workspace_path", "").strip()
    display_workspace_path = host_workspace_path or info.get("workspace_root", DEFAULT_WORKSPACE_PATH)

    st.markdown(
        f"""
        <div class="block-note">
          <strong>MCP server URL:</strong> {html.escape(info.get("mcp_url", ""))}<br>
          <strong>Suggested workspace path:</strong> {html.escape(display_workspace_path)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if running_in_docker:
        st.caption("Open Location is disabled in the Docker deployment because the dashboard cannot launch your host file explorer from inside the container.")

    workspace_path = st.text_input("Workspace path", value=st.session_state.get("workspace_path", info.get("workspace_root", DEFAULT_WORKSPACE_PATH)))
    target_label = st.radio("Config target", ["Both", "VS Code", "Codex"], horizontal=True)
    target = {"Both": "both", "VS Code": "vscode", "Codex": "codex"}[target_label]

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Generate MCP Config", use_container_width=True):
            data, error = api_post("/api/integration/config", {"workspace_path": workspace_path, "target": target})
            if error:
                st.error(error)
            else:
                st.session_state["mcp_config"] = data
                st.session_state["workspace_path"] = workspace_path
    with col2:
        if st.button("Enable VS Code Integration", use_container_width=True):
            data, error = api_post("/api/integration/enable", {"workspace_path": workspace_path, "target": target})
            if error:
                st.error(error)
            else:
                st.session_state["mcp_config"] = data
                st.session_state["workspace_path"] = workspace_path
                st.success("Config written to the workspace.")
    with col3:
        button_label = "Copy Host Path" if running_in_docker else "Open Location"
        if st.button(button_label, use_container_width=True):
            if running_in_docker:
                render_copy_button(display_workspace_path, "Copy Workspace Path", "workspace-path")
                st.info(f"Open this folder manually on your host machine: {display_workspace_path}")
            else:
                _, error = api_post("/api/integration/open-location", {"path": workspace_path})
                if error:
                    st.warning(error)
                else:
                    st.success("Opened the workspace location.")

    config = st.session_state.get("mcp_config")
    if not config:
        return

    for instruction in config.get("instructions", []):
        st.caption(instruction)

    if config.get("written_files"):
        st.success("Written files: " + ", ".join(config["written_files"]))

    vscode_config = config.get("vscode")
    codex_config = config.get("codex")

    if vscode_config:
        st.subheader(".vscode/mcp.json")
        render_copy_button(vscode_config["content"], "Copy Config", "vscode-config")
        st.code(vscode_config["content"], language="json")

    if codex_config:
        st.subheader(".codex/config.toml")
        render_copy_button(codex_config["content"], "Copy Config", "codex-config")
        st.code(codex_config["content"], language="toml")


def sidebar() -> None:
    st.sidebar.markdown(
        """
        <div class="brand-lockup">
          <div class="brand-name">VeriAgent</div>
          <div class="brand-copy">Local-first QA hub grounded in Confluence and powered by Ollama.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.radio("Navigate", PAGES, key="page_nav")
    st.sidebar.caption(f"Backend: {BACKEND_URL}")


def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    pending_page = st.session_state.pop("_pending_page_nav", None)
    if pending_page is not None:
        st.session_state["page_nav"] = pending_page
    if "page_nav" not in st.session_state:
        st.session_state["page_nav"] = "Home"
    sidebar()

    page = st.session_state["page_nav"]
    if page == "Home":
        home_page()
    elif page == "Setup":
        setup_page()
    elif page == "Ask":
        ask_page()
    elif page == "VS Code Integration":
        vscode_page()
    else:
        home_page()


if __name__ == "__main__":
    main()
