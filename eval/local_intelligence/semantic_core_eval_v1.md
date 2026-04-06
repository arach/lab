# Semantic Core Eval v1

This pack is a reset.

It assumes tiny local models should be judged on semantic usefulness, not on
their ability to emit perfect structured output.

## Principles

1. Ask what the app actually needs from the model in that moment.
2. Prefer plain-language answers over JSON when structure is not the product
   requirement.
3. Reward semantic usefulness first:
   - did the model understand the memo?
   - did it suggest the right help?
   - did it preserve the important facts?
4. Treat formatting discipline as secondary.
5. Keep the pack small, concrete, and easy to audit by eye.

## Core app moments

1. Give this memo a useful title
2. What kind of memo is this?
3. What should the user do next?
4. Rewrite this memo more clearly
5. What matters most?
6. Should this become a reminder?
7. Should this become a calendar event?
8. What follow-up question should we ask?
9. Which old memo is most similar?

## What this pack is not

It is not a function-calling benchmark.

It is not trying to measure:

- exact JSON obedience
- nested schema reliability
- routing policy output
- agent-loop state machines
- knowledge graph packet generation

Those may still matter elsewhere, but they are not the right default eval for
tiny local models.

## Scoring

Each card uses three dimensions:

- `task`: did the answer get the substance right?
- `clarity`: was the answer concise and readable?
- `discipline`: did it avoid obvious bad habits like filler or evasive format?

Passing requires the task dimension to pass and the supporting dimensions to be
at least decent.
