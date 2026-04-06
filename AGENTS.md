# VeriAgent Agent Instructions

Use the `veriagent` MCP server for any request that asks about Confluence documentation, deadlines, requirements, QA scenarios, Selenium generation, dashboard drafts, Confluence publishing, or Jira ticket creation.

Preferred tool order:
1. Use `retrieve_confluence_context(query, top_k)` for documentation Q&A, then write the final answer yourself from the returned chunks.
2. Use `answer_from_confluence(query, top_k)` when the user still wants the MCP server to choose the answer path. This tool now defaults to retrieval-only context unless `use_local_llm=true` is explicitly requested.
3. Use `generate_selenium_test_plan(query, top_k)` and `generate_selenium_code(query, top_k)` in retrieval-first mode, then generate the final plan or code yourself from the returned chunks.
4. Use `save_dashboard_draft(title, target, raw_input, structured_markdown)` when the user wants Codex to hand a draft off to the VeriAgent dashboard for review and publishing.
5. Use `create_confluence_page(title, space, content_markdown, parent_page_id)` when the user explicitly wants to publish content into Confluence immediately.
6. Use `create_jira_ticket(summary, project_key, description_markdown, issue_type, labels)` when the user explicitly wants to publish directly into Jira.
7. Only use `search_confluence` and `get_confluence_page` when you need to inspect sources manually or when the retrieval-first tools do not provide enough detail.

Answering rules:
- Ground the answer only in tool results from `veriagent`.
- If the answer is not present in the retrieved content, say it is not documented.
- Keep the answer short unless the user asks for more detail.
- Always include a `Sources` section.
- In `Sources`, format each source as a Markdown link like `[Page Title](https://...)` so links are clickable in supporting clients.
- Do not request `use_local_llm=true` unless the user explicitly asks for a Gemma or Ollama-generated answer.
- If the tool returns assumptions or generation errors, mention them briefly.
- Before publishing, make sure the user has either provided the content or asked you to draft it first.
- Prefer `save_dashboard_draft` when a human review step is useful.
- After publishing, return the created URL and the page ID or Jira key.
