---
name: slayshopper-shopping
description: "Use for any product search, price compare, or shopping run."
version: 0.2.0-alpha
author: SlayShopper
license: MIT
platforms: [linux, macos, windows]
---

# SlayShopper product search

> **Status: ALPHA** — the MCP endpoint (`slay.cytr.us`) is transitional; the response contract and fields (`availability`, `reply`, `brand`, `previewUrl`) may change without notice. Not for production.

Tool: the `shopping_assistant` tool on the **`slayshopper` MCP server** (`https://slay.cytr.us/mcp`). Your MCP client registers it under a client-specific name (e.g. `mcp__slayshopper__shopping_assistant` in Hermes) — call whichever name your client exposes. The Bearer key is supplied by your client's MCP config (env var or `Authorization` header); never hard-code it here.

Returns `sessionId`, `title`, `reply`, `previewUrl`, `products[]`, `selected[]`.

**One call is a real shopping session** billed to the user's SlayShopper/OpenRouter key. Treat every call as costing money and 10–60 s.

**Always reply to the user in the user's own language.** This skill's instructions are in English, but your summary and verdicts must be in whatever language the user writes.

## When to Use

- The user names a product type plus a constraint (budget, use-case, size, brand): "find me X under Y", "wireless headphones under 300", "something to sleep in under 200".
- The user wants price comparison, availability, or a recommendation from a product category.
- The user wants to browse products with photos.
- Any mention of products/shops/shopping/prices in a buying context, in any language.

Do **not** trigger for: general questions about a shop or marketplace, product research without buying intent (specs, reviews, history), or fetching a single URL the user already gave you **with no buying question attached**.

A pasted product URL plus a value question ("is it worth it?", "good price?", "opłaca się?") **is** a price comparison — trigger, and treat the price in the pasted page as a claim to verify, not as the price.

**If in doubt whether the ask is shopping — trigger.** A wasted skill load costs a few hundred tokens; a missed one produces a raw JSON blob instead of an answer.

## Markets (multi-country)

The shop set and currency depend on the user's **market**, not the query language. Determine the market from the user's country/language/context and pass it explicitly (`market`, ISO alpha-2: `PL`, `CZ`, …) when the client tool exposes it; otherwise put the country into `message` and let the backend default. Never assume one country — a Czech user typing "iphone 15" (English) still wants CZ shops. Follow-ups keep the previous `sessionId`, which carries the market.

## Call discipline

1. **One call per shopping question.** Put budget, use-case and excluded attributes into `message` up front ("wireless earbuds for running, under 300, not over-ear"). Do not call twice to "improve" results.
2. **Refine with `sessionId`, not a new search.** Follow-ups ("anything cheaper?", "only Xiaomi") get the previous `sessionId`.
3. **No speculative calls.** Never fire a search to build examples, to test the connection, or before the user has stated a product type and budget.
4. **Treat the payload as a sample, not the market.** A session returns only a handful of shops, and its cheapest row is often not the market cheapest. After the call, price the same item directly in one or two big chains before answering.

## Showing results

`previewUrl` **is the listing.** It is a page rendered by SlayShopper: photos, prices with sale badges, the same product across shops collapsed to the cheapest offer, working shop links, labels in the market's language. You do not render products yourself.

1. **One sentence of your own, then the link.** Name the cheapest sensible option and the trade-off, then give `previewUrl` as a link ("see all results"). Do not re-list what the page already shows — mention at most 1–3 picks from `selected[]` by name and price.
2. **Same session, same link.** The page shows the latest turn of the session, so after a refinement with `sessionId` the same `previewUrl` shows the new results — share it again with a one-line note on what changed.
3. **The link is unlisted, not private.** Anyone holding it can see the results (not the conversation). Share it with the user; do not post it anywhere else unless asked.
4. **No `previewUrl`** (`null` or missing, e.g. an older backend): write up to 5 lines from `selected[]` (or the cheapest `products[]`), one per product, same product in several shops listed once:

   ```
   **Xiaomi Redmi Buds 5 Black** — 169 zł · geekstore-pl · [see in shop](https://slay.cytr.us/api/go/...)
   ```

   Add `![title](imageLink)` under a line only when `imageLink` is non-empty and your surface renders remote images.

## REST fallback (no MCP client)

If your agent has no MCP client (a plain-HTTP harness, OpenClaw/ClawHub, a `fetch`-only runtime), call the same search over REST — same response object, no SSE, no JSON-RPC:

```bash
curl -sS -m 180 -X POST https://slay.cytr.us/api/search \
  -H "Authorization: Bearer $SLAYSHOPPER_API_KEY" -H 'Content-Type: application/json' \
  -d '{"query":"wireless earbuds for running, under 300","sessionId":null,"market":"PL"}'
```

`query` is the MCP tool's `message`; `sessionId` continues a session (`null` = new); `market` is ISO alpha-2 (`null` = account default). 401 without a key.

## Never invent

Every fact you state must come from the payload or a live check you made:

- `availability` is `"unknown"` for nearly all rows — never claim "in stock"; say availability is unknown (in the user's language).
- `url` is an **affiliate redirect** (`slay.cytr.us/api/go/...`), not the shop's own address. Label it as a link ("see in shop"), never as the shop URL.
- `brand` is usually `null` — do not guess a brand from the title unless the title states it.
- `reply` from the backend can contain mojibake (CJK characters leaking into the text). Read it for context, but write your own summary from `products[]`; never quote `reply` verbatim when it looks corrupted.
- The page shows prices as of the search. When a live check contradicts the payload (or a price the user pasted), quote the live price in your text and say the page may be stale for that row.

## Answering "is it worth it?" / "opłaca się?"

That is a decision, not a listing request. The order that works:

1. **Verdict in the first sentence**, negatives unsoftened — "no, it's not a deal" — followed by the number that justifies it.
2. **A price table**: shop | price | per unit | delivery, cheapest first, 3–5 verified shops, no photos in the table.
3. **`previewUrl` underneath** for opening offers: the table carries the decision, the page carries the click.
4. **Reframe to unit cost**: price per unit (piece/gram/ml) and per month of use, and say where the bigger pack stops paying off.
5. **Shipping decides tight races.** A small sticker gap is one delivery fee, so quote the real total — pickup, courier, free-shipping thresholds — and label any fee you could not establish as unconfirmed. Never infer a fee.

## Failure modes

- **Tool missing after config change** — MCP has no hot-reload; the client process must restart.
- **401 / "unauthorized"** — key revoked or wrong in the MCP config; regenerate at `slay.cytr.us/settings`.
- **Slow or empty** — calls regularly take 10–60 s; one retry is fine, three is burning credits.
- **`previewUrl` answers 404** — the session was deleted; run a new search if the user still wants results.

## Verified contract (2026-11)

`initialize` → `SlayShopper.Web 1.0.0.0`; `tools/list` → exactly one tool `shopping_assistant`; no `Mcp-Session-Id` issued (stateless); responses arrive as SSE. A real query returns ~30 `products`, 4–6 `selected` and a `previewUrl` of the form `https://slay.cytr.us/p/<token>`.
