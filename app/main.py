"""FastAPI app serving the Vinted price research UI and JSON/PDF endpoints."""

import os
import time
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from constants import DEFAULT_BASE_URL, DEFAULT_PER_PAGE, ORDER_RELEVANCE
from models import ItemDTO
from pdf import build_pdf
from session_store import SessionStore
from vinted_client import VintedClient, download_photo

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Vinted Price Research")
_store = SessionStore()
_client: VintedClient | None = None
BASE_URL = os.environ.get("VINTED_BASE_URL", DEFAULT_BASE_URL)


def _ensure_client() -> VintedClient:
    """Build the Vinted client lazily, reusing a stored cookie when present."""
    global _client
    if _client is None:
        cookie = _store.load()
        _client = (
            VintedClient(baseurl=BASE_URL, cookie=cookie)
            if cookie
            else VintedClient(baseurl=BASE_URL)
        )
    return _client


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
):
    brand_id = None
    if brand:
        try:
            brand_id = int(brand)
        except ValueError:
            brand_id = None
    items = _ensure_client().search(
        query=q,
        brand_id=brand_id,
        price_min=price_min,
        price_max=price_max,
        condition=condition,
        order=order,
        page=page,
        per_page=per_page,
    )
    return [asdict(i) for i in items]


@app.get("/api/brands")
def brands():
    return [asdict(b) for b in _ensure_client().get_brands()]


@app.post("/api/session")
def save_session(payload: SessionPayload):
    cookie = payload.cookie.strip()
    if not cookie:
        raise HTTPException(status_code=400, detail="cookie must not be empty")
    _store.save(cookie)
    global _client
    _client = VintedClient(baseurl=BASE_URL, cookie=cookie)
    return {"ok": True}


@app.post("/api/export")
def export(payload: ExportPayload):
    items = [ItemDTO(**d) for d in payload.items]
    photos: dict[int, bytes] = {}
    client = _ensure_client()
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
