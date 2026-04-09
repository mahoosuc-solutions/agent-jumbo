# Search Stack Transition

## Current State

`SearXNG` is still the built-in query search backend in the codebase.

- `python/tools/search_engine.py` exposes the generic web-search tool.
- `python/helpers/searxng.py` is the active local backend integration.
- `prompts/agent.system.tool.search_engine.md` still frames this as the default search tool.
- `docs/architecture.md` still describes `SearXNG` as the primary search layer.

## What Is Replacing It

For local workflows, the replacement direction is not another metasearch engine. It is agentic browsing plus optional provider search.

- `python/tools/browser_agent.py` is the stronger long-term path for web research.
- The repo already treats the browser model as a first-class runtime role.
- MCP-backed providers such as Brave Search or Fetch are a better fit for opt-in search than a mandatory bundled metasearch service.

## Recommended Pitch

Use this framing:

`SearXNG` is the legacy query-only search layer. Agent Mahoo is moving toward an agentic research stack where the default path is browser-driven investigation, with optional provider-backed search via MCP when fast retrieval is enough.

That pitch is more accurate than saying `SearXNG` has already been replaced. In the current code, it has not.

## Practical Positioning

- `local-lite`: keep the UI and agent runtime usable without needing the full local search stack.
- `research`: enable browsing- and search-heavy workflows intentionally.
- `full`: enable the whole platform when operational systems are actually needed.

## Next Migration Step

When we choose to retire `SearXNG` from default local Docker, do it explicitly:

1. make `browser_agent` the default recommended research path in prompts and docs
2. move `SearXNG` behind an opt-in run mode or profile
3. document MCP search providers as the preferred lightweight search add-on
