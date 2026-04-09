#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError
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

NEWS_SUMMARY_DIR = REPO_ROOT / "eval" / "news_summarization"
DATA_DIR = NEWS_SUMMARY_DIR / "data"
RESULTS_DIR = NEWS_SUMMARY_DIR / "results"
DEFAULT_DATASETS = {
    "bbc2024_qwen_reference": "https://raw.githubusercontent.com/Xtra-Computing/SLM_Summary_Benchmark/main/dataset/sample_500_qwen1.5_72b_summary/bbc2024_sample_500_0k5_1k5_qwen1.5_72b_summary_no_len_limit.jsonl",
}
PROMPT_TEMPLATES = {
    "simple": (
        "News: {article}\n"
        "Summarize the news in two sentences. Summary:"
    ),
    "helpful": (
        "You are a helpful summary assistant. You can help users summarize news in two sentences.\n"
        "News: {article}\n"
        "Summarize the news in two sentences. Summary:"
    ),
    "detailed": (
        "News: {article}\n"
        "Summarize the news in two sentences. "
        "Your summary should: 1. Capture the main points of the article. "
        "2. Be concise and informative. 3. Use clear and simple language. "
        "4. Avoid unnecessary details or opinions. Summary:"
    ),
}

try:
    from rouge_score import rouge_scorer  # type: ignore
except ImportError:
    rouge_scorer = None

try:
    from bert_score import score as bert_score_fn  # type: ignore
except ImportError:
    bert_score_fn = None


@dataclass(frozen=True)
class NewsSummaryCase:
    case_id: str
    article: str
    reference_summary: str
    source_url: str | None


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_slug(value: str | None) -> str:
    text = value or "unknown"
    return re.sub(r"[^a-z0-9._-]+", "-", text.lower()).strip("-") or "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a lightweight news summarization pilot based on the NAACL 2025 SLM benchmark.")
    parser.add_argument("--provider", choices=["replay", "apple", "mlx", "mlx_vlm", "ollama", "hf", "github_models", "openrouter", "nous", "groq"], required=True)
    parser.add_argument("--model")
    parser.add_argument("--adapter")
    parser.add_argument("--apple-command")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--hf-token")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--max-tokens", type=int, default=220)
    parser.add_argument("--dataset", choices=sorted(DEFAULT_DATASETS), default="bbc2024_qwen_reference")
    parser.add_argument("--prompt-style", choices=sorted(PROMPT_TEMPLATES), default="simple")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-article-chars", type=int, default=8000)
    parser.add_argument("--disable-rouge", action="store_true")
    parser.add_argument("--disable-bertscore", action="store_true")
    parser.add_argument("--bertscore-model", default="roberta-large")
    parser.add_argument("--output")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--save-every", type=int, default=10)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def ensure_dataset(dataset_name: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{dataset_name}.json"
    if path.exists():
        return path
    url = DEFAULT_DATASETS[dataset_name]
    with urlopen(url) as response:
        path.write_bytes(response.read())
    return path


def clip_article(text: str, max_chars: int) -> str:
    article = re.sub(r"\s+", " ", text).strip()
    if len(article) <= max_chars:
        return article
    clipped = article[:max_chars].rsplit(" ", 1)[0].strip()
    return clipped or article[:max_chars].strip()


def load_cases(path: Path, limit: int, seed: int, max_article_chars: int) -> list[NewsSummaryCase]:
    rows = json.loads(path.read_text())
    rng = random.Random(seed)
    sample = list(rows)
    rng.shuffle(sample)
    cases = []
    for index, row in enumerate(sample[:limit], start=1):
        article = clip_article(row["article"], max_article_chars)
        reference_summary = row["qwen_reference_summary"].strip()
        cases.append(
            NewsSummaryCase(
                case_id=f"news-{index:03d}",
                article=article,
                reference_summary=reference_summary,
                source_url=row.get("url"),
            )
        )
    return cases


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
        return {"token_f1": 0.0, "rouge_l_f1_approx": 0.0}

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
    if disabled or rouge_scorer is None:
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
        references = [row["reference_summary"] for row in rows]
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


def clean_summary(text: str) -> str:
    cleaned = text.strip()
    cleaned = cleaned.removeprefix("Summary:").strip()
    cleaned = cleaned.removeprefix("The news summary is:").strip().strip('"')
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def build_messages(case: NewsSummaryCase, prompt_style: str, article_override: str | None = None) -> list[dict[str, str]]:
    system = (
        "You summarize news articles. "
        "Return only the summary in plain text. "
        "Do not add bullets, labels, or commentary."
    )
    user = PROMPT_TEMPLATES[prompt_style].format(article=article_override or case.article)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_prompt_text(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(f"{message['role'].upper()}:\n{message['content']}" for message in messages)


def evaluate_case(provider, args: argparse.Namespace, case: NewsSummaryCase) -> dict[str, Any]:
    reduction_steps = [args.max_article_chars, 6000, 4000, 2500, 1500, 1000, 700]
    response = None
    prediction = ""
    last_error: Exception | None = None
    used_article = case.article
    for char_limit in reduction_steps:
        used_article = clip_article(case.article, min(len(case.article), char_limit))
        messages = build_messages(case, args.prompt_style, article_override=used_article)
        prompt_text = build_prompt_text(messages)
        started = time.perf_counter()
        try:
            response = provider.generate(
                {
                    "id": case.case_id,
                    "title": f"{args.dataset}:{case.case_id}",
                    "evaluationMode": "news_summarization",
                },
                messages,
                prompt_text,
            )
            break
        except HTTPError as exc:
            last_error = exc
            if exc.code != 400 or char_limit == reduction_steps[-1]:
                raise
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            raise

    if response is None:
        raise RuntimeError(f"Provider failed for {case.case_id}: {last_error}")

    latency_ms = round(response.latency_ms or ((time.perf_counter() - started) * 1000), 2)
    prediction = clean_summary(response.raw_text)
    scores = score_text(prediction, case.reference_summary)
    scores.update(compute_rouge_scores(prediction, case.reference_summary, args.disable_rouge))
    scores["word_count"] = len(prediction.split())
    return {
        "case_id": case.case_id,
        "article_chars": len(used_article),
        "reference_summary": case.reference_summary,
        "prediction": prediction,
        "source_url": case.source_url,
        "latency_ms": latency_ms,
        "scores": scores,
        "provider_metadata": response.metadata,
    }


def summarize(rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    summary = {
        "provider": args.provider,
        "model": args.model,
        "dataset": args.dataset,
        "prompt_style": args.prompt_style,
        "cases": len(rows),
        "average_token_f1": round(sum(row["scores"]["token_f1"] for row in rows) / len(rows), 4),
        "average_rouge_l_f1_approx": round(sum(row["scores"]["rouge_l_f1_approx"] for row in rows) / len(rows), 4),
        "average_word_count": round(sum(row["scores"]["word_count"] for row in rows) / len(rows), 2),
        "median_latency_ms": round(sorted(row["latency_ms"] for row in rows)[len(rows) // 2], 2),
    }
    for metric in ["rouge1_f1", "rouge2_f1", "rougeL_f1", "bertscore_f1"]:
        present = [row["scores"][metric] for row in rows if row["scores"].get(metric) is not None]
        summary[f"average_{metric}"] = round(sum(present) / len(present), 4) if present else None
    return summary


def default_output_path(args: argparse.Namespace) -> Path:
    return RESULTS_DIR / f"{args.provider}-{safe_slug(args.model)}-{args.dataset}-{args.prompt_style}-seed{args.seed}-limit{args.limit}.json"


def write_progress(output_path: Path, rows: list[dict[str, Any]], args: argparse.Namespace, *, final: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if final:
        payload = {"summary": summarize(rows, args), "rows": rows}
    else:
        payload = {
            "summary": {
                "provider": args.provider,
                "model": args.model,
                "dataset": args.dataset,
                "prompt_style": args.prompt_style,
                "cases_completed": len(rows),
                "finalized": False,
            },
            "rows": rows,
        }
    output_path.write_text(json.dumps(payload, indent=2))


def main() -> int:
    from eval.local_intelligence.providers import create_provider  # noqa: E402

    args = parse_args()
    dataset_path = ensure_dataset(args.dataset)
    cases = load_cases(dataset_path, limit=args.limit, seed=args.seed, max_article_chars=args.max_article_chars)
    if not cases:
        raise SystemExit("No news summarization cases selected.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output) if args.output else default_output_path(args)
    provider = create_provider(args)
    rows: list[dict[str, Any]] = []
    completed_case_ids: set[str] = set()
    if args.resume and output_path.exists():
        existing = json.loads(output_path.read_text())
        rows = existing.get("rows", [])
        completed_case_ids = {row["case_id"] for row in rows}
        print(f"Resuming from {output_path} with {len(rows)} completed cases.")

    pending_cases = [case for case in cases if case.case_id not in completed_case_ids]
    for index, case in enumerate(pending_cases, start=len(rows) + 1):
        row = evaluate_case(provider, args, case)
        rows.append(row)
        if args.save_every > 0 and len(rows) % args.save_every == 0:
            write_progress(output_path, rows, args, final=False)
            print(f"Saved progress at {len(rows)}/{len(cases)} cases -> {output_path}")
        if args.verbose:
            print(
                f"[{index:02d}] {case.case_id} "
                f"token_f1={row['scores']['token_f1']:.4f} "
                f"rouge_l_approx={row['scores']['rouge_l_f1_approx']:.4f} "
                f"words={row['scores']['word_count']}"
            )
            print(f"PRED: {row['prediction']}")
            print(f"REF:  {case.reference_summary}")
            print()

    compute_bertscore(rows, args.disable_bertscore, args.bertscore_model)
    summary = summarize(rows, args)
    print(json.dumps(summary, indent=2))
    write_progress(output_path, rows, args, final=True)
    print(f"Wrote results to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
