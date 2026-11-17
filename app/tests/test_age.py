import unittest

from age import compute_listed_days, format_listed_age


class TestAge(unittest.TestCase):
    def test_compute_listed_days(self):
        self.assertEqual(compute_listed_days(1_000_000_000.0, 1_000_086_400.0), 1.0)

    def test_format_none(self):
        self.assertEqual(format_listed_age(None), "")

    def test_format_just_now(self):
        self.assertEqual(format_listed_age(0.01), "just now")

    def test_format_hours(self):
        self.assertEqual(format_listed_age(0.5), "12 hours ago")

    def test_format_days(self):
        self.assertEqual(format_listed_age(3.0), "3 days ago")

    def test_format_months(self):
        self.assertEqual(format_listed_age(45.0), "1 month ago")
