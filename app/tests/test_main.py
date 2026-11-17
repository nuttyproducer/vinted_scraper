import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import main
from models import ItemDTO


class TestRoutes(unittest.TestCase):
    def test_index_served(self):
        r = TestClient(main.app).get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Vinted Price Research", r.text)

    def test_static_assets_served(self):
        client = TestClient(main.app)
        for path in ("/static/style.css", "/static/app.js"):
            r = client.get(path)
            self.assertEqual(r.status_code, 200, path)

    def test_search_route(self):
        with patch.object(main, "_get_client") as get_client:
            client = MagicMock()
            client.search.return_value = [ItemDTO(id=1, title="A", price=5.0)]
            get_client.return_value = client
            r = TestClient(main.app).get(
                "/api/search", params={"q": "lego", "order": "price_asc"}
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["items"][0]["title"], "A")
        self.assertFalse(r.json()["has_more"])

    def test_search_multiple_markets_sorted(self):
        with patch.object(main, "_get_client") as get_client:
            be = MagicMock()
            be.search.return_value = [ItemDTO(id=1, title="A", price=5.0)]
            nl = MagicMock()
            nl.search.return_value = [ItemDTO(id=2, title="B", price=3.0)]
            get_client.side_effect = [be, nl]
            r = TestClient(main.app).get(
                "/api/search",
                params={"q": "lego", "markets": "be,nl", "order": "price_low_to_high"},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual([i["id"] for i in r.json()["items"]], [2, 1])

    def test_session_route_rejects_empty(self):
        with patch.object(main, "_store") as store, patch.object(main, "_clients"):
            r = TestClient(main.app).post("/api/session", json={"cookie": "  "})
        self.assertEqual(r.status_code, 400)

    def test_export_survives_blocked_enrich(self):
        with patch.object(main, "_get_client") as get_client, patch.object(
            main, "download_photo", return_value=None
        ):
            client = MagicMock()
            client.enrich_item.side_effect = RuntimeError("blocked")
            get_client.return_value = client
            r = TestClient(main.app).post(
                "/api/export", json={"items": [{"id": 1, "title": "A"}]}
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "application/pdf")


class TestGetClient(unittest.TestCase):
    def test_uses_stored_cookie_for_base_url(self):
        with patch.object(main, "_clients", {}), patch.object(
            main, "_store"
        ) as store, patch.object(main, "VintedClient") as vc:
            store.load.return_value = "abc123"
            main._get_client(main.BASE_URL)
            vc.assert_called_once_with(baseurl=main.BASE_URL, cookie="abc123")

    def test_anonymous_for_other_market(self):
        with patch.object(main, "_clients", {}), patch.object(
            main, "_store"
        ) as store, patch.object(main, "VintedClient") as vc:
            store.load.return_value = "abc123"
            main._get_client("https://www.vinted.nl")
            vc.assert_called_once_with(baseurl="https://www.vinted.nl", cookie=None)

    def test_caches_clients(self):
        with patch.object(main, "_clients", {}), patch.object(
            main, "VintedClient"
        ) as vc:
            main._get_client("https://www.vinted.nl")
            main._get_client("https://www.vinted.nl")
            vc.assert_called_once()


class TestMergeItems(unittest.TestCase):
    def test_dedupes_and_sorts_price_asc(self):
        a = [ItemDTO(id=1, price=20.0), ItemDTO(id=2, price=5.0)]
        b = [ItemDTO(id=2, price=5.0), ItemDTO(id=3, price=10.0)]
        out = main._merge_items([a, b], "price_low_to_high")
        self.assertEqual([i.id for i in out], [2, 3, 1])

    def test_sorts_price_desc_none_last(self):
        a = [ItemDTO(id=1, price=20.0), ItemDTO(id=2, price=None)]
        out = main._merge_items([a], "price_high_to_low")
        self.assertEqual([i.id for i in out], [1, 2])


class TestFrontendContract(unittest.TestCase):
    def test_index_has_contract_ids(self):
        r = TestClient(main.app).get("/")
        for elem in [
            "#search-input",
            "#brand-select",
            "#price-min",
            "#price-max",
            "#condition-select",
            "#order-select",
            "#items-grid",
            "#export-btn",
            "#cookie-modal",
            "#cookie-input",
            "#cookie-save",
        ]:
            self.assertIn(f'id="{elem[1:]}"', r.text)
