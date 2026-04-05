# 2026-04-05: Model Calibration and Benchmark Sanity

<!-- METADATA
slug: model-calibration-and-benchmark-sanity
date: 2026-04-05
tags: evals, calibration, github-models, openrouter, nous, gemma
author: Arach
-->

## What Changed

Today we moved the local-intelligence eval from a single-provider experiment to
a real calibration harness.

We now have working providers for:

- Hugging Face Jobs / hosted inference
- GitHub Models
- OpenRouter
- Nous / Hermes direct API

We also cleaned up the grading logic so the benchmark is less brittle about
output shape, fenced JSON, and common field aliases.

## What I Ran

The main benchmark family sweep was Gemma 4:

- `google/gemma-4-E2B-it`
- `google/gemma-4-E4B-it`
- `google/gemma-4-26B-A4B-it`

That run used the baked GHCR image and finished as one job:

- `69d289624adb81dd2de74caf`

I also ran single-card sanity probes through:

- `openai/gpt-4.1` via GitHub Models
- `nousresearch/hermes-2-pro-llama-3-8b` via OpenRouter
- `Hermes-4-70B` via the direct Nous API

## What I Learned

- The benchmark is not crazy.
- It was too strict about parsing and schema shape, but once normalized it
  starts showing meaningful differences between models.
- Gemma 4 `E4B` looks like the strongest Gemma size for this task family.
- Smaller models can work, but the gap is real.
- GitHub Models, OpenRouter, and Nous all work well as calibration backends.

## Results

Gemma 4 family sweep:

| Model | Pass | Avg Score | Median Latency |
|---|---:|---:|---:|
| `google/gemma-4-E2B-it` | 8/24 | 0.4931 | 4461 ms |
| `google/gemma-4-E4B-it` | 13/24 | 0.6181 | 6895 ms |
| `google/gemma-4-26B-A4B-it` | 9/24 | 0.5278 | 5944 ms |

Calibration probes:

- GitHub Models `openai/gpt-4.1` on `memo-auto-title`: pass
- OpenRouter `nousresearch/hermes-2-pro-llama-3-8b` on `memo-auto-title`: pass
- Nous `Hermes-4-70B` on `memo-auto-title`: partial pass

V2 score snapshot:

```json
{
  "provider": "github_models",
  "model": "openai/gpt-4.1",
  "cards": 3,
  "passed": 3,
  "pass_rate": 1.0,
  "average_score": 0.95,
  "median_latency_ms": 1363.15,
  "exact_parse_rate": 1.0,
  "normalized_parse_rate": 0.0,
  "parse_failure_rate": 0.0,
  "task_score": 1.0,
  "usable_score": 1.0,
  "contract_score": 0.6667
}
```

## Next

- Clean up the provider wrapper layer so token handling and OpenAI-compatible
  request logic are shared.
- Run a short apples-to-apples calibration slice on a few important cards.
- Tighten the remaining cards that still feel too schema-specific.
