# Preserve Perplexity search during the Pi migration

Owner requirement: keep Perplexity search available to Morty, Iztac and Neo where appropriate. OpenClaw retirement is incomplete until this capability has a verified replacement or the owner explicitly changes the requirement.

Observed 2026-09-24: OpenClaw's Perplexity plugin is enabled, its web-search provider is Perplexity, and its plugin configuration contains an API-key setting. The value was not printed, copied or tested. Configuration presence does not establish current API entitlement or a successful query.

Perplexity provides an official MCP server, both remote (`https://api.perplexity.ai/mcp`) and local (`@perplexity-ai/mcp-server`), including `perplexity_search`. Prefer that supported interface for clients with an existing MCP implementation. Do not implement another search daemon or wrap every agent command.

The pinned Pi runtime supports extension tools. This audit did not establish a built-in MCP client or a currently installed Perplexity extension. Verify an appropriate maintained Pi MCP integration before choosing it. If none is suitable, compare its dependency and maintenance cost against a single bounded Pi tool using Perplexity's official Search API; do not assume generic MCP plumbing is automatically the smaller solution.

Credentials should come from an explicitly selected protected source outside repository content and prompts. Do not keep the replacement dependent on reading OpenClaw's configuration forever. Credential relocation and billing/entitlement verification are explicit migration steps. Claude/Codex account selection must not silently select a different Perplexity credential.

Acceptance: invoke search through the actual Pi tool, get useful results with source URLs, verify missing credentials and errors do not disclose secrets, preserve requested date/domain filters supported by the chosen interface, and demonstrate that OpenClaw is not required. No live API query, credential move, MCP installation or successful Pi search is claimed yet.

Source: https://github.com/perplexityai/modelcontextprotocol (official server and supported clients); installed Pi documentation and extension API; local OpenClaw configuration keys inspected without printing their values.

## Implemented candidate

`integrations/pi/perplexity.ts` is one native Pi extension, explicitly loaded by
the role resource loader for Morty, Iztac and Neo. It calls the fixed official
Search API endpoint; it adds no dependencies or background process. Its sole
credential source is `PERPLEXITY_API_KEY` supplied by the protected launch
environment. It never reads OpenClaw configuration. No credential has been moved.

The current alternative, [pi-mcp-adapter](https://pi.dev/packages/pi-mcp-adapter),
supports remote MCP and protected token storage but introduces a general server
lifecycle/configuration layer (catalog version 2.37.0 lists 15 dependencies).
For this single tool, the direct API is the smaller maintained surface. Revisit
the adapter when several needed services justify sharing that infrastructure.

The tool preserves domain, recency, publication-date and update-date filters from
the [official Search API](https://docs.perplexity.ai/api-reference/search-post).
It requests bounded content, limits response bytes, rejects redirects, supports
abort/timeout, returns only source fields and never returns raw provider errors.
Missing credentials produce a clear local error. Search results remain untrusted
reference material. A model account does not choose the search credential.

`node integrations/pi/check-perplexity.mjs` exercises the actual registered Pi
tool's missing-credential and pre-aborted paths without a live query or mocks.
`check-role-context.mjs` verifies explicit loading across ten role/scope cases.
These checks do not prove useful search results, live filter behavior, provider
entitlement or successful secret redaction in a real provider response. Live
acceptance and the credential migration remain required before cutover.
