# Vinted Price Research

A local web app to search Vinted, filter/sort results, select items by
checkbox, and export the selection to a styled PDF.

## Run

```bash
cd app
uv sync
uv run uvicorn main:app --reload
```

Then open the printed URL (default http://127.0.0.1:8000).

## Market

The app searches one Vinted market host. Pick yours with the
`VINTED_BASE_URL` environment variable (defaults to `https://www.vinted.com`,
the US market). For example, Belgium:

```bash
VINTED_BASE_URL=https://www.vinted.be uv run uvicorn main:app
```

## Tests

```bash
cd app
uv run python -m unittest discover -s tests -t .
```
