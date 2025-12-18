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

PRICING_URL = "https://ai.google.dev/pricing"

FALLBACK_MODELS = [
    ("gemini-1.5-pro", "input", "1M tokens", 7.0),
    ("gemini-1.5-pro", "output", "1M tokens", 21.0),
    ("gemini-1.5-flash", "input", "1M tokens", 0.35),
    ("gemini-1.5-flash", "output", "1M tokens", 1.05),
]


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
    for row in soup.find_all("tr"):
        text = row.get_text(" ", strip=True).lower()
        if not text or "gemini" not in text:
            continue
        parts = text.replace("$", "").replace("usd", "").split()
        prices = [float(p) for p in parts if p.replace(".", "", 1).isdigit()]
        if not prices:
            continue
        model_token = next((p for p in parts if p.startswith("gemini")), None)
        if not model_token:
            continue
        unit = "1M tokens"
        if "/1k" in text:
            unit = "1K tokens"
        for usage, price in zip(["input", "output"], prices[:2]):
            rows.append(
                normalize_row(
                    "gemini",
                    model_token,
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
        normalize_row("gemini", model, usage, unit, price, "USD", PRICING_URL)
        for model, usage, unit, price in FALLBACK_MODELS
    ]


if __name__ == "__main__":
    import json

    print(json.dumps(extract_rows(), indent=2))
