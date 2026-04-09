# Title + Intent Pack v1 Spec

## Core question

Can a small model make a fresh voice note more usable by doing two things well:

1. giving it a useful title
2. extracting only the clearest action intent

This pack is not trying to measure:

- broad summarization
- retrieval
- agent planning
- reminder logic
- long-form cleanup
- large schema obedience

## Output shape

Every card expects the same lightweight response shape:

```json
{
  "title": "Lease addendum question for landlord",
  "intent": "email",
  "target": "landlord about summer subletting"
}
```

Rules:

- `title` should be concise, specific, and list-view useful
- `intent` must be one of `none | research | email | call | schedule`
- `target` must be empty unless the action target is explicit in the note

## Pack composition

### 1. Title slice

Four notes where the main challenge is naming the note well.

What we want:

- specific titles
- no generic filler
- no fake action intent

### 2. Intent slice

Four notes with clear action language and an explicit target.

What we want:

- right label
- right target
- title still remains useful

### 3. Restraint slice

Four notes where the user is vague, conflicted, or still describing.

What we want:

- `intent = none`
- empty target
- title still captures the note

## Scoring

Each card is scored on three dimensions:

### `title_task` — 50%

Question:

Would a human actually want this as the note title?

High score means:

- specific rather than generic
- reflects the note's center of gravity
- compact enough for list view

### `intent_task` — 35%

Question:

Did the model identify the right action label, and did it keep the target
grounded in the note?

High score means:

- correct label from the tiny set
- target only includes explicit information
- no action-channel confusion such as `email` vs `call`

### `restraint` — 15%

Question:

Did the model avoid inventing action, target, or false certainty?

High score means:

- returns `none` when the note is ambiguous
- leaves target empty when the target is not explicit
- respects spoken corrections like "actually wait"

## Pass criteria

A card should be treated as a practical pass when:

- the title is clearly usable
- the intent label is correct
- the model does not invent a target or action

Suggested threshold:

- card score `>= 0.85`

Also track slice scores separately:

- title slice average
- intent slice average
- restraint slice average

That helps distinguish:

- weak naming
- weak routing
- over-eager guessing

## Design rules

- Prefer product usefulness over rich schema
- Keep the label set tiny
- Reward restraint, not just confidence
- Make every card easy to audit in under a minute
- Treat title quality as the primary value layer

## Prompt shape

Recommended prompt:

```text
You write titles for voice notes and detect only the clearest action intent.

Return JSON only with:
- title
- intent
- target

Rules:
- Write one concise, specific title.
- intent must be one of: none, research, email, call, schedule.
- Use none unless the action is clearly explicit.
- Only fill target when the note explicitly says who or what the action is about.
- Do not invent timing, people, or next steps.
```

## Why this pack is small

The point of this version is not coverage. The point is trust.

If this pack becomes trustworthy, it gives the repo a clean foundation for
future expansions such as:

- `buy`
- calendar intent
- rewrite clearly
- what matters most
