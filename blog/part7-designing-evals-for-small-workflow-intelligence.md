# Part 7: Designing Evals for Small Workflow Intelligence

> If a strong mainstream model can't clearly do well, the benchmark is wrong.

<!-- METADATA
slug: designing-evals-for-small-workflow-intelligence
series: teaching-a-tiny-model-to-hear-bash
part: 7
date: 2026-04-05
tags: evals, benchmark-design, structured-output, local-intelligence, model-evaluation
author: Arach
-->

## The turn

For a while, the eval looked productive.

We had a harness. We had model sweeps. We had Hugging Face Jobs, GitHub Models,
OpenRouter, and direct provider APIs all wired up. We had JSON outputs, pass
rates, latency numbers, and a growing pile of result files.

And then the most useful thing happened: the benchmark started disagreeing with
the product.

A strong mainstream model did not look clearly strong on what were supposed to
be small, practical tasks. Not protein folding. Not frontier planning. Tiny
workflow challenges:

- title a memo
- extract an action item
- normalize a reminder
- redact a transcript
- find a related note

At that point, the right question is no longer "How do we get a better score?"
It's "What are we actually evaluating?"

This post is the reset.

## The original problem

The product problem was never "build a benchmark for general intelligence."

It was much smaller:

> Given a short spoken note or transcript, can a model turn it into a small,
> useful, structured artifact that helps the user act, remember, or organize?

That's it.

The tasks we care about are narrow and practical:

- summarize what matters
- turn vague speech into a reminder
- pull out an action item
- create a decent title
- retrieve something similar from prior notes
- package enough context for the next step

This is not a research benchmark for broad agency. It's a benchmark for
workflow usefulness.

That distinction matters, because it tells us what a good eval should reward.

## What went wrong in the first eval

The first version of the eval bundled together three different ideas:

1. **Task correctness**
2. **Product usability**
3. **Exact schema obedience**

Those are not the same thing.

A model can solve the task and still miss the benchmark if:

- it uses `summary` instead of `topPoints`
- it returns a list instead of `{ "items": [...] }`
- it says `3 out of 5` instead of `3 of 5`
- it returns a usable calendar intent in a different shape than the one we
  happened to prefer

We saw exactly that.

The most dramatic example was `Gemma 4 E4B`. An early run looked like a
complete disaster. After normalization and better grading, the same model moved
to a much healthier result. The model had not magically become smarter. The
benchmark had simply stopped punishing it for harmless output variation.

That was the real lesson:

> the eval was over-weighting formatting and under-weighting product truth.

## The calibration signal we needed

The most important benchmark run was not the one with the highest score. It was
the one that forced us to admit the benchmark still was not sane enough.

We ran `gpt-4.1` through GitHub Models as a calibration model. It started strong
and then hit provider rate limits before finishing the full set, but the first
ten cards were already enough to tell the story.

Some failures were legitimate.

Some were obviously benchmark-shaped:

- a memo-type card failing because the model was *too confident*
- a cleanup card failing because it wrote `3 out of 5` instead of `3 of 5`
- a summary card failing because it used a slightly different field name
- a calendar card failing because it expressed the right outcome in a different
  representation

If a strong mainstream model can't clearly look strong on tiny workflow tasks,
the benchmark is not done.

Not useless. Not hopeless. Just not done.

## What a good eval should do

A good eval for this problem space should be:

### Representative

It should reflect real product work, not synthetic cleverness.

Good:

- title generation
- action extraction
- reminder normalization
- redaction
- related-note retrieval

Less good as core tasks:

- full agent loops
- voice OS orchestration
- broad personal knowledge graph updates

Those may still matter, but they are stretch tasks, not sanity tasks.

### Discriminative

A stronger model should do better than a weaker one in a way that makes sense.

We have started to see that:

| Model | Result |
|---|---:|
| `google/gemma-4-E2B-it` | 8/24 |
| `google/gemma-4-E4B-it` | 13/24 |
| `google/gemma-4-26B-A4B-it` | 9/24 |
| `NousResearch/Hermes-3-Llama-3.1-8B` | 7/24 |
| `Nemotron Nano 4B` | 2/24 |

Those numbers are not the whole story, but they are at least not flat noise.

### Stable

Small phrasing or schema variations should not overwhelm the result when the
underlying task answer is good.

This is where the first eval was weakest.

### Interpretable

A failure should tell us something actionable:

- the model missed the task
- the model was useful but schema-wrong
- the model returned invalid JSON
- the model was overconfident in an ambiguous case

If all failures collapse into "fail," we learn very little.

### Hard to game

We should be careful not to train or benchmark models into looking good by
memorizing answer shapes. With a small hand-authored set, it is easy to create
the illusion of progress by teaching to the eval.

This is why fine-tuning weak models against the current set would be premature.

## The shape of a better eval

The cleanest fix is not more patches. It's a better structure.

I would split the benchmark into two layers.

## Core Eval v2

This is the benchmark that should answer the product question:

> Can a model do the small, useful workflow task?

It should be small. Around 8 to 12 cards.

It should include only tasks that are:

- clearly product-real
- small enough to be fair
- easy to explain to someone outside the project

### Suggested core categories

#### Capture

- memo auto-title
- memo type detection
- transcript cleanup
- private redaction

#### Action

- action item extraction
- reminder normalization
- calendar intent detection
- follow-up question generation when info is missing

#### Context

- similar memo recall
- context packet builder
- maybe project clustering

That alone is a meaningful benchmark.

## Stretch Eval

This is where we keep the more ambitious tasks:

- agent loops
- contradiction tracking
- momentum scoring
- live meeting structure
- voice operating layer
- trend alerts

These are still useful. They just should not define whether the benchmark is
reasonable.

## A better scoring model

The other change is to stop pretending every card has one perfect JSON answer.

Each card should score along three dimensions:

### 1. Task correctness

Did the model do the actual job?

### 2. Product usability

Could the product use this with light normalization?

### 3. Exact contract match

Did it match our preferred schema exactly?

Those are three different things.

A model can be:

- high on task correctness
- medium on usability
- low on exact contract

That is not a failure. That is a usable model that needs wrapper work.

Once those three are separated, the benchmark becomes much easier to reason
about.

## Prior art, but not copy-paste

We are not inventing this problem space out of thin air.

There is relevant prior art in:

- function calling and structured output evals
- meeting summarization datasets
- task-oriented dialogue benchmarks
- assistant memory benchmarks

But there is not a single off-the-shelf benchmark for:

> voice memo -> small workflow artifact

So the right approach is:

- borrow evaluation principles from prior art
- keep the tasks grounded in the actual product loop

That means learning from public benchmarks without forcing this problem into
someone else's shape.

## The operational lesson

One thing did work extremely well: the benchmark harness itself matured fast.

We now have:

- Hugging Face Jobs for family sweeps
- GitHub Models for strong mainstream calibration
- OpenRouter for broad model access
- direct Nous/Hermes for a cleaner reference path
- a shared provider layer instead of one-off wrappers
- a daily-note lane in the repo to capture results and reasoning

That infrastructure was worth building.

But infrastructure creates a temptation: once the harness feels good, it's easy
to assume the benchmark must be good too.

That's not true.

A polished pipeline can still be measuring the wrong thing.

## What comes next

The next step is not another giant model bakeoff.

It's a redesign.

### 1. Define `core_eval_v2`

Pick 8 to 12 truly core tasks.

### 2. Separate scoring dimensions

Task correctness, usability, exact contract.

### 3. Calibrate with strong mainstream models

If a strong model cannot post a clearly good score, the benchmark is still not
ready.

### 4. Keep stretch tasks separate

Interesting is not the same thing as foundational.

## The real standard

The standard for this benchmark is simple:

> A strong mainstream model should look obviously good on the core eval.

Not perfect. Not magical. Just obviously good.

If it doesn't, the benchmark is still overcooked.

That is the bar for the next version.

## A first V2 score

Once we split the benchmark into a smaller `core_eval_v2` and separated
`task`, `usable`, and `contract` scoring, the result started to look much more
like the product we were actually trying to evaluate.

We ran a 3-card `core_eval_v2` slice on `openai/gpt-4.1` through GitHub Models:

- `memo-auto-title`
- `memo-type-detection`
- `transcript-cleanup-presets`

Result:

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

This is the kind of benchmark signal we wanted all along.

The model looks clearly strong on the actual job:

- it solved the tasks
- it returned usable outputs
- it still showed some variance on exact contract match

That is a much healthier benchmark story than a single brittle pass/fail number.
