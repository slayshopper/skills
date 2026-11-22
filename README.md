# SlayShopper Skills

Agent skills for integrating with [SlayShopper](https://slay.cytr.us) — a product search engine over MCP. Each skill turns the `shopping_assistant` result into a photo listing with deduplication, price sorting, and "never invent" rules.

## Status: ALPHA

Early version. The MCP endpoint (`https://slay.cytr.us/mcp`) is **transitional** — not yet on the final domain. The response contract and fields (`availability`, `reply`, `brand`) may change without a stability guarantee. Use deliberately, not in production.

## Contents

- [`skills/slayshopper-shopping/`](skills/slayshopper-shopping/) — product search, price comparison, and photo listing.

## Installation

### 1. MCP server (required)

The skill assumes the `shopping_assistant` tool of the `slayshopper` MCP server is connected. Generate your API key at https://slay.cytr.us/settings.

- **Hermes Agent**
  ```bash
  hermes mcp add slayshopper --url https://slay.cytr.us/mcp --auth header
  ```
- **Claude Code**
  ```bash
  claude mcp add --transport http slayshopper https://slay.cytr.us/mcp --header "Authorization: Bearer $KEY"
  ```
- **OpenCode / Claude Desktop / Cursor** — see https://slay.cytr.us/mcp-model-context-protocol

### 2. Skill

- **skills.sh** (any agent): `npx skills add slayshopper/skills --skill slayshopper-shopping`
- **ClawHub / OpenClaw**: `openclaw skills install @slayshopper/slayshopper-shopping`
- **Hermes**: `hermes skills install well-known:https://slay.cytr.us/.well-known/skills/slayshopper-shopping`

### 3. Direct REST (no MCP client)

For agents without an MCP client (plain-HTTP harness, OpenClaw/ClawHub, `fetch`-only runtimes) the skill also works over plain REST — same response, no SSE/JSON-RPC:

```bash
curl -sS -X POST https://slay.cytr.us/api/search \
  -H "Authorization: Bearer $SLAYSHOPPER_API_KEY" -H 'Content-Type: application/json' \
  -d '{"query":"wireless earbuds under 300","sessionId":null,"market":"PL"}'
```

See `skills/slayshopper-shopping/SKILL.md` → "REST fallback" for the full contract (`query`, `sessionId`, `market`).

## License

MIT — see [LICENSE](LICENSE).
