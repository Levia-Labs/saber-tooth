# 0010 MCP over streamable HTTP in the API process

## Context

Agents need to list maps, review proposals and start jobs without the browser UI. A separate MCP service would add a container, a second copy of the store and a second place to enforce the Host allowlist and the YouTube rule.

## Decision

1. The official `mcp` SDK (pinned exactly) builds an `MCPServer`; its Streamable HTTP routes are added to the FastAPI app at `/mcp`, stateless with JSON responses, so no session state lives in the process.
2. Tools call the same `Api` methods as the REST routes, so validation, the YouTube allowlist and the approval gate are shared. List results are capped at 200 entries with a total count.
3. The existing same-origin middleware covers `/mcp`. The SDK's own Host check is disabled because it cannot honour `SABER_ALLOWED_HOSTS` or trusted proxies.
4. `apply_map` is the only tool that writes into `CustomLevels`, and only into a new sibling folder ([ADR 0003](0003-sibling-folder-and-approval-gate.md)).

## Consequences

1. No new service or port; `docker compose` is unchanged.
2. Any client that can reach the port can call the tools, as with REST; there is no authentication, so keep the published port on loopback.
3. SDK upgrades can change the API (2.x renamed `FastMCP` to `MCPServer`), so the pin moves deliberately.
