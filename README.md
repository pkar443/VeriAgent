# VeriAgent

VeriAgent is a local-first, Docker-friendly quality engineering hub that connects Confluence Cloud, Ollama, and MCP-enabled editor agents through one shared backend.

As of April 4, 2026, the closest official Ollama tag to the requested `gemma:4e2b` is `gemma4:e2b`, so this MVP uses `gemma4:e2b` by default.

## Architecture Summary

```text
[Streamlit Dashboard]
        |
        v
[FastAPI Backend + Mounted MCP Endpoint]
        |
        +-- Confluence Cloud REST API
        +-- Retrieval + chunk ranking
        +-- Ollama / Gemma 4 E2B
```

- The dashboard calls FastAPI REST endpoints.
- VS Code and Codex connect to the MCP endpoint mounted on the same backend at `http://localhost:8000/mcp` by default.
- Both modes use the same Confluence client, retrieval logic, prompt strategy, and Ollama provider.

## File Structure

```text
backend/
  app/
    api/
    core/
    models/
    services/
    utils/
  Dockerfile
  requirements.txt
  start_backend.py
dashboard/
  Dockerfile
  requirements.txt
  app.py
mcp/
  README.md
veriagent_mcp/
  server.py
docker-compose.yml
.env.example
README.md
```

## What The MVP Does

- Connects to Confluence Cloud using email and API token auth.
- Searches pages, fetches page content, cleans HTML, and extracts snippets.
- Retrieves only top-ranked chunks instead of sending full documents to the model.
- Calls Ollama through `POST /api/generate` with retries and timeout handling.
- Uses a strict QA prompt to reduce hallucination on a smaller local model.
- Generates grounded answers, test scenarios, steps, expected results, and Selenium starter code.
- Surfaces Confluence links in dashboard results and MCP tool responses.
- Generates editor MCP config for `.vscode/mcp.json` and `.codex/config.toml`.
- Includes a workspace `AGENTS.md` so Codex prefers the direct VeriAgent MCP tools for Confluence questions.
- Uses local Ollama generation for the dashboard, while MCP tools default to retrieval-only context so Codex can write the final answer itself.

## Quick Start

### 1. Create the environment file

```bash
cp .env.example .env
```

Fill in at least:

```env
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_EMAIL=you@example.com
CONFLUENCE_API_TOKEN=your_token
OLLAMA_MODEL=gemma4:e2b
APP_PORT=8000
MCP_PORT=8000
PUBLIC_BACKEND_URL=http://localhost:8000
```

`MCP_PORT` should normally match `APP_PORT` because the MCP server is mounted inside the backend process.

### 2. Start the stack

```bash
docker compose up --build
```

This starts:

- `ollama`
- `backend`
- `dashboard`

The Ollama container auto-pulls `gemma4:e2b` and the backend waits for Ollama readiness before serving requests.

### 3. Open the product

- Dashboard: `http://localhost:8501`
- Backend API: `http://localhost:8000`
- MCP endpoint: `http://localhost:8000/mcp`

## Confluence Token Setup

1. Sign in to Atlassian.
2. Open the Atlassian API token management page.
3. Create a new API token.
4. Copy the token into `.env` or into the dashboard Setup page.
5. Use your Confluence email address with the token.

Expected base URL format:

```text
https://your-domain.atlassian.net/wiki
```

If you only provide `https://your-domain.atlassian.net`, VeriAgent normalizes it to include `/wiki`.

## Dashboard Guide

### Home

- Shows backend, Confluence, Ollama, and MCP health.
- Displays the advertised MCP URL used for editor setup.

### Setup

- Saves Confluence and Ollama settings into the runtime config file.
- Creates or updates the workspace `.env` file directly from the dashboard.
- Lets you test Confluence credentials and Ollama connectivity.
- Includes a shortcut into the VS Code integration page.

### Ask

- Accepts a grounded question.
- Lets you choose grounding depth.
- Optionally generates Selenium starter code.
- Shows the matched Confluence pages beside the answer.
- Lets you preview the selected page and matched excerpts used for grounding.
- Always returns source links and snippets, even if generation fails.

### VS Code Integration

- Shows the MCP server URL.
- Generates workspace config for `.vscode/mcp.json` and `.codex/config.toml`.
- Writes config into the selected workspace path when possible.
- Falls back to copyable config blocks when automatic writing is not enough.

## MCP Setup Instructions

The backend exposes the MCP server at:

```text
http://localhost:8000/mcp
```

### Recommended setup for Codex

If your main target is Codex in VS Code, the most reliable first-run setup is:

```bash
codex mcp add veriagent --url http://localhost:8000/mcp
```

You can also place the same entry in your global Codex config:

```toml
[mcp_servers.veriagent]
url = "http://localhost:8000/mcp"
```

Typical location:

```text
~/.codex/config.toml
```

This is the preferred path for Codex. The workspace `.vscode/mcp.json` file is optional and is mainly useful for the generic VS Code MCP workspace flow.

### MCP generation behavior

- Dashboard `Ask` keeps using local Ollama and `gemma4:e2b`.
- MCP tools for Codex default to retrieval-only context and do not call Ollama unless `use_local_llm=true` is explicitly requested.
- This keeps Codex answers grounded in Confluence while letting Codex do the final summarization in the editor.

### VS Code workspace config

Generated file:

```json
{
  "servers": {
    "veriagent": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Path:

```text
.vscode/mcp.json
```

### Codex config snippet

Generated file:

```toml
[mcp_servers.veriagent]
url = "http://localhost:8000/mcp"
```

Path:

```text
.codex/config.toml
```

After writing the config:

1. Restart VS Code.
2. Confirm you are signed in to the editor agent you plan to use.
3. Re-open the workspace.
4. Verify the `veriagent` MCP server appears in the agent tool list.

If your Codex setup only reads the global config, copy the generated snippet into `~/.codex/config.toml`.

## Testing In Codex VS Code

### Recommended direct-answer test

Use the retrieval-first MCP path so Codex summarizes from grounded Confluence chunks:

```text
Use veriagent.retrieve_confluence_context for: "product requirement deadline".

Return only:
Answer:
Sources:
- [title](url)
```

This retrieves the same grounded Confluence context used by the backend retrieval layer without sending the final answer through Ollama.

### Optional local-LLM answer path

If you explicitly want the MCP server to use local Gemma for the final answer, ask for:

```text
Use veriagent.answer_from_confluence for: "product requirement deadline" with use_local_llm=true.
Return the answer and sources.
```

### Other useful tool prompts

```text
Use veriagent.generate_selenium_test_plan for: "login workflow validation".
Return the grounded QA plan and source links.
```

```text
Use veriagent.generate_selenium_code for: "login workflow validation".
Return starter Selenium Python code and source links.
```

```text
Use veriagent.search_confluence for: "decision documentation".
List the top matching pages with clickable markdown links only.
```

### How to verify the MCP server is really being used

1. Run `codex mcp list` and confirm `veriagent` is enabled.
2. Keep `docker compose up` running.
3. In another terminal, run:

```bash
docker compose logs -f backend
```

4. Send the prompt in Codex.
5. Look for `/mcp` requests in the backend logs.

If you see `/mcp` traffic and the answer includes Confluence page URLs, Codex is using the VeriAgent MCP server.

## Local Development

Run the backend locally:

```bash
pip install -r backend/requirements.txt
python backend/start_backend.py
```

Run the dashboard locally:

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

Environment defaults:

- Dashboard backend URL: `http://localhost:8000`
- Backend runtime config file: `.veriagent/runtime-config.json`

## Key Endpoints

- `GET /api/health`
- `GET /api/config`
- `POST /api/config`
- `POST /api/confluence/test`
- `POST /api/ollama/test`
- `GET /api/confluence/pages`
- `GET /api/confluence/pages/{page_id}`
- `POST /api/qa/ask`
- `POST /api/qa/context`
- `POST /api/integration/config`
- `POST /api/integration/enable`
- `POST /api/integration/open-location`
- `POST /mcp` using Streamable HTTP MCP transport

## Prompting Strategy

The QA service always starts from a strict prompt:

- Use only provided Confluence content.
- Do not assume missing details.
- Extract scenarios, steps, expected results, and Selenium code only when requested.
- Push missing detail into explicit assumptions rather than inventing facts.

The backend sends only the top 2 to 3 relevant chunks to the model during normal use.

## Troubleshooting

### Ollama not ready

- Check `docker compose logs ollama`.
- Confirm the model name is `gemma4:e2b`.
- Wait for the initial pull to finish on the first run.

### Model not loaded

- Run `docker compose exec ollama ollama list`.
- If needed, run `docker compose exec ollama ollama pull gemma4:e2b`.

### Confluence auth fails

- Confirm the email matches your Atlassian account.
- Confirm the token is an Atlassian API token, not a password.
- Confirm the base URL points to Confluence Cloud.

### Empty results

- Check whether the Confluence page is accessible to the configured account.
- Try broader search terms.
- Use the Ask page source panel to confirm pages can be listed at all.

### MCP config written but not detected

- Restart VS Code fully.
- Re-open the workspace folder.
- Verify the workspace path used by the dashboard is the same path opened in VS Code.
- For Codex-specific setups, prefer `codex mcp add veriagent --url http://localhost:8000/mcp` or copy the generated snippet into `~/.codex/config.toml`.

### Codex MCP calls seem slow or get cancelled

- Prefer direct prompts that call `veriagent.retrieve_confluence_context` instead of asking Codex to explore and decide on tools itself.
- Keep the request narrow, such as `product requirement deadline` instead of a broad question.
- Retrieval-only MCP calls should be much faster than the local Ollama answer path.
- If you explicitly use `use_local_llm=true` and Ollama is running on CPU only, the grounded answer step can still take tens of seconds.
- If a chat shows tool calls being cancelled, start a fresh chat and retry with the direct tool prompt above.

### Docker build cannot start

- Confirm Docker Desktop or the Docker engine is running before using `docker compose up --build`.
- On Windows, the CLI may be present even when the engine pipe is unavailable, which prevents builds from starting.

## Limitations

- No embedding index or vector store yet; retrieval is keyword and title-score based.
- No user auth layer on the backend because this MVP is intended for local use.
- Confluence search quality depends on page access and Cloud API result quality.
- Selenium code is starter code and may still require locator refinement.
- Automatic file opening is environment-dependent and may not work inside every Docker setup.
- CPU-only Ollama inference can still be slow even on high-RAM machines; RAM helps model fit, but token generation speed is mostly CPU or GPU bound.

## Future Improvements

- Add persistent chunk indexing for faster retrieval on larger Confluence spaces.
- Add test case export formats such as Gherkin, Pytest, and Jira-ready artifacts.
- Add richer page chunking with section-aware heading preservation.
- Add background sync and local caching for source explorer performance.
- Add role-based auth and audit logging for shared team deployments.
- Add regression packs and requirements-to-test traceability views.
