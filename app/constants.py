"""Constants for the Vinted price research app."""

COOKIE_NAME = "access_token_web"
DEFAULT_BASE_URL = "https://www.vinted.com"
DEFAULT_PER_PAGE = 48
BRANDS_ENDPOINT = "/api/v2/catalog/brands"

ORDER_RELEVANCE = "relevance"
ORDER_PRICE_ASC = "price_asc"
ORDER_PRICE_DESC = "price_desc"
ORDER_NEWEST = "newest_first"

# Vinted condition labels -> numeric ``attribute_ids[status]`` IDs.
# Verified against the live API in Task 3.
CONDITION_IDS = {
    "new_with_tags": 6,
    "new_without_tags": 7,
    "very_good": 8,
    "good": 1,
    "satisfactory": 2,
}
