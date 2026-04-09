#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.news_summarization.run_news_summary_pilot import (  # noqa: E402
    RESULTS_DIR,
    build_messages,
    clean_summary,
    compute_bertscore,
    compute_rouge_scores,
    default_output_path,
    ensure_dataset,
    load_cases,
    score_text,
    summarize,
    write_progress,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the news summarization pilot on Hugging Face/Colab with transformers.")
    parser.add_argument("--model", required=True, help="Hub model id, e.g. Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--dataset", default="bbc2024_qwen_reference")
    parser.add_argument("--prompt-style", default="simple", choices=["simple", "helpful", "detailed"])
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-article-chars", type=int, default=8000)
    parser.add_argument("--max-new-tokens", type=int, default=220)
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--dtype", default="auto")
    parser.add_argument("--attn-implementation")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--disable-rouge", action="store_true")
    parser.add_argument("--disable-bertscore", action="store_true")
    parser.add_argument("--bertscore-model", default="roberta-large")
    parser.add_argument("--output")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--save-every", type=int, default=1)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def build_generator(args: argparse.Namespace):
    import torch
    from transformers import pipeline

    dtype = None
    if args.dtype != "auto":
        dtype = getattr(torch, args.dtype)

    kwargs: dict[str, object] = {
        "model": args.model,
        "device_map": args.device_map,
        "trust_remote_code": args.trust_remote_code,
    }
    if dtype is not None:
        kwargs["dtype"] = dtype
    if args.attn_implementation:
        kwargs["model_kwargs"] = {"attn_implementation": args.attn_implementation}

    generator = pipeline("text-generation", **kwargs)
    return generator


def render_prompt(generator, messages: list[dict[str, str]]) -> str:
    tokenizer = getattr(generator, "tokenizer", None)
    if tokenizer is not None and hasattr(tokenizer, "apply_chat_template") and getattr(tokenizer, "chat_template", None):
        try:
            return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        except Exception:
            pass
    return "\n\n".join(f"{message['role'].upper()}:\n{message['content']}" for message in messages)


def main() -> int:
    args = parse_args()
    dataset_path = ensure_dataset(args.dataset)
    cases = load_cases(dataset_path, limit=args.limit, seed=args.seed, max_article_chars=args.max_article_chars)
    if not cases:
        raise SystemExit("No news summarization cases selected.")

    generator = build_generator(args)
    output_path = Path(args.output) if args.output else default_output_path(
        argparse.Namespace(
            provider="hf-transformers",
            model=args.model,
            dataset=args.dataset,
            prompt_style=args.prompt_style,
            seed=args.seed,
            limit=args.limit,
        )
    )

    rows: list[dict] = []
    completed_case_ids: set[str] = set()
    if args.resume and output_path.exists():
        existing = json.loads(output_path.read_text())
        rows = existing.get("rows", [])
        completed_case_ids = {row["case_id"] for row in rows}
        print(f"Resuming from {output_path} with {len(rows)} completed cases.")

    pending_cases = [case for case in cases if case.case_id not in completed_case_ids]
    total_cases = len(cases)
    for index, case in enumerate(pending_cases, start=len(rows) + 1):
        messages = build_messages(case, args.prompt_style)
        prompt = render_prompt(generator, messages)
        start = time.perf_counter()
        output = generator(
            prompt,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
            return_full_text=False,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        prediction = clean_summary(output[0]["generated_text"])
        scores = score_text(prediction, case.reference_summary)
        scores.update(compute_rouge_scores(prediction, case.reference_summary, args.disable_rouge))
        scores["word_count"] = len(prediction.split())
        row = {
            "case_id": case.case_id,
            "article_chars": len(case.article),
            "reference_summary": case.reference_summary,
            "prediction": prediction,
            "source_url": case.source_url,
            "latency_ms": round(latency_ms, 2),
            "scores": scores,
            "provider_metadata": {"model": args.model},
        }
        rows.append(row)
        print(
            f"[{index:03d}/{total_cases:03d}] {case.case_id} "
            f"token_f1={row['scores']['token_f1']:.4f} "
            f"rougeL={row['scores'].get('rougeL_f1') or 0:.4f} "
            f"words={row['scores']['word_count']} "
            f"latency_ms={row['latency_ms']:.2f}",
            flush=True,
        )
        if args.save_every > 0 and len(rows) % args.save_every == 0:
            write_progress(output_path, rows, argparse.Namespace(
                provider="hf-transformers",
                model=args.model,
                dataset=args.dataset,
                prompt_style=args.prompt_style,
            ), final=False)
            print(f"Saved progress at {len(rows)}/{total_cases} cases -> {output_path}", flush=True)
        if args.verbose:
            print(
                f"PRED: {prediction[:300]}",
                flush=True,
            )

    compute_bertscore(rows, args.disable_bertscore, args.bertscore_model)
    final_args = argparse.Namespace(
        provider="hf-transformers",
        model=args.model,
        dataset=args.dataset,
        prompt_style=args.prompt_style,
    )
    print(json.dumps(summarize(rows, final_args), indent=2))
    write_progress(output_path, rows, final_args, final=True)
    print(f"Wrote results to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
