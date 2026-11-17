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

The app searches one Vinted market host. It defaults to
`https://www.vinted.be` (Belgium, EUR). To use another European market, set the
`VINTED_BASE_URL` environment variable, e.g.:

```bash
VINTED_BASE_URL=https://www.vinted.nl uv run uvicorn main:app
```

Vinted is per-country — there is no single Europe-wide search — so pick the
country you want (`.be`, `.nl`, `.fr`, `.de`, `.it`, `.es`, …).

## Tests

```bash
cd app
uv run python -m unittest discover -s tests -t .
```
