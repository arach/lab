# Core Eval v2

This directory defines the redesigned benchmark for Talkie's small workflow
intelligence tasks.

The goal of `core_eval_v2` is not to test broad agency or research-style
reasoning. The goal is much smaller and more practical:

> Given a short spoken note or transcript, can a model reliably turn it into a
> small, useful, structured artifact that helps the user act, remember, or
> organize?

## What v2 changes

The original eval mixed together three things:

- task correctness
- product usability
- exact schema conformance

`core_eval_v2` separates them.

Each card should be judged along three dimensions:

1. `task`
   Did the model solve the actual user-facing job?
2. `usable`
   Could the product use this with light normalization?
3. `contract`
   Did it match our exact preferred schema?

The current v1 benchmark is still useful, but it remains a draft blend of core
and stretch tasks. This v2 spec defines a smaller, cleaner, more defensible
benchmark.

## Core benchmark design rules

- Keep the benchmark small: 8-12 cards
- Use only product-real tasks
- Prefer semantic assertions over exact field names
- Accept multiple usable structured variants
- Keep stretch/research-y tasks out of the core score
- Require that a strong mainstream model looks obviously good on this set

## Files

- [PRINCIPLES.md](/Users/arach/dev/training-lab/eval/local_intelligence/v2/PRINCIPLES.md)
  The design rules for the benchmark
- [CORE_EVAL_V2_SPEC.md](/Users/arach/dev/training-lab/eval/local_intelligence/v2/CORE_EVAL_V2_SPEC.md)
  The card list, scoring model, and migration plan
