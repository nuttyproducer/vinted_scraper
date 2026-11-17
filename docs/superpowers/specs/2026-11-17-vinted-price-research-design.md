# Vinted Price Research Tool — Design Spec

- **Date:** 2026-11-17
- **Status:** Draft (awaiting review)
- **Audience:** personal, single-user, local
- **Host repository:** `vinted_scraper` (this repo)

## 1. Overview

A local web application for researching Vinted prices to support reselling. The
user is launching their own webshop and needs to compare Vinted asking prices to
know what to charge. The tool lets them search Vinted like they would on the
site itself, filter and sort the results, tick the items they care about, and
export the selected items to a single, well-styled PDF.

The application **builds on the existing `vinted_scraper` library** — it does not
reimplement scraping. It reuses `VintedScraper.search()`, `enrich()`/`item()`,
and `curl()` for catalog calls, and adds the presentation (search/filter UI),
selection, listing-age analysis, and PDF generation on top.

## 2. Goals and non-goals

### Goals

- Search Vinted by keyword (title), with filters for brand, price, condition,
  and sort (price low↔high / high↔low / newest / listed-longest).
- Show, per item, how long it has been listed ("listed N days ago") as an
  overpricing signal.
- Select items via checkboxes and export the selection to a single PDF.
- Handle Vinted anti-bot blocks gracefully: try an anonymous session first,
  fall back to a user-supplied `access_token_web` cookie, with in-app
  instructions for copying that cookie.

### Non-goals (v1)

- Automated email/password login (anti-bot-protected and against Vinted ToS).
- Multi-photo galleries per item.
- Year/category attributes (kept as a stretch goal, see §12).
- Multi-user hosting or account features (favourites, inbox, purchases).
- Saved searches, CSV export, scheduled price tracking.

## 3. User flow

1. Open the app (local URL) and type a keyword (e.g. "LEGO Star Wars",
   "Nike jacket").
2. Optionally pick a brand from the dropdown, set price min/max, choose
   condition, and pick a sort order (default: price low→high).
3. Browse a grid of item cards, each showing photo, title, price, brand, size,
   condition, and "listed N days ago", with a checkbox.
4. Tick the items of interest.
5. Click "Export N selected → PDF" and download the generated PDF.

## 4. Architecture

A FastAPI backend wraps the existing `vinted_scraper` library and serves a
single-page HTML/JS frontend styled to resemble Vinted's search screen. PDF
generation happens server-side in Python.

```
┌──────────────────────────────────────────────────────┐
│  Browser (static/ — single-page UI, Vinted-like)      │
│  search bar · filters · item cards · checkboxes ·     │
│  export button · cookie-paste modal                   │
└──────────────────────────┬───────────────────────────┘
                           │ HTTP (JSON / PDF)
┌──────────────────────────▼───────────────────────────┐
│  FastAPI (main.py)                                    │
│  /api/search · /api/brands · /api/export · /api/session│
└──────────────────────────┬───────────────────────────┘
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────────┐   ┌──────────────────────────┐
│  VintedClient           │   │  pdf.py                  │
│  (adapter over          │   │  ReportLab: summary table│
│   VintedScraper)        │   │  + per-item cards        │
│  search/enrich/brands/  │   └──────────────────────────┘
│  age + session fallback │
└─────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────┐
│  vinted_scraper (existing library)                    │
│  VintedScraper / VintedWrapper / VintedSession        │
└──────────────────────────────────────────────────────┘
```

## 5. Project structure

A new top-level `app/` directory, sibling to `src/`, importing `vinted_scraper`
via the existing editable install. The library's contracts (100% coverage,
four-client parity) are left untouched.

```
app/
├── pyproject.toml          # fastapi, uvicorn, reportlab, jinja2, httpx
├── main.py                 # FastAPI app + routes
├── vinted_client.py        # adapter over VintedScraper: search, brands, enrich, age
├── session_store.py        # local ~/.vinted_research/session.json (cookie + fallback)
├── pdf.py                  # PDF builder (comparison table + cards)
├── static/                 # index.html, style.css, app.js  (Vinted-like UI)
└── tests/                  # test_client.py, test_pdf.py, test_api.py
```

## 6. Components

### 6.1 `vinted_client.py` — `VintedClient`

Thin adapter over `VintedScraper`. Owns the session identity and all anti-bot
handling.

- `search(**filters) -> list[ItemDTO]` — calls `VintedScraper.search()` with the
  resolved params and normalises each `VintedItem` into a plain `ItemDTO`
  (dataclass) carrying: `id`, `title`, `price`, `currency`, `brand`, `size`,
  `condition`, `photo_url`, `listed_days_ago`, `url`.
- `get_brands() -> list[BrandDTO]` — fetches the brand list via `curl()` (endpoint
  to be confirmed, §11) and maps `brand name → id` for filtering.
- `enrich_item(item_id) -> ItemDTO` — adds the description from the public item
  page via `enrich()`/`item()`.
- `compute_listed_days(created_at_ts) -> float` — `(now - created_at_ts) / 86400`,
  formatted as "N days ago"/"N hours ago".
- Session resolution: anonymous (library auto-fetch) first; if a pasted cookie is
  stored, construct `VintedSession(cookies={"access_token_web": ...})` and use it.

### 6.2 `session_store.py`

Persists a user-pasted cookie to `~/.vinted_research/session.json` (small, plain
JSON). Exposes `load()`, `save(cookie)`, and `clear()`. Used only for the
cookie-fallback path; the anonymous path stores nothing.

### 6.3 `pdf.py`

Pure function `build_pdf(items: list[ExportItem]) -> bytes` using **ReportLab**
(pure Python; installs cleanly on Windows). Two parts, in order:

1. **Summary table** — one row per selected item, columns
   `Brand / Title / Price / Condition / Listed`, sorted price low→high.
2. **Item cards** — one card per item with photo, title, description, price,
   brand, size, condition, seller, "listed N days ago", and the item URL. Cards
   may span multiple pages; no strict one-item-per-page constraint.

### 6.4 `main.py`

FastAPI routes:

- `GET /` — serves the UI.
- `GET /api/search?q=&brand=&price_min=&price_max=&condition=&sort=` — returns a
  JSON list of `ItemDTO`.
- `GET /api/brands` — returns the brand list for the dropdown.
- `POST /api/export` (body: the selected items as full JSON) — enriches each,
  downloads photos, and returns the PDF bytes.
- `POST /api/session` (body: cookie) — saves the pasted cookie and clears any
  cached anonymous session.

### 6.5 `static/`

Single-page UI: a Vinted-like search bar and filter panel, a responsive grid of
item cards (each with a checkbox), a sticky "Export N selected → PDF" bar, and a
cookie-paste modal containing the step-by-step guide for copying
`access_token_web` from browser dev tools.

## 7. Data flow

- **Search:** UI → `GET /api/search` → `VintedClient.search()` → normalised
  `ItemDTO` list → cards render.
- **Export:** UI → `POST /api/export` (the selected items as JSON) → per item:
  `enrich()` (description) + download photo bytes → `build_pdf()` → PDF bytes
  stream back to the browser.
- **Blocked:** any 403/401/captcha → UI banner "Vinted is blocking us — paste
  your cookie" → user pastes → saved via `session_store` → retry.

## 8. Anti-bot and session strategy

- Try an **anonymous** session first (the library auto-fetches `access_token_web`
  from the landing page).
- On a block, surface an actionable banner (never a crash) and direct the user to
  the cookie-paste modal with instructions.
- The only credentialed path is the user-supplied `access_token_web` cookie.
- **No automated login.**
- Throttle enrich/image requests politely (small delay) to avoid rate limits.

## 9. Error handling

- Blocks → actionable banner + cookie-paste fallback.
- Per-item `enrich()` failure → omit the description, keep the card.
- Per-item image download failure → placeholder box, keep the card.
- Any single item failing must not fail the whole export.

## 10. Testing strategy

Match repo conventions: `unittest` + `unittest.mock`, reusing `tests/samples/`
fixtures where possible.

- `tests/test_client.py` — mock `VintedScraper`; assert param mapping, session
  fallback, and `compute_listed_days` (hours/days boundaries).
- `tests/test_pdf.py` — fixture items → assert the PDF is produced and contains
  the summary table and card sections.
- `tests/test_api.py` — mock `VintedClient`; assert route responses (search JSON,
  brands, export content-type, session save).

## 11. Open verifications (spike before/during build)

To be confirmed with live calls against Vinted:

1. Exact `created_at_ts` field name in the search response (assumed present and
   passed through by `VintedJsonModel`).
2. The brand-catalog endpoint and response shape (for `get_brands()`).
3. Correct param names/values for brand, condition, and sort (`order`) — IDs vs
   names, and the exact low/high/newest/oldest values.
4. Which photo URL field yields a reliably downloadable image (`full_size_url`
   vs `url`).

## 12. Stretch goals (not in v1)

- **Year** attribute — depends on Vinted's per-category attributes (works for
  some catalogs, e.g. LEGO); wire up only where the catalog exposes it.
- Multi-photo galleries (requires a non-403-blocked source).
- Saved searches and CSV export.

## 13. Success criteria

- Searching, filtering (brand/price/condition/sort), and selecting items works
  locally against real Vinted.
- The listing-age indicator appears per item and is usable for spotting
  overpriced listings.
- The exported PDF contains the summary table (price low→high) and one card per
  selected item with photo, description, and link.
- A block is handled gracefully with a clear cookie-paste path and instructions.
