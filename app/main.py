"""FastAPI app serving the Vinted price research UI and JSON/PDF endpoints."""

import os
import time
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from constants import (
    DEFAULT_BASE_URL,
    DEFAULT_MARKET,
    DEFAULT_PER_PAGE,
    MARKETS,
    ORDER_PRICE_ASC,
    ORDER_PRICE_DESC,
    ORDER_RELEVANCE,
)
from models import ItemDTO
from pdf import build_pdf
from session_store import SessionStore
from vinted_client import VintedClient, download_photo

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Vinted Price Research")
_store = SessionStore()
_clients: dict[str, VintedClient] = {}
BASE_URL = os.environ.get("VINTED_BASE_URL", DEFAULT_BASE_URL)


def _get_client(base_url: str) -> VintedClient:
    """Return a cached client for a market, cookie-aware only for the primary."""
    if base_url not in _clients:
        cookie = _store.load() if base_url == BASE_URL else None
        _clients[base_url] = VintedClient(baseurl=base_url, cookie=cookie)
    return _clients[base_url]


def _resolve_market_codes(markets: str | None) -> list[str]:
    codes = [c.strip() for c in (markets or "").split(",") if c.strip()]
    return codes or [DEFAULT_MARKET]


def _merge_items(results: list[list[ItemDTO]], order: str) -> list[ItemDTO]:
    """Merge per-market results, de-duping by id and re-sorting price orders."""
    merged: list[ItemDTO] = []
    seen: set[int] = set()
    for items in results:
        for item in items:
            if item.id not in seen:
                seen.add(item.id)
                merged.append(item)
    if order == ORDER_PRICE_ASC:
        merged.sort(key=lambda i: (i.price is None, i.price or 0.0))
    elif order == ORDER_PRICE_DESC:
        merged.sort(key=lambda i: (i.price is None, -(i.price or 0.0)))
    return merged


class ExportPayload(BaseModel):
    items: list[dict]


class SessionPayload(BaseModel):
    cookie: str


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/search")
def search(
    q: str | None = None,
    brand: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    condition: str | None = None,
    order: str = ORDER_RELEVANCE,
    page: int = 1,
    per_page: int = DEFAULT_PER_PAGE,
    markets: str | None = None,
):
    brand_id = None
    if brand:
        try:
            brand_id = int(brand)
        except ValueError:
            brand_id = None

    results: list[list[ItemDTO]] = []
    for code in _resolve_market_codes(markets):
        base_url = MARKETS.get(code)
        if not base_url:
            continue
        results.append(
            _get_client(base_url).search(
                query=q,
                brand_id=brand_id,
                price_min=price_min,
                price_max=price_max,
                condition=condition,
                order=order,
                page=page,
                per_page=per_page,
            )
        )

    items = _merge_items(results, order)
    has_more = any(len(r) == per_page for r in results)
    return {"items": [asdict(i) for i in items], "has_more": has_more}


@app.get("/api/brands")
def brands():
    return [asdict(b) for b in _get_client(BASE_URL).get_brands()]


@app.post("/api/session")
def save_session(payload: SessionPayload):
    cookie = payload.cookie.strip()
    if not cookie:
        raise HTTPException(status_code=400, detail="cookie must not be empty")
    _store.save(cookie)
    _clients.clear()
    return {"ok": True}


@app.post("/api/export")
def export(payload: ExportPayload):
    items = [ItemDTO(**d) for d in payload.items]
    photos: dict[int, bytes] = {}
    client = _get_client(BASE_URL)
    for item in items:
        try:
            client.enrich_item(item)
        except Exception:
            pass
        if item.photo_url:
            data = download_photo(item.photo_url)
            if data is not None:
                photos[item.id] = data
        time.sleep(0.2)
    pdf_bytes = build_pdf(items, photos)
    return Response(content=pdf_bytes, media_type="application/pdf")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
