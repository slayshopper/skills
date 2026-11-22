---
name: slayshopper-shopping
description: "Use for any product search, price compare, or shopping run."
version: 0.1.0-alpha
author: SlayShopper
license: MIT
platforms: [linux, macos, windows]
---

# SlayShopper product search + listing

> **Status: ALPHA** — endpoint MCP (`slay.cytr.us`) jest przejściowy; kontrakt odpowiedzi i pola (`availability`, `reply`, `brand`) mogą się zmienić bez zapowiedzi. Nie do produkcji.

Tool: the `shopping_assistant` tool on the **`slayshopper` MCP server** (`https://slay.cytr.us/mcp`). Your MCP client registers it under a client-specific name (e.g. `mcp__slayshopper__shopping_assistant` in Hermes) — call whichever name your client exposes. The Bearer key is supplied by your client's MCP config (env var or `Authorization` header); never hard-code it here.

Returns `sessionId`, `title`, `reply`, `products[]`, `selected[]`.

**One call is a real shopping session** billed to the user's SlayShopper/OpenRouter key. Treat every call as costing money and 10–60 s.

## When to Use

- The user names a product type plus a constraint (budget, use-case, size, brand): "znajdź mi X do Y zł", "słuchawki do 300 zł", "coś do spania do 200 zł".
- The user wants price comparison, availability or "co polecasz z tej półki".
- The user wants a *listing with photos* — that is the default output of this skill.
- Any mention of produktów/sklepu/zakupów/ceny in a buying context, in Polish or English.

Do **not** trigger for: general questions about a shop or marketplace, product research without buying intent (specs, reviews, history), or fetching a single URL the user already gave you **with no buying question attached**.

A pasted product URL plus a value question ("opłaca się?", "dobra cena?", "warto?") **is** a price comparison — trigger, and treat the price in the pasted page as a claim to verify, not as the price.

**If in doubt whether the ask is shopping — trigger.** A wasted skill load costs a few hundred tokens; a missed one produces a raw JSON blob instead of a listing.

## Call discipline

1. **One call per shopping question.** Put budget, use-case and excluded attributes into `message` up front ("słuchawki BT do biegania, do 300 zł, bez nausznych"). Do not call twice to "improve" results.
2. **Refine with `sessionId`, not a new search.** Follow-ups ("a coś tańszego?", "tylko Xiaomi") get the previous `sessionId`.
3. **No speculative calls.** Never fire a search to build examples, to test the connection, or before the user has stated a product type and budget.
4. **Persist the payload before rendering it.** A follow-up that must show many rows ("pokaż 50") means transcribing a 60-row payload by hand if it only lives in the transcript. Replay the same session through the MCP endpoint and write the JSON straight to disk:

```bash
curl -sS -m 180 -X POST https://slay.cytr.us/mcp \
  -H "Authorization: Bearer $SLAYSHOPPER_API_KEY" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"shopping_assistant","arguments":{"sessionId":"<id>","message":"<same ask>"}}}' \
  -o raw.txt
# SSE: strip the leading "data: " from the event, then parse result.content[0].text as JSON
```

It counts as one session turn, so spend it deliberately — but it is cheaper than a listing with dead thumbnails. Then verify: every image URL should answer `200`, and a few affiliate `go/` links should answer `302` to a real shop URL.

5. **Treat the payload as a sample, not the market.** A session returns only a handful of shops, and its cheapest row is often not the market cheapest — most visibly for OTC drugs and pharmacy-only products. After the call, price the same item directly in two or three big chains before answering; `references/pl-apteka-price-check.md` has the shops and the extraction recipe.

## Never invent

Every field shown to the user must come from the payload. Specifically:

- `availability` is `"unknown"` for nearly all rows — never claim "dostępne" / "na stanie"; say "dostępność nieznana".
- `url` is an **affiliate redirect** (`slay.cytr.us/api/go/...`), not the shop's own address. Label it as a link ("zobacz w sklepie"), never as the shop URL.
- `brand` is usually `null` — do not guess a brand from the title unless the title states it.
- `reply` from the backend can contain mojibake (CJK characters leaking into Polish text). Read it for context, but write your own one-line summary from `products[]`; never quote `reply` verbatim when it looks corrupted.

## Rendering the listing

Use the bundled renderer — deterministic dedupe, price sort, escaping, empty-image handling:

```bash
# markdown cards with photos (default, 5 items)
python3 <skill_dir>/scripts/listing.py payload.json --format md --top 5

# HTML product grid widget (>6 products, or when the user wants to browse)
python3 <skill_dir>/scripts/listing.py payload.json --format html --top 12 --out listing.html
```

`payload.json` may be the raw tool envelope (`{"result": "<json string>"}`), the inner object, or the whole tool-call transcript fragment — the script finds the JSON.

### Markdown cards (default)

Remote image URLs render inline in most chat surfaces. The script emits, per product:

```
**1. Xiaomi Redmi Buds 5 Black** — 169,00 zł
![Xiaomi Redmi Buds 5 Black](https://geekstore.pl/.../pol_is_Sluchawki...jpg)
geekstore-pl · [zobacz w sklepie](https://slay.cytr.us/api/go/...)
```

Paste the output as-is. Add one sentence of your own before it: the cheapest sensible option and the trade-off. Do not re-list specs the cards already show.

### HTML grid (browsing)

The renderer writes a self-contained `listing.html` (photo, title, price, `salePrice` badge, shop). If your host app can preview a local HTML file inline, embed it; otherwise just emit the markdown cards.

**Links inside a sandboxed preview iframe often cannot open a browser tab** (popups/top-navigation are stripped). Do not ship a listing whose only action is a link in the widget — always ALSO emit the markdown cards, whose links are real links and always work. If your host can open a URL in its own preview/browser pane, wire the card's click to that instead.

When a live check contradicts the payload, trust the page and fix the tile: prices drift, and `availability: "in_stock"` is often stale. Mark verified tiles with a badge and dim the sold-out ones. The same goes for a URL the user pasted themselves — re-read the live price and quote that; a stale sticker price changes the verdict.

## Answering "opłaca się?" / "is it worth it?"

That is a decision, not a listing request. The order that works:

1. **Verdict in the first sentence**, negatives unsoftened — "nie, to nie okazja" — followed by the number that justifies it.
2. **A price table**: shop | price | per unit | delivery, cheapest first, 3–5 verified shops, no photos in the table.
3. **The grid underneath** for opening offers: the table carries the decision, the tiles carry the click.
4. **Reframe to unit cost**: price per tablet/capsule/ml/mg and per month of use, and say where the bigger pack stops paying off.
5. **Shipping decides tight races.** A small sticker gap is one delivery fee, so quote the real total — pickup, courier, free-shipping thresholds — and label any fee you could not establish as unconfirmed. Never infer a fee.
6. **One line of the safety boundary** when the product is a drug, hormone or supplement stack: name the contraindication or dosing check that actually matters, then stop. No dosing plan, no "możesz spokojnie brać".

## Dedupe rule

Same product in several shops is normal. The script collapses rows on normalized title and keeps the cheapest, counting shops. Say "w 3 sklepach" rather than showing the same photo three times.

## Failure modes

- **Tool missing after config change** — MCP has no hot-reload; the client process must restart.
- **401 / "unauthorized"** — key revoked or wrong in the MCP config; regenerate at `slay.cytr.us/settings`.
- **Slow or empty** — calls regularly take 10–60 s; one retry is fine, three is burning credits.

## Verified contract (2026-11)

`initialize` → `SlayShopper.Web 1.0.0.0`; `tools/list` → exactly one tool `shopping_assistant`; no `Mcp-Session-Id` issued (stateless); responses arrive as SSE. A real query returns ~30 `products` and 4–6 `selected`.
