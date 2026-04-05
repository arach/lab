# Principles

## Product truth first

The benchmark exists to evaluate whether a model can help with the product's
real loop:

- capture
- extract
- normalize
- connect
- act

If a task is interesting but not central to that loop, it does not belong in
the core eval.

## Strong models should look strong

The benchmark is not sane unless a strong mainstream model can post a clearly
good score on the core set.

If a strong model fails mostly because of narrow schema expectations or brittle
phrasing checks, the benchmark is wrong.

## Task correctness is primary

The benchmark should reward semantic task success before exact contract match.

Good order:

1. solve the task
2. produce a usable structured output
3. match the ideal product contract

## Usability matters more than one exact JSON shape

The product can normalize:

- aliases
- list vs wrapped object
- alternate field names
- slightly different but equivalent representations

The benchmark should not punish those differences as harshly as true task
mistakes.

## Small, auditable, explainable

Every core card should be:

- easy to explain to a non-specialist
- easy to audit manually
- narrow enough to have a clear success condition

## Stretch tasks stay separate

Agent loops, trend detection, meeting-state updates, and similar architectural
tasks can remain in a stretch benchmark. They should not define whether the core
benchmark is reasonable.

## Hard to game

The benchmark should avoid rewarding superficial answer-template mimicry. This
is why:

- semantic checks matter
- benchmark size should stay manageable but non-trivial
- fine-tuning should wait until the core eval is stable

## Comparative, not absolute

The benchmark should help answer:

- which models are worth deeper investment
- whether output normalization or prompt work is enough
- whether a model family is fundamentally capable of the task shape

It should not pretend to be a complete measure of product quality.
