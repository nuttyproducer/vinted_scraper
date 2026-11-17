# Live verification findings (2026-11-17)

Verified against `https://www.vinted.com` with an anonymous session.

## Confirmed working

- `search_text` — keyword search.
- `attribute_ids[brand]` = numeric brand id — filters by brand.
- `price_from` / `price_to` — price range filter.
- `order=price_low_to_high` / `price_high_to_low` / `newest_first` — sort.
- Brand list endpoint: `GET /api/v2/brands` on the **www** host (`api_endpoint=False`).
  Response: `{"brands": [{"id", "title", "slug", ...}], "pagination", "code"}`.

## Not available (anonymous)

- **Listing timestamp.** Search results carry no `created_at_ts` (or any timestamp
  field). The item page HTML has no static timestamp, and the JSON item-details
  endpoint (`/api/v2/items/{id}/details`) returns 403. So `listed_days_ago` is
  always `None` for real results. Use `order=newest_first` for recency ordering.

## Corrections applied

- `BRANDS_ENDPOINT`: `/api/v2/catalog/brands` (404) → `/api/v2/brands` (www host).
- `ORDER_PRICE_ASC/DESC`: `price_asc`/`price_desc` (ignored by the API) →
  `price_low_to_high`/`price_high_to_low`.
- `CONDITION_IDS`: corrected to 6=new with tags, 1=new without tags, 2=very good,
  3=good, 4=satisfactory, 7=not fully functional (reverse-engineered from
  `attribute_ids[status]` filtering + `item_box.second_line`).
- Brand/size/condition are read from `item_box.first_line` (brand) and
  `item_box.second_line` (`"<size> · <condition>"`), not top-level
  `brand_title`/`size_title`.

## Other observations

- `photos` (plural) carries the full photo list (multi-photo), each with `full_size_url`.
- Currency is market-dependent (USD for `vinted.com`).
- Search results are not deterministic across requests (item order/ids vary).
