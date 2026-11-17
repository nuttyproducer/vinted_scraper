import tempfile
import unittest
from pathlib import Path

from session_store import SessionStore


class TestSessionStore(unittest.TestCase):
    def _store(self, d):
        return SessionStore(Path(d) / "session.json")

    def test_load_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(self._store(d).load())

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            s = self._store(d)
            s.save("cookie123")
            self.assertEqual(s.load(), "cookie123")

    def test_save_empty_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                self._store(d).save("   ")

    def test_clear(self):
        with tempfile.TemporaryDirectory() as d:
            s = self._store(d)
            s.save("cookie123")
            s.clear()
            self.assertIsNone(s.load())
