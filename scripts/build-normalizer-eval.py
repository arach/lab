#!/usr/bin/env python3
"""Build normalizer evaluation set from eval-fuzzy.json.

For each entry in eval-fuzzy.json:
  - Input: the 'dictated' field (possibly degraded)
  - Expected: the clean protocol format of the expected bash command

Uses bash_to_dictation() to convert expected bash → clean protocol.

Output: datasets/eval-normalizer.json
"""

import json
import sys
from pathlib import Path
from importlib import import_module
from collections import Counter

# Import the v3 converter (has hyphens in filename)
sys.path.insert(0, 'datasets')
btd = import_module('bash-to-dictation-v3')
bash_to_dictation = btd.bash_to_dictation


def main():
    eval_path = Path("datasets/eval-fuzzy.json")
    data = json.load(open(eval_path))

    result = []
    skipped = []

    for entry in data:
        dictated = entry['dictated']
        expected_bash = entry['expected']
        difficulty = entry.get('difficulty', 'unknown')
        category = entry.get('category', '')

        # Convert expected bash → clean protocol
        protocol = bash_to_dictation(expected_bash)
        if protocol is None:
            skipped.append({
                'expected': expected_bash,
                'difficulty': difficulty,
                'category': category,
            })
            continue

        result.append({
            'dictated': dictated,
            'expected_protocol': protocol,
            'expected_bash': expected_bash,
            'category': category,
            'difficulty': difficulty,
        })

    out_path = Path("datasets/eval-normalizer.json")
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)

    # Report
    diff_counts = Counter(e['difficulty'] for e in result)
    print(f"Built {len(result)} eval entries from {eval_path}")
    for diff in ['clean', 'fuzzy', 'natural', 'chaotic']:
        print(f"  {diff}: {diff_counts.get(diff, 0)}")

    if skipped:
        print(f"\nSkipped {len(skipped)} entries (bash_to_dictation returned None):")
        for s in skipped[:10]:
            print(f"  [{s['difficulty']}] [{s['category']}] {s['expected'][:60]}")

    print(f"\nWrote to {out_path}")

    # Verify: for clean entries, dictated should equal expected_protocol
    clean_entries = [e for e in result if e['difficulty'] == 'clean']
    mismatches = 0
    for e in clean_entries:
        if e['dictated'] != e['expected_protocol']:
            mismatches += 1
            if mismatches <= 3:
                print(f"\n  MISMATCH (clean):")
                print(f"    dictated:  {e['dictated'][:100]}")
                print(f"    protocol:  {e['expected_protocol'][:100]}")

    if mismatches:
        print(f"\n  {mismatches}/{len(clean_entries)} clean entries have dictated != expected_protocol")
    else:
        print(f"\n  All {len(clean_entries)} clean entries: dictated == expected_protocol ✓")


if __name__ == '__main__':
    main()
