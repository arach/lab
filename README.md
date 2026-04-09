# training-lab

Experiments in voice interfaces, small models, and narrow eval design.

The repo has two related threads:

- older dictation-to-structure work for spoken syntax and protocol cleanup
- newer local-intelligence work around short voice notes, useful titles, and
  tiny intent extraction

The current focus is the second one.

## Current benchmark direction

The clean-slate pack in this repo asks one narrow question:

> Given a short voice note, can a model write a useful title and extract only
> the clearest action intent?

That pack currently lives here:

- [`eval/local_intelligence/title_intent_v1/cards.json`](/Users/arach/dev/lab/eval/local_intelligence/title_intent_v1/cards.json)
- [`eval/local_intelligence/title_intent_v1/TITLE_INTENT_V1_SPEC.md`](/Users/arach/dev/lab/eval/local_intelligence/title_intent_v1/TITLE_INTENT_V1_SPEC.md)

The benchmark is intentionally small:

- `12` cards
- tiny intent set: `none | research | email | call | schedule`
- scoring weighted toward title usefulness and restraint

Model/provider inventory and billing heuristics live in:

- [`MODEL_GUIDE.md`](/Users/arach/dev/lab/MODEL_GUIDE.md)

Why so small:

- title quality is broadly useful in voice-note products
- intent extraction is only interesting if the model does not overreach
- a tiny, auditable pack is easier to trust than a broad pseudo-assistant benchmark

## Repo structure

```text
app/                Next.js site shell for essays, notes, and benchmark views
blog/               Longform drafts and daily notes
components/         Reading UI and benchmark panels
eval/               Benchmark packs, runners, and external calibration work
lib/                TypeScript ports plus site data helpers
pipeline/           Model artifacts and earlier normalization work
processor/          Canonical Python procedural processor
scripts/            Experiments, harnesses, and utility scripts
training/           Training corpora, converters, adapters, and notes
```

## What stays from the older work

The earlier dictation pipeline is still part of the repo because it matters as
foundation work:

- spoken syntax reconstruction
- procedural token scanning
- protocol cleanup
- classifier gates for when to use more model help

That layer still lives in:

- [`lib/index.ts`](/Users/arach/dev/lab/lib/index.ts)
- [`processor/procedural.py`](/Users/arach/dev/lab/processor/procedural.py)
- [`scripts/test-protocol-processor.py`](/Users/arach/dev/lab/scripts/test-protocol-processor.py)

It is just no longer the active front-door story.

## Local benchmark work

The broader local-intelligence harness is still here:

- [`eval/local_intelligence/README.md`](/Users/arach/dev/lab/eval/local_intelligence/README.md)
- [`eval/local_intelligence/v2/README.md`](/Users/arach/dev/lab/eval/local_intelligence/v2/README.md)

But the current repo direction is to narrow before expanding again.

## External calibration

These experiments remain useful as side probes, not the main benchmark:

- [`eval/news_summarization/README.md`](/Users/arach/dev/lab/eval/news_summarization/README.md)
- [`eval/qmsum/README.md`](/Users/arach/dev/lab/eval/qmsum/README.md)

## Quick checks

```bash
# Run the older procedural processor test harness
python3 scripts/test-protocol-processor.py

# Build the site
bun run build
```
