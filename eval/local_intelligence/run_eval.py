#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
import json
from pathlib import Path
import random
from statistics import median
import time

from config import CARDS_PATH, DEFAULT_OLLAMA_URL, DEFAULT_TIMEOUT_SECONDS, RESULTS_DIR, load_cards, utc_timestamp
from grader import grade_card
from providers import create_provider
from template import build_messages, build_prompt_text

REMOTE_PROVIDERS = {"hf", "github_models", "openrouter", "nous"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local-intelligence evals against a provider.")
    parser.add_argument("--provider", choices=["replay", "apple", "mlx", "mlx_vlm", "ollama", "hf", "github_models", "openrouter", "nous"], required=True)
    parser.add_argument("--cards", default=str(CARDS_PATH))
    parser.add_argument("--card")
    parser.add_argument("--tier")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--model")
    parser.add_argument("--adapter")
    parser.add_argument("--apple-command")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--hf-token")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-tokens", type=int, default=400)
    parser.add_argument("--max-concurrency", type=int)
    parser.add_argument("--launch-interval-ms", type=int, default=1000)
    parser.add_argument("--launch-jitter-ms", type=int, default=250)
    parser.add_argument("--replay-file")
    parser.add_argument("--output")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def resolve_concurrency(args: argparse.Namespace) -> int:
    if args.max_concurrency is not None:
        return max(1, args.max_concurrency)
    if args.provider in REMOTE_PROVIDERS:
        return 2
    return 1


def evaluate_card(args: argparse.Namespace, provider, card) -> dict:
    payload = card.payload
    messages = build_messages(payload, card.test_input)
    prompt_text = build_prompt_text(payload, card.test_input)
    response = provider.generate(payload, messages, prompt_text)
    grade = grade_card(payload, response.raw_text)
    return {
        "card_id": card.id,
        "title": card.title,
        "tier": card.tier,
        "provider": args.provider,
        "model": args.model,
        "latency_ms": round(response.latency_ms, 2),
        "raw_text": response.raw_text,
        "metadata": response.metadata,
        "grade": grade,
    }


def print_verbose_row(index: int, row: dict) -> None:
    grade = row["grade"]
    status = "PASS" if grade["passed"] else "FAIL"
    print(f"[{status}] {index:02d}. {row['card_id']} ({row['tier']})")
    if not grade["passed"]:
        for assertion in grade["assertions"]:
            if not assertion["passed"]:
                print(f"  - {assertion['assertion']}: {assertion['details']}")


def main() -> int:
    args = parse_args()
    cards = load_cards(Path(args.cards))
    if args.card:
        cards = [card for card in cards if card.id == args.card]
    if args.tier:
        cards = [card for card in cards if card.tier == args.tier]
    if args.limit:
        cards = cards[: args.limit]
    if not cards:
        raise SystemExit("No cards selected.")

    provider = create_provider(args)
    rows: list[dict | None] = [None] * len(cards)
    concurrency = resolve_concurrency(args)

    if concurrency == 1:
        for index, card in enumerate(cards, start=1):
            row = evaluate_card(args, provider, card)
            rows[index - 1] = row
            if args.verbose:
                print_verbose_row(index, row)
            if index < len(cards):
                delay_ms = args.launch_interval_ms + random.randint(0, max(0, args.launch_jitter_ms))
                time.sleep(delay_ms / 1000)
    else:
        future_to_meta: dict[Future, tuple[int, object]] = {}
        next_index = 0
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            while next_index < len(cards) and len(future_to_meta) < concurrency:
                card = cards[next_index]
                future = executor.submit(evaluate_card, args, provider, card)
                future_to_meta[future] = (next_index, card)
                next_index += 1
                if next_index < len(cards):
                    delay_ms = args.launch_interval_ms + random.randint(0, max(0, args.launch_jitter_ms))
                    time.sleep(delay_ms / 1000)

            while future_to_meta:
                done, _ = wait(future_to_meta.keys(), return_when=FIRST_COMPLETED)
                for future in done:
                    index, _card = future_to_meta.pop(future)
                    row = future.result()
                    rows[index] = row
                    if args.verbose:
                        print_verbose_row(index + 1, row)
                    if next_index < len(cards):
                        card = cards[next_index]
                        future = executor.submit(evaluate_card, args, provider, card)
                        future_to_meta[future] = (next_index, card)
                        next_index += 1
                        if next_index < len(cards):
                            delay_ms = args.launch_interval_ms + random.randint(0, max(0, args.launch_jitter_ms))
                            time.sleep(delay_ms / 1000)

    rows = [row for row in rows if row is not None]

    passed = sum(1 for row in rows if row["grade"]["passed"])
    average_score = sum(row["grade"]["score"] for row in rows) / len(rows)
    latencies = [row["latency_ms"] for row in rows]
    exact_parse_count = sum(1 for row in rows if row["grade"].get("parse_mode") == "exact")
    normalized_parse_count = sum(1 for row in rows if row["grade"].get("parse_mode") == "normalized")
    parse_failure_count = sum(1 for row in rows if row["grade"].get("parse_error"))
    summary = {
        "provider": args.provider,
        "model": args.model,
        "cards": len(rows),
        "passed": passed,
        "pass_rate": round(passed / len(rows), 4),
        "average_score": round(average_score, 4),
        "median_latency_ms": round(median(latencies), 2),
        "exact_parse_rate": round(exact_parse_count / len(rows), 4),
        "normalized_parse_rate": round(normalized_parse_count / len(rows), 4),
        "parse_failure_rate": round(parse_failure_count / len(rows), 4),
    }

    dimension_names = ["task", "usable", "contract"]
    if any("dimensions" in row["grade"] for row in rows):
        dimension_scores = {}
        for dimension in dimension_names:
            present = [row["grade"]["dimensions"][dimension]["score"] for row in rows if "dimensions" in row["grade"] and dimension in row["grade"]["dimensions"]]
            if present:
                dimension_scores[f"{dimension}_score"] = round(sum(present) / len(present), 4)
        summary.update(dimension_scores)

    print(json.dumps(summary, indent=2))

    output_path = Path(args.output) if args.output else RESULTS_DIR / f"{args.provider}-{utc_timestamp()}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    print(f"Wrote results to {output_path}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
