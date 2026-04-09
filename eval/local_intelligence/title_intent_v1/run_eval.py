#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean, median
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL_INTELLIGENCE_DIR = REPO_ROOT / "eval" / "local_intelligence"
if str(LOCAL_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_INTELLIGENCE_DIR))

from grader import parse_json_output  # noqa: E402
from providers import create_provider  # noqa: E402

PACK_DIR = Path(__file__).resolve().parent
CARDS_PATH = PACK_DIR / "cards.json"
RESULTS_DIR = PACK_DIR / "results"

REMOTE_PROVIDERS = {"hf", "github_models", "openrouter", "nous", "groq"}
GENERIC_TITLES = {
    "voice memo",
    "memo",
    "new memo",
    "thoughts",
    "idea",
    "note",
    "work note",
    "audio note",
}
STOPWORDS = {
    "a", "an", "and", "about", "actually", "again", "all", "also", "am", "are",
    "as", "at", "be", "because", "before", "but", "by", "do", "does", "for",
    "from", "had", "has", "have", "how", "i", "if", "in", "into", "is", "it",
    "just", "maybe", "need", "of", "on", "or", "out", "over", "should", "so",
    "still", "that", "the", "their", "them", "then", "there", "they", "this",
    "to", "too", "up", "want", "was", "we", "what", "when", "which", "with",
}

SYSTEM_PROMPT = """You write titles for short voice notes and detect only the clearest action intent.

Return JSON only with exactly these keys:
- title
- intent
- target

Rules:
- Write one concise, specific title that would be useful in a notes list.
- intent must be one of: none, research, email, call, schedule.
- Use intent=none unless the action is clearly explicit in the note.
- Only fill target when the note explicitly says who or what the action is about.
- Do not invent timing, people, or next steps.
- If target is not explicit, return an empty string for target.
"""


@dataclass(frozen=True)
class PackCard:
    payload: dict[str, Any]

    @property
    def id(self) -> str:
        return self.payload["id"]

    @property
    def slice(self) -> str:
        return self.payload["packSlice"]

    @property
    def transcript(self) -> str:
        return self.payload["input"]["transcript"]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_cards(cards_path: Path = CARDS_PATH) -> list[PackCard]:
    data = json.loads(cards_path.read_text())
    return [PackCard(payload=item) for item in data["cards"]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the title+intent v1 benchmark against a provider.")
    parser.add_argument(
        "--provider",
        choices=["replay", "apple", "mlx", "mlx_vlm", "ollama", "hf", "github_models", "openrouter", "nous", "groq"],
        required=True,
    )
    parser.add_argument("--cards", default=str(CARDS_PATH))
    parser.add_argument("--card")
    parser.add_argument("--slice", choices=["title", "intent", "restraint"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--model")
    parser.add_argument("--adapter")
    parser.add_argument("--apple-command")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--hf-token")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--max-tokens", type=int, default=200)
    parser.add_argument("--replay-file")
    parser.add_argument("--output")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def build_messages(card: PackCard) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Memo ID: {card.payload['input']['memoId']}\n"
                f"Transcript:\n{card.transcript}\n\n"
                "Return JSON only."
            ),
        },
    ]


def build_prompt_text(card: PackCard) -> str:
    return f"SYSTEM:\n{SYSTEM_PROMPT}\n\nUSER:\nMemo ID: {card.payload['input']['memoId']}\nTranscript:\n{card.transcript}\n"


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def tokenize(text: str) -> set[str]:
    cleaned = []
    current = []
    for char in text.lower():
        if char.isalnum():
            current.append(char)
        else:
            if current:
                cleaned.append("".join(current))
                current = []
    if current:
        cleaned.append("".join(current))
    return {token for token in cleaned if token and token not in STOPWORDS}


def phrase_overlap(text: str, candidate: str) -> float:
    candidate_tokens = tokenize(candidate)
    if not candidate_tokens:
        return 0.0
    text_tokens = tokenize(text)
    return len(candidate_tokens & text_tokens) / len(candidate_tokens)


def best_overlap(text: str, candidates: list[str]) -> float:
    if not candidates:
        return 0.0
    return max(phrase_overlap(text, candidate) for candidate in candidates)


def normalize_output(parsed: Any) -> dict[str, Any]:
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        parsed = parsed[0]
    if not isinstance(parsed, dict):
        return {"title": "", "intent": "", "target": ""}
    return {
        "title": str(parsed.get("title", "") or "").strip(),
        "intent": normalize_text(parsed.get("intent", "")),
        "target": str(parsed.get("target", "") or "").strip(),
    }


def grade_card(card: PackCard, raw_text: str) -> dict[str, Any]:
    parsed, parse_error, parse_mode = parse_json_output(raw_text)
    if parse_error is not None:
        return {
            "passed": False,
            "score": 0.0,
            "parse_error": parse_error,
            "parse_mode": parse_mode,
            "dimensions": {
                "title_task": {"score": 0.0, "details": "output was not valid JSON"},
                "intent_task": {"score": 0.0, "details": "output was not valid JSON"},
                "restraint": {"score": 0.0, "details": "output was not valid JSON"},
            },
            "parsed": None,
        }

    output = normalize_output(parsed)
    gold = card.payload["gold"]

    title = output["title"]
    title_norm = normalize_text(title)
    title_usable = (
        bool(title.strip())
        and title_norm not in GENERIC_TITLES
        and 4 <= len(title) <= 72
    )
    title_focus = best_overlap(title, gold.get("titleMustMentionAny", []))
    title_score = round((0.4 * (1.0 if title_usable else 0.0)) + (0.6 * title_focus), 4)

    accepted_intents = [normalize_text(item) for item in gold.get("acceptedIntents", [])]
    intent_score_exact = 1.0 if output["intent"] in accepted_intents else 0.0

    target = output["target"]
    target_empty = not target.strip()
    accepted_targets = gold.get("acceptedTargets", [])
    target_overlap = best_overlap(target, accepted_targets) if accepted_targets else 0.0

    if accepted_targets:
        grounding_score = target_overlap
    elif gold.get("targetMustBeEmpty"):
        grounding_score = 1.0 if target_empty else 0.0
    else:
        grounding_score = 1.0

    intent_task_score = round((0.65 * intent_score_exact) + (0.35 * grounding_score), 4)

    if gold.get("targetMustBeEmpty"):
        restraint_score = round(((1.0 if output["intent"] in accepted_intents else 0.0) + (1.0 if target_empty else 0.0)) / 2, 4)
    elif accepted_targets:
        if target_empty:
            restraint_score = 0.35
        else:
            restraint_score = round(min(1.0, target_overlap + 0.15), 4)
    else:
        restraint_score = 1.0

    overall = round((title_score * 0.5) + (intent_task_score * 0.35) + (restraint_score * 0.15), 4)

    passed = (
        overall >= 0.85
        and title_score >= 0.55
        and intent_score_exact == 1.0
        and (not gold.get("targetMustBeEmpty") or target_empty)
        and (not accepted_targets or target_overlap >= 0.35)
    )

    return {
        "passed": passed,
        "score": overall,
        "parse_error": None,
        "parse_mode": parse_mode,
        "dimensions": {
            "title_task": {
                "score": title_score,
                "details": f"title={title!r} overlap={title_focus:.2f} usable={title_usable}",
            },
            "intent_task": {
                "score": intent_task_score,
                "details": f"intent={output['intent']!r} target={target!r} target_overlap={target_overlap:.2f}",
            },
            "restraint": {
                "score": restraint_score,
                "details": f"intent={output['intent']!r} target_empty={target_empty}",
            },
        },
        "parsed": output,
    }


def evaluate_card(args: argparse.Namespace, provider: Any, card: PackCard) -> dict[str, Any]:
    messages = build_messages(card)
    response = provider.generate(card.payload, messages, build_prompt_text(card))
    grade = grade_card(card, response.raw_text)
    return {
        "card_id": card.id,
        "slice": card.slice,
        "provider": args.provider,
        "model": args.model,
        "latency_ms": round(response.latency_ms, 2),
        "raw_text": response.raw_text,
        "metadata": response.metadata,
        "grade": grade,
    }


def print_verbose_row(index: int, row: dict[str, Any]) -> None:
    status = "PASS" if row["grade"]["passed"] else "FAIL"
    print(f"[{status}] {index:02d}. {row['card_id']} ({row['slice']})")
    if not row["grade"]["passed"]:
        for name, dimension in row["grade"]["dimensions"].items():
            print(f"  - {name}: {dimension['details']}")


def summarize(rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    passed = sum(1 for row in rows if row["grade"]["passed"])
    latencies = [row["latency_ms"] for row in rows]
    exact_parse_count = sum(1 for row in rows if row["grade"].get("parse_mode") == "exact")
    normalized_parse_count = sum(1 for row in rows if row["grade"].get("parse_mode") == "normalized")
    parse_failure_count = sum(1 for row in rows if row["grade"].get("parse_error"))
    by_slice: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_slice.setdefault(row["slice"], []).append(row)

    summary = {
        "provider": args.provider,
        "model": args.model,
        "pack": "title_intent_v1",
        "cards": len(rows),
        "passed": passed,
        "pass_rate": round(passed / len(rows), 4),
        "average_score": round(mean(row["grade"]["score"] for row in rows), 4),
        "median_latency_ms": round(median(latencies), 2) if latencies else 0.0,
        "exact_parse_rate": round(exact_parse_count / len(rows), 4),
        "normalized_parse_rate": round(normalized_parse_count / len(rows), 4),
        "parse_failure_rate": round(parse_failure_count / len(rows), 4),
        "title_task_score": round(mean(row["grade"]["dimensions"]["title_task"]["score"] for row in rows), 4),
        "intent_task_score": round(mean(row["grade"]["dimensions"]["intent_task"]["score"] for row in rows), 4),
        "restraint_score": round(mean(row["grade"]["dimensions"]["restraint"]["score"] for row in rows), 4),
    }
    for slice_name, slice_rows in sorted(by_slice.items()):
        summary[f"{slice_name}_slice_score"] = round(mean(row["grade"]["score"] for row in slice_rows), 4)
        summary[f"{slice_name}_slice_pass_rate"] = round(
            sum(1 for row in slice_rows if row["grade"]["passed"]) / len(slice_rows),
            4,
        )
    return summary


def main() -> int:
    args = parse_args()
    cards = load_cards(Path(args.cards))
    if args.card:
        cards = [card for card in cards if card.id == args.card]
    if args.slice:
        cards = [card for card in cards if card.slice == args.slice]
    if args.limit:
        cards = cards[: args.limit]
    if not cards:
        raise SystemExit("No cards selected.")

    provider = create_provider(args)

    rows = []
    for index, card in enumerate(cards, start=1):
        row = evaluate_card(args, provider, card)
        rows.append(row)
        if args.verbose:
            print_verbose_row(index, row)

    summary = summarize(rows, args)
    print(json.dumps(summary, indent=2))

    output_path = Path(args.output) if args.output else RESULTS_DIR / f"{args.provider}-{utc_timestamp()}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    print(f"Wrote results to {output_path}")
    return 0 if summary["passed"] == summary["cards"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
