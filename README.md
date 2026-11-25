# SlayShopper Skills

Agent skills for integrating with [SlayShopper](https://slay.cytr.us) — a product layer for AI agents over MCP. Each skill drives the `search_products` tool (you plan the query, SlayShopper picks shops and filters products) and hands the user a server-rendered results page (`previewUrl`: photos, prices, deduplication, shop links) plus a short verdict under "never invent" rules. No local scripts or runtimes are required.

## Status: ALPHA

Early version. The MCP endpoint (`https://slay.cytr.us/mcp`) is **transitional** — not yet on the final domain. The response contract and fields (`availability`, `brand`, `credits`) may change without a stability guarantee. Calls are billed in SlayShopper credits. Use deliberately, not in production.

## Contents

- [`skills/slayshopper-shopping/`](skills/slayshopper-shopping/) — product search, price comparison, and a link to the results page.

## Installation

### 1. MCP server (required)

The skill assumes the `slayshopper` MCP server is connected (tools `search_products` and `shopping_assistant`). Generate your API key at https://slay.cytr.us/settings.

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
curl -sS -X POST https://slay.cytr.us/api/products/search \
  -H "Authorization: Bearer $SLAYSHOPPER_API_KEY" -H 'Content-Type: application/json' \
  -d '{"query":"wireless earbuds","intent":"wireless earbuds for running, under 300","maxPrice":300,"market":"PL"}'
```

See `skills/slayshopper-shopping/SKILL.md` → "REST fallback" for the full contract.

## License

MIT — see [LICENSE](LICENSE).
