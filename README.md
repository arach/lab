# training-lab

Experiments in voice dictation to programming syntax. Teaching small models to understand spoken code.

## Domain

Converting spoken dictation like `"git space push space dash u space origin space main"` into actual syntax: `git push -u origin main`.

The challenge: users don't always speak in perfect protocol format. They use synonyms ("minus" for "dash"), skip separator words, add conversational filler ("okay so the command is..."), and make mid-sentence corrections ("no wait, actually...").

## Architecture

```
Raw speech transcript
  → Protocol detector (is it already clean?)
  → IF clean: bypass LLM → procedural processor
  → IF messy: LLM normalizer → procedural processor
  → Final syntax output
```

**Procedural processor** — deterministic token scanner. Symbol vocabulary, number words, casing directives. 93% on clean input, zero hallucination, instant.

**LLM normalizer** — rewrites messy dictation into clean protocol format. Strips filler, resolves corrections, inserts spacing keywords. The LLM never outputs actual symbols — it only outputs protocol words.

## Structure

```
lib/                TypeScript ports of the core classifiers + processor
processor/          Canonical Python procedural processor
pipeline/           Canonical model artifacts + zero-training normalizer
eval/               Canonical evaluation datasets and runners
training/
  data/             Canonical training corpora
  converters/       Dataset generation and conversion scripts
  adapters/         Fine-tuned model adapters (LoRA/DoRA)
  finetune/         Generated JSONL splits and training notes
scripts/            Experiments, eval harnesses, and compatibility wrappers
blog/               Writeup drafts, daily notes, and longform posts
blog/daily/         Short TIL-style logs for runs, lessons, and results
```

The refactor is moving the repo toward one canonical home for each kind of
artifact: datasets in `eval/` and `training/data/`, model JSON in `pipeline/`,
core Python runtime in `processor/`, and TypeScript ports in `lib/`.

## Local Intelligence Evals

```bash
# Export the 24-case Talkie local-intelligence pack for notebook use
python3 eval/local_intelligence/push_to_hf.py --dry-run

# Run the rebuilt harness against a replay file or local provider
python3 eval/local_intelligence/run_eval.py --provider replay --replay-file /tmp/local-intelligence-replay.jsonl --limit 1
```

## Quick start

```bash
# Run the procedural processor on clean protocol input
python3 processor/procedural.py eval/independent.json

# Run the protocol processor test harness
python3 scripts/test-protocol-processor.py

# Run the normalizer pipeline (requires mlx-lm)
pip install mlx mlx-lm
python3 pipeline/normalizer.py eval/fuzzy.json --model mlx-community/Qwen2.5-1.5B-Instruct-4bit

# Generate finetune splits from the canonical training corpus
python3 training/converters/prepare-finetune.py
```

## Results (zero-training, prompted only)

| Model | Clean | Fuzzy | Natural | Chaotic | Overall |
|---|---|---|---|---|---|
| Processor only | 92% | 0% | 0% | 2% | 23.5% |
| Qwen 2.5 1.5B | 90% | 20% | 54% | 24% | 47% |
| Qwen 2.5 0.5B | 90% | 12% | 44% | 20% | 41.5% |
| Llama 3.2 1B | 92% | 14% | 34% | 10% | 37.5% |

## Protocol format

The "space-as-a-word" protocol eliminates spacing ambiguity:

- `"space"` → literal space between tokens
- Symbol words: `dash dot slash pipe colon quote` etc.
- Casing: `camel case`, `snake case`, `pascal case`, `kebab case`
- Numbers: `zero` through `nineteen`, `twenty`...`ninety`, `hundred`, `thousand`
- Capitalization: `capital X`, `all caps WORD`
