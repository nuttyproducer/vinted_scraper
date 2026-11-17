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

## Tests

```bash
cd app
uv run python -m unittest discover -s tests -t .
```
