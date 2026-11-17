"""Constants for the Vinted price research app."""

COOKIE_NAME = "access_token_web"
DEFAULT_BASE_URL = "https://www.vinted.com"
DEFAULT_PER_PAGE = 96
BRANDS_ENDPOINT = "/api/v2/brands"

ORDER_RELEVANCE = "relevance"
ORDER_PRICE_ASC = "price_low_to_high"
ORDER_PRICE_DESC = "price_high_to_low"
ORDER_NEWEST = "newest_first"

# Vinted condition labels -> numeric ``attribute_ids[status]`` IDs.
# Verified against the live API (Task 3): 6=new with tags, 1=new without
# tags, 2=very good, 3=good, 4=satisfactory, 7=not fully functional.
CONDITION_IDS = {
    "new_with_tags": 6,
    "new_without_tags": 1,
    "very_good": 2,
    "good": 3,
    "satisfactory": 4,
    "not_functional": 7,
}
