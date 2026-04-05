#!/usr/bin/env python3
"""Convert syntax-reconstruction.json → train/valid/test JSONL for mlx_lm.

Uses stratified splitting by category so each split has proportional
category representation.
"""

import json
import random
from collections import defaultdict
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from repo_paths import TRAINING_DATA_DIR, TRAINING_FINETUNE_DIR

SRC = TRAINING_DATA_DIR / "syntax-reconstruction.json"
OUT = TRAINING_FINETUNE_DIR

SYSTEM = "Reconstruct the intended syntax from the dictated text. Output only the result."

with open(SRC) as f:
    entries = json.load(f)["entries"]

random.seed(42)

# --- Stratified split by category ---
by_cat = defaultdict(list)
for e in entries:
    by_cat[e["cat"]].append(e)

train, valid, test = [], [], []

for cat, items in sorted(by_cat.items()):
    random.shuffle(items)
    n = len(items)
    train_end = int(n * 0.80)
    valid_end = int(n * 0.90)
    train.extend(items[:train_end])
    valid.extend(items[train_end:valid_end])
    test.extend(items[valid_end:])

# Shuffle within each split so categories are interleaved
random.shuffle(train)
random.shuffle(valid)
random.shuffle(test)

splits = {"train": train, "valid": valid, "test": test}

# Print category distribution
print("Category distribution:")
for cat in sorted(by_cat.keys()):
    total = len(by_cat[cat])
    t = sum(1 for e in train if e["cat"] == cat)
    v = sum(1 for e in valid if e["cat"] == cat)
    te = sum(1 for e in test if e["cat"] == cat)
    print(f"  {cat:<20} {total:>4} total → {t:>4} train / {v:>3} valid / {te:>3} test")

# --- Completions format ---
comp_dir = OUT / "completions"
comp_dir.mkdir(parents=True, exist_ok=True)

for split_name, split_entries in splits.items():
    path = comp_dir / f"{split_name}.jsonl"
    with open(path, "w") as f:
        for e in split_entries:
            line = {
                "prompt": e["dictated"],
                "completion": e["output"],
            }
            f.write(json.dumps(line) + "\n")
    print(f"  {split_name}: {len(split_entries)} → {path}")

# --- Chat format ---
chat_dir = OUT / "chat"
chat_dir.mkdir(parents=True, exist_ok=True)

for split_name, split_entries in splits.items():
    path = chat_dir / f"{split_name}.jsonl"
    with open(path, "w") as f:
        for e in split_entries:
            line = {
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": e["dictated"]},
                    {"role": "assistant", "content": e["output"]},
                ]
            }
            f.write(json.dumps(line) + "\n")
    print(f"  {split_name}: {len(split_entries)} → {path}")

n = len(entries)
print(f"\nTotal: {n} entries → {len(train)} train / {len(valid)} valid / {len(test)} test")
print(f"System prompt: \"{SYSTEM}\"")
print("Formats: completions (prompt/completion), chat (messages with system prompt)")
