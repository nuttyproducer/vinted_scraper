"""Data models for the Vinted price research app."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ItemDTO:
    """A normalized Vinted item for display and export."""

    id: int
    title: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    brand: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    photo_url: Optional[str] = None
    listed_days_ago: Optional[float] = None
    url: Optional[str] = None
    description: Optional[str] = None


@dataclass
class BrandDTO:
    """A Vinted brand for the filter dropdown."""

    id: int
    title: str
