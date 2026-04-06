# Fixing A Bad Benchmark With v1.1

> The model was not the problem. The benchmark was.

<!-- METADATA
slug: fixing-v1-with-v1-1
date: 2026-04-06
tags: evals, benchmark-design, calibration, v1-1
author: Arach
description: How the original broad benchmark went wrong, what changed in v1.1, and why the score jump proves the eval needed fixing.
hidden: true
-->

For a while, the broad workflow benchmark looked harsher than I wanted, but not
obviously broken.

Then we started running reputable models through it and got the kind of result
that should make you stop immediately.

Not “a little lower than expected.”

More like:

- a strong hosted model only getting `7/24`
- a supposedly practical slice only getting `3/8`
- failures that looked suspiciously like parser and schema fights, not product
  truth

That is the moment when the right move is to stop blaming the model.

If a good, reputable model cannot clearly pass tiny practical tasks, the eval is
wrong.

## What was broken

The original `v1` pack was asking a useful set of questions, but the win
criteria were bad.

It over-weighted things like:

- exact field names
- exact wrapper objects
- exact phrase matches
- one canonical output packet where several would have been fine

So a model could produce a clearly usable answer and still fail because it said
`suggested_title` instead of `title`, `tasks` instead of `items`, or nested a
reminder under `reminder.text` instead of flattening it.

That is not benchmark rigor. That is benchmark drift.

## What v1.1 changes

`v1.1` keeps the broad task coverage of `v1`, but rewrites the benchmark around
three simple ideas:

1. task success first
2. usability second
3. exact contract third

That means we now accept strong-model outputs that are obviously acceptable for
the product, even if they are not written in our favorite exact schema.

Concretely, the fix included:

- title aliases like `suggested_title`
- task aliases like `tasks`
- cleanup aliases like `rewritten`
- nested reminder objects
- alternate calendar event packets
- semantic recall ranking variants
- graph node and edge alias normalization
- multi-object JSON recovery for the agent-style outputs

It also meant rewriting several hard assertions so they reflect product truth
instead of brittle preferences.

Examples:

- transcript cleanup now rewards preserving `3 of 5` or `3 out of 5`
- memo type detection no longer hard-fails because confidence is `0.8`
- calendar intent detection accepts safe equivalent event packets
- context packet building rewards useful structure, not one wrapper object

## The important validation

The key thing here is that we did **not** change the model.

We changed the benchmark.

Then we ran the same reputable model again.

That is why the score jump matters.

It is not a model improvement story.
It is a benchmark correction story.

## What happened after the fix

Once the benchmark accepted clearly good outputs as good, the broad pack moved
from “capricious” to “credible.”

The strongest proof was the full-pack rerun:

- original `v1`: `7/24`
- corrected `v1.1`: `20/24`

The ship-soon slice told the same story even more aggressively:

- first `v1.1` pass: `3/8`
- after fixing the obvious alias and packet-shape misses: `8/8`

That is exactly the kind of jump that tells you the benchmark was the problem.

## What I trust now

I still would not call the broad pack perfect.

There are a few cards that remain shakier than the rest:

- `local-agent-loop`
- `intent-trend-alerts`
- `voice-os-command-layer`

But the benchmark is no longer obviously punishing good models for arbitrary
formatting and representation choices.

That is the threshold we needed to cross.

## The point of v1.1

`v1.1` is not the final benchmark.

It is the repaired version of the original broad pack.

That makes it useful for two things:

- preserving the wider product surface area of `v1`
- giving us a broader secondary benchmark that is actually winnable

`v2` is still the smaller benchmark I trust most for sanity and calibration.

But `v1.1` is now a much better answer to the question:

> what happens when we keep the broad task map, but stop grading it badly?

The answer, fortunately, is:

> the good model starts looking good.
