#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import re
import sys
import time
from typing import Any
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.local_intelligence.providers import create_provider  # noqa: E402

QMSUM_DIR = REPO_ROOT / "eval" / "qmsum"
DATA_DIR = QMSUM_DIR / "data"
RESULTS_DIR = QMSUM_DIR / "results"
DEFAULT_DATASET_BASE = "https://raw.githubusercontent.com/Yale-LILY/QMSum/main/data/ALL/jsonl"
DEFAULT_PROMPT_STYLE = "query_focused_summary"

try:
    from rouge_score import rouge_scorer  # type: ignore
except ImportError:
    rouge_scorer = None

try:
    from bert_score import score as bert_score_fn  # type: ignore
except ImportError:
    bert_score_fn = None


@dataclass(frozen=True)
class QMSumCase:
    case_id: str
    meeting_id: str
    query_mode: str
    query: str
    answer: str
    transcript_excerpt: str
    transcript_turns: int
    metadata: dict[str, Any]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a lightweight QMSum pilot against an existing provider.")
    parser.add_argument("--provider", choices=["replay", "apple", "mlx", "mlx_vlm", "ollama", "hf", "github_models", "openrouter", "nous", "groq"], required=True)
    parser.add_argument("--model")
    parser.add_argument("--adapter")
    parser.add_argument("--apple-command")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--hf-token")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--max-tokens", type=int, default=220)
    parser.add_argument("--split", choices=["train", "val", "test"], default="test")
    parser.add_argument("--query-mode", choices=["specific", "general", "mixed"], default="specific")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--context-window", type=int, default=2, help="Extra transcript turns on each side of gold spans.")
    parser.add_argument("--max-transcript-chars", type=int, default=6000)
    parser.add_argument("--disable-rouge", action="store_true")
    parser.add_argument("--disable-bertscore", action="store_true")
    parser.add_argument("--bertscore-model", default="roberta-large")
    parser.add_argument("--output")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def ensure_dataset(split: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{split}.jsonl"
    if path.exists():
        return path
    url = f"{DEFAULT_DATASET_BASE}/{split}.jsonl"
    with urlopen(url) as response:
        path.write_bytes(response.read())
    return path


def load_meetings(path: Path) -> list[dict[str, Any]]:
    meetings = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        meetings.append(json.loads(line))
    return meetings


def normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", token.lower()).strip()


def tokenize(text: str) -> list[str]:
    tokens = [normalize_token(part) for part in re.split(r"\s+", text)]
    return [token for token in tokens if token]


def lcs_length(a: list[str], b: list[str]) -> int:
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for left in a:
        curr = [0]
        for j, right in enumerate(b, start=1):
            if left == right:
                curr.append(prev[j - 1] + 1)
            else:
                curr.append(max(prev[j], curr[-1]))
        prev = curr
    return prev[-1]


def score_text(prediction: str, reference: str) -> dict[str, float]:
    pred_tokens = tokenize(prediction)
    ref_tokens = tokenize(reference)
    if not pred_tokens or not ref_tokens:
        return {"token_f1": 0.0, "rouge_l_f1": 0.0}

    pred_counts: dict[str, int] = {}
    for token in pred_tokens:
        pred_counts[token] = pred_counts.get(token, 0) + 1

    overlap = 0
    for token in ref_tokens:
        count = pred_counts.get(token, 0)
        if count > 0:
            overlap += 1
            pred_counts[token] = count - 1

    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    token_f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)

    lcs = lcs_length(pred_tokens, ref_tokens)
    rouge_precision = lcs / len(pred_tokens)
    rouge_recall = lcs / len(ref_tokens)
    rouge_l_f1 = 0.0 if rouge_precision + rouge_recall == 0 else 2 * rouge_precision * rouge_recall / (rouge_precision + rouge_recall)

    return {
        "token_f1": round(token_f1, 4),
        "rouge_l_f1_approx": round(rouge_l_f1, 4),
    }


def compute_rouge_scores(prediction: str, reference: str, disabled: bool) -> dict[str, float | None]:
    if disabled:
        return {"rouge1_f1": None, "rouge2_f1": None, "rougeL_f1": None}
    if rouge_scorer is None:
        return {"rouge1_f1": None, "rouge2_f1": None, "rougeL_f1": None}
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    scores = scorer.score(reference, prediction)
    return {
        "rouge1_f1": round(scores["rouge1"].fmeasure, 4),
        "rouge2_f1": round(scores["rouge2"].fmeasure, 4),
        "rougeL_f1": round(scores["rougeL"].fmeasure, 4),
    }


def compute_bertscore(rows: list[dict[str, Any]], disabled: bool, model_type: str) -> None:
    if disabled or bert_score_fn is None or not rows:
        for row in rows:
            row["scores"]["bertscore_f1"] = None
        return

    try:
        predictions = [row["prediction"] for row in rows]
        references = [row["gold_answer"] for row in rows]
        _, _, f1 = bert_score_fn(
            predictions,
            references,
            lang="en",
            model_type=model_type,
            verbose=False,
        )
        for row, value in zip(rows, f1.tolist(), strict=True):
            row["scores"]["bertscore_f1"] = round(float(value), 4)
    except Exception as exc:
        for row in rows:
            row["scores"]["bertscore_f1"] = None
            row["scores"]["bertscore_error"] = str(exc)


def build_excerpt(transcript: list[dict[str, str]], spans: list[list[str]] | None, context_window: int, max_chars: int) -> tuple[str, int, tuple[int, int] | None]:
    if not transcript:
        return "", 0, None

    if not spans:
        selected = transcript
        excerpt = format_turns(selected)
        return excerpt[:max_chars].strip(), len(selected), None

    min_index = min(int(start) for start, _end in spans)
    max_index = max(int(end) for _start, end in spans)
    start_index = max(0, min_index - context_window)
    end_index = min(len(transcript) - 1, max_index + context_window)
    selected = transcript[start_index : end_index + 1]
    excerpt = format_turns(selected)

    while len(excerpt) > max_chars and len(selected) > 1:
      if len(selected) % 2 == 0:
          selected = selected[:-1]
      else:
          selected = selected[1:]
      excerpt = format_turns(selected)

    return excerpt.strip(), len(selected), (start_index, end_index)


def format_turns(turns: list[dict[str, str]]) -> str:
    return "\n".join(
        f"{turn.get('speaker', 'Unknown')}: {turn.get('content', '').strip()}"
        for turn in turns
        if turn.get("content", "").strip()
    )


def build_cases(meetings: list[dict[str, Any]], query_mode: str, limit: int, seed: int, context_window: int, max_chars: int) -> list[QMSumCase]:
    pairs: list[QMSumCase] = []
    rng = random.Random(seed)

    shuffled = list(enumerate(meetings))
    rng.shuffle(shuffled)

    for meeting_index, meeting in shuffled:
        transcript = meeting.get("meeting_transcripts", [])
        meeting_id = f"{meeting_index:04d}"

        if query_mode in {"general", "mixed"}:
            for query_index, item in enumerate(meeting.get("general_query_list", [])):
                excerpt, turns, span_range = build_excerpt(transcript, None, context_window, max_chars)
                pairs.append(
                    QMSumCase(
                        case_id=f"{meeting_id}-general-{query_index}",
                        meeting_id=meeting_id,
                        query_mode="general",
                        query=item["query"],
                        answer=item["answer"],
                        transcript_excerpt=excerpt,
                        transcript_turns=turns,
                        metadata={"span_range": span_range},
                    )
                )

        if query_mode in {"specific", "mixed"}:
            for query_index, item in enumerate(meeting.get("specific_query_list", [])):
                excerpt, turns, span_range = build_excerpt(
                    transcript,
                    item.get("relevant_text_span"),
                    context_window,
                    max_chars,
                )
                pairs.append(
                    QMSumCase(
                        case_id=f"{meeting_id}-specific-{query_index}",
                        meeting_id=meeting_id,
                        query_mode="specific",
                        query=item["query"],
                        answer=item["answer"],
                        transcript_excerpt=excerpt,
                        transcript_turns=turns,
                        metadata={"span_range": span_range},
                    )
                )

    rng.shuffle(pairs)
    return pairs[:limit]


def build_messages(case: QMSumCase) -> list[dict[str, str]]:
    system = (
        "You answer questions about meeting transcripts. "
        "Use only the provided transcript excerpt. "
        "Return a short, faithful answer in plain text. "
        "Do not mention limitations unless the excerpt truly lacks the needed information."
    )
    user = (
        f"Question:\n{case.query}\n\n"
        f"Transcript excerpt:\n{case.transcript_excerpt}\n\n"
        "Answer the question directly."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_prompt_text(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(f"{message['role'].upper()}:\n{message['content']}" for message in messages)


def evaluate_case(provider, args: argparse.Namespace, case: QMSumCase) -> dict[str, Any]:
    messages = build_messages(case)
    prompt_text = build_prompt_text(messages)
    started = time.perf_counter()
    response = provider.generate(
        {
            "id": case.case_id,
            "title": case.query,
            "evaluationMode": DEFAULT_PROMPT_STYLE,
        },
        messages,
        prompt_text,
    )
    latency_ms = round(response.latency_ms or ((time.perf_counter() - started) * 1000), 2)
    scores = score_text(response.raw_text, case.answer)
    scores.update(compute_rouge_scores(response.raw_text, case.answer, args.disable_rouge))
    return {
        "case_id": case.case_id,
        "meeting_id": case.meeting_id,
        "query_mode": case.query_mode,
        "query": case.query,
        "gold_answer": case.answer,
        "prediction": response.raw_text.strip(),
        "transcript_turns": case.transcript_turns,
        "transcript_excerpt": case.transcript_excerpt,
        "metadata": case.metadata,
        "latency_ms": latency_ms,
        "scores": scores,
        "provider_metadata": response.metadata,
    }


def summarize(rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    token_f1 = sum(row["scores"]["token_f1"] for row in rows) / len(rows)
    rouge_l_f1_approx = sum(row["scores"]["rouge_l_f1_approx"] for row in rows) / len(rows)
    summary = {
        "provider": args.provider,
        "model": args.model,
        "split": args.split,
        "query_mode": args.query_mode,
        "cases": len(rows),
        "average_token_f1": round(token_f1, 4),
        "average_rouge_l_f1_approx": round(rouge_l_f1_approx, 4),
        "median_latency_ms": round(sorted(row["latency_ms"] for row in rows)[len(rows) // 2], 2),
    }
    numeric_metrics = ["rouge1_f1", "rouge2_f1", "rougeL_f1", "bertscore_f1"]
    for metric in numeric_metrics:
        present = [row["scores"][metric] for row in rows if row["scores"].get(metric) is not None]
        if present:
            summary[f"average_{metric}"] = round(sum(present) / len(present), 4)
        else:
            summary[f"average_{metric}"] = None
    return summary


def main() -> int:
    args = parse_args()
    dataset_path = ensure_dataset(args.split)
    meetings = load_meetings(dataset_path)
    cases = build_cases(
        meetings,
        query_mode=args.query_mode,
        limit=args.limit,
        seed=args.seed,
        context_window=args.context_window,
        max_chars=args.max_transcript_chars,
    )
    if not cases:
        raise SystemExit("No QMSum cases selected.")

    provider = create_provider(args)
    rows = []
    for index, case in enumerate(cases, start=1):
        row = evaluate_case(provider, args, case)
        rows.append(row)
        if args.verbose:
            print(
                f"[{index:02d}] {case.case_id} "
                f"token_f1={row['scores']['token_f1']:.4f} "
                f"rouge_l_approx={row['scores']['rouge_l_f1_approx']:.4f}"
            )
            print(f"Q: {case.query}")
            print(f"PRED: {row['prediction']}")
            print(f"GOLD: {case.answer}")
            print()

    compute_bertscore(rows, args.disable_bertscore, args.bertscore_model)

    summary = summarize(rows, args)
    print(json.dumps(summary, indent=2))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output) if args.output else RESULTS_DIR / f"{args.provider}-{args.split}-{args.query_mode}-{utc_timestamp()}.json"
    output_path.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    print(f"Wrote results to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
