from typing import List

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - optional dependency
    BeautifulSoup = None

try:
    from scripts.pricing_lib import normalize_row
except ImportError:  # pragma: no cover - runtime convenience
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parent))
    from pricing_lib import normalize_row

PRICING_URL = "https://www.anthropic.com/pricing"

FALLBACK_MODELS = [
    ("claude-3-opus", "input", "1M tokens", 15.0),
    ("claude-3-opus", "output", "1M tokens", 75.0),
    ("claude-3.5-sonnet", "input", "1M tokens", 3.0),
    ("claude-3.5-sonnet", "output", "1M tokens", 15.0),
    ("claude-3-haiku", "input", "1M tokens", 0.25),
    ("claude-3-haiku", "output", "1M tokens", 1.25),
]


TOKEN_ROW_CLASSNAMES = ["pricing-table-row", "pricing-table__row"]


def fetch_html() -> str | None:
    if not requests:
        return None
    try:
        resp = requests.get(PRICING_URL, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def parse_rows_from_html(html: str) -> List[dict]:
    if not BeautifulSoup:
        return []

    soup = BeautifulSoup(html, "html.parser")
    rows: List[dict] = []

    # Anthropic renders prices inside table-looking divs; keep parsing flexible.
    for row in soup.find_all("tr") + soup.find_all("div", class_=TOKEN_ROW_CLASSNAMES):
        text = row.get_text(" ", strip=True).lower()
        if not text:
            continue
        if "claude" not in text:
            continue
        unit = "1M tokens"
        if "/1k" in text:
            unit = "1K tokens"
        parts = text.replace("$", "").replace("usd", "").split()
        prices = [float(p) for p in parts if p.replace(".", "", 1).isdigit()]
        if not prices:
            continue
        model_name = "claude"
        for token in text.split():
            if token.startswith("claude"):
                model_name = token
                break
        for usage, price in zip(["input", "output"], prices[:2]):
            rows.append(
                normalize_row(
                    "anthropic",
                    model_name,
                    usage,
                    unit,
                    price,
                    "USD",
                    PRICING_URL,
                    notes="Parsed from pricing page",
                )
            )
    return rows


def extract_rows() -> List[dict]:
    html = fetch_html()
    parsed = parse_rows_from_html(html) if html else []
    if parsed:
        return parsed

    return [
        normalize_row("anthropic", model, usage, unit, price, "USD", PRICING_URL)
        for model, usage, unit, price in FALLBACK_MODELS
    ]


if __name__ == "__main__":
    import json

    print(json.dumps(extract_rows(), indent=2))
