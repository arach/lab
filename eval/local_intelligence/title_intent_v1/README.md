# Title + Intent Pack v1

Focused benchmark for one narrow post-capture question:

> Given a short voice note, can a model write a useful title and extract only
> the clearest action intent?

This pack is deliberately smaller than the broader workflow benchmark work.
It is meant to be the clean-slate pack for the current repo direction.

## Scope

- `12` cards total
- `4` title-heavy cards
- `4` clear intent cards
- `4` restraint cards where the right move is **not** to guess

## Output contract

Return only:

- `title`
- `intent`
- `target`

Allowed intents:

- `none`
- `research`
- `email`
- `call`
- `schedule`

`target` should only be filled when the action target is explicit in the note.

## Why this pack exists

- Title quality is broadly useful in a voice-note product.
- Tiny intent extraction is interesting only when it stays restrained.
- This keeps the benchmark close to the capture moment instead of drifting into
  broad assistant behavior.

## Files

- [`cards.json`](/Users/arach/dev/lab/eval/local_intelligence/title_intent_v1/cards.json)
  Draft 12-card pack
- [`TITLE_INTENT_V1_SPEC.md`](/Users/arach/dev/lab/eval/local_intelligence/title_intent_v1/TITLE_INTENT_V1_SPEC.md)
  Scoring model, pack structure, and prompt shape
- [`run_eval.py`](/Users/arach/dev/lab/eval/local_intelligence/title_intent_v1/run_eval.py)
  Minimal runner for this pack using the shared provider adapters

## Example

```bash
python3 eval/local_intelligence/title_intent_v1/run_eval.py \
  --provider github_models \
  --model openai/gpt-4.1-mini \
  --verbose
```
