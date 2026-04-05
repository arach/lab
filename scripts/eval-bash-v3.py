#!/usr/bin/env python3
"""Evaluate v3-trained models on the NL2Bash holdout set.

v3 uses "space as a word" model:
- The word "space" in dictation = literal space in output
- Everything else concatenates
- Casing qualifiers: "capital X", "all caps var"

Compares v3 to v2 baseline using the SAME bash commands but different
dictation conventions.
"""

import json
import re
import time
from collections import defaultdict
from mlx_lm import load, generate

# ── Prompts (must match training) ────────────────────────────────────────

SYSTEM_V3_MINIMAL = (
    "Reconstruct the intended syntax from the dictated text. "
    "The word 'space' means insert a literal space. "
    "Everything else concatenates. "
    "Output only the result."
)

SYSTEM_V2_MINIMAL = (
    "Reconstruct the intended syntax from the dictated text. "
    "Output only the result."
)


def ws_normalize(s: str) -> str:
    """Normalize whitespace for lenient comparison."""
    return re.sub(r'\s+', ' ', s.strip())


# ── Load test data ───────────────────────────────────────────────────────

# Load v3 test data
with open("datasets/finetune/bash-v3/minimal/test.jsonl") as f:
    v3_tests = []
    for line in f:
        msg = json.loads(line)["messages"]
        v3_tests.append({
            "dictated": msg[1]["content"],
            "expected": msg[2]["content"],
        })

print(f"Loaded {len(v3_tests)} held-out bash test entries (v3 converter)\n")

configs = [
    {
        "label": "v3: 1.5B + space-as-word",
        "model": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        "adapter": "datasets/finetune/adapters/qwen-1.5b-bash-v3-minimal",
        "system": SYSTEM_V3_MINIMAL,
        "tests": v3_tests,
    },
]

# Optionally load v2 for comparison (same model, different adapter + data)
try:
    with open("datasets/finetune/bash-v2/minimal/test.jsonl") as f:
        v2_tests = []
        for line in f:
            msg = json.loads(line)["messages"]
            v2_tests.append({
                "dictated": msg[1]["content"],
                "expected": msg[2]["content"],
            })
    configs.append({
        "label": "v2: 1.5B + baseline",
        "model": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        "adapter": "datasets/finetune/adapters/qwen-1.5b-bash-v2-minimal",
        "system": SYSTEM_V2_MINIMAL,
        "tests": v2_tests,
    })
except FileNotFoundError:
    pass

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
    tests = cfg["tests"]

    for i, t in enumerate(tests):
        messages = [
            {"role": "system", "content": cfg["system"]},
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
        exact = got == t["expected"]
        ws_match = ws_normalize(got) == ws_normalize(t["expected"])
        case_match = got.lower() == t["expected"].lower()
        ws_case = ws_normalize(got).lower() == ws_normalize(t["expected"]).lower()

        results.append({
            "exact": exact,
            "ws_match": ws_match,
            "case_match": case_match,
            "ws_case": ws_case,
            "got": got,
            "expected": t["expected"],
            "dictated": t["dictated"],
        })

        if not exact and errors_shown < 25:
            tag = "~" if ws_match else "✗"
            color = "\033[33m" if ws_match else "\033[31m"
            print(f"{color}{tag}\033[0m {i+1:>3}. \"{t['dictated'][:60]}\"")
            print(f"      expected: {t['expected']}")
            print(f"      got:      {got}")
            errors_shown += 1

    exact_correct = sum(1 for r in results if r["exact"])
    ws_correct = sum(1 for r in results if r["ws_match"])
    wscase_correct = sum(1 for r in results if r["ws_case"])
    total = len(results)
    avg_ms = round(total_time / total * 1000)

    print(f"\n  Exact match:   {exact_correct}/{total} ({round(exact_correct/total*100, 1)}%)")
    print(f"  WS-normalized: {ws_correct}/{total} ({round(ws_correct/total*100, 1)}%)")
    print(f"  WS+case norm:  {wscase_correct}/{total} ({round(wscase_correct/total*100, 1)}%)")
    print(f"  Avg latency:   {avg_ms}ms")

    all_results[cfg["label"]] = results
    del model, tokenizer

# ── Summary ──────────────────────────────────────────────────────────────

print(f"\n{'='*60}")
print("  RESULTS SUMMARY")
print(f"{'='*60}\n")

print(f"  {'Model':<30} {'Exact':>8} {'WS-norm':>8} {'WS+case':>8}")
print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*8}")

for label, results in all_results.items():
    total = len(results)
    exact = sum(1 for r in results if r["exact"])
    ws = sum(1 for r in results if r["ws_match"])
    wsc = sum(1 for r in results if r["ws_case"])
    print(f"  {label:<30} {exact/total*100:>7.1f}% {ws/total*100:>7.1f}% {wsc/total*100:>7.1f}%")

# ── Error Categories ─────────────────────────────────────────────────────

for label, results in all_results.items():
    print(f"\n{'='*60}")
    print(f"  ERROR CATEGORIES — {label}")
    print(f"{'='*60}\n")

    errors = [r for r in results if not r["exact"]]

    cats = defaultdict(int)
    for r in errors:
        if r["ws_case"]:
            cats["spacing+case only"] += 1
        elif r["ws_match"]:
            cats["spacing only"] += 1
        elif r["case_match"]:
            cats["case only"] += 1
        elif len(r["got"]) > len(r["expected"]) * 2:
            cats["hallucination"] += 1
        elif abs(len(r["got"]) - len(r["expected"])) <= 3:
            cats["minor diff"] += 1
        else:
            cats["structural"] += 1

    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:<20} {count:>4}")
