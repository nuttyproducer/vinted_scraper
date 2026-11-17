import unittest

from constants import (
    BRANDS_ENDPOINT,
    CONDITION_IDS,
    ORDER_NEWEST,
    ORDER_PRICE_ASC,
    ORDER_PRICE_DESC,
    ORDER_RELEVANCE,
)


class TestConstants(unittest.TestCase):
    def test_live_verified_values(self):
        self.assertEqual(BRANDS_ENDPOINT, "/api/v2/brands")
        self.assertEqual(ORDER_PRICE_ASC, "price_low_to_high")
        self.assertEqual(ORDER_PRICE_DESC, "price_high_to_low")
        self.assertEqual(ORDER_NEWEST, "newest_first")
        self.assertEqual(ORDER_RELEVANCE, "relevance")
        self.assertEqual(CONDITION_IDS["new_with_tags"], 6)
        self.assertEqual(CONDITION_IDS["new_without_tags"], 1)
        self.assertEqual(CONDITION_IDS["very_good"], 2)
        self.assertEqual(CONDITION_IDS["good"], 3)
        self.assertEqual(CONDITION_IDS["satisfactory"], 4)
