#!/usr/bin/env python3
"""Evaluate fine-tuned LoRA models on expanded bakeoff test set.

30 tests organized by tier:
  Tier 1 (1-10):  Core functionality — basic symbol subs, casing, paths, URLs
  Tier 2 (11-20): Compound patterns — multi-symbol, git commands, env vars, pipes
  Tier 3 (21-30): Known failure modes — dot dot, compound &&, numbers, fidelity
"""

import json
import time
from collections import defaultdict
from mlx_lm import load, generate

SYS = "Reconstruct the intended syntax from the dictated text. Output only the result."

tests = [
    # --- Tier 1: Core functionality ---
    {"id": 1, "cat": "symbols-basic", "dictated": "hello dash world", "expected": "hello-world"},
    {"id": 2, "cat": "symbols-basic", "dictated": "hello underscore world", "expected": "hello_world"},
    {"id": 3, "cat": "symbols-compound", "dictated": "dash dash verbose", "expected": "--verbose"},
    {"id": 4, "cat": "symbols-compound", "dictated": "equals equals equals", "expected": "==="},
    {"id": 5, "cat": "casing", "dictated": "camel case get user name", "expected": "getUserName"},
    {"id": 6, "cat": "casing", "dictated": "snake case total tokens generated", "expected": "total_tokens_generated"},
    {"id": 7, "cat": "casing", "dictated": "kebab case dark mode toggle", "expected": "dark-mode-toggle"},
    {"id": 8, "cat": "quotes", "dictated": "quote hello world quote", "expected": "\"hello world\""},
    {"id": 9, "cat": "paths", "dictated": "tilde slash dev slash talkie", "expected": "~/dev/talkie"},
    {"id": 10, "cat": "urls", "dictated": "HTTPS colon slash slash GitHub dot com slash arach slash talkie", "expected": "https://github.com/arach/talkie"},

    # --- Tier 2: Compound patterns ---
    {"id": 11, "cat": "mixed", "dictated": "git commit dash M quote fix latency quote", "expected": "git commit -m \"fix latency\""},
    {"id": 12, "cat": "mixed", "dictated": "export all caps API underscore KEY equals quote my dash key dash one two three quote", "expected": "export API_KEY=\"my-key-123\""},
    {"id": 13, "cat": "mixed", "dictated": "shebang slash bin slash bash", "expected": "#!/bin/bash"},
    {"id": 14, "cat": "mixed", "dictated": "docker run dash D dash P eighty eighty colon eighty eighty nginx", "expected": "docker run -d -p 8080:8080 nginx"},
    {"id": 15, "cat": "mixed", "dictated": "func camel case view did load open paren close paren", "expected": "func viewDidLoad()"},
    {"id": 16, "cat": "mixed", "dictated": "import open brace camel case use state close brace from single quote react single quote", "expected": "import { useState } from 'react'"},
    {"id": 17, "cat": "mixed", "dictated": "LS dash L A pipe grep dot swift", "expected": "ls -la | grep .swift"},
    {"id": 18, "cat": "mixed", "dictated": "GH PR create dash dash title quote fix inference latency quote dash dash body quote added TTFT tracking and latency instrumentation quote", "expected": "gh pr create --title \"fix inference latency\" --body \"Added TTFT tracking and latency instrumentation\""},
    {"id": 19, "cat": "identifiers", "dictated": "dot E N V dot local", "expected": ".env.local"},
    {"id": 20, "cat": "operators", "dictated": "open paren X close paren fat arrow open brace close brace", "expected": "(x) => {}"},

    # --- Tier 3: Known failure modes ---
    {"id": 21, "cat": "symbols-compound", "dictated": "dot dot slash dev", "expected": "../dev"},
    {"id": 22, "cat": "paths", "dictated": "dot dot slash dot dot slash dot dot slash", "expected": "../../../"},
    {"id": 23, "cat": "paths", "dictated": "dot dot slash configs", "expected": "../configs"},
    {"id": 24, "cat": "operators", "dictated": "A and and B and and C", "expected": "a && b && c"},
    {"id": 25, "cat": "numbers", "dictated": "zero point seven", "expected": "0.7"},
    {"id": 26, "cat": "numbers", "dictated": "one two seven dot zero dot zero dot one", "expected": "127.0.0.1"},
    {"id": 27, "cat": "mixed", "dictated": "git add dash A and and git commit dash M quote fix typo quote and and git push", "expected": "git add -A && git commit -m \"fix typo\" && git push"},
    {"id": 28, "cat": "spacing", "dictated": "no space git hub", "expected": "github"},
    {"id": 29, "cat": "brackets", "dictated": "open bracket colon colon dash one close bracket", "expected": "[::-1]"},
    {"id": 30, "cat": "mixed", "dictated": "dash dash temp zero point seven dash dash tokens five twelve", "expected": "--temp 0.7 --tokens 512"},
]

configs = [
    {
        "label": "QWEN 0.5B + LoRA v3",
        "model": "mlx-community/Qwen2.5-0.5B-Instruct-4bit",
        "adapter": "/Users/arach/dev/talkie/datasets/finetune/adapters/qwen-0.5b-lora-v3",
    },
]

all_results = {}

for cfg in configs:
    print(f"\n{'='*60}")
    print(f"  {cfg['label']}")
    print(f"{'='*60}\n")

    model, tokenizer = load(cfg["model"], adapter_path=cfg["adapter"])

    results = []
    total_time = 0
    for t in tests:
        messages = [
            {"role": "system", "content": SYS},
            {"role": "user", "content": t["dictated"]},
        ]

        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        start = time.perf_counter()
        got = generate(
            model, tokenizer, prompt=prompt,
            max_tokens=80, verbose=False
        )
        elapsed = time.perf_counter() - start
        total_time += elapsed

        got = got.strip()
        match = got == t["expected"]
        results.append({"id": t["id"], "cat": t["cat"], "match": match, "got": got})

        icon = "\033[32m✓\033[0m" if match else "\033[31m✗\033[0m"
        print(f"{icon} {str(t['id']).rjust(2)}. \"{t['dictated']}\"")
        print(f"     expected: {t['expected']}")
        if not match:
            print(f"     got:      {got}")

    correct = sum(1 for r in results if r["match"])
    pct = round(correct / len(results) * 100)
    avg_ms = round(total_time / len(results) * 1000)
    print(f"\nScore: {correct}/{len(results)} ({pct}%)")
    print(f"Avg latency: {avg_ms}ms per inference")
    all_results[cfg["label"]] = results

    # --- Per-category breakdown ---
    print(f"\nPer-category accuracy:")
    cat_results = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        cat_results[r["cat"]]["total"] += 1
        if r["match"]:
            cat_results[r["cat"]]["correct"] += 1

    for cat in sorted(cat_results.keys()):
        cr = cat_results[cat]
        cat_pct = round(cr["correct"] / cr["total"] * 100)
        bar = "█" * cr["correct"] + "░" * (cr["total"] - cr["correct"])
        print(f"  {cat:<20} {cr['correct']}/{cr['total']} ({cat_pct:>3}%) {bar}")

    # --- Per-tier breakdown ---
    print(f"\nPer-tier accuracy:")
    tiers = [
        ("Tier 1: Core", results[0:10]),
        ("Tier 2: Compound", results[10:20]),
        ("Tier 3: Failure modes", results[20:30]),
    ]
    for tier_name, tier_results in tiers:
        tier_correct = sum(1 for r in tier_results if r["match"])
        tier_pct = round(tier_correct / len(tier_results) * 100)
        print(f"  {tier_name:<25} {tier_correct}/{len(tier_results)} ({tier_pct}%)")

    del model, tokenizer

# Summary
print(f"\n{'='*60}")
print("  RESULTS SUMMARY")
print(f"{'='*60}\n")

for label, results in all_results.items():
    correct = sum(1 for r in results if r["match"])
    pct = round(correct / len(results) * 100)
    print(f"  {label}: {correct}/{len(results)} ({pct}%)")

print("\nBaselines:")
print("  LoRA v1 (240 train): 13/15 (87%)")
print("  LoRA v2 (474 train): 27/30 (90%)")
print("  Claude:              14/15 (93%)")
