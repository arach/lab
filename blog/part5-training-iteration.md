# Part 5: From 18% to 79% in an Afternoon

> Six training runs, zero hyperparameter changes. Every accuracy jump came from fixing the data.

<!-- METADATA
slug: from-18-to-79-in-an-afternoon
series: teaching-a-tiny-model-to-hear-bash
part: 5
date: TBD
tags: fine-tuning, mlx, lora, training-data, on-device-ml, voice, dictation
author: Arach
-->

## Series context

- **Part 1** — Fine-tuned a 1.5B model to reconstruct bash from dictation. 97% accuracy, 3GB RAM, 0.7s inference.
- **Part 2** — Split architecture: deterministic processor for symbols, LLM for language understanding.
- **Part 3** — A classifier trained in 40ms gates whether input needs an LLM at all. 100% accuracy on held-out data.
- **Part 4** — Per-word classifier segments mixed speech so only command fragments hit the model.
- **Part 5** (this post) — Six training runs took accuracy from 18% to 79%. Every fix was in the data, not the model.

## The setup

A 1.7B parameter model (Qwen3-1.7B), LoRA fine-tuned on a Mac mini M4 with 16GB RAM. Training takes 20 minutes per run. The eval set is 100 hand-written dictation-to-bash pairs across 31 categories — git, docker, curl, ssh, kubernetes, terraform, and more.

The goal: take dictated speech like "git space push space dash u space origin space main" and reconstruct `git push -u origin main`. The dictation protocol uses words like "dash", "dot", "slash", "space", "capital", "all caps" as literal syntax markers.

7,400 training examples. One system prompt. One eval script. Let's see what breaks.

## Run 1: 18% — The regex that ate the output

First eval: 18% exact match. Terrible. But something looked wrong in the failures — the model was producing empty strings for everything.

The Qwen3 model outputs a thinking prefix before every response:

```
<think>

</think>
git push -u origin main
```

The stripping code had two regexes:

```python
# Strip closed think blocks
text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
# Strip unclosed think blocks
text = re.sub(r'<think>.*', '', text, flags=re.DOTALL).strip()
```

The first regex correctly removes `<think>...</think>`. But the second regex — intended for unclosed blocks — matches `<think>` and then `.*` with `re.DOTALL` consumes *everything after it*, including the actual output.

The model was right. The eval was wrong.

Fix:

```python
text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
text = re.sub(r'^<think>\s*', '', text).strip()  # only strip prefix
```

This didn't change accuracy much by itself (the model was still bad), but it meant we could trust the eval.

## Run 2: 58% — The system prompt that mattered more than anything

Still at ~30% after the regex fix. Looking at the failures, the model was producing reasonable-looking output but with odd formatting — extra spaces, wrong symbol choices, inconsistent behavior.

Then I checked the system prompts.

Training used: `"Reconstruct the intended syntax from the dictated text. Output only the result."`

Eval used: `"Convert dictated speech to bash. Words like dash, dot, slash, space, colon are literal symbols. Output ONLY the command."`

Same intent. Completely different prompt. Swapping to the exact training prompt:

**30% → 58%.**

A 28-point accuracy jump from matching a string. The model wasn't confused about bash — it was confused about what it was being asked to do. A fine-tuned model builds strong associations between the system prompt and the expected behavior pattern. Change the prompt, break the associations.

This is the single most important lesson from the entire exercise: **your eval system prompt must be identical to your training system prompt.** Not similar. Identical.

## Run 3: 68% — The training data that taught nothing

At 58%, the failures clustered around capitalization. Every `capital X` and `all caps Y` example was wrong. The model treated "capital" as a regular word, passing it through unchanged.

I looked at the training data:

```json
{"user": "capital Talkie", "assistant": "Talkie"}
{"user": "all caps POST", "assistant": "POST"}
```

"capital Talkie" → "Talkie". The word was already capitalized in the input. The model learned: see "capital", output the next word as-is. Which is what it does. Correctly. From its perspective.

75 out of 77 `capital X` examples had this bug. The training data was teaching pass-through, not transformation.

Fix: lowercase everything after `capital` and `all caps`:

```json
{"user": "capital talkie", "assistant": "Talkie"}
{"user": "all caps post", "assistant": "POST"}
```

Now the model has to learn the transformation. **58% → 68%.** Ten points from fixing the case of training examples.

The principle: **if the input and output are the same, the model learns nothing.** Training data must demonstrate the transformation you want, not the identity function.

## Runs 4-6: 68% → 71% → 78% → 79% — Targeted augmentation

With the big systemic bugs fixed, the remaining failures fell into specific patterns. Each run added 60-125 targeted training examples:

**Run 4 (71%): Spacing and boundaries**
Multi-character flags like `-sL`, `-rn`, `-sh` — the model inserted spaces between flag characters. IP addresses got truncated. Path separators merged wrong.

Added examples: `"dash s capital l" → "-sL"`, `"one nine two dot one six eight dot one dot one" → "192.168.1.1"`, `"dot slash dot dot dot" → "./..."`

**Run 5 (78%): The big targeted push**
Analyzed all 28 remaining failures, categorized them into 7 patterns, wrote examples for each:
- `all caps` inside quotes: `'grep -rn "TODO" .'`
- `all caps` for single letters: `"all caps a" → "A"`
- Multi-char flags in curl, grep, du
- Full IP addresses with "one hundred" → "100"
- `at` as `@`: `"at hono" → "@hono"`
- `sed -i '' '...'` (empty string quoting)
- `./...` Go test pattern

**Run 6 (79%): Diminishing returns**
Targeted `./` path prefixes, `--` double dashes, colon joins, bracket regex.

One point. And three Docker cases regressed.

```
v3   68%   Fixed capital/allcaps data
v4   71%   Spacing/boundary examples
v5   78%   7 targeted failure categories
v6   79%   Path/dash/colon patterns (with regressions)
```

## The augmentation see-saw

Run 6 is where the pattern changed. Adding 62 examples for `./` paths and `--` double dashes fixed those specific patterns — but broke Docker commands, Xcode builds, and Rust cargo commands that worked in v5.

The model wasn't learning new capabilities. It was reallocating attention. Fix the SSH examples, Docker regresses. Fix Docker, Rust regresses. The total accuracy stays around 79%, but the failures shuffle.

This is the capacity ceiling. A 1.7B model with 7,700 training examples can hold about 80% of the pattern space for this task. Pushing past it requires one of:

1. **More diverse base training data** — not patches, but a larger foundation
2. **Larger model** — more parameters to hold more patterns
3. **Not using the model at all** — the procedural processor already handles 96% of clean protocol input at 11 microseconds

The answer is probably option 3 with the model as fallback for genuinely ambiguous input.

## What I'd do differently

**Start with the eval, not the model.** I spent time debugging model behavior that turned out to be eval bugs (regex, system prompt). A correct eval is table stakes.

**Audit training data before training.** The capitalization bug wasted a full training run. Five minutes of grep would have caught it:

```bash
grep '"capital [A-Z]' train.jsonl | head
```

**Don't patch. Regenerate.** The augmentation approach — adding 60-125 examples per run — works until it doesn't. The base training set should be generated with these patterns included from the start, not bolted on after.

**Track per-category accuracy across runs.** I should have built a comparison table from run 1. Seeing that Docker went from 6/7 → 3/7 between v5 and v6 would have been an immediate signal to stop augmenting and rethink.

## The numbers

| | v3 | v4 | v5 | v6 |
|---|---|---|---|---|
| **Exact match** | 68% | 71% | 78% | 79% |
| **Case-insensitive** | 72% | 72% | 82% | 80% |
| **Training examples** | 7,377 | 7,593 | 7,718 | 7,780 |
| **Training time** | 20m | 20m | 20m | 20m |
| **Peak GPU memory** | 4.5GB | 4.5GB | 4.6GB | 4.6GB |
| **Quantized model size** | 934MB | 934MB | 934MB | 934MB |
| **Inference latency** | ~480ms | ~480ms | ~500ms | ~475ms |

All runs: Qwen3-1.7B, LoRA rank 16, lr 5e-5, 3000 iterations, 4-bit quantization. Mac mini M4, 16GB RAM.

## Code references

- `datasets/finetune/bash-v{3-6}/train.jsonl` — training data for each version
- `datasets/eval-independent.json` — 100 labeled dictation-to-command pairs
- `datasets/procedural-processor.py` — deterministic protocol processor (96%, 11μs)
- `macOS/TalkieInference/TalkieInference/InferenceService.swift` — MLX inference service
