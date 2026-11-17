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

    def test_static_assets_served(self):
        client = TestClient(main.app)
        for path in ("/static/style.css", "/static/app.js"):
            r = client.get(path)
            self.assertEqual(r.status_code, 200, path)

    def test_search_route(self):
        with patch.object(main, "_client") as m:
            m.search.return_value = [ItemDTO(id=1, title="A", price=5.0)]
            r = TestClient(main.app).get(
                "/api/search", params={"q": "lego", "order": "price_asc"}
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()[0]["title"], "A")

    def test_session_route_rejects_empty(self):
        with patch.object(main, "_store") as store, patch.object(main, "_client"):
            r = TestClient(main.app).post("/api/session", json={"cookie": "  "})
        self.assertEqual(r.status_code, 400)

    def test_export_survives_blocked_enrich(self):
        with patch.object(main, "_client") as m, patch.object(
            main, "download_photo", return_value=None
        ):
            m.enrich_item.side_effect = RuntimeError("blocked")
            m.enrich_item.return_value = ItemDTO(id=1, title="A")
            r = TestClient(main.app).post(
                "/api/export", json={"items": [{"id": 1, "title": "A"}]}
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "application/pdf")


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


class TestEnsureClient(unittest.TestCase):
    def test_uses_stored_cookie(self):
        with patch.object(main, "_client", None), patch.object(
            main, "_store"
        ) as store, patch.object(main, "VintedClient") as vc:
            store.load.return_value = "abc123"
            main._ensure_client()
            vc.assert_called_once_with(cookie="abc123")

    def test_anonymous_when_no_cookie(self):
        with patch.object(main, "_client", None), patch.object(
            main, "_store"
        ) as store, patch.object(main, "VintedClient") as vc:
            store.load.return_value = None
            main._ensure_client()
            vc.assert_called_once_with()
