import json
from datetime import datetime
from pathlib import Path
from typing import List

try:
    from scripts import extract_anthropic, extract_gemini, extract_openai
    from scripts.pricing_lib import diff_snapshots, validate_rows, write_snapshot
except ImportError:  # pragma: no cover - runtime convenience
    import sys

    BASE = Path(__file__).resolve().parent
    sys.path.append(str(BASE))
    import extract_anthropic  # type: ignore
    import extract_gemini  # type: ignore
    import extract_openai  # type: ignore
    from pricing_lib import diff_snapshots, validate_rows, write_snapshot

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
HISTORY_DIR = DATA_DIR / "history"
DIFF_DIR = DATA_DIR / "diffs"


def collect_rows() -> List[dict]:
    rows = []
    rows.extend(extract_openai.extract_rows())
    rows.extend(extract_anthropic.extract_rows())
    rows.extend(extract_gemini.extract_rows())
    return rows


def main() -> None:
    print("Collecting rows from providers...")
    rows = collect_rows()
    print(f"Collected {len(rows)} rows. Validating...")
    rows = validate_rows(rows)

    previous_history = sorted(HISTORY_DIR.glob("prices.*.json"))
    snapshot_path = write_snapshot(rows, DATA_DIR)
    print(f"Snapshot written to {snapshot_path.relative_to(BASE_DIR)}")

    if previous_history:
        previous_path = previous_history[-1]
        diff = diff_snapshots(previous_path, snapshot_path)
        timestamp = snapshot_path.stem.split(".")[1]
        diff_path = DIFF_DIR / f"prices.{timestamp}.diff.json"
        diff_path.write_text(json.dumps({"generated_at": datetime.utcnow().isoformat() + "Z", "diff": diff}, indent=2))
        print(f"Diff written to {diff_path.relative_to(BASE_DIR)}")
    else:
        print("No previous snapshot to diff against.")


if __name__ == "__main__":
    main()
