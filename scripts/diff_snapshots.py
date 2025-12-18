import argparse
import json
from pathlib import Path

try:
    from scripts.pricing_lib import diff_snapshots
except ImportError:  # pragma: no cover - runtime convenience
    import sys

    sys.path.append(str(Path(__file__).resolve().parent))
    from pricing_lib import diff_snapshots


def main() -> None:
    parser = argparse.ArgumentParser(description="Diff two pricing snapshots")
    parser.add_argument("old", type=Path, help="Path to older snapshot JSON")
    parser.add_argument("new", type=Path, help="Path to newer snapshot JSON")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Optional file path to write the diff as JSON",
    )
    args = parser.parse_args()

    diff = diff_snapshots(args.old, args.new)
    if args.output:
        args.output.write_text(json.dumps(diff, indent=2))
    print(json.dumps(diff, indent=2))


if __name__ == "__main__":
    main()
