import unittest
from unittest.mock import MagicMock, patch

import httpx
from vinted_scraper import OgField
from vinted_scraper.models import VintedItem

from models import ItemDTO
from vinted_client import VintedClient, download_photo


def make_item(**kw):
    data = {
        "id": 1,
        "title": "t",
        "price": {"amount": "5.0", "currency_code": "USD"},
        "created_at_ts": 1_700_000_000.0,
        "photos": [{"full_size_url": "https://x/i.jpg", "url": "https://x/i.jpg"}],
        "item_box": {"first_line": "LEGO", "second_line": "M · Very good"},
        "url": "https://x/item/1",
    }
    data.update(kw)
    return VintedItem(json_data=data)


class TestSearch(unittest.TestCase):
    def test_maps_fields_and_params(self):
        scraper = MagicMock()
        scraper.search.return_value = [make_item()]
        c = VintedClient(scraper=scraper)
        out = c.search(
            query="lego",
            brand_id=1,
            price_min=1.0,
            price_max=10.0,
            condition="new_with_tags",
            order="price_low_to_high",
        )
        params = scraper.search.call_args.kwargs["params"]
        self.assertEqual(params["search_text"], "lego")
        self.assertEqual(params["attribute_ids[brand]"], "1")
        self.assertEqual(params["price_from"], 1.0)
        self.assertEqual(params["price_to"], 10.0)
        self.assertEqual(params["attribute_ids[status]"], "6")
        self.assertEqual(params["order"], "price_low_to_high")
        dto = out[0]
        self.assertEqual(dto.brand, "LEGO")
        self.assertEqual(dto.size, "M")
        self.assertEqual(dto.condition, "Very good")
        self.assertEqual(dto.price, 5.0)
        self.assertEqual(dto.currency, "USD")
        self.assertIsNotNone(dto.listed_days_ago)

    def test_condition_ids(self):
        scraper = MagicMock()
        scraper.search.return_value = []
        c = VintedClient(scraper=scraper)
        c.search(condition="new_without_tags")
        self.assertEqual(
            scraper.search.call_args.kwargs["params"]["attribute_ids[status]"], "1"
        )
        c.search(condition="very_good")
        self.assertEqual(
            scraper.search.call_args.kwargs["params"]["attribute_ids[status]"], "2"
        )

    def test_missing_created_at_ts(self):
        scraper = MagicMock()
        scraper.search.return_value = [make_item(created_at_ts=None)]
        out = VintedClient(scraper=scraper).search(query="x")
        self.assertIsNone(out[0].listed_days_ago)

    def test_unknown_condition_ignored(self):
        scraper = MagicMock()
        scraper.search.return_value = []
        VintedClient(scraper=scraper).search(condition="bogus")
        params = scraper.search.call_args.kwargs["params"]
        self.assertNotIn("attribute_ids[status]", params)


class TestGetBrands(unittest.TestCase):
    def test_maps_brands(self):
        scraper = MagicMock()
        scraper.curl.return_value = {
            "brands": [{"id": 1, "title": "Lego"}, {"id": 2, "title": "Nike"}]
        }
        out = VintedClient(scraper=scraper).get_brands()
        self.assertEqual([(b.id, b.title) for b in out], [(1, "Lego"), (2, "Nike")])

    def test_calls_site_endpoint(self):
        scraper = MagicMock()
        scraper.curl.return_value = {"brands": []}
        VintedClient(scraper=scraper).get_brands()
        scraper.curl.assert_called_once_with("/api/v2/brands", api_endpoint=False)


class TestEnrich(unittest.TestCase):
    def test_sets_description(self):
        scraper = MagicMock()
        scraper.item.return_value = VintedItem(
            json_data={"id": 1, "description": "Great set"}
        )
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

    @patch("vinted_client.httpx.get")
    def test_returns_none_on_non_200(self, get):
        get.return_value.raise_for_status.side_effect = httpx.HTTPError("403")
        self.assertIsNone(download_photo("https://x/i.jpg"))
