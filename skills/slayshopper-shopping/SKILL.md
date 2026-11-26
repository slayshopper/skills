---
name: slayshopper-shopping
description: "Use for any product search, price compare, or shopping run."
version: 0.3.3-alpha
author: SlayShopper
license: MIT
platforms: [linux, macos, windows]
---

# SlayShopper product search

> **Status: ALPHA** — the MCP endpoint (`slay.cytr.us`) is transitional; the response contract and fields (`availability`, `brand`, `previewUrl`, `credits`) may change without notice. Not for production.

Tools on the **`slayshopper` MCP server** (`https://slay.cytr.us/mcp`). Your MCP client registers them under client-specific names (e.g. `mcp__slayshopper__search_products` in Hermes) — call whichever names your client exposes. The Bearer key is supplied by your client's MCP config (env var or `Authorization` header); never hard-code it here.

- **`search_products`** — the default. You turn the user's ask into a short product phrase plus filters; SlayShopper picks the shops, filters out products that don't match the ask, and returns offers with a results page. No second LLM on the server: a few seconds, a few dozen credits.
- **`shopping_assistant`** — a full assistant with its own model that plans several searches from a natural message. Slower (10–60 s) and pricier. Use it only when you cannot plan the search yourself.

Every call is **billed in credits** to the user's SlayShopper account (`credits.charged`, `credits.balance` in the `search_products` response). Treat every call as costing money.

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

The shop set and currency depend on the user's **market**, not the query language. Determine the market from the user's country/language/context and pass `market` (ISO alpha-2: `PL`, `CZ`, …) on the first call of a topic. Never assume one country — a Czech user typing "iphone 15" (English) still wants CZ shops. A `sessionId` carries the market to follow-ups. Prices (`minPrice`, `maxPrice`) are in the market's currency.

**Not every market is live yet.** A market with no shops is rejected before anything is billed: a tool error over MCP, HTTP 400 over REST. The message names the market you sent and lists the supported market codes (e.g. you sent `CZ`, supported: `PL`). Its wording and language may change — recognise it by the market code you sent plus the list of codes, not by exact text. Then:

- Tell the user, in their language, that SlayShopper does not cover their country yet and which markets it does cover.
- **Do not silently retry with `PL`** (or any other market) — foreign shops mean foreign prices, currency and delivery. Search another market only if the user says they want it.
- Do not retry the same market; the answer won't change within the conversation.

## Calling `search_products`

| Field | What to put there |
| --- | --- |
| `query` (required) | A short **product phrase**, 1–4 words, in the words shops use in product titles: `słuchawki do biegania`, `zasłona blackout`. **Every word must appear in the product** (prepositions like "do", "z", "i" are ignored), so leave adjectives, units and numbers out — put them in `intent` and filters. No prices, no "I'm looking for". |
| `intent` (recommended) | The user's **full ask** in their words, with conditions and exclusions: `earbuds for running, waterproof, not in-ear, under 300`. Products that contradict it are filtered out — this is what makes results relevant. |
| `market` | ISO alpha-2 country code of the **user's** shops (`PL`, `CZ`, …) — from their country/language, not from the language of `query`. Pass it on the first call of a topic; with `sessionId` it can be omitted (the session keeps it). Omitted with no session = `PL`. See "Markets". |
| `minPrice` / `maxPrice` | Budget in the market's currency. |
| `brands`, `shops`, `onSale` | Only when the user asked for them. |
| `sessionId` | From the previous response, to keep the same `previewUrl` for this topic. Omit for a new topic. |
| `shopOffset` | Only for "show more": the previous `nextShopOffset`. At most 4 pages of 30. |

1. **One call per shopping question.** Put all known constraints in `intent` and the filters up front. Do not fire variants of the same query "to improve" results.
2. **Refinements are a new call with the same `sessionId`** ("cheaper", "only Xiaomi", "over-ear instead") — adjust `query`/`intent`/filters. The same `previewUrl` then shows the new results.
3. **Empty `products` → one retry with a broader phrase.** Drop adjectives, units and numbers, or use the general product name (`pilarka tarczowa` instead of `pilarka cicha do desek`, `karma dla psa` instead of `karma dla psa 10kg`), keep `intent` and filters. If the retry is empty too, tell the user and suggest what to change; do not loop.
4. **No speculative calls.** Never search to build examples or to test the connection, or before the user has named a product type.
5. **Treat the payload as a sample, not the market.** It covers the shops picked for this query; for a buying decision, price the same item in one or two big chains before answering.

`shopping_assistant` takes a natural `message` (plus `sessionId`, `market`) instead and returns `reply` and `selected[]` (its picks) on top of `products[]`. `market` works exactly as in `search_products`: the user's country code, kept by `sessionId`, and the same "not supported yet" error (see "Markets").

## Showing results

`previewUrl` **is the listing.** It is a page rendered by SlayShopper: photos, prices with sale badges, the same product across shops collapsed to the cheapest offer, working shop links, labels in the market's language. You do not render products yourself.

1. **One sentence of your own, then the link.** Name the cheapest sensible option and the trade-off, then give `previewUrl` as a link ("see all results"). Do not re-list what the page already shows — mention at most 1–3 picks by name and price. `products[]` is ordered by relevance to the ask, not by price; pick yourself.
2. **Same session, same link.** The page shows the latest search of the session, so after a refinement with `sessionId` the same `previewUrl` shows the new results — share it again with a one-line note on what changed.
3. **The link is unlisted, not private.** Anyone holding it can see the results (not the conversation). Share it with the user; do not post it anywhere else unless asked.
4. **No `previewUrl`** (`null` or missing): write up to 5 lines from `products[]`, one per product, same product in several shops listed once:

   ```
   **Xiaomi Redmi Buds 5 Black** — 169 zł · geekstore-pl · [see in shop](https://slay.cytr.us/api/go/...)
   ```

   Add `![title](imageLink)` under a line only when `imageLink` is non-empty and your surface renders remote images.

## Credits

- `credits.charged` is what the call cost; `credits.balance` is what is left. Mention cost only if the user asks or the balance is getting low (under ~500 credits ≈ a dozen searches).
- **Out of credits** (HTTP 402 over REST, a tool error over MCP; the message starts with "Out of credits") — stop and tell the user their SlayShopper credits ran out; the balance is at `slay.cytr.us/settings`. Do not retry.

## REST fallback (no MCP client)

If your agent has no MCP client (a plain-HTTP harness, OpenClaw/ClawHub, a `fetch`-only runtime), call the same search over REST — same response object, no SSE, no JSON-RPC:

```bash
curl -sS -m 60 -X POST https://slay.cytr.us/api/products/search \
  -H "Authorization: Bearer $SLAYSHOPPER_API_KEY" -H 'Content-Type: application/json' \
  -d '{"query":"wireless earbuds","intent":"wireless earbuds for running, under 300","maxPrice":300,"market":"PL"}'
```

Same fields as the MCP tool (`sessionId`: `null` = new topic). 401 without a key, 402 out of credits, 400 on invalid fields or an unsupported `market` (the `error` says which — see "Markets"). The assistant variant is `POST /api/search` with `{"query": "<natural message>", "sessionId": null, "market": "PL"}`.

## Never invent

Every fact you state must come from the payload or a live check you made:

- `availability` is `"unknown"` for nearly all rows — never claim "in stock"; say availability is unknown (in the user's language).
- `url` is an **affiliate redirect** (`slay.cytr.us/api/go/...`), not the shop's own address. Label it as a link ("see in shop"), never as the shop URL.
- `brand` is usually `null` — do not guess a brand from the title unless the title states it.
- `reply` (only from `shopping_assistant`) can contain mojibake (CJK characters leaking into the text). Read it for context, but write your own summary from `products[]`; never quote `reply` verbatim when it looks corrupted.
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
- **Out of credits** — see "Credits"; do not retry.
- **Error naming your `market` and listing supported codes** — unsupported market; see "Markets". Tell the user, do not fall back to `PL`.
- **Slow** — `search_products` usually answers in seconds; one retry after a timeout is fine, three is burning credits. Empty results: see rule 3 under "Calling `search_products`".
- **`previewUrl` answers 404** — the session was deleted; run a new search if the user still wants results.

## Verified contract (2026-11)

`tools/list` → `search_products` and `shopping_assistant`; stateless (no `Mcp-Session-Id`); responses arrive as SSE. `search_products` returns `sessionId`, `previewUrl` (`https://slay.cytr.us/p/<token>`), `query`, up to 30 `products[]`, `more`, `nextShopOffset` and `credits {charged, balance}`. All words of `query` (minus prepositions/conjunctions) must match; no server-side retry. Each shop belongs to one market; an explicit `market` without shops is rejected before billing, and the error lists the supported markets. Error messages are in English (a tool error over MCP, `{"error": "..."}` over REST); translate them for the user, never paste them raw.
