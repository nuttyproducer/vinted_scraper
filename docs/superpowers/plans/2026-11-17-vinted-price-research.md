# Vinted Price Research Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local FastAPI web app that searches Vinted, filters/sorts results, selects items by checkbox, and exports the selection to a styled PDF (summary table + per-item cards) with a listing-age indicator.

**Architecture:** A FastAPI backend wraps the existing `vinted_scraper` library (no library changes) and serves a single-page Vinted-like UI. PDF generation is server-side in ReportLab. Session strategy is anonymous-first with a pasted-cookie fallback persisted to a local file.

**Tech Stack:** Python ≥3.10, FastAPI, uvicorn, httpx, ReportLab, Jinja2, `vinted_scraper` (path dep), `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-17-vinted-price-research-design.md`

## Global Constraints

- Python ≥ 3.10 (the app); the library stays at its own ≥ 3.8 floor and is **not modified**.
- Tests use **`unittest`** (not pytest); run from `app/` with `uv run python -m unittest discover -s tests -t .`.
- No automated login; a pasted `access_token_web` cookie is the only credentialed path.
- Full type annotations on all app functions (match the library's style).
- App default base URL: `https://www.vinted.com`.
- Sort option `listed-longest` is applied client-side on the fetched results (the server `order` param only offers price/newest/relevance).

## Review Focus

1. **Item without `created_at_ts`** — must render "listed age" as empty, not crash. → test in Task 3.
2. **Item without a photo / failed photo download** — PDF must render a placeholder, not crash. → tests in Tasks 4 and 5.
3. **Blocked (403) on one item's enrich or photo during export** — the whole PDF must still be produced, that item degraded. → test in Task 5.
4. **Pasted cookie is empty/whitespace** — must be rejected, never overwrite a working anonymous session. → test in Task 2.
5. **`price=None` items in the summary sort** — must sort last (not break the low→high ordering). → test in Task 4.

---

### Task 1: Scaffold, models, and age helpers

**Files:**
- Create: `app/pyproject.toml`
- Create: `app/README.md`
- Create: `app/constants.py`
- Create: `app/models.py`
- Create: `app/age.py`
- Test: `app/tests/test_age.py`

**Interfaces:**
- Produces:
  - `models.ItemDTO` — `@dataclass` with fields: `id: int`, `title: str | None = None`, `price: float | None = None`, `currency: str | None = None`, `brand: str | None = None`, `size: str | None = None`, `condition: str | None = None`, `photo_url: str | None = None`, `listed_days_ago: float | None = None`, `url: str | None = None`, `description: str | None = None`.
  - `models.BrandDTO` — `@dataclass` with `id: int`, `title: str`.
  - `age.compute_listed_days(created_at_ts: float, now: float) -> float` — `(now - created_at_ts) / 86400.0`.
  - `age.format_listed_age(days: float | None) -> str` — `""` when `None`; `"just now"` when `< 1/24`; `"{int(days*24)} hours ago"` when `< 1`; `"{int(days)} days ago"` when `< 30`; `"{int(days//30)} months ago"` when `< 365`; else `"{int(days//365)} years ago"`.
  - `constants.COOKIE_NAME = "access_token_web"`, `DEFAULT_BASE_URL = "https://www.vinted.com"`, `DEFAULT_PER_PAGE = 48`, `BRANDS_ENDPOINT = "/api/v2/catalog/brands"`, `ORDER_RELEVANCE = "relevance"`, `ORDER_PRICE_ASC = "price_asc"`, `ORDER_PRICE_DESC = "price_desc"`, `ORDER_NEWEST = "newest_first"`, `CONDITION_IDS = {"new_with_tags": 6, "new_without_tags": 7, "very_good": 8, "good": 1, "satisfactory": 2}` (IDs verified live in Task 3).

- [ ] **Step 1: Write the failing test** in `app/tests/test_age.py`

```python
import unittest
from age import compute_listed_days, format_listed_age

class TestAge(unittest.TestCase):
    def test_compute_listed_days(self):
        self.assertEqual(compute_listed_days(1_000_000_000.0, 1_000_086_400.0), 1.0)

    def test_format_none(self):
        self.assertEqual(format_listed_age(None), "")

    def test_format_just_now(self):
        self.assertEqual(format_listed_age(0.01), "just now")

    def test_format_hours(self):
        self.assertEqual(format_listed_age(0.5), "12 hours ago")

    def test_format_days(self):
        self.assertEqual(format_listed_age(3.0), "3 days ago")

    def test_format_months(self):
        self.assertEqual(format_listed_age(45.0), "1 month ago")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && uv run python -m unittest tests.test_age -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'age'`.

- [ ] **Step 3: Create `app/pyproject.toml`** with this exact content, then `app/constants.py`, `app/models.py`, `app/age.py`, and `app/README.md` (README: one paragraph — how to `uv sync` and run `uv run uvicorn main:app --reload`).

```toml
[project]
name = "vinted-price-research"
version = "0.1.0"
description = "Local web app to search Vinted and export selected items to PDF."
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "reportlab>=4.2",
    "jinja2>=3.1",
    "httpx>=0.27",
    "vinted_scraper",
]

[tool.uv.sources]
vinted_scraper = { path = "..", editable = true }
```

- [ ] **Step 4: Run `uv sync` and the test to verify it passes**

Run: `cd app && uv sync && uv run python -m unittest tests.test_age -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/
git commit -m "feat: scaffold app with models and age helpers"
```

---

### Task 2: Session store

**Files:**
- Create: `app/session_store.py`
- Test: `app/tests/test_session_store.py`

**Interfaces:**
- Consumes: `constants.COOKIE_NAME` (Task 1) — only for the default filename, not used inside the class logic.
- Produces:
  - `session_store.DEFAULT_PATH: Path = Path.home() / ".vinted_research" / "session.json"`.
  - `session_store.SessionStore(path: Path = DEFAULT_PATH)` with `load(self) -> str | None`, `save(self, cookie: str) -> None` (raises `ValueError` when the cookie is empty or whitespace), `clear(self) -> None`.

- [ ] **Step 1: Write the failing test** in `app/tests/test_session_store.py`

```python
import tempfile, unittest
from pathlib import Path
from session_store import SessionStore

class TestSessionStore(unittest.TestCase):
    def _store(self, d):
        return SessionStore(Path(d) / "session.json")

    def test_load_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(self._store(d).load())

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            s = self._store(d); s.save("cookie123")
            self.assertEqual(s.load(), "cookie123")

    def test_save_empty_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                self._store(d).save("   ")

    def test_clear(self):
        with tempfile.TemporaryDirectory() as d:
            s = self._store(d); s.save("cookie123"); s.clear()
            self.assertIsNone(s.load())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && uv run python -m unittest tests.test_session_store -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'session_store'`.

- [ ] **Step 3: Implement `session_store.py`**

Write the `DEFAULT_PATH` constant and the `SessionStore` class. `save` stores the trimmed cookie string in a JSON file at `self.path` (create parent dirs); `load` returns the string or `None` if missing/corrupt; `clear` deletes the file. Wrap file reads in `try/except (OSError, ValueError)` and return `None`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && uv run python -m unittest tests.test_session_store -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/session_store.py app/tests/test_session_store.py
git commit -m "feat: add local session store for pasted cookie"
```

---

### Task 3: Vinted client adapter

**Files:**
- Create: `app/vinted_client.py`
- Test: `app/tests/test_vinted_client.py`

**Interfaces:**
- Consumes: `models.ItemDTO`, `models.BrandDTO`, `constants.*` (Tasks 1); `session_store` is NOT used here (session resolution takes `cookie` directly).
- Produces:
  - `vinted_client.VintedClient(baseurl: str = DEFAULT_BASE_URL, cookie: str | None = None, scraper: VintedScraper | None = None)`.
    - When `scraper` is given, store it. Otherwise construct `VintedScraper(baseurl=baseurl, session=VintedSession(cookies={COOKIE_NAME: cookie}) if cookie else None)`.
  - `VintedClient.search(self, query: str | None = None, brand_id: int | None = None, price_min: float | None = None, price_max: float | None = None, condition: str | None = None, order: str = ORDER_RELEVANCE, per_page: int = DEFAULT_PER_PAGE) -> list[ItemDTO]` — builds a `params` dict (`search_text`, `attribute_ids[brand]`, `price_from`, `price_to`, `attribute_ids[status]`, `order`, `per_page`, `page=1`) with `None`/empty keys omitted, calls `self._scraper.search(params)`, and maps each `VintedItem` to an `ItemDTO` (see mapping below).
  - `VintedClient.get_brands(self) -> list[BrandDTO]` — calls `self._scraper.curl(BRANDS_ENDPOINT, api_endpoint=True)`, normalises `data = resp if isinstance(resp, dict) else resp.json_data`, and maps `data["brands"]` (`{"id", "title"}` entries).
  - `VintedClient.enrich_item(self, item: ItemDTO) -> ItemDTO` — calls `self._scraper.item(str(item.id), [OgField.DESCRIPTION])`, copies `.description` onto `item`, returns it.
  - `vinted_client.download_photo(url: str) -> bytes | None` — `httpx.get(url).content`, returns `None` on any `httpx.HTTPError`.

  **Item mapping** (`VintedItem` → `ItemDTO`): `id`←`item.id`, `title`←`item.title`, `price`←`item.price`, `currency`←`item.currency`, `brand`←`item.brand_title`, `size`←`item.size_title`, `photo_url`← first `item.photos` entry's `full_size_url or url`, `url`←`item.url`, `listed_days_ago`←`compute_listed_days(item.json_data.get("created_at_ts"), time.time())` when `created_at_ts` is not `None` else `None`, `condition`← reverse lookup of `item.json_data.get("status_id")` in `CONDITION_IDS` else `None`.

- [ ] **Step 1: Write the failing tests** in `app/tests/test_vinted_client.py`

```python
import unittest
from unittest.mock import MagicMock, patch
import httpx
from vinted_scraper import OgField
from vinted_scraper.models import VintedItem
from models import ItemDTO
from vinted_client import VintedClient, download_photo

def make_item(**kw):
    data = {"id": 1, "title": "t", "price": {"amount": "5.0", "currency_code": "EUR"},
            "created_at_ts": 1_700_000_000.0, "photo": {"full_size_url": "https://x/i.jpg"},
            "brand_title": "Lego", "size_title": "M", "url": "https://x/item/1"}
    data.update(kw)
    return VintedItem(json_data=data)

class TestSearch(unittest.TestCase):
    def test_maps_fields_and_params(self):
        scraper = MagicMock()
        scraper.search.return_value = [make_item()]
        c = VintedClient(scraper=scraper)
        out = c.search(query="lego", brand_id=1, price_min=1.0, price_max=10.0, condition="new_with_tags", order="price_asc")
        params = scraper.search.call_args.kwargs["params"]
        self.assertEqual(params["search_text"], "lego")
        self.assertEqual(params["attribute_ids[brand]"], "1")
        self.assertEqual(params["price_from"], 1.0)
        self.assertEqual(params["price_to"], 10.0)
        self.assertEqual(params["attribute_ids[status]"], "6")
        self.assertEqual(params["order"], "price_asc")
        dto = out[0]
        self.assertEqual((dto.brand, dto.size, dto.price, dto.currency), ("Lego", "M", 5.0, "EUR"))
        self.assertIsNotNone(dto.listed_days_ago)

    def test_missing_created_at_ts(self):
        scraper = MagicMock()
        scraper.search.return_value = [make_item(created_at_ts=None)]
        out = VintedClient(scraper=scraper).search(query="x")
        self.assertIsNone(out[0].listed_days_ago)

class TestGetBrands(unittest.TestCase):
    def test_maps_brands(self):
        scraper = MagicMock()
        scraper.curl.return_value = {"brands": [{"id": 1, "title": "Lego"}, {"id": 2, "title": "Nike"}]}
        out = VintedClient(scraper=scraper).get_brands()
        self.assertEqual([(b.id, b.title) for b in out], [(1, "Lego"), (2, "Nike")])

class TestEnrich(unittest.TestCase):
    def test_sets_description(self):
        scraper = MagicMock()
        scraper.item.return_value = VintedItem(json_data={"id": 1, "description": "Great set"})
        dto = VintedClient(scraper=scraper).enrich_item(ItemDTO(id=1, title="x"))
        self.assertEqual(dto.description, "Great set")
        scraper.item.assert_called_once_with("1", [OgField.DESCRIPTION])

class TestSessionResolution(unittest.TestCase):
    def test_cookie_builds_session(self):
        c = VintedClient(cookie="abc123")
        self.assertEqual(c._scraper.session.cookies, {"access_token_web": "abc123"})

class TestDownloadPhoto(unittest.TestCase):
    @patch("vinted_client.httpx.get")
    def test_returns_bytes(self, get):
        get.return_value = MagicMock(content=b"img")
        self.assertEqual(download_photo("https://x/i.jpg"), b"img")

    @patch("vinted_client.httpx.get")
    def test_returns_none_on_error(self, get):
        get.side_effect = httpx.HTTPError("boom")
        self.assertIsNone(download_photo("https://x/i.jpg"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && uv run python -m unittest tests.test_vinted_client -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'vinted_client'`.

- [ ] **Step 3: Implement `vinted_client.py`**

Implement `VintedClient` and `download_photo` per the Interfaces. Import `VintedSession` from `vinted_scraper`, `OgField` from `vinted_scraper`, and `time`. For `download_photo`, use `httpx.get(url, timeout=10.0)` and return `None` on exception.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && uv run python -m unittest tests.test_vinted_client -v`
Expected: PASS.

- [ ] **Step 5: Live verification (manual, records §11 findings)**

Run this snippet once (anonymous session) and record the actual `created_at_ts` field name, brand endpoint shape, and `order`/condition values into a short `app/live_verification.md`, updating `constants.py` if they differ from the defaults:

```bash
cd app && uv run python -c "from vinted_client import VintedClient; c=VintedClient(); r=c.search(query='lego', per_page=5); print([(i.title, i.listed_days_ago) for i in r]); print(c.get_brands()[:3])"
```

Expected: real items print with non-`None` ages, or a documented block (proceed with library-documented param names and flag it).

- [ ] **Step 6: Commit**

```bash
git add app/vinted_client.py app/tests/test_vinted_client.py app/live_verification.md
git commit -m "feat: add Vinted client adapter with search, brands, enrich"
```

---

### Task 4: PDF builder

**Files:**
- Create: `app/pdf.py`
- Test: `app/tests/test_pdf.py`

**Interfaces:**
- Consumes: `models.ItemDTO` (Task 1), `age.format_listed_age` (Task 1).
- Produces:
  - `pdf._summary_rows(items: list[ItemDTO]) -> list[list[str]]` — header row `["Brand", "Title", "Price", "Condition", "Listed"]` followed by one row per item sorted by price low→high with `None` prices last; price cell is `f"{price} {currency}".strip()`; listed cell is `format_listed_age(listed_days_ago)`; empty string for missing `brand`/`condition`.
  - `pdf.build_pdf(items: list[ItemDTO], photos: dict[int, bytes]) -> bytes` — a ReportLab `SimpleDocTemplate` into a `BytesIO`, containing the summary `Table` (from `_summary_rows`) followed by one card per item (photo `Image` from `photos.get(item.id)` if present else a "No image" paragraph, then title/description/price/brand/size/condition/listed/url paragraphs). Returns the PDF bytes.

- [ ] **Step 1: Write the failing tests** in `app/tests/test_pdf.py`

```python
import unittest
from pdf import build_pdf, _summary_rows
from models import ItemDTO

class TestSummaryRows(unittest.TestCase):
    def test_sorted_price_asc_none_last(self):
        items = [ItemDTO(id=1, title="B", price=20.0, brand="X"),
                 ItemDTO(id=2, title="A", price=5.0, brand="Y"),
                 ItemDTO(id=3, title="C", price=None, brand="Z")]
        rows = _summary_rows(items)
        self.assertEqual(rows[0], ["Brand", "Title", "Price", "Condition", "Listed"])
        self.assertEqual([r[0] for r in rows[1:]], ["Y", "X", "Z"])

class TestBuildPdf(unittest.TestCase):
    def test_returns_pdf_bytes_without_photos(self):
        out = build_pdf([ItemDTO(id=1, title="A", price=5.0)], photos={})
        self.assertTrue(out.startswith(b"%PDF"))
        self.assertGreater(len(out), 100)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && uv run python -m unittest tests.test_pdf -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pdf'`.

- [ ] **Step 3: Implement `pdf.py`**

Implement `_summary_rows` and `build_pdf` per the Interfaces. Use `reportlab.platypus.SimpleDocTemplate`, `Table`, `Paragraph`, `Image`, `Spacer`, and `reportlab.lib.styles.getSampleStyleSheet`. Wrap photo bytes in `io.BytesIO` for `Image`. Sort key: `(item.price is None, item.price or 0)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && uv run python -m unittest tests.test_pdf -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/pdf.py app/tests/test_pdf.py
git commit -m "feat: add PDF builder (summary table + item cards)"
```

---

### Task 5: FastAPI app

**Files:**
- Create: `app/main.py`
- Test: `app/tests/test_main.py`

**Interfaces:**
- Consumes: `VintedClient` + `download_photo` (Task 3), `SessionStore` (Task 2), `build_pdf` (Task 4), `models.ItemDTO`.
- Produces:
  - `main.app` — a `fastapi.FastAPI` instance.
  - Module-level `main._client: VintedClient = VintedClient()` and `main._store: SessionStore = SessionStore()` (tests patch these).
  - Routes:
    - `GET /` → `FileResponse` of `static/index.html`.
    - `GET /api/search` (query params `q`, `brand`, `price_min`, `price_max`, `condition`, `order`) → `_client.search(...)` → `list[dict]` via `dataclasses.asdict`.
    - `GET /api/brands` → `_client.get_brands()` → `list[dict]`.
    - `POST /api/session` (body `{"cookie": str}`) → `_store.save(cookie)`, rebuild `_client = VintedClient(cookie=cookie)`, return `{"ok": True}`; on `ValueError` return 400.
    - `POST /api/export` (body `{"items": [<ItemDTO json>...]}`) → for each item: `enrich_item` in a `try/except` (ignore failure) and `download_photo(item.photo_url)`; build `photos` dict; `build_pdf` → `Response(content=..., media_type="application/pdf")`.

- [ ] **Step 1: Write the failing tests** in `app/tests/test_main.py`

```python
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
import main
from models import ItemDTO

class TestRoutes(unittest.TestCase):
    def test_index_served(self):
        r = TestClient(main.app).get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Vinted Price Research", r.text)

    def test_search_route(self):
        with patch.object(main, "_client") as m:
            m.search.return_value = [ItemDTO(id=1, title="A", price=5.0)]
            r = TestClient(main.app).get("/api/search", params={"q": "lego", "order": "price_asc"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()[0]["title"], "A")

    def test_session_route_rejects_empty(self):
        with patch.object(main, "_store") as store, patch.object(main, "_client"):
            r = TestClient(main.app).post("/api/session", json={"cookie": "  "})
        self.assertEqual(r.status_code, 400)

    def test_export_survives_blocked_enrich(self):
        with patch.object(main, "_client") as m, patch.object(main, "download_photo", return_value=None):
            m.enrich_item.side_effect = RuntimeError("blocked")
            m.enrich_item.return_value = ItemDTO(id=1, title="A")
            r = TestClient(main.app).post("/api/export", json={"items": [{"id": 1, "title": "A"}]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "application/pdf")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && uv run python -m unittest tests.test_main -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'main'` (and `static/index.html` missing).

- [ ] **Step 3: Implement `main.py`**

Implement `app`, `_client`, `_store`, and the five routes per the Interfaces. Map query params to `search()` kwargs: `q`→`query`, `brand`→`brand_id` (parse `int`, ignore when invalid), `price_min`/`price_max`→`float`, `condition`, `order`. For `POST /api/export`, use a Pydantic `BaseModel` with `items: list[dict]`, rebuild `ItemDTO(**d)` per dict, and add `time.sleep(0.2)` between items to stay polite. Return the PDF via `fastapi.Response`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && uv run python -m unittest tests.test_main -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/tests/test_main.py
git commit -m "feat: add FastAPI routes for search, brands, session, export"
```

---

### Task 6: Frontend UI

**Files:**
- Create: `app/static/index.html`
- Create: `app/static/style.css`
- Create: `app/static/app.js`
- Modify: `app/tests/test_main.py` (add an element-contract assertion)

**Interfaces:**
- Consumes: `/api/search`, `/api/brands`, `/api/export`, `/api/session` (Task 5).
- Produces: a static single-page UI whose `index.html` contains these element IDs (the JS↔HTML contract, asserted by the test): `#search-input`, `#brand-select`, `#price-min`, `#price-max`, `#condition-select`, `#order-select`, `#items-grid`, `#export-btn`, `#cookie-modal`, `#cookie-input`, `#cookie-save`.

- [ ] **Step 1: Write the failing test** (append to `app/tests/test_main.py`)

```python
class TestFrontendContract(unittest.TestCase):
    def test_index_has_contract_ids(self):
        r = TestClient(main.app).get("/")
        for elem in ["#search-input", "#brand-select", "#price-min", "#price-max",
                     "#condition-select", "#order-select", "#items-grid",
                     "#export-btn", "#cookie-modal", "#cookie-input", "#cookie-save"]:
            self.assertIn(f'id="{elem[1:]}"', r.text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && uv run python -m unittest tests.test_main.TestFrontendContract -v`
Expected: FAIL — `static/index.html` has none of those IDs (only the Task 5 placeholder/title).

- [ ] **Step 3: Implement `static/index.html`, `style.css`, `app.js`**

`index.html`: a `<title>Vinted Price Research</title>`, a search bar + filter panel (brand dropdown populated from `/api/brands`, price min/max, condition select, order select with `price_asc`/`price_desc`/`newest_first`/`relevance`), a `<div id="items-grid">` of cards each with a checkbox, a sticky `#export-btn` (label "Export N selected → PDF"), and a `#cookie-modal` with `#cookie-input` + `#cookie-save` and the copy-your-cookie instructions. `app.js`: fetch brands on load; on search render cards (photo, title, price+currency, brand, size, condition, `format_listed_age`-style "N days ago", a Vinted link); track checked IDs; "listed-longest" sorts the loaded cards client-side by age; `#export-btn` POSTs selected items to `/api/export` and triggers a download; on a 403/401 it shows the cookie modal, whose save POSTs `/api/session`. `style.css`: Vinted-like card grid (responsive, image-aspect-ratio box) — match Vinted's light neutral palette.

- [ ] **Step 4: Run the full test suite**

Run: `cd app && uv run python -m unittest discover -s tests -t . -v`
Expected: ALL PASS.

- [ ] **Step 5: Manual smoke (documented)**

Run: `cd app && uv run uvicorn main:app --reload`, open the printed URL, search "lego", verify filters/sort/selection/export and the cookie modal.

- [ ] **Step 6: Commit**

```bash
git add app/static app/tests/test_main.py
git commit -m "feat: add Vinted-like search and export UI"
```
