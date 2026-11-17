"""Adapter over ``vinted_scraper`` for the app's search/brand/enrich needs."""

import time

import httpx
from vinted_scraper import OgField, VintedScraper, VintedSession
from vinted_scraper.models import VintedItem

from age import compute_listed_days
from constants import (
    BRANDS_ENDPOINT,
    CONDITION_IDS,
    COOKIE_NAME,
    DEFAULT_BASE_URL,
    DEFAULT_PER_PAGE,
    ORDER_RELEVANCE,
)
from models import BrandDTO, ItemDTO


def download_photo(url: str) -> bytes | None:
    """Download image bytes, returning ``None`` on any failure."""
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        return resp.content
    except httpx.HTTPError:
        return None


class VintedClient:
    """Thin adapter over ``VintedScraper`` for the app's needs."""

    def __init__(
        self,
        baseurl: str = DEFAULT_BASE_URL,
        cookie: str | None = None,
        scraper: VintedScraper | None = None,
    ) -> None:
        if scraper is not None:
            self._scraper = scraper
        elif cookie is not None:
            self._scraper = VintedScraper(
                baseurl=baseurl,
                session=VintedSession(cookies={COOKIE_NAME: cookie}),
            )
        else:
            self._scraper = VintedScraper(baseurl=baseurl)

    def search(
        self,
        query: str | None = None,
        brand_id: int | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
        condition: str | None = None,
        order: str = ORDER_RELEVANCE,
        per_page: int = DEFAULT_PER_PAGE,
    ) -> list[ItemDTO]:
        params: dict = {"order": order, "per_page": per_page, "page": 1}
        if query:
            params["search_text"] = query
        if brand_id is not None:
            params["attribute_ids[brand]"] = str(brand_id)
        if price_min is not None:
            params["price_from"] = price_min
        if price_max is not None:
            params["price_to"] = price_max
        if condition is not None:
            status_id = CONDITION_IDS.get(condition)
            if status_id is not None:
                params["attribute_ids[status]"] = str(status_id)

        now = time.time()
        return [self._to_dto(item, now) for item in self._scraper.search(params=params)]

    def get_brands(self) -> list[BrandDTO]:
        resp = self._scraper.curl(BRANDS_ENDPOINT, api_endpoint=False)
        data = resp if isinstance(resp, dict) else resp.json_data
        return [
            BrandDTO(id=b["id"], title=b["title"])
            for b in data.get("brands", [])
        ]

    def enrich_item(self, item: ItemDTO) -> ItemDTO:
        enriched = self._scraper.item(str(item.id), [OgField.DESCRIPTION])
        item.description = enriched.description
        return item

    @staticmethod
    def _to_dto(item: VintedItem, now: float) -> ItemDTO:
        photo_url: str | None = None
        if item.photos:
            photo = item.photos[0]
            photo_url = photo.full_size_url or photo.url

        json_data = item.json_data or {}
        created_at_ts = json_data.get("created_at_ts")
        listed_days_ago = (
            compute_listed_days(created_at_ts, now)
            if created_at_ts is not None
            else None
        )

        brand = json_data.get("brand_title")
        size = json_data.get("size_title")
        condition: str | None = None
        box = json_data.get("item_box") or {}
        if box.get("first_line"):
            brand = box["first_line"]
        second = (box.get("second_line") or "").strip()
        if second:
            if "·" in second:
                parts = [p.strip() for p in second.split("·")]
                size = parts[0] if len(parts) > 1 else None
                condition = parts[-1] if parts else None
            else:
                condition = second

        return ItemDTO(
            id=item.id,
            title=item.title,
            price=item.price,
            currency=item.currency,
            brand=brand,
            size=size,
            condition=condition,
            photo_url=photo_url,
            listed_days_ago=listed_days_ago,
            url=item.url,
        )
