#!/usr/bin/env python3
"""Evaluate fine-tuned Qwen2.5-1.5B on bash dictation → syntax task.

Runs inference on test examples, then applies post-processing heuristics
to catch common failure modes (repetition loops, casing). Reports raw vs
corrected accuracy and categorizes all failures.

Usage:
    python datasets/finetune/eval_bash.py [--n 630] [--max-tokens 256]
"""

import json
import re
import argparse
import random
import time
from pathlib import Path
from difflib import SequenceMatcher

import mlx.core as mx
from mlx_lm import load, generate


# ---------------------------------------------------------------------------
# Post-processing heuristics
# ---------------------------------------------------------------------------

def fix_repetition(text: str) -> str:
    """Detect and truncate degenerate repetition loops.

    Strategy: find the shortest repeating unit (2-20 chars) that occurs 3+
    times consecutively, then keep just the first occurrence in context.

    Examples:
        "echo {} {}. {}. {}. {}. ..." → "echo {} {}"
        "ls -la -la -la"              → "ls -la"
    """
    # Look for a repeated pattern: (unit)(separator + unit){2,}
    # The separator is typically ". " or " " or nothing
    for unit_len in range(2, min(25, len(text) // 3 + 1)):
        for start in range(len(text) - unit_len * 3):
            unit = text[start:start + unit_len]
            if not unit.strip():
                continue
            # Count consecutive repeats of this unit starting at `start`
            count = 1
            pos = start + unit_len
            while pos + unit_len <= len(text) and text[pos:pos + unit_len] == unit:
                count += 1
                pos += unit_len
            # Also try with ". " separator (common in repetition bugs)
            if count < 3:
                count = 1
                pos = start + unit_len
                for sep in [". ", " ", ", "]:
                    count_sep = 1
                    pos_sep = start + unit_len
                    while (pos_sep + len(sep) + unit_len <= len(text)
                           and text[pos_sep:pos_sep + len(sep)] == sep
                           and text[pos_sep + len(sep):pos_sep + len(sep) + unit_len] == unit):
                        count_sep += 1
                        pos_sep += len(sep) + unit_len
                    if count_sep > count:
                        count = count_sep
                        pos = pos_sep

            if count >= 3:
                # Truncate: keep everything before the repetition + one instance
                return text[:start + unit_len].rstrip(". ,")

    return text


def fix_casing(predicted: str, dictated: str) -> str:
    """Normalize casing for flags and common arguments.

    Heuristic: bash flags (single char after -) are usually lowercase.
    But some are legitimately uppercase (-R, -N, -I, -P, -L, -S, -E, -H).
    When the model preserves dictated casing but the expected is different,
    we lowercase single-char flags that aren't in the "commonly uppercase" set.

    Also: filename/path arguments that are ALL CAPS in dictation but would
    typically be lowercase in practice get lowercased.
    """
    # Common uppercase flags that should stay uppercase
    UPPERCASE_FLAGS = set("RNIPLSEHOCGFXVDWBZAMUTJKQY")
    # Actually, almost any letter can be an uppercase flag depending on the command.
    # The real issue is: when someone dictates "dash I H", is it -iH or -ih or -I -H?
    # We can't solve this purely with heuristics — it's ambiguous.
    #
    # Simpler approach: if pred.lower() == expected.lower(), treat as case-insensitive match.
    # For production: just lowercase the output when the dictation uses capital letters
    # for what are clearly spoken letter names, not acronyms.
    #
    # For eval purposes, we just detect case-only differences and flag them.
    return predicted  # Don't auto-correct — just detect (see classify_result_corrected)


def postprocess(text: str, dictated: str) -> tuple[str, list[str]]:
    """Apply all post-processing heuristics. Returns (corrected_text, applied_fixes)."""
    fixes = []
    result = text

    # 1. Repetition guard
    fixed = fix_repetition(result)
    if fixed != result:
        fixes.append("repetition_truncated")
        result = fixed

    # 2. Strip trailing whitespace / dots from repetition artifacts
    result = result.rstrip(". ")
    if result != text.rstrip():
        if "repetition_truncated" not in fixes:
            fixes.append("trailing_cleanup")

    return result, fixes


def is_case_only_diff(a: str, b: str) -> bool:
    """Check if two strings differ only in letter casing."""
    return a.lower() == b.lower() and a != b


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_result(predicted: str, expected: str) -> str:
    pred = " ".join(predicted.strip().split())
    exp = " ".join(expected.strip().split())

    if pred == exp:
        return "exact"

    ratio = SequenceMatcher(None, pred, exp).ratio()
    if ratio >= 0.9:
        return "near"
    elif ratio >= 0.7:
        return "partial"
    else:
        return "wrong"


def classify_with_heuristics(predicted: str, expected: str) -> str:
    """Classify after considering case-insensitive matching."""
    pred = " ".join(predicted.strip().split())
    exp = " ".join(expected.strip().split())

    if pred == exp:
        return "exact"

    # Case-insensitive exact match
    if pred.lower() == exp.lower():
        return "exact_ci"

    ratio = SequenceMatcher(None, pred, exp).ratio()
    # Case-insensitive similarity
    ratio_ci = SequenceMatcher(None, pred.lower(), exp.lower()).ratio()

    if ratio >= 0.9 or ratio_ci >= 0.95:
        return "near"
    elif ratio >= 0.7 or ratio_ci >= 0.8:
        return "partial"
    else:
        return "wrong"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_test_data(path: str, n: int, seed: int = 42) -> list[dict]:
    examples = []
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            msgs = row["messages"]
            user_msg = next(m["content"] for m in msgs if m["role"] == "user")
            expected = next(m["content"] for m in msgs if m["role"] == "assistant")
            system = next(m["content"] for m in msgs if m["role"] == "system")
            examples.append({
                "system": system,
                "input": user_msg,
                "expected": expected,
            })
    random.seed(seed)
    if n < len(examples):
        examples = random.sample(examples, n)
    return examples


def build_prompt(tokenizer, system: str, user_input: str) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_input},
    ]
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=630, help="Number of test examples (630 = all)")
    parser.add_argument("--max-tokens", type=int, default=256, help="Max generation tokens")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    adapter_dir = base_dir / "adapters" / "qwen-1.5b-bash-v2-minimal"
    test_path = base_dir / "bash-v2" / "minimal" / "test.jsonl"

    print(f"Model: mlx-community/Qwen2.5-1.5B-Instruct-4bit + LoRA (iter 1000)")
    print(f"Test examples: {args.n}")
    print()

    # Load model
    print("Loading model...")
    t0 = time.time()
    model, tokenizer = load(
        "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        adapter_path=str(adapter_dir),
    )
    print(f"Loaded in {time.time() - t0:.1f}s\n")

    # Load test data
    examples = load_test_data(str(test_path), args.n, args.seed)
    print(f"Evaluating {len(examples)} examples...")
    print("=" * 70)

    # --- Run inference ---
    raw_results = {"exact": [], "near": [], "partial": [], "wrong": []}
    corrected_results = {"exact": [], "exact_ci": [], "near": [], "partial": [], "wrong": []}
    all_predictions = []
    total_time = 0
    heuristic_fixes = {"repetition_truncated": 0, "trailing_cleanup": 0, "case_fix": 0}

    for i, ex in enumerate(examples):
        prompt = build_prompt(tokenizer, ex["system"], ex["input"])

        t0 = time.time()
        response = generate(
            model, tokenizer, prompt=prompt,
            max_tokens=args.max_tokens,
            verbose=False,
        )
        elapsed = time.time() - t0
        total_time += elapsed

        raw_pred = response.strip()

        # Apply post-processing
        corrected_pred, fixes = postprocess(raw_pred, ex["input"])
        for f in fixes:
            heuristic_fixes[f] = heuristic_fixes.get(f, 0) + 1

        # Classify raw
        raw_cat = classify_result(raw_pred, ex["expected"])
        raw_results[raw_cat].append(True)

        # Classify with heuristics (post-processing + case-insensitive)
        corr_cat = classify_with_heuristics(corrected_pred, ex["expected"])
        corrected_results[corr_cat].append(True)

        entry = {
            "input": ex["input"],
            "expected": ex["expected"],
            "raw_pred": raw_pred,
            "corrected_pred": corrected_pred,
            "raw_cat": raw_cat,
            "corrected_cat": corr_cat,
            "fixes": fixes,
            "time": elapsed,
        }
        all_predictions.append(entry)

        # Progress + inline failure reporting
        status = "✓" if corr_cat in ("exact", "exact_ci") else "≈" if corr_cat == "near" else "~" if corr_cat == "partial" else "✗"
        if (i + 1) % 50 == 0:
            running_acc = sum(1 for p in all_predictions if p["corrected_cat"] in ("exact", "exact_ci", "near")) / len(all_predictions) * 100
            print(f"[{i+1:3d}/{len(examples)}] {status} — running accuracy: {running_acc:.1f}% ({elapsed:.1f}s)")
        elif corr_cat in ("wrong",):
            print(f"[{i+1:3d}/{len(examples)}] {status} ({elapsed:.1f}s)")
            print(f"  IN:  {ex['input'][:90]}")
            print(f"  EXP: {ex['expected'][:90]}")
            print(f"  GOT: {corrected_pred[:90]}")

    # === SUMMARY ===
    n_total = len(examples)
    print()
    print("=" * 70)
    print("RESULTS — RAW (no post-processing)")
    print("=" * 70)
    for cat in ["exact", "near", "partial", "wrong"]:
        count = len(raw_results[cat])
        pct = count / n_total * 100
        label = {"exact": "Exact match", "near": "Near (>90%)", "partial": "Partial (70-90%)", "wrong": "Wrong (<70%)"}[cat]
        print(f"  {label:25s}: {count:3d} / {n_total} ({pct:.1f}%)")
    raw_acc = (len(raw_results["exact"]) + len(raw_results["near"])) / n_total * 100
    print(f"  {'Effective accuracy':25s}: {raw_acc:.1f}%")

    print()
    print("=" * 70)
    print("RESULTS — WITH HEURISTICS (repetition guard + case-insensitive)")
    print("=" * 70)
    for cat in ["exact", "exact_ci", "near", "partial", "wrong"]:
        count = len(corrected_results[cat])
        pct = count / n_total * 100
        label = {
            "exact": "Exact match",
            "exact_ci": "Exact (case-insensitive)",
            "near": "Near (>90%)",
            "partial": "Partial (70-90%)",
            "wrong": "Wrong (<70%)",
        }[cat]
        print(f"  {label:25s}: {count:3d} / {n_total} ({pct:.1f}%)")

    corr_acc = (len(corrected_results["exact"]) + len(corrected_results["exact_ci"]) + len(corrected_results["near"])) / n_total * 100
    print(f"  {'Effective accuracy':25s}: {corr_acc:.1f}%")
    print(f"  {'Improvement':25s}: +{corr_acc - raw_acc:.1f}pp")

    print()
    print("=" * 70)
    print("HEURISTIC STATS")
    print("=" * 70)
    for name, count in heuristic_fixes.items():
        print(f"  {name:30s}: {count}")

    # Count case-only diffs
    case_only = sum(1 for p in all_predictions if is_case_only_diff(
        " ".join(p["corrected_pred"].strip().split()),
        " ".join(p["expected"].strip().split())
    ))
    print(f"  {'case_only_difference':30s}: {case_only}")

    print()
    print(f"  Avg inference time: {total_time / n_total:.2f}s/example")
    print(f"  Total time: {total_time:.0f}s")

    # === FAILURE DETAILS ===
    wrong = [p for p in all_predictions if p["corrected_cat"] == "wrong"]
    if wrong:
        print()
        print("=" * 70)
        print(f"WRONG ({len(wrong)} examples):")
        print("=" * 70)
        for j, r in enumerate(wrong):
            sim = SequenceMatcher(None, r["corrected_pred"].strip(), r["expected"].strip()).ratio()
            print(f"\n  [{j+1}] similarity={sim:.0%} fixes={r['fixes']}")
            print(f"  IN:  {r['input']}")
            print(f"  EXP: {r['expected']}")
            print(f"  GOT: {r['corrected_pred']}")

    partial = [p for p in all_predictions if p["corrected_cat"] == "partial"]
    if partial:
        print()
        print("=" * 70)
        print(f"PARTIAL ({len(partial)} examples):")
        print("=" * 70)
        for j, r in enumerate(partial):
            sim = SequenceMatcher(None, r["corrected_pred"].strip(), r["expected"].strip()).ratio()
            ci = " [case-only]" if is_case_only_diff(r["corrected_pred"].strip(), r["expected"].strip()) else ""
            print(f"\n  [{j+1}] similarity={sim:.0%}{ci} fixes={r['fixes']}")
            print(f"  IN:  {r['input']}")
            print(f"  EXP: {r['expected']}")
            print(f"  GOT: {r['corrected_pred']}")

    # === SAVE FULL RESULTS ===
    output_path = base_dir / "adapters" / "qwen-1.5b-bash-v2-minimal" / "eval_results.jsonl"
    with open(output_path, "w") as f:
        for p in all_predictions:
            f.write(json.dumps(p) + "\n")
    print(f"\nFull results saved to: {output_path}")


if __name__ == "__main__":
    main()
