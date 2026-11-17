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
