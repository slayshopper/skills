#!/usr/bin/env python3
"""Render SlayShopper `shopping_assistant` output as markdown cards or an HTML grid.

Accepts, in any nesting: the raw MCP tool envelope ({"result": "<json string>"}),
the MCP content-block form ({"content": [{"type": "text", "text": "..."}]}),
the inner result object, or a whole transcript fragment containing them.

Usage:
    listing.py payload.json --format md  --top 5
    listing.py payload.json --format html --top 12 --out listing.html
"""

from __future__ import annotations

import argparse
import html as _html
import json
import re
import sys
from pathlib import Path

CURRENCY = {"PLN": "zł", "EUR": "€", "USD": "$", "GBP": "£", "CZK": "Kč", "HUF": "Ft", "RON": "lei", "SEK": "kr", "NOK": "kr", "DKK": "kr", "CHF": "CHF", "UAH": "₴"}


def _try_json(text: str):
    text = text.strip()
    if not text or text[0] not in "{[":
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _find_object(text: str):
    """Scan for the first decodable JSON object that carries 'products'."""
    dec = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            value, _ = dec.raw_decode(text[match.start():])
        except ValueError:
            continue
        if isinstance(value, dict) and "products" in value:
            return value
        if isinstance(value, dict):
            found = unwrap(value)
            if found:
                return found
    return None


def unwrap(data):
    """Walk tool-envelope nesting until the object holding 'products'."""
    seen = 0
    while seen < 10:
        seen += 1
        if isinstance(data, str):
            data = _try_json(data)
            if data is None:
                return None
            continue
        if isinstance(data, dict):
            if "products" in data:
                return data
            for key in ("result", "structuredContent", "data"):
                if key in data:
                    data = data[key]
                    break
            else:
                content = data.get("content")
                if isinstance(content, list):
                    text = "".join(
                        part.get("text", "") for part in content if isinstance(part, dict)
                    )
                    data = text
                    continue
                return None
            continue
        return None
    return None


def load(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    candidate = unwrap(raw) or _try_json(raw) or _find_object(raw)
    if not isinstance(candidate, dict) or "products" not in candidate:
        raise SystemExit(f"no shopping payload with 'products' found in {path}")
    return candidate


def money(price, currency: str) -> str:
    if price is None:
        return "cena nieznana"
    symbol = CURRENCY.get(currency or "", "")
    if float(price).is_integer():
        body = f"{int(price)}"
    else:
        body = f"{price:.2f}".replace(".", ",")
    return f"{body} {symbol}" if symbol else body


def _key(item: dict) -> str:
    title = re.sub(r"[^a-z0-9 ]+", " ", (item.get("title") or "").lower())
    return " ".join(title.split())


def dedupe(items: list[dict]) -> list[dict]:
    """Collapse the same product across shops, keeping the cheapest and counting shops."""
    best: dict[str, dict] = {}
    shops: dict[str, set] = {}
    for item in items:
        key = _key(item) or item.get("id", "?")
        shops.setdefault(key, set()).add(item.get("shop") or "?")
        current = best.get(key)
        price = item.get("salePrice") or item.get("price")
        current_price = None if current is None else (current.get("salePrice") or current.get("price"))
        if current is None or (
            price is not None and (current_price is None or price < current_price)
        ):
            best[key] = item
    out = []
    for key, item in best.items():
        item = dict(item)
        item["_shops"] = len(shops[key])
        out.append(item)
    out.sort(key=lambda i: (i.get("salePrice") or i.get("price") or float("inf")))
    return out


def select(payload: dict, top: int) -> list[dict]:
    items = payload.get("products") or []
    rows = dedupe([i for i in items if isinstance(i, dict)])
    return rows[:top] if top else rows


def render_md(payload: dict, rows: list[dict]) -> str:
    lines: list[str] = []
    title = (payload.get("title") or "").strip()
    if title:
        lines.append(f"**{title}** — {len(rows)} pozycji")
        lines.append("")
    for index, item in enumerate(rows, 1):
        name = (item.get("title") or "?").strip()
        currency = item.get("currency") or "PLN"
        price = item.get("price")
        sale = item.get("salePrice")
        price_txt = money(price, currency)
        if sale is not None and price is not None and sale < price:
            price_txt = f"~~{price_txt}~~ **{money(sale, currency)}**"
        shop = item.get("shop") or "?"
        shops = item.get("_shops") or 1
        shop_txt = f"{shop} (+{shops - 1} inne sklepy)" if shops > 1 else shop
        lines.append(f"**{index}. {name}** — {price_txt}")
        image = (item.get("imageLink") or "").strip()
        if image:
            lines.append(f"![{name}]({image})")
        link = (item.get("url") or "").strip()
        tail = f"{shop_txt} · [zobacz w sklepie]({link})" if link else shop_txt
        lines.append(tail)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_html(payload: dict, rows: list[dict], heading: str | None = None) -> str:
    title = heading or (payload.get("title") or "Wyniki wyszukiwania").strip()
    cards = []
    for item in rows:
        name = (item.get("title") or "?").strip()
        currency = item.get("currency") or "PLN"
        price = item.get("price")
        sale = item.get("salePrice")
        price_txt = money(sale if (sale is not None and price is not None and sale < price) else price, currency)
        was = ""
        if sale is not None and price is not None and sale < price:
            was = f'<span class="was">{_html.escape(money(price, currency))}</span>'
        image = (item.get("imageLink") or "").strip()
        visual = (
            f'<img src="{_html.escape(image, quote=True)}" alt="{_html.escape(name, quote=True)}" loading="lazy">'
            if image
            else '<div class="noimg">brak zdjęcia</div>'
        )
        shop = item.get("shop") or "?"
        shops = item.get("_shops") or 1
        shop_txt = f"{shop} +{shops - 1}" if shops > 1 else shop
        link = (item.get("url") or "").strip()
        cta = (
            f'<a class="cta" href="{_html.escape(link, quote=True)}" target="_blank" rel="noopener">zobacz w sklepie</a>'
            if link
            else ""
        )
        cards.append(
            f'<article class="card"><div class="thumb">{visual}</div>'
            f'<h3>{_html.escape(name)}</h3>'
            f'<div class="meta"><span class="price">{price_txt}</span>{was}'
            f'<span class="shop">{_html.escape(shop_txt)}</span></div>{cta}</article>'
        )
    return f"""<!doctype html>
<meta charset="utf-8">
<style>
  h2 {{ font-size: 15px; font-weight: 600; margin: 0 0 10px; color: var(--foreground); }}
  .grid {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); }}
  .card {{ border: 1px solid var(--border); border-radius: 10px; padding: 10px; display: flex;
           flex-direction: column; gap: 8px; background: var(--card); }}
  .thumb {{ aspect-ratio: 1 / 1; display: flex; align-items: center; justify-content: center;
            overflow: hidden; border-radius: 6px; }}
  .thumb img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
  .noimg {{ font-size: 11px; color: var(--muted-foreground); }}
  h3 {{ font-size: 12.5px; line-height: 1.35; font-weight: 500; margin: 0; color: var(--foreground);
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 34px; }}
  .meta {{ display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; margin-top: auto; }}
  .price {{ font-size: 14px; font-weight: 600; color: var(--foreground); }}
  .was {{ font-size: 11px; text-decoration: line-through; color: var(--muted-foreground); }}
  .shop {{ font-size: 11px; color: var(--muted-foreground); }}
  .cta {{ font-size: 11.5px; color: var(--accent); text-decoration: none; }}
  .cta:hover {{ text-decoration: underline; }}
</style>
<h2>{_html.escape(title)}</h2>
<div class="grid">{''.join(cards)}</div>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("payload", type=Path, help="file with the tool output (json)")
    ap.add_argument("--format", choices=["md", "html"], default="md")
    ap.add_argument("--top", type=int, default=5, help="max products (0 = all)")
    ap.add_argument("--out", type=Path, help="write HTML here instead of stdout")
    ap.add_argument("--title", help="override the heading")
    args = ap.parse_args()

    payload = load(args.payload)
    rows = select(payload, args.top)
    if not rows:
        print("no products in payload", file=sys.stderr)
        return 1
    if args.format == "md":
        sys.stdout.write(render_md(payload, rows))
    else:
        doc = render_html(payload, rows, args.title)
        if args.out:
            args.out.write_text(doc, encoding="utf-8")
            print(f"{args.out} ({len(rows)} products)")
        else:
            sys.stdout.write(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
