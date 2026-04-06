# Building Core Eval v2

> A good eval should tell the truth about the product, not just the parser.

<!-- METADATA
slug: building-core-eval-v2
date: 2026-04-05
tags: evals, benchmark-design, calibration, structured-output, local-intelligence
author: Arach
hidden: true
-->

## Why this post exists

The previous eval post was the reset.

That post was about admitting the first benchmark had drifted. We had built a
solid harness around a shaky question. A strong mainstream model was not
looking clearly strong on tiny workflow tasks, and that meant the benchmark was
still wrong in an important way.

What that post did **not** do was walk through the construction of the replacement.
It argued for a better eval, but it did not really show how we chose the tasks,
how we structured the scoring, and what rules we used to keep the new benchmark
honest.

This post is that missing piece.

It is the practical design document behind `core_eval_v2`, written in plain
English instead of benchmark shorthand.

## The problem we were actually trying to solve

The product question is much smaller than a generic AI benchmark usually
assumes.

We are not asking whether a model can:

- reason across arbitrary domains
- act autonomously for a long time
- manage a whole tool graph
- behave like a full personal agent

We are asking whether it can take a short spoken note or transcript and turn it
into something small, useful, and structured.

That means the real product loop looks more like this:

1. capture the note
2. extract what matters
3. normalize it into a usable shape
4. connect it to relevant context when needed
5. avoid hallucinating or overreaching

That is the loop the eval needs to measure.

Once we wrote it that plainly, a lot of the confusion disappeared.

## What was wrong with the first benchmark

The first benchmark mixed together three different questions:

1. Did the model solve the task?
2. Could the product use the output?
3. Did it follow our exact favorite schema?

Those are not the same question.

That sounds obvious in hindsight, but it created most of the brittleness.
A model could produce the right summary with the wrong field name. It could
return a useful action list in a top-level array instead of a wrapped object. It
could represent a scheduling intent correctly but in a different structured
packet than the one we preferred.

In all of those cases, the benchmark was too eager to say “fail.”

So the first design rule for V2 became:

> solve the task first, then evaluate usability, then evaluate exact contract

That sounds small, but it changes the whole benchmark.

## The design constraints for V2

We wrote down a small set of principles and then forced the benchmark to obey
them.

### 1. Product truth first

If a task is clever but not central to the actual product loop, it does not
belong in the core eval.

That immediately demoted a bunch of things that were interesting but too
architectural:

- local agent loops
- momentum scoring
- voice operating layer behavior
- live meeting state tracking
- knowledge graph maintenance

Those tasks may still matter eventually. They just should not decide whether
the benchmark is sane.

### 2. Strong models should look strong

This became our sanity rule.

If a strong mainstream model cannot post a clearly good score on the core set,
then either:

- the task is underspecified
- the grading is brittle
- the schema contract is too narrow
- or the benchmark is simply wrong

That rule turned out to be incredibly useful because it is hard to talk yourself
out of.

### 3. Small, auditable, explainable

Every core card should be easy to explain to a non-specialist.

Good core cards are things like:

- title this memo
- redact this transcript
- extract the action items
- ask a clarifying question if the reminder is ambiguous

If a card requires three paragraphs of architecture context before it makes
sense, it probably does not belong in the core eval.

### 4. Usability matters more than one exact JSON shape

The product can normalize a lot.

It can handle:

- aliases
- top-level arrays
- equivalent field names
- alternate but still safe representations

The benchmark should not punish those differences as harshly as real task
mistakes.

### 5. Keep the core benchmark hard to game

A small hand-authored eval can become a trap. If we optimize models too hard
against the benchmark before the benchmark is stable, we risk teaching them the
shape of the answer instead of the job itself.

So the core set had to stay:

- small enough to audit
- broad enough not to collapse into template memorization
- stable enough that a good score would mean something

## How we structured the benchmark

The cleanest move was to split the benchmark into layers.

### Core Eval v2

This is the benchmark that is supposed to answer the product question:

> Can a model do the small workflow task clearly and usefully?

It is deliberately small.

The current core set has ten cards.

### Stretch / draft benchmark

This is where we keep the broader, more architectural, more subjective tasks.
That older set is still useful, but it no longer gets to define sanity.

This split matters because it keeps us from mixing:

- product-real tasks
- internal architecture probes
- research-y ambition

into one misleading blended score.

## The actual core cards

We grouped the core set into three buckets.

### Capture

These cards ask whether the model can cleanly turn a note into a more useful
artifact.

| Card | Why it belongs |
|---|---|
| `memo-auto-title` | Tiny, useful, easy to judge |
| `memo-type-detection` | Useful routing signal |
| `transcript-cleanup-presets` | Real post-capture transformation |
| `private-redaction-pass` | High-value and safety-sensitive |

### Action

These cards ask whether the model can move from note content to the next usable
step.

| Card | Why it belongs |
|---|---|
| `action-item-extraction` | Very close to what people actually want |
| `reminder-normalization` | Good ambiguity-handling test |
| `calendar-intent-detection` | Common assistant task, but with looser acceptable shapes |
| `follow-up-question-generator` | Tests whether the model asks instead of inventing |

### Context

These cards ask whether the model can retrieve or compress the right surrounding
context.

| Card | Why it belongs |
|---|---|
| `similar-memo-recall` | Concrete memory retrieval task |
| `context-packet-builder` | Good proxy for useful compression |

That gives us ten cards that are practical, legible, and reasonably narrow.

## What we explicitly moved out

This was just as important as what we kept.

The easiest way to ruin a benchmark is to let every interesting task into the
core set.

So we moved out things like:

- project clustering
- daily brief generation
- contradiction drift detection
- model routing
- writing style memory
- checklist dependency logic
- local agent loop behavior
- voice OS command layer behavior

Some of those are still valuable. Some may come back in a future stretch suite.
But they are not part of the benchmark we use to answer the simple question:

> does this model seem natively capable of our small workflow tasks?

## The scoring model

This is the piece that made the new benchmark feel sane again.

Instead of forcing every card into one pass/fail bucket, V2 scores three
separate dimensions.

### 1. Task score

Did the model do the actual job?

Examples:

- the title is specific and not generic
- the redaction removes the sensitive information
- the right action item was extracted
- the retrieved memo is actually relevant

### 2. Usability score

Could the product use this output with light normalization?

Examples:

- the model used `matches` instead of `top_matches`
- it returned a top-level list instead of a wrapped object
- it used a different but still safe date packet
- it represented ranking or rationale differently but still usefully

### 3. Contract score

Did it match our exact preferred schema?

Examples:

- preferred field names
- preferred object nesting
- preferred packet wrapper
- preferred canonical representation

This is still useful. It just does not get to dominate the whole result.

That distinction gives us much more truthful interpretations.

A model can now be:

- high task
- high usability
- medium contract

and that tells us something practical:

> the model is probably good enough, but the product integration layer still
> needs normalization work.

That is a much better insight than a flat “fail.”

## The acceptance rules we had to loosen

A lot of the real design work was in defining what counts as an acceptable
variant.

### Memo type detection

The old benchmark encoded a narrow confidence preference into correctness.
That was a mistake.

The better check is:

- did the model choose an acceptable type?
- did it represent confidence numerically?
- did it handle uncertainty in some reasonable way?

### Transcript cleanup

The benchmark should care about preserved meaning, not exact phrasing. If the
model says `3 out of 5` instead of `3 of 5`, that should not sink the card.

### Calendar intent

This was one of the most obviously over-constrained cards.

The model should get credit for any safe, usable representation of scheduling
intent, including:

- event drafts
- scheduling packets
- direct event objects with unresolved fields

### Similar memo recall

We should care about whether the right memo came back with a usable rationale,
not whether the ranking object was named exactly the way we expected.

### Context packet builder

We should reward the useful compression itself:

- active tasks
- decisions
- open questions
- relevant memo references

not one single exact wrapper object.

## The calibration rule

Once we had the structure, we needed a discipline for checking whether it was
working.

That rule became:

> a strong mainstream model should look obviously good on the core eval.

Not perfect.
Not magical.
Just clearly good.

This is why the first `gpt-4.1` V2 slice mattered so much.

On a three-card V2 slice it posted:

```json
{
  "pass_rate": 1.0,
  "average_score": 0.95,
  "task_score": 1.0,
  "usable_score": 1.0,
  "contract_score": 0.6667
}
```

That result is almost more useful than a perfect score.

It says:

- the tasks are now reasonable
- the model solved them cleanly
- the output was fully usable
- and exact contract is still something separate we can improve

That is exactly the kind of signal we wanted.

## What we implemented in the repo

The benchmark is not just an essay now. It has a concrete shape in the repo.

Key files:

- [`eval/local_intelligence/v2/PRINCIPLES.md`](/Users/arach/dev/training-lab/eval/local_intelligence/v2/PRINCIPLES.md)
- [`eval/local_intelligence/v2/CORE_EVAL_V2_SPEC.md`](/Users/arach/dev/training-lab/eval/local_intelligence/v2/CORE_EVAL_V2_SPEC.md)
- [`eval/local_intelligence/v2/card_manifest_v2.json`](/Users/arach/dev/training-lab/eval/local_intelligence/v2/card_manifest_v2.json)
- [`eval/local_intelligence/v2/core_eval_v2_cards.json`](/Users/arach/dev/training-lab/eval/local_intelligence/v2/core_eval_v2_cards.json)
- [`eval/local_intelligence/grader.py`](/Users/arach/dev/training-lab/eval/local_intelligence/grader.py)
- [`eval/local_intelligence/run_eval.py`](/Users/arach/dev/training-lab/eval/local_intelligence/run_eval.py)

That matters because the benchmark is no longer only a theory.
We now have:

- written principles
- an explicit card set
- separate scoring dimensions
- calibration runs against real models
- a clearer story about what the benchmark is for

## What I would still treat as unfinished

Even though V2 is much better, I would still call it a living benchmark.

The biggest unfinished pieces are:

- broadening the calibration set beyond one great reference score
- continuing to test weaker and mid-tier models for healthy variance
- manually auditing failures to make sure the grader and product truth still
  agree
- deciding which stretch tasks deserve their own benchmark instead of staying in
  a pile of “interesting extras”

That is healthy unfinishedness, though. It is not the same as basic confusion.

## The real standard

The standard for this benchmark is simple.

A strong model should look strong.
A weak model should look weaker.
The score should tell us whether the problem is:

- the model
- the schema contract
- the product integration layer
- or the benchmark itself

That is what `core_eval_v2` is trying to do.

Not settle the whole question of intelligence.
Just tell the truth about a small workflow product.

And honestly, that is already hard enough.
