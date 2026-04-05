# 2026-04-05: Benchmark Scoreboard

<!-- METADATA
slug: benchmark-scoreboard
date: 2026-04-05
tags: evals, scoreboard, calibration, v2, gemma, github-models, nous, openrouter
author: Arach
-->

## What Changed

Today the blog started acting like the website for the benchmark itself.

Instead of only writing longform notes about the eval, we now have a compact
scoreboard post that can be appended over time with:

- model runs
- provider backends
- benchmark versions
- calibration snapshots

The idea is simple: keep a running visual story of what the benchmark is
showing us as we improve it.

## How To Read This

There are really two benchmark stories right now:

1. `local_intelligence` v1
   - the original 24-card pack
   - useful, but still mixes task correctness and contract brittleness

2. `core_eval_v2`
   - the new smaller benchmark
   - designed around task correctness, usability, and exact contract as
     separate ideas

The most important score right now is not the absolute highest score. It is
whether strong mainstream models look clearly strong on `core_eval_v2`.

## Scoreboard

### Core Eval v2

| Model | Provider | Cards | Pass | Avg | Task | Usable | Contract | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `openai/gpt-4.1` | GitHub Models | 3 | 3/3 | 0.95 | 1.00 | 1.00 | 0.67 | First healthy calibration anchor |

### Local Intelligence v1

| Model | Provider | Cards | Pass | Avg | Exact Parse | Normalized Parse | Parse Fail |
|---|---|---:|---:|---:|---:|---:|---:|
| `google/gemma-4-E2B-it` | HF Jobs | 24 | 8/24 | 0.4931 | 0.0000 | 0.9167 | 0.0833 |
| `google/gemma-4-E4B-it` | HF Jobs | 24 | 13/24 | 0.6181 | 0.0000 | 0.9583 | 0.0417 |
| `google/gemma-4-26B-A4B-it` | HF Jobs | 24 | 9/24 | 0.5278 | 0.0000 | 0.9167 | 0.0833 |
| `NousResearch/Hermes-3-Llama-3.1-8B` | HF Jobs | 24 | 7/24 | 0.4167 | 0.8750 | 0.0000 | 0.1250 |
| `nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1` | HF Jobs | 24 | 2/24 | 0.1945 | 0.3333 | 0.1250 | 0.5417 |

### Single-Card Calibration Probes

| Model | Provider | Card | Result | Avg | Latency |
|---|---|---|---|---:|---:|
| `openai/gpt-4.1` | GitHub Models | `memo-auto-title` | pass | 1.0000 | 1315 ms |
| `openai/gpt-4.1` | GitHub Models | `memo-type-detection` | pass | 1.0000 | 1445 ms |
| `openai/gpt-4.1` | GitHub Models | `transcript-cleanup-presets` | pass | 0.8500 | 1293 ms |
| `nousresearch/hermes-2-pro-llama-3-8b` | OpenRouter | `memo-auto-title` | pass | 1.0000 | 887 ms |
| `Hermes-4-70B` | Nous | `memo-auto-title` | partial fail | 0.6667 | 1444 ms |

## Interactive View

<details>
<summary><strong>Open the current benchmark interpretation</strong></summary>

### What looks strong

- `gpt-4.1` on `core_eval_v2` now looks clearly strong.
- `Gemma 4 E4B` is still the strongest open/local-ish model in the original
  24-card pack.

### What still looks drafty

- v1 still overweights schema and representation in a few places.
- some providers are more reliable than others for repeated calibration runs.

### What this means

The benchmark is no longer obviously broken, but the new benchmark line is the
one to trust going forward:

- `core_eval_v2` for sanity and selection
- v1 as a broader stretch pack

</details>

<details>
<summary><strong>Open the v2 anchor score JSON</strong></summary>

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

</details>

<details>
<summary><strong>Open the Gemma family sweep</strong></summary>

Job:

- `69d289624adb81dd2de74caf`

Results:

- `google/gemma-4-E2B-it` -> `8/24`, avg `0.4931`
- `google/gemma-4-E4B-it` -> `13/24`, avg `0.6181`
- `google/gemma-4-26B-A4B-it` -> `9/24`, avg `0.5278`

Takeaway:

- `E4B` is the strongest Gemma size we have seen so far.
- Bigger did not automatically mean better.

</details>

## What I Learned

- The blog can absolutely serve as the benchmark website for now.
- A scoreboard post is a better way to track the daily movement than rewriting
  the same longform article every time.
- `core_eval_v2` now has a real calibration anchor.

## Next

- Add more `core_eval_v2` scores to this page as they land.
- Add a second reliable model to show healthy variance on the new core set.
- Consider a generated index later if the daily scoreboard posts start to pile
  up.
