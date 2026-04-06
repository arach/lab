# Semantic Local Eval v1

This pack is the reset.

It exists for one reason:

> evaluate tiny and local models on the semantic usefulness of their answers,
> not on their willingness or ability to emit structured contracts.

## Design Rules

1. Ask for plain text unless structure is genuinely the product requirement.
2. Grade the meaning of the answer before its formatting.
3. Prefer short, real app moments over orchestrated multi-step workflows.
4. Make the tasks winnable for small local models.
5. Keep the outputs human-legible so failures are easy to inspect.

## What This Pack Measures

- Can the model title a memo usefully?
- Can it identify the best next step?
- Can it describe user intent in plain English?
- Can it rewrite a messy note without losing the facts?
- Can it summarize what matters?
- Can it ask a good clarifying question?
- Can it connect a note to a related prior memo?
- Can it notice sensitive information?
- Can it distinguish reflection from action?

## What This Pack Does Not Measure

- exact JSON schema obedience
- tool-calling reliability
- downstream contract compatibility
- agent-loop orchestration
- memory graph serialization

Those may still matter elsewhere, but they are not the right first test for
tiny local models.

## Scoring

Each card uses two layers:

- `task`: did the answer do the semantic job?
- `helpful`: was the answer concise and usable?

The pack passes a card when the semantic task passes and the helpfulness layer
is at least minimally acceptable.

## Local Models Run So Far

- `mlx-community/Qwen2.5-0.5B-Instruct-4bit`
- `mlx-community/Llama-3.2-1B-Instruct-4bit`
- `mlx-community/Qwen2.5-1.5B-Instruct-4bit`

Initial read:

- the pack is clearly winnable
- it is not flat
- family and alignment differences still matter

That is already a healthier place than the earlier contract-heavy evals.
