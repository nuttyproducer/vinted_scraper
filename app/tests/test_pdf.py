import unittest

from models import ItemDTO
from pdf import build_pdf, _summary_rows


class TestSummaryRows(unittest.TestCase):
    def test_sorted_price_asc_none_last(self):
        items = [
            ItemDTO(id=1, title="B", price=20.0, brand="X"),
            ItemDTO(id=2, title="A", price=5.0, brand="Y"),
            ItemDTO(id=3, title="C", price=None, brand="Z"),
        ]
        rows = _summary_rows(items)
        self.assertEqual(rows[0], ["Brand", "Title", "Price", "Condition", "Listed"])
        self.assertEqual([r[0] for r in rows[1:]], ["Y", "X", "Z"])


class TestBuildPdf(unittest.TestCase):
    def test_returns_pdf_bytes_without_photos(self):
        out = build_pdf([ItemDTO(id=1, title="A", price=5.0)], photos={})
        self.assertTrue(out.startswith(b"%PDF"))
        self.assertGreater(len(out), 100)
