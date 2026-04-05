#!/usr/bin/env python3
"""Test harness for the procedural dictation protocol processor.

Tests the deterministic symbol/number/casing engine that converts
dictated protocol words into actual syntax — no LLM needed.

Covers:
  - Symbol mapping: "dash" → "-", "dot" → ".", "slash" → "/", etc.
  - Two-word symbols: "open paren" → "(", "dash dash" → "--", etc.
  - Three-word symbols: "two redirect ampersand" → "2>&"
  - Number words: "eight zero eight zero" → "8080", "forty two" → "42"
  - Casing: "capital A" → "A", "all caps POST" → "POST"
  - Casing directives: "camel case get user" → "getUser"
  - Spacing: "space" as explicit token separator
  - Full commands: git, docker, curl, ssh, etc.

Usage:
  python3 test-protocol-processor.py                    # run full suite
  python3 test-protocol-processor.py --category git     # filter by category
  python3 test-protocol-processor.py --verbose          # show all cases, not just errors
  python3 test-protocol-processor.py --unit             # run unit tests only (no eval file)
  python3 test-protocol-processor.py --eval FILE        # use custom eval file
"""

import json
import re
import sys
import time
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from repo_paths import EVAL_DIR

# Import processor
sys.path.insert(0, str(REPO_ROOT / "processor"))
from importlib import import_module
_proc = import_module("procedural-processor")
process_dictation = _proc.process_dictation
consume_number = _proc.consume_number
consume_casing = _proc.consume_casing
SYMBOLS = _proc.SYMBOLS
TWO_WORD_SYMBOLS = _proc.TWO_WORD_SYMBOLS
THREE_WORD_SYMBOLS = _proc.THREE_WORD_SYMBOLS


# ── Colors ──────────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ── Unit Tests ──────────────────────────────────────────────────────────
# These test individual features of the processor in isolation.

UNIT_TESTS = {
    "symbols_basic": [
        ("dash", "-"),
        ("dot", "."),
        ("slash", "/"),
        ("pipe", "|"),
        ("tilde", "~"),
        ("hash", "#"),
        ("at", "@"),
        ("dollar", "$"),
        ("percent", "%"),
        ("caret", "^"),
        ("ampersand", "&"),
        ("equals", "="),
        ("plus", "+"),
        ("colon", ":"),
        ("semicolon", ";"),
        ("underscore", "_"),
        ("comma", ","),
        ("backslash", "\\"),
        ("quote", '"'),
        ("backtick", "`"),
        ("star", "*"),
        ("bang", "!"),
        ("redirect", ">"),
    ],
    "symbols_synonyms": [
        ("minus", "-"),
        ("hyphen", "-"),
        ("period", "."),
        ("asterisk", "*"),
        ("hashtag", "#"),
    ],
    "two_word_symbols": [
        ("single quote", "'"),
        ("open paren", "("),
        ("close paren", ")"),
        ("open brace", "{"),
        ("close brace", "}"),
        ("open bracket", "["),
        ("close bracket", "]"),
        ("open angle", "<"),
        ("close angle", ">"),
        ("open curly", "{"),
        ("close curly", "}"),
        ("less than", "<"),
        ("question mark", "?"),
        ("dash dash", "--"),
        ("double dash", "--"),
        ("and and", "&&"),
        ("pipe pipe", "||"),
        ("dot dot", ".."),
        ("forward slash", "/"),
        ("back slash", "\\"),
        ("equals sign", "="),
        ("at sign", "@"),
        ("dollar sign", "$"),
        ("open parenthesis", "("),
        ("close parenthesis", ")"),
        ("new line", "\n"),
    ],
    "three_word_symbols": [
        ("two redirect ampersand", "2>&"),
    ],
    "numbers_single": [
        ("zero", "0"),
        ("one", "1"),
        ("five", "5"),
        ("nine", "9"),
        ("ten", "10"),
        ("twelve", "12"),
        ("nineteen", "19"),
    ],
    "numbers_compound": [
        ("twenty", "20"),
        ("forty two", "42"),
        ("ninety nine", "99"),
    ],
    "numbers_multiplier": [
        ("one hundred", "100"),
        ("three thousand", "3000"),
        ("five hundred", "500"),
    ],
    "numbers_digit_sequence": [
        ("one nine two", "192"),
        ("eight zero eight zero", "8080"),
        ("one two seven dot zero dot zero dot one", "127.0.0.1"),
        ("four four three", "443"),
    ],
    "casing_capital": [
        ("capital a", "A"),
        ("capital x", "X"),
        ("capital hello", "Hello"),
    ],
    "casing_all_caps": [
        ("all caps post", "POST"),
        ("all caps get", "GET"),
        ("all caps node", "NODE"),
    ],
    "casing_directives": [
        ("camel case get user profile", "getUserProfile"),
        ("snake case api key", "api_key"),
        ("pascal case my component", "MyComponent"),
        ("kebab case my component", "my-component"),
        ("screaming case max retries", "MAX_RETRIES"),
    ],
    "space_handling": [
        ("git space push", "git push"),
        ("ls space dash la", "ls -la"),
        ("a space b space c", "a b c"),
    ],
    "mixed_basic": [
        ("git space commit space dash m space quote hello quote", 'git commit -m "hello"'),
        ("echo space dollar all caps home", "echo $HOME"),
        ("cd space tilde slash projects", "cd ~/projects"),
        ("chmod space seven five five space script dot sh", "chmod 755 script.sh"),
    ],
    "append_redirect": [
        ("echo space hello space append space log dot txt", "echo hello >> log.txt"),
        ("cat space file space redirect space output", "cat file > output"),
    ],
}


def run_unit_tests(verbose=False):
    """Run isolated unit tests for each processor feature."""
    print(f"\n{BOLD}UNIT TESTS{RESET}")
    print("=" * 70)

    total = 0
    passed = 0
    failed_cases = []

    for group_name, cases in UNIT_TESTS.items():
        group_pass = 0
        group_total = len(cases)

        for dictated, expected in cases:
            total += 1
            got = process_dictation(dictated)

            # Normalize whitespace for comparison
            got_norm = re.sub(r'\s+', ' ', got.strip())
            exp_norm = re.sub(r'\s+', ' ', expected.strip())

            if got_norm == exp_norm:
                group_pass += 1
                passed += 1
                if verbose:
                    print(f"  {GREEN}PASS{RESET} [{group_name}] {dictated!r} → {got!r}")
            else:
                failed_cases.append((group_name, dictated, expected, got))
                print(f"  {RED}FAIL{RESET} [{group_name}] {dictated!r}")
                print(f"         expected: {expected!r}")
                print(f"         got:      {got!r}")

        if not verbose and group_pass == group_total:
            print(f"  {GREEN}PASS{RESET} {group_name}: {group_pass}/{group_total}")

    print(f"\n  Total: {passed}/{total} passed", end="")
    if failed_cases:
        print(f", {RED}{len(failed_cases)} failed{RESET}")
    else:
        print(f" {GREEN}(all pass){RESET}")

    return passed, total, failed_cases


def run_eval_tests(eval_file, category=None, verbose=False):
    """Run the processor against the eval dataset."""
    print(f"\n{BOLD}EVAL TESTS{RESET} — {eval_file}")
    print("=" * 70)

    with open(eval_file) as f:
        data = json.load(f)

    if category:
        data = [d for d in data if d.get("category", "") == category]
        print(f"  Filtered to category={category}: {len(data)} cases")

    total = len(data)
    exact = 0
    ws_match = 0
    ws_case_match = 0
    failed_cases = []
    by_category = defaultdict(lambda: {"exact": 0, "total": 0})
    timings = []

    for d in data:
        dictated = d["dictated"]
        expected = d["expected"]
        cat = d.get("category", "unknown")

        t0 = time.perf_counter()
        got = process_dictation(dictated)
        elapsed_us = (time.perf_counter() - t0) * 1_000_000
        timings.append(elapsed_us)

        got_ws = re.sub(r'\s+', ' ', got.strip())
        exp_ws = re.sub(r'\s+', ' ', expected.strip())

        is_exact = got == expected
        is_ws = got_ws == exp_ws
        is_wsc = got_ws.lower() == exp_ws.lower()

        by_category[cat]["total"] += 1

        if is_exact:
            exact += 1
            by_category[cat]["exact"] += 1
            if verbose:
                print(f"  {GREEN}PASS{RESET} [{cat}] {dictated[:60]}")
        else:
            failed_cases.append({
                "category": cat,
                "dictated": dictated,
                "expected": expected,
                "got": got,
                "ws_match": is_ws,
                "wsc_match": is_wsc,
            })
            if is_ws:
                ws_match += 1
                if verbose:
                    print(f"  {YELLOW}WS{RESET}   [{cat}] whitespace diff only")
            elif is_wsc:
                ws_case_match += 1

        if is_ws:
            ws_match += (1 if is_exact else 0)  # already counted
        if is_wsc:
            ws_case_match += (1 if is_exact else 0)

    # Recount properly
    ws_match = sum(1 for d in data if re.sub(r'\s+', ' ', process_dictation(d["dictated"]).strip()) == re.sub(r'\s+', ' ', d["expected"].strip()))
    ws_case_match = sum(1 for d in data if re.sub(r'\s+', ' ', process_dictation(d["dictated"]).strip()).lower() == re.sub(r'\s+', ' ', d["expected"].strip()).lower())

    # Summary
    print(f"\n  {BOLD}ACCURACY{RESET}")
    print(f"    Exact match:      {exact}/{total} ({exact/total*100:.1f}%)")
    print(f"    Whitespace-norm:  {ws_match}/{total} ({ws_match/total*100:.1f}%)")
    print(f"    WS+case-norm:     {ws_case_match}/{total} ({ws_case_match/total*100:.1f}%)")

    # Timing
    if timings:
        timings.sort()
        median = timings[len(timings)//2]
        p95 = timings[int(len(timings) * 0.95)]
        p99 = timings[int(len(timings) * 0.99)]
        print(f"\n  {BOLD}TIMING{RESET} (per command)")
        print(f"    Median: {median:.0f}us  P95: {p95:.0f}us  P99: {p99:.0f}us")

    # Per category
    if len(by_category) > 1:
        print(f"\n  {BOLD}BY CATEGORY{RESET}")
        for cat in sorted(by_category.keys()):
            r = by_category[cat]
            pct = r["exact"] / r["total"] * 100 if r["total"] else 0
            bar = GREEN if pct == 100 else (YELLOW if pct >= 80 else RED)
            print(f"    {cat:>14}: {bar}{r['exact']}/{r['total']}{RESET} ({pct:.0f}%)")

    # Errors
    if failed_cases:
        print(f"\n  {BOLD}FAILURES{RESET} ({len(failed_cases)}):")
        print("  " + "-" * 66)
        for e in failed_cases[:20]:
            ws_note = f" {DIM}(whitespace only){RESET}" if e["ws_match"] else ""
            wsc_note = f" {DIM}(case only){RESET}" if e["wsc_match"] and not e["ws_match"] else ""
            print(f"    [{e['category']}]{ws_note}{wsc_note}")
            print(f"      input:    {e['dictated'][:70]}")
            print(f"      expected: {e['expected'][:70]}")
            print(f"      got:      {e['got'][:70]}")

            # Show character-level diff for near-misses
            exp, got = e["expected"], e["got"]
            if len(exp) < 80 and len(got) < 80:
                diff_pos = next((i for i in range(min(len(exp), len(got))) if exp[i] != got[i]), min(len(exp), len(got)))
                if diff_pos < len(exp) or diff_pos < len(got):
                    print(f"      diff at {diff_pos}: expected {exp[diff_pos:diff_pos+10]!r} got {got[diff_pos:diff_pos+10]!r}")
            print()

        if len(failed_cases) > 20:
            print(f"    ... and {len(failed_cases) - 20} more")

    return exact, total, failed_cases


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test the procedural dictation processor")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--eval", type=str, default=None, help="Eval JSON file (default: eval-independent.json)")
    parser.add_argument("--category", type=str, help="Filter eval cases by category")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all cases, not just failures")
    args = parser.parse_args()

    print("=" * 70)
    print(f"  PROTOCOL PROCESSOR TEST HARNESS")
    print("=" * 70)

    # Always run unit tests
    unit_passed, unit_total, unit_failures = run_unit_tests(verbose=args.verbose)

    eval_passed = eval_total = 0
    eval_failures = []

    if not args.unit:
        eval_file = args.eval or str(EVAL_DIR / "independent.json")
        if Path(eval_file).exists():
            eval_passed, eval_total, eval_failures = run_eval_tests(
                eval_file, category=args.category, verbose=args.verbose
            )
        else:
            print(f"\n  {YELLOW}SKIP{RESET} eval tests — {eval_file} not found")

    # Grand summary
    print(f"\n{'=' * 70}")
    print(f"  {BOLD}GRAND SUMMARY{RESET}")
    print(f"{'=' * 70}")
    print(f"  Unit tests:  {unit_passed}/{unit_total}", end="")
    print(f" {GREEN}PASS{RESET}" if not unit_failures else f" {RED}{len(unit_failures)} FAIL{RESET}")

    if eval_total:
        print(f"  Eval tests:  {eval_passed}/{eval_total} exact ({eval_passed/eval_total*100:.1f}%)", end="")
        print(f" {GREEN}PASS{RESET}" if not eval_failures else f" — {YELLOW}{len(eval_failures)} diff{RESET}")

    total_pass = unit_passed + eval_passed
    total_all = unit_total + eval_total
    print(f"  Combined:    {total_pass}/{total_all} ({total_pass/total_all*100:.1f}%)")

    sys.exit(0 if not unit_failures else 1)


if __name__ == "__main__":
    main()
