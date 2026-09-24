# Preserve Perplexity search during the Pi migration

Owner requirement: keep Perplexity search available to Morty, Iztac and Neo where appropriate. OpenClaw retirement is incomplete until this capability has a verified replacement or the owner explicitly changes the requirement.

Observed 2026-09-24: OpenClaw's Perplexity plugin is enabled, its web-search provider is Perplexity, and its plugin configuration contains an API-key setting. The value was not printed, copied or tested. Configuration presence does not establish current API entitlement or a successful query.

Perplexity provides an official MCP server, both remote (`https://api.perplexity.ai/mcp`) and local (`@perplexity-ai/mcp-server`), including `perplexity_search`. Prefer that supported interface for clients with an existing MCP implementation. Do not implement another search daemon or wrap every agent command.

The pinned Pi runtime supports extension tools. This audit did not establish a built-in MCP client or a currently installed Perplexity extension. Verify an appropriate maintained Pi MCP integration before choosing it. If none is suitable, compare its dependency and maintenance cost against a single bounded Pi tool using Perplexity's official Search API; do not assume generic MCP plumbing is automatically the smaller solution.

Credentials should come from an explicitly selected protected source outside repository content and prompts. Do not keep the replacement dependent on reading OpenClaw's configuration forever. Credential relocation and billing/entitlement verification are explicit migration steps. Claude/Codex account selection must not silently select a different Perplexity credential.

Acceptance: invoke search through the actual Pi tool, get useful results with source URLs, verify missing credentials and errors do not disclose secrets, preserve requested date/domain filters supported by the chosen interface, and demonstrate that OpenClaw is not required. No live API query, credential move, MCP installation or successful Pi search is claimed yet.

Source: https://github.com/perplexityai/modelcontextprotocol (official server and supported clients); installed Pi documentation and extension API; local OpenClaw configuration keys inspected without printing their values.
