import base64
import unittest

from models import ItemDTO
from pdf import build_pdf, _prepare_photo, _summary_rows

PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


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

    def test_returns_pdf_bytes_with_photo(self):
        out = build_pdf(
            [ItemDTO(id=1, title="A", price=5.0)],
            photos={1: PNG_1x1},
        )
        self.assertTrue(out.startswith(b"%PDF"))
        self.assertGreater(len(out), 100)

    def test_prepare_photo_converts_to_jpeg(self):
        out = _prepare_photo(PNG_1x1)
        self.assertTrue(out.startswith(b"\xff\xd8"))

    def test_build_pdf_survives_bad_photo(self):
        out = build_pdf(
            [ItemDTO(id=1, title="A", price=5.0)],
            photos={1: b"<html>not an image</html>"},
        )
        self.assertTrue(out.startswith(b"%PDF"))
