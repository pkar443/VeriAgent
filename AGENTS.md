# VeriAgent Agent Instructions

Use the `veriagent` MCP server for any request that asks about Confluence documentation, deadlines, requirements, QA scenarios, or Selenium generation.

Preferred tool order:
1. Use `answer_from_confluence(query, top_k)` for direct documentation Q&A.
2. Use `generate_selenium_test_plan(query, top_k)` for QA scenario generation.
3. Use `generate_selenium_code(query, top_k)` for Selenium starter code.
4. Only use `search_confluence` and `get_confluence_page` when you need to inspect sources manually or when the direct answer tool does not provide enough detail.

Answering rules:
- Ground the answer only in tool results from `veriagent`.
- If the answer is not present in the retrieved content, say it is not documented.
- Keep the answer short unless the user asks for more detail.
- Always include a `Sources` section.
- In `Sources`, format each source as a Markdown link like `[Page Title](https://...)` so links are clickable in supporting clients.
- If the tool returns assumptions or generation errors, mention them briefly.
