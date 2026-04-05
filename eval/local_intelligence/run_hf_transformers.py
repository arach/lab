#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from statistics import median
import time

from config import CARDS_PATH, RESULTS_DIR, load_cards, utc_timestamp
from grader import grade_card
from template import build_messages, build_prompt_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local-intelligence eval pack on Hugging Face compute with transformers.")
    parser.add_argument("--model", required=True, help="Hub model id, e.g. google/gemma-4-E4B-it")
    parser.add_argument("--cards", default=str(CARDS_PATH))
    parser.add_argument("--card")
    parser.add_argument("--tier")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--dtype", default="auto")
    parser.add_argument("--attn-implementation")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--output-prefix", default="hf-transformers")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def slugify_model(model_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", model_id.lower()).strip("-")


def build_generator(args: argparse.Namespace):
    import torch
    from transformers import pipeline

    torch_dtype = None
    if args.dtype != "auto":
        torch_dtype = getattr(torch, args.dtype)

    kwargs = {
        "model": args.model,
        "device_map": args.device_map,
        "trust_remote_code": args.trust_remote_code,
    }
    if torch_dtype is not None:
        kwargs["torch_dtype"] = torch_dtype
    if args.attn_implementation:
        kwargs["model_kwargs"] = {"attn_implementation": args.attn_implementation}

    generator = pipeline("text-generation", **kwargs)
    generation_config = getattr(generator.model, "generation_config", None)
    if generation_config is not None and getattr(generation_config, "max_length", None) == 20:
        generation_config.max_length = None
    return generator


def build_generation_input(generator, payload: dict, test_input: dict) -> str:
    messages = build_messages(payload, test_input)
    tokenizer = getattr(generator, "tokenizer", None)
    if tokenizer is not None and hasattr(tokenizer, "apply_chat_template") and getattr(tokenizer, "chat_template", None):
        try:
            return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        except Exception:
            pass
    return build_prompt_text(payload, test_input)


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

    generator = build_generator(args)
    rows = []

    for index, card in enumerate(cards, start=1):
        payload = card.payload
        generation_input = build_generation_input(generator, payload, card.test_input)
        start = time.perf_counter()
        output = generator(
            generation_input,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
            return_full_text=False,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        raw_text = output[0]["generated_text"].strip()
        grade = grade_card(payload, raw_text)

        row = {
            "card_id": card.id,
            "title": card.title,
            "tier": card.tier,
            "provider": "hf-transformers",
            "model": args.model,
            "latency_ms": round(latency_ms, 2),
            "raw_text": raw_text,
            "grade": grade,
        }
        rows.append(row)

        if args.verbose:
            status = "PASS" if grade["passed"] else "FAIL"
            print(f"[{status}] {index:02d}. {card.id} ({card.tier})")
            if not grade["passed"]:
                for assertion in grade["assertions"]:
                    if not assertion["passed"]:
                        print(f"  - {assertion['assertion']}: {assertion['details']}")

    passed = sum(1 for row in rows if row["grade"]["passed"])
    average_score = sum(row["grade"]["score"] for row in rows) / len(rows)
    latencies = [row["latency_ms"] for row in rows]
    exact_parse_count = sum(1 for row in rows if row["grade"].get("parse_mode") == "exact")
    normalized_parse_count = sum(1 for row in rows if row["grade"].get("parse_mode") == "normalized")
    parse_failure_count = sum(1 for row in rows if row["grade"].get("parse_error"))
    summary = {
        "provider": "hf-transformers",
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

    print(json.dumps(summary, indent=2))

    default_name = f"{args.output_prefix}-{slugify_model(args.model)}-{utc_timestamp()}.json"
    output_path = Path(args.output) if args.output else RESULTS_DIR / default_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    print(f"Wrote results to {output_path}")
    if args.fail_on_incomplete and passed != len(rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
