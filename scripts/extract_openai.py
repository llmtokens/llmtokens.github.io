import re
from typing import List

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - optional dependency
    BeautifulSoup = None

try:  # Support running as `python -m scripts.extract_openai` or directly.
    from scripts.pricing_lib import normalize_row
except ImportError:  # pragma: no cover - runtime convenience
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parent))
    from pricing_lib import normalize_row

PRICING_URL = "https://openai.com/api/pricing"


FALLBACK_MODELS = [
    ("gpt-4o", "input", "1M tokens", 5.0),
    ("gpt-4o", "output", "1M tokens", 15.0),
    ("gpt-4o-mini", "input", "1M tokens", 0.15),
    ("gpt-4o-mini", "output", "1M tokens", 0.6),
    ("gpt-4.1", "input", "1M tokens", 5.0),
    ("gpt-4.1", "output", "1M tokens", 15.0),
    ("o1-mini", "input", "1M tokens", 3.0),
    ("o1-mini", "output", "1M tokens", 12.0),
]


TOKEN_REGEX = re.compile(r"\$([0-9.]+)\s*/\s*(1[MK])\s*tokens", re.I)


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
    """Attempt to parse pricing tables from the OpenAI pricing page.

    The OpenAI page is dynamic, but the static HTML still contains multiple
    instances of price strings like "$5 / 1M tokens" near the model names. The
    parsing below keeps the approach lenient and falls back to the baked-in
    table when nothing is discovered.
    """

    if not BeautifulSoup:
        return []

    soup = BeautifulSoup(html, "html.parser")
    rows: List[dict] = []
    for section in soup.find_all(text=TOKEN_REGEX):
        match = TOKEN_REGEX.search(section)
        if not match:
            continue
        price = float(match.group(1))
        unit = "1M tokens" if match.group(2).upper() == "1M" else "1K tokens"
        # walk upwards to find the model heading near the price string
        model_name = None
        for parent in section.parents:
            heading = parent.find_previous(["h2", "h3", "h4"])
            if heading and heading.get_text(strip=True):
                model_name = heading.get_text(strip=True).split(" ")[0]
                break
        if not model_name:
            continue

        # Without clear input/output labeling, default to both directions.
        for usage in ("input", "output"):
            rows.append(
                normalize_row(
                    "openai",
                    model_name.lower(),
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
    parsed_rows: List[dict] = []
    if html:
        parsed_rows = parse_rows_from_html(html)

    if parsed_rows:
        return parsed_rows

    # fallback table when parsing fails
    return [
        normalize_row("openai", model, usage, unit, price, "USD", PRICING_URL)
        for model, usage, unit, price in FALLBACK_MODELS
    ]


if __name__ == "__main__":
    import json

    print(json.dumps(extract_rows(), indent=2))
