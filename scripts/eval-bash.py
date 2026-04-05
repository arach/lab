#!/usr/bin/env python3
"""Evaluate fine-tuned models on the NL2Bash holdout set (604 entries).

Compares multiple adapters on the same held-out dictation → bash pairs.
"""

import json
import time
from collections import defaultdict
from mlx_lm import load, generate

SYS = "Reconstruct the intended syntax from the dictated text. Output only the result."

# Load test split
with open("datasets/finetune/bash/test.jsonl") as f:
    tests = []
    for line in f:
        msg = json.loads(line)["messages"]
        tests.append({
            "dictated": msg[1]["content"],
            "expected": msg[2]["content"],
        })

print(f"Loaded {len(tests)} held-out bash test entries\n")

configs = [
    {
        "label": "Qwen 0.5B + LoRA (bash)",
        "model": "mlx-community/Qwen2.5-0.5B-Instruct-4bit",
        "adapter": "datasets/finetune/adapters/qwen-0.5b-bash-v1",
    },
    {
        "label": "Qwen 1.5B + LoRA (bash)",
        "model": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        "adapter": "datasets/finetune/adapters/qwen-1.5b-bash-v1",
    },
]

all_results = {}

for cfg in configs:
    print(f"\n{'='*60}")
    print(f"  {cfg['label']}")
    print(f"{'='*60}\n")

    try:
        model, tokenizer = load(cfg["model"], adapter_path=cfg["adapter"])
    except Exception as e:
        print(f"  SKIPPED — {e}\n")
        continue

    results = []
    total_time = 0
    errors_shown = 0

    for i, t in enumerate(tests):
        messages = [
            {"role": "system", "content": SYS},
            {"role": "user", "content": t["dictated"]},
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        start = time.perf_counter()
        got = generate(model, tokenizer, prompt=prompt, max_tokens=120, verbose=False)
        elapsed = time.perf_counter() - start
        total_time += elapsed

        got = got.strip()
        match = got == t["expected"]
        results.append({
            "match": match,
            "got": got,
            "expected": t["expected"],
            "dictated": t["dictated"],
        })

        if not match and errors_shown < 30:
            icon = "\033[31m✗\033[0m"
            print(f"{icon} {i+1:>3}. \"{t['dictated']}\"")
            print(f"      expected: {t['expected']}")
            print(f"      got:      {got}")
            errors_shown += 1

    correct = sum(1 for r in results if r["match"])
    pct = round(correct / len(results) * 100, 1)
    avg_ms = round(total_time / len(results) * 1000)
    print(f"\nScore: {correct}/{len(results)} ({pct}%)")
    print(f"Avg latency: {avg_ms}ms")

    if errors_shown < sum(1 for r in results if not r["match"]):
        print(f"({sum(1 for r in results if not r['match'])} total errors, showing first {errors_shown})")

    all_results[cfg["label"]] = results
    del model, tokenizer

# Summary
print(f"\n{'='*60}")
print("  RESULTS SUMMARY")
print(f"{'='*60}\n")

for label, results in all_results.items():
    correct = sum(1 for r in results if r["match"])
    pct = round(correct / len(results) * 100, 1)
    print(f"  {label}: {correct}/{len(results)} ({pct}%)")

# Error analysis: categorize common failure patterns
if all_results:
    print(f"\n{'='*60}")
    print("  ERROR ANALYSIS (first model)")
    print(f"{'='*60}\n")

    first_results = list(all_results.values())[0]
    errors = [r for r in first_results if not r["match"]]

    # Categorize errors
    categories = defaultdict(list)
    for r in errors:
        got, exp = r["got"], r["expected"]
        if len(got) > len(exp) * 2:
            categories["hallucination"].append(r)
        elif got.lower() == exp.lower():
            categories["case_mismatch"].append(r)
        elif got.replace(" ", "") == exp.replace(" ", ""):
            categories["spacing"].append(r)
        elif abs(len(got) - len(exp)) <= 3:
            categories["minor_diff"].append(r)
        else:
            categories["structural"].append(r)

    for cat, items in sorted(categories.items(), key=lambda x: -len(x[1])):
        print(f"  {cat}: {len(items)}")
        for item in items[:3]:
            print(f"    \"{item['dictated'][:50]}...\"")
            print(f"      exp: {item['expected'][:60]}")
            print(f"      got: {item['got'][:60]}")
