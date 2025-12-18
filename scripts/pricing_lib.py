import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

ALLOWED_CURRENCIES = {"USD"}
ALLOWED_UNITS = {
    "1K tokens",
    "1M tokens",
    "1K characters",
    "image",
    "request",
    "second",
    "session",
}
REQUIRED_FIELDS = [
    "provider",
    "model",
    "usage_type",
    "unit",
    "price",
    "currency",
    "source",
]


def normalize_row(
    provider: str,
    model: str,
    usage_type: str,
    unit: str,
    price: float,
    currency: str,
    source: str,
    notes: str | None = None,
) -> Dict[str, object]:
    return {
        "provider": provider,
        "model": model,
        "usage_type": usage_type,
        "unit": unit,
        "price": float(price),
        "currency": currency,
        "source": source,
        **({"notes": notes} if notes else {}),
    }


def validate_rows(rows: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    cleaned: List[Dict[str, object]] = []
    seen: set[Tuple[str, str, str, str]] = set()
    errors: List[str] = []
    for idx, row in enumerate(rows):
        for field in REQUIRED_FIELDS:
            if field not in row:
                errors.append(f"Row {idx} missing required field '{field}'")
        try:
            key = (
                str(row.get("provider")),
                str(row.get("model")),
                str(row.get("usage_type")),
                str(row.get("unit")),
            )
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"Row {idx} key construction failed: {exc}")
            continue

        if key in seen:
            errors.append(f"Duplicate key detected: {key}")
        seen.add(key)

        currency = row.get("currency")
        if currency not in ALLOWED_CURRENCIES:
            errors.append(
                f"Row {idx} has unsupported currency '{currency}'. Allowed: {sorted(ALLOWED_CURRENCIES)}"
            )

        unit = row.get("unit")
        if unit not in ALLOWED_UNITS:
            errors.append(
                f"Row {idx} has unsupported unit '{unit}'. Allowed: {sorted(ALLOWED_UNITS)}"
            )

        try:
            price_value = float(row.get("price"))
            if price_value < 0:
                errors.append(f"Row {idx} has negative price '{price_value}'")
        except (TypeError, ValueError):
            errors.append(f"Row {idx} price is not numeric: {row.get('price')}")

        cleaned.append(dict(row))

    if errors:
        raise ValueError("; ".join(errors))

    return cleaned


def write_snapshot(rows: List[Dict[str, object]], base_path: Path) -> Path:
    base_path.mkdir(parents=True, exist_ok=True)
    history_dir = base_path / "history"
    diff_dir = base_path / "diffs"
    history_dir.mkdir(parents=True, exist_ok=True)
    diff_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    latest_path = base_path / "prices.latest.json"
    snapshot_path = history_dir / f"prices.{timestamp}.json"

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "rows": rows,
    }
    snapshot_path.write_text(json.dumps(payload, indent=2))
    latest_path.write_text(json.dumps(payload, indent=2))

    return snapshot_path


def load_rows(path: Path) -> Dict[str, Dict[str, object]]:
    data = json.loads(path.read_text())
    rows = data.get("rows", [])
    mapping: Dict[str, Dict[str, object]] = {}
    for row in rows:
        key = canonical_key(row)
        mapping[key] = row
    return mapping


def canonical_key(row: Dict[str, object]) -> str:
    return ":".join(
        [
            str(row.get("provider")),
            str(row.get("model")),
            str(row.get("usage_type")),
            str(row.get("unit")),
        ]
    )


def diff_snapshots(old_path: Path, new_path: Path) -> Dict[str, object]:
    old_rows = load_rows(old_path) if old_path.exists() else {}
    new_rows = load_rows(new_path)

    added_keys = sorted(set(new_rows) - set(old_rows))
    removed_keys = sorted(set(old_rows) - set(new_rows))
    changed: Dict[str, Dict[str, object]] = {}
    for key in set(new_rows) & set(old_rows):
        if new_rows[key] != old_rows[key]:
            changed[key] = {
                "old": old_rows[key],
                "new": new_rows[key],
            }

    return {
        "added": {key: new_rows[key] for key in added_keys},
        "removed": {key: old_rows[key] for key in removed_keys},
        "changed": changed,
    }
