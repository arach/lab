#!/usr/bin/env python3
"""Evaluate v2-trained models on the NL2Bash holdout set.

Compares minimal vs protocol prompts on the same held-out data.
Reports both exact match AND whitespace-normalized match.
"""

import json
import re
import time
from collections import defaultdict
from mlx_lm import load, generate

# ── Prompts (must match training) ────────────────────────────────────────

SYSTEM_MINIMAL = (
    "Reconstruct the intended syntax from the dictated text. "
    "Output only the result."
)

SYSTEM_PROTOCOL = (
    "Convert dictated syntax to code.\n"
    "Symbol words: dash(-) dot(.) slash(/) pipe(|) star(*) bang(!) "
    "hash(#) tilde(~) at(@) dollar($) percent(%) caret(^) equals(=) "
    "plus(+) colon(:) semicolon(;) underscore(_) comma(,) backslash(\\)\n"
    "Quotes: quote(\") single quote(') backtick(`)\n"
    "Brackets: open/close paren()  brace{}  bracket[]  angle<>\n"
    "Pairs: dash dash(--) and and(&&) pipe pipe(||) dot dot(..)\n"
    "Casing: camel case(camelCase) snake case(snake_case) "
    "kebab case(kebab-case) pascal case(PascalCase) all caps(ALLCAPS)\n"
    "Spacing: no space(join words)\n"
    "Letters after dash are flags: dash L A → -la\n"
    "Numbers spoken as words: forty two → 42\n"
    "Output only the result."
)


def ws_normalize(s: str) -> str:
    """Normalize whitespace for lenient comparison."""
    return re.sub(r'\s+', ' ', s.strip())


# ── Load test data ───────────────────────────────────────────────────────

# Use minimal test file (same data, different system prompt doesn't matter
# for loading — we override the system prompt at inference time)
with open("datasets/finetune/bash-v2/minimal/test.jsonl") as f:
    tests = []
    for line in f:
        msg = json.loads(line)["messages"]
        tests.append({
            "dictated": msg[1]["content"],
            "expected": msg[2]["content"],
        })

print(f"Loaded {len(tests)} held-out bash test entries (v2 converter)\n")

configs = [
    {
        "label": "1.5B + minimal prompt",
        "model": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        "adapter": "datasets/finetune/adapters/qwen-1.5b-bash-v2-minimal",
        "system": SYSTEM_MINIMAL,
    },
    {
        "label": "1.5B + protocol prompt",
        "model": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        "adapter": "datasets/finetune/adapters/qwen-1.5b-bash-v2-protocol",
        "system": SYSTEM_PROTOCOL,
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

if all_results:
    print(f"\n{'='*60}")
    print("  ERROR CATEGORIES (first model)")
    print(f"{'='*60}\n")

    first_results = list(all_results.values())[0]
    errors = [r for r in first_results if not r["exact"]]

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
