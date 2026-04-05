# Benchmark Status

Last updated: 2026-04-05

## Current state

The local-intelligence eval is now useful for calibration and model comparison,
but it is not fully publish-ready yet.

What is working:

- the benchmark differentiates model behavior in believable ways
- the grading logic now tolerates common formatting noise
- the harness can run against multiple backends:
  - Hugging Face Jobs / `transformers`
  - GitHub Models
  - OpenRouter
  - Nous direct API

What is still incomplete:

- a few cards still reward exact schema shape more than product usefulness
- the reporting is good for internal work, but not yet editorially polished
- we still need a broader calibration slice on strong API models

## Results so far

### Multi-card benchmark runs

| Model | Backend | Cards | Passed | Avg score | Median latency | Exact parse | Normalized parse | Parse failure |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `google/gemma-4-E2B-it` | HF Jobs | 24 | 8 | 0.4931 | 4461 ms | 0.0000 | 0.9167 | 0.0833 |
| `google/gemma-4-E4B-it` | HF Jobs | 24 | 13 | 0.6181 | 6895 ms | 0.0000 | 0.9583 | 0.0417 |
| `google/gemma-4-26B-A4B-it` | HF Jobs | 24 | 9 | 0.5278 | 5944 ms | 0.0000 | 0.9167 | 0.0833 |
| `NousResearch/Hermes-3-Llama-3.1-8B` | HF Jobs | 24 | 7 | 0.4167 | 2874 ms | 0.8750 | 0.0000 | 0.1250 |
| `nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1` | HF Jobs | 24 | 2 | 0.1945 | 5519 ms | 0.3333 | 0.1250 | 0.5417 |

### Single-card calibration probes

These are not benchmark-quality comparisons yet. They only confirm provider
health and give a first sanity check on the `memo-auto-title` task.

| Model | Backend | Card | Result | Avg score | Latency |
|---|---|---|---|---:|---:|
| `openai/gpt-4.1` | GitHub Models | `memo-auto-title` | pass | 1.0000 | 1315 ms |
| `nousresearch/hermes-2-pro-llama-3-8b` | OpenRouter | `memo-auto-title` | pass | 1.0000 | 887 ms |
| `Hermes-4-70B` | Nous | `memo-auto-title` | partial fail | 0.6667 | 1444 ms |

## What the benchmark is telling us

### 1. The eval is not crazy

The current results are not flat or random. They show:

- clear separation between stronger and weaker models
- different failure modes by model family
- meaningful improvements after parser and alias normalization

That is what a useful eval should do.

### 2. The eval was initially too brittle

The earlier `Gemma 4 E4B` result looked like `0/24`, which was misleading.
After cleanup, the same model rose to `13/24`.

That change was not fake improvement in the model. It reflected:

- fenced JSON cleanup
- trailing token cleanup
- alias normalization
- better handling of collection-shaped outputs

This tells us the benchmark previously over-weighted formatting errors.

### 3. The current benchmark has real signal

The strongest result so far is `Gemma 4 E4B`, and it outperformed both:

- the smaller `Gemma 4 E2B`
- the larger `Gemma 4 26B-A4B`

That is a believable and interesting outcome. It suggests:

- more parameters do not automatically help
- architecture and alignment matter
- this task family is sensitive to output control, not just raw capability

### 4. The benchmark is still a product-contract eval, not a pure capability eval

Some cards still measure:

- task correctness
- product usability
- schema compliance

all at once.

That is okay for internal product work, but it makes public interpretation
harder unless we explain the scoring clearly.

## What makes a good eval

The current benchmark is close to good because it is grounded in real product
tasks. A good eval is usually:

### Representative

It should test work the product really needs, not just easy-to-grade trivia.

Good examples here:

- memo title generation
- action item extraction
- reminder normalization
- redaction
- project clustering

### Discriminative

It should separate strong behavior from weak behavior. If every model ties, the
eval is not useful.

We now have that.

### Stable

Tiny formatting differences should not overwhelm the result when the underlying
task answer is good.

We improved this, but we are not finished.

### Legible

A human should be able to explain why a model failed.

That is mostly true now, especially with:

- parse failures
- schema-or-task failures
- task failures

### Hard to game

A model should not be able to win by learning superficial answer shapes only.

This is why early fine-tuning on the current benchmark would be risky. With
only 24 hand-authored cards, a weak model could learn the answer format without
gaining the real product skill.

## Where the current eval is strongest

- real workflow framing
- structured outputs that mirror downstream product use
- now-good parser normalization
- good cross-provider portability

## Where the current eval is weakest

- some remaining schema brittleness on a few cards
- small benchmark size
- limited reference-model calibration so far
- no manual audit report yet for a curated subset of failures

## Practical conclusion

The current eval is good enough to:

- compare model families internally
- reject clearly weak candidates
- guide prompt and wrapper work
- decide which models are worth deeper investment

The current eval is not yet good enough to:

- publish a definitive leaderboard
- justify fine-tuning weak models
- make broad claims without a methodology note

## Recommended next steps

1. Run a 5-8 card calibration slice on strong API models:
   - `openai/gpt-4.1` via GitHub Models
   - `Hermes-4-70B` via Nous
   - one OpenRouter model

2. Inspect failures on the same small slice manually.

3. Tighten the remaining schema-sensitive cards before broader publication.

4. Keep `Gemma 4 E4B` as the leading open-model candidate for now.
