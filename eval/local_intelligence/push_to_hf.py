#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from config import EXPORT_DIR, JSONL_EXPORT_PATH, MANIFEST_EXPORT_PATH, load_cards


def main() -> int:
    parser = argparse.ArgumentParser(description="Export local-intelligence eval cards for Hugging Face or notebook use.")
    parser.add_argument("--cards", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cards = load_cards(Path(args.cards)) if args.cards else load_cards()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for card in cards:
        payload = card.payload
        rows.append(
            {
                "id": payload["id"],
                "title": payload["title"],
                "tier": payload["tier"],
                "task": payload["prompt"]["task"],
                "system": payload["prompt"]["system"],
                "user_template": payload["prompt"]["user"],
                "test_input": payload["testCase"]["input"],
                "assertions": payload["testCase"]["assertions"],
            }
        )

    if args.dry_run:
        print(json.dumps({"rows": len(rows), "export_dir": str(EXPORT_DIR)}, indent=2))
        return 0

    JSONL_EXPORT_PATH.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    MANIFEST_EXPORT_PATH.write_text(
        json.dumps(
            {
                "version": 1,
                "rows": len(rows),
                "tiers": sorted({row["tier"] for row in rows}),
                "primary_file": str(JSONL_EXPORT_PATH.name),
            },
            indent=2,
        )
    )
    print(f"Wrote {len(rows)} rows to {JSONL_EXPORT_PATH}")
    print(f"Wrote manifest to {MANIFEST_EXPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
