#!/usr/bin/env python3
"""Compare v2 vs v3 on the full held-out test split (66 entries)."""

import json
import time
from collections import defaultdict
from mlx_lm import load, generate

SYS = "Reconstruct the intended syntax from the dictated text. Output only the result."

# Load test split
with open("datasets/finetune/chat/test.jsonl") as f:
    tests = []
    for line in f:
        msg = json.loads(line)["messages"]
        tests.append({
            "dictated": msg[1]["content"],
            "expected": msg[2]["content"],
        })

print(f"Loaded {len(tests)} held-out test entries\n")

configs = [
    {
        "label": "LoRA v2",
        "adapter": "datasets/finetune/adapters/qwen-0.5b-lora-v2",
    },
    {
        "label": "LoRA v3",
        "adapter": "datasets/finetune/adapters/qwen-0.5b-lora-v3",
    },
]

all_results = {}

for cfg in configs:
    print(f"\n{'='*60}")
    print(f"  {cfg['label']}")
    print(f"{'='*60}\n")

    model, tokenizer = load(
        "mlx-community/Qwen2.5-0.5B-Instruct-4bit",
        adapter_path=cfg["adapter"],
    )

    results = []
    total_time = 0
    for i, t in enumerate(tests):
        messages = [
            {"role": "system", "content": SYS},
            {"role": "user", "content": t["dictated"]},
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        start = time.perf_counter()
        got = generate(model, tokenizer, prompt=prompt, max_tokens=80, verbose=False)
        elapsed = time.perf_counter() - start
        total_time += elapsed

        got = got.strip()
        match = got == t["expected"]
        results.append({"match": match, "got": got, "expected": t["expected"], "dictated": t["dictated"]})

        icon = "\033[32m✓\033[0m" if match else "\033[31m✗\033[0m"
        if not match:
            print(f"{icon} {i+1:>2}. \"{t['dictated']}\"")
            print(f"     expected: {t['expected']}")
            print(f"     got:      {got}")

    correct = sum(1 for r in results if r["match"])
    pct = round(correct / len(results) * 100, 1)
    avg_ms = round(total_time / len(results) * 1000)
    print(f"\nScore: {correct}/{len(results)} ({pct}%)")
    print(f"Avg latency: {avg_ms}ms")
    all_results[cfg["label"]] = results
    del model, tokenizer

# Head-to-head comparison
print(f"\n{'='*60}")
print("  HEAD TO HEAD")
print(f"{'='*60}\n")

v2 = all_results["LoRA v2"]
v3 = all_results["LoRA v3"]

v2_only = []  # v2 right, v3 wrong
v3_only = []  # v3 right, v2 wrong
both_wrong = []

for i in range(len(tests)):
    if v2[i]["match"] and not v3[i]["match"]:
        v2_only.append((i, tests[i], v3[i]["got"]))
    elif v3[i]["match"] and not v2[i]["match"]:
        v3_only.append((i, tests[i], v2[i]["got"]))
    elif not v2[i]["match"] and not v3[i]["match"]:
        both_wrong.append((i, tests[i], v2[i]["got"], v3[i]["got"]))

v2_correct = sum(1 for r in v2 if r["match"])
v3_correct = sum(1 for r in v3 if r["match"])

print(f"LoRA v2: {v2_correct}/{len(tests)} ({round(v2_correct/len(tests)*100,1)}%)")
print(f"LoRA v3: {v3_correct}/{len(tests)} ({round(v3_correct/len(tests)*100,1)}%)")

if v2_only:
    print(f"\nv2 correct, v3 wrong ({len(v2_only)}):")
    for i, t, got in v2_only:
        print(f"  {i+1}. \"{t['dictated']}\" → expected \"{t['expected']}\" got \"{got}\"")

if v3_only:
    print(f"\nv3 correct, v2 wrong ({len(v3_only)}):")
    for i, t, got in v3_only:
        print(f"  {i+1}. \"{t['dictated']}\" → expected \"{t['expected']}\" got \"{got}\"")

if both_wrong:
    print(f"\nBoth wrong ({len(both_wrong)}):")
    for i, t, v2_got, v3_got in both_wrong:
        print(f"  {i+1}. \"{t['dictated']}\"")
        print(f"      expected: \"{t['expected']}\"")
        print(f"      v2:       \"{v2_got}\"")
        print(f"      v3:       \"{v3_got}\"")
