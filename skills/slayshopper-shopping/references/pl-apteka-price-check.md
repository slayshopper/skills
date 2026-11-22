# Polish pharmacy price check (OTC drugs, supplements)

Domain notes for pricing the same pack across Polish online pharmacies. Pharmacy prices on an
identical OTC pack spread by 20%+ routinely, and the SlayShopper rows cover only part of the market —
so the payload is a starting point, not the answer. Re-verify any policy value below before quoting it;
they change without notice.

## Shops worth checking directly

| Shop | Extraction | Notes |
|---|---|---|
| `gemini.pl` | `web_extract` works | Price sits right under the title; page also prints "X zł za 10 tabletek". Delivery: kurier / punkt odbioru / paczkomat |
| `doz.pl` | `web_extract` works | Prints "Cena za szt." and a "Formy dostawy" block with every fee; also lists the neighbour pack sizes (10 mg / 25 mg) with prices |
| `rosa24.pl` | browser only (client-rendered) | Price in `.product-card__price-card__prices__price--purchase`; expiry date and "Wysyłka jutro" shown on the page |
| `drmax.pl` | browser only | Cloudflare "Performing security verification" blocks `web_extract`; a chain, not a comparison site |
| `swiatleku.pl`, `nowafarmacja.pl`, `aptekacodzienna.pl` | `web_extract` mostly works | Long tail; usually mid-to-expensive |

Homeopathic/supplement chains (aptekawsieci, aptekacodzienna) frequently render prices in JS — when a
page returns no `\d+,\d\d zł` match, it is a render problem, not "no price".

## Fast extraction recipe

```python
web_extract([product_url], char_limit=6000)            # doz / gemini / swiatleku
re.findall(r"\d{1,3},\d{2}\s?zł", text)[:10]          # prices in order of appearance
```

In the browser, `js("(() => document.body.innerText)()")` then the same regex. Grab the shop's own
`og:image` (or the first `img` whose src matches the product name) for the listing tile, and confirm it
answers `200` before shipping the widget.

## Policy facts to re-check, not to assume

- `doz.pl`: pharmacy pickup 0 zł (min. order 25 zł), courier 11,99 zł, free InPost delivery from 79 zł — verified 2026-11.
- `gemini.pl`: "Wysyłka w 24h" badge; delivery priced per method, no flat free threshold on the product page.
- `rosa24.pl`: the "Wysyłka 0 zł" flag page (`/flags/wysylka-0zl`) lists **multi-packs only** — it does not mean
  free delivery on a normal order. `/zamowienia/dostawa` renders blank for a fresh session and add-to-cart may not
  register, so shipping cost usually stays unconfirmed: say so instead of guessing.

## Presenting the comparison

- Sort by sticker price, but add a per-unit column (`price / tablets`) and, when pack sizes differ, a per-mg
  column — that combination is what actually settles "which pack".
- A 10 mg and a 25 mg pack of the same drug are different products for the user, not just a quantity: quote both
  when the starting dose is below the strength of the cheap-per-mg pack.
- Say when a difference is within one delivery fee; that is the honest way to answer "opłaca się" for a single pack.
