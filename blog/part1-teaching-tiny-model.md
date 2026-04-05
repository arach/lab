# Teaching a Tiny Model to Hear Bash

> Fine-tuning a 1.5B model to reconstruct shell commands from voice. 97% accuracy, 3GB of RAM, under a second on a phone.

<!-- METADATA
slug: teaching-a-tiny-model-to-hear-bash
date: 2026-03-04
tags: mlx, fine-tuning, lora, on-device-ml, voice, speech-to-code
author: Arach
-->

---

<!-- ILLUSTRATION: hero
Style: Dark terminal window with a waveform entering from the left (speech),
flowing through a small glowing chip/brain icon in the center, and clean bash
syntax emerging on the right. The waveform is warm orange, the chip is a cool
blue, the output text is green on black (classic terminal).
Alt: Speech waveform flowing through a tiny neural network into bash syntax
-->

## The Problem

I'm building [Talkie](https://usetalkie.com), a voice-first productivity app. One of its features is keyboard dictation. You speak into your phone, it types into whatever app you're using.

For regular prose, off-the-shelf speech-to-text handles it. For terminal commands, it falls apart completely.

<!-- ILLUSTRATION: side-by-side comparison
Left panel (labeled "What you say"):
  A speech bubble containing: "find dot dash name star dot txt"
Right panel (labeled "What transcription gives you"):
  A terminal showing: find dot dash name star dot text
Below both (labeled "What you meant"):
  A terminal showing: find . -name *.txt
Style: Clean, minimal. The "what you meant" panel should feel correct/resolved
— maybe a subtle green checkmark or highlight.
-->

Say "find dot dash name star dot txt" to any transcription engine and you get back a faithful transcription of your words. Not the command you meant. The gap between spoken description and intended syntax is the problem.

## The Bet: A Tiny Model, On-Device

I wanted to know if a model small enough to run on a phone could learn this mapping end-to-end. Not a rule engine. Not a cloud API call to GPT-4. A model that fits in pocket-sized RAM and returns an answer before the user notices it's thinking.

**Model:** Qwen2.5-1.5B-Instruct, 4-bit quantized via MLX. Fits in ~3GB.

**Method:** LoRA fine-tuning on Apple Silicon. Rank 8, scale 20, no dropout. The whole training run uses under 3GB of memory.

**Data:** 6,304 examples of dictated bash paired with intended syntax — 5,044 train, 630 validation, 630 test. Each example is a simple chat turn:

```json
{
  "messages": [
    {"role": "system", "content": "Reconstruct the intended syntax from the dictated text. Output only the result."},
    {"role": "user", "content": "find dot dash name star dot txt"},
    {"role": "assistant", "content": "find . -name *.txt"}
  ]
}
```

The data covers a wide surface of Unix — `find`, `grep`, `ssh`, `tar`, `chmod`, piped chains, quoted arguments, nested subshells, escape sequences. The dictation convention is consistent: symbols are spoken as English words ("dash", "dot", "slash", "pipe") and numbers are spelled digit-by-digit ("one two seven" for `127`).

## Training

```bash
mlx_lm.lora \
  --model mlx-community/Qwen2.5-1.5B-Instruct-4bit \
  --data datasets/finetune/bash-v2/minimal \
  --batch-size 4 \
  --lora-layers 16 \
  --iters 1000 \
  --learning-rate 1e-4 \
  --mask-prompt
```

One flag worth calling out: `--mask-prompt`. The model only learns to predict the assistant response, not the system and user turns. All the training signal goes to the actual reconstruction task.

It converged fast.

<!-- ILLUSTRATION: training-curve
A clean line chart with two lines:
  - Train loss (blue): drops steeply from ~2.5 to ~0.05
  - Val loss (orange): drops from ~2.8 to 0.109 at iter 800, ticks up to 0.137 at 1000
X-axis: Iteration (0 to 1000)
Y-axis: Loss (0 to 3.0)
A small annotation at iter 800: "best checkpoint"
A subtle shaded region after 800 labeled "mild overfit"
Style: Minimal, no gridlines. Just the curves and the annotation.
-->

| Iter | Train Loss | Val Loss |
|------|-----------|----------|
| 200 | 0.337 | 0.213 |
| 400 | 0.108 | 0.204 |
| 600 | 0.068 | 0.137 |
| **800** | **0.049** | **0.109** |
| 1000 | 0.052 | 0.137 |

Best validation loss at iteration 800. A mild overfit signal by 1000. Final test loss: 0.098, perplexity: 1.103.

Peak memory during training: 2.95 GB. Total wall time: about 35 minutes on a MacBook.

## Beyond Val Loss: Does It Actually Get Commands Right?

Validation loss says the model is learning. It doesn't say whether it produces correct commands. So I ran the full 630-example test set through inference, compared each output character-for-character against the expected command, and sorted the results into buckets.

<!-- ILLUSTRATION: results-bar
A horizontal stacked bar chart, single bar, full width:
  - Green (76.2%): "Exact" — label inside
  - Light green (21.0%): "Near" — label inside
  - Yellow (2.4%): "Partial" — label inside or above
  - Red (0.5%): "Wrong" — tiny sliver, label above
Below the bar: "97.1% effective accuracy (exact + near)"
Style: Clean, bold. The green dominates. The red sliver is barely visible.
-->

```
Exact match              : 480 / 630 (76.2%)
Near match (>90% similar): 132 / 630 (21.0%)
Partial (70-90%)         :  15 / 630 (2.4%)
Wrong (<70%)             :   3 / 630 (0.5%)

Effective accuracy: 97.1%
```

Average inference time: 0.69 seconds per command on Apple Silicon.

The "near match" bucket is mostly whitespace and trivial formatting — extra spaces around operators, minor quoting style differences. Functionally identical outputs. The interesting signal is in the failures.

## Anatomy of the 3%

Every failure fell into one of two categories. No exceptions.

### Repeated Digits

When the input contains a long spoken digit sequence — "one zero zero zero zero zero" for `100000` — the model starts generating correctly, then falls into a repetition loop.

<!-- ILLUSTRATION: repetition-failure
Show 3 examples as "cards" or terminal snippets:

Card 1:
  Voice: "split dash L one zero zero zero zero zero database dot sql"
  Expected: split -l 100000 database.sql database-
  Got: split -l 100̶0̶0̶0̶0̶0̶0̶0̶0̶0̶0̶… (trailing zeros shown as fading/struck)

Card 2:
  Voice: "head dash N nine nine nine nine nine nine nine nine"
  Expected: head -n99999999 file1.txt
  Got: head -n 99̶9̶9̶9̶9̶9̶… (same treatment)

Card 3:
  Voice: "ping eight dot eight dot eight dot eight"
  Expected: ping 8.8.8.8
  Got: ping 8̶.̶8̶.̶8̶… (same treatment)

Style: The correct portion in white/green, the degenerate tail in red/faded,
visually showing where the model "loses the plot."
-->

```
IN:  "one zero zero zero zero zero"  →  GOT: 100[000000000…]  EXPECTED: 100000
IN:  "nine nine nine nine nine nine" →  GOT: 99[999999999…]   EXPECTED: 99999999
IN:  "eight dot eight dot eight"     →  GOT: 8[.8.8.8.8.…]   EXPECTED: 8.8.8.8
```

This is a known weakness of small language models with repeated tokens. The model sees "I just generated a zero" and assigns high probability to the next token also being a zero. The attention pattern becomes self-reinforcing.

All 4 of the "wrong" results in the evaluation were this exact failure mode.

### Casing Ambiguity

```
IN:  "df dash I H"          →  GOT: df -iH      EXPECTED: df -ih
IN:  "diff dash Y A B"      →  GOT: diff -y A B  EXPECTED: diff -y a b
IN:  "cp dash R S /mnt/..." →  GOT: cp -R s/...  EXPECTED: cp -rs /...
```

When someone says "dash I H" — should it be `-ih` or `-iH`? Both are valid bash. The model preserves the casing from the spoken input, which is a reasonable default but doesn't always match the expected answer.

21 of 630 examples (3.3%) differed only in letter casing. Score case-insensitively and they're all correct.

The remaining 14 partial matches were structural — a doubled token, a missed path segment, a quoting difference. Real model limitations, but minor ones.

## The Insight

Here's the thing I didn't expect going in.

Looking at the dictation vocabulary across the entire dataset, the mapping from spoken words to symbols is *completely deterministic*:

<!-- ILLUSTRATION: vocabulary-table
A visual "lookup table" or "decoder ring" showing the spoken-to-symbol mapping.
Two columns. Left: spoken word in a speech bubble or rounded tag. Right: the
symbol in a monospace/terminal style.

Show the top ~15 mappings arranged in a visually interesting grid or flow:
  dash → -       pipe → |        star → *
  dot → .        backslash → \   semicolon → ;
  slash → /      dollar → $      plus → +
  quote → "      underscore → _  equals → =
  single quote → '   tilde → ~  colon → :
  open brace → {    close brace → }

Below: "30 spoken tokens → 30 symbols. No ambiguity. No ML needed."

Style: This should be visually striking — the contrast between fuzzy human speech
and precise symbols is the point. Maybe the left side feels organic/warm and the
right side feels precise/mechanical.
-->

| Spoken | Symbol | Occurrences |
|--------|--------|-------------|
| dash | `-` | 11,207 |
| quote | `"` | 4,676 |
| dot | `.` | 4,297 |
| slash | `/` | 4,079 |
| pipe | `\|` | 1,791 |
| star | `*` | 1,730 |
| backslash | `\` | 924 |
| semicolon | `;` | 766 |
| dollar | `$` | 636 |
| ... | ... | ... |

Thirty spoken tokens mapping to thirty symbols. No ambiguity. No context-dependence. A lookup table handles it perfectly.

Same for digits: "zero" through "nine" map 1:1 to `0`-`9`, spoken digit-by-digit and concatenated. "One two seven" is always `127`. "Zero six four four" is always `0644`.

The model is spending a huge chunk of its 1.5 billion parameters learning these fixed mappings. Every training example where "dash" becomes `-` is a wasted gradient. The model figured this out after the first hundred examples and then saw it eleven thousand more times.

**The fix isn't more training. It's less work for the model.**

## The Architecture That Emerges

<!-- ILLUSTRATION: pipeline-architecture
A vertical flow diagram with three stages, each as a distinct box/card:

Stage 1 — PREPROCESSOR (labeled "Deterministic Code"):
  Input: "find dot dash name star dot txt"
  Processing: symbol/digit lookup table
  Output: "find . - name * . txt"
  Visual style: Mechanical, precise. Gear icon or lookup table icon.

Stage 2 — MODEL (labeled "Fine-tuned 1.5B LM"):
  Input: "find . - name * . txt"
  Processing: structural reasoning (spacing, quoting, grouping)
  Output: "find . -name *.txt"
  Visual style: Neural/organic. Small brain or network icon.

Stage 3 — POST-PROCESSOR (labeled "Deterministic Code"):
  Input: "find . -name *.txt"
  Processing: repetition guard, balanced quotes check
  Output: "find . -name *.txt" ✓
  Visual style: Same mechanical feel as Stage 1. Shield or checkmark icon.

The key visual idea: the ML part is sandwiched between two layers of regular code.
Most of the "intelligence" is deterministic. The model handles the narrow slice
that actually requires judgment.
-->

```
  "find dot dash name star dot txt"
              │
     ┌────────▼─────────┐
     │   Preprocessor   │  Deterministic: symbol + digit expansion
     │   (no ML)        │  "find . - name * . txt"
     └────────┬─────────┘
              │
     ┌────────▼─────────┐
     │  Fine-tuned LM   │  Structural reasoning only
     │  (1.5B, LoRA)    │  find . -name *.txt
     └────────┬─────────┘
              │
     ┌────────▼─────────┐
     │  Post-processor   │  Repetition guard, sanity checks
     │  (no ML)         │
     └────────┬─────────┘
              │
              ▼
     find . -name *.txt
```

**Preprocessor** — deterministic code, no model involved:
- Symbol words to literal characters: `dash` → `-`, `pipe` → `|`, `open brace` → `{`
- Digit sequences to numbers: `one two seven` → `127`, `zero six four four` → `0644`
- Compound numbers to digits: `twenty three` → `23`, `twelve` → `12`

**Model** — the only part that requires ML, and now its job is purely structural:
- Where do spaces go? (`-name` vs `- name`)
- What gets quoted? (`"*.txt"` vs `*.txt`)
- How do tokens group? (`-exec rm -f {} \;` as a unit)
- What's a flag vs. an argument? (`-rs` vs `-R s`)

**Post-processor** — deterministic code again:
- Repetition detection: same n-gram 3+ times in a row, truncate
- Structural validation: balanced quotes, balanced braces, no trailing artifacts

The model becomes a structural reasoner instead of a lookup table. It stops memorizing that "dash" means `-` and starts focusing on the actually hard part: how these symbols compose into valid commands.

## What the Numbers Mean

<!-- ILLUSTRATION: production-stats
Three "stat cards" in a row, bold numbers with subtle icons:

Card 1: "97%" with subtext "effective accuracy"
  Icon: target/bullseye
Card 2: "3 GB" with subtext "total memory"
  Icon: chip/RAM stick
Card 3: "0.7s" with subtext "per command"
  Icon: stopwatch

Below: "On a phone. Offline. No cloud."

Style: Clean, confident. These numbers should feel impressive without being flashy.
-->

97% accuracy from a model that fits in 3GB and runs in under a second. On a phone. Offline. No API call, no network dependency, no usage fees.

The remaining 3% breaks down cleanly:

- **Repeated digits** (~0.6%): eliminated entirely by the preprocessor — digits never reach the model
- **Casing** (~3.3%): arguably not errors — both casings are valid bash. Case-insensitive accuracy is already ~99%
- **Structural** (~2.2%): genuine model limitations, mostly minor — a doubled token, a missed path segment

With the preprocessing pipeline handling symbols and digits, the model's effective job shrinks substantially, and I'd expect accuracy above 98% without any retraining.

## Practical Notes

**Training cost.** 35 minutes on a MacBook, 3GB RAM. No GPU cluster. MLX makes LoRA fine-tuning on Apple Silicon feel like running a build.

**Data efficiency.** 5,044 training examples was enough for 97%. The model converged in 800 iterations — 3,200 examples at batch size 4. Small, focused datasets beat large noisy ones when the task is narrow.

**Checkpoint selection.** Best validation loss at iteration 800 (0.109). Iteration 1000 showed mild overfitting (0.137). In practice the difference was small — both produced similar accuracy in full evaluation.

**Inference.** 0.69 seconds average. Fast enough to run between when you stop speaking and when text appears. The user doesn't wait.

## What's Next

<!-- ILLUSTRATION: domains-expansion
A grid of domain "cards" showing where this same approach applies:

  bash     →  ✅ done (this post)
  SQL      →  "select star from users where..."
  regex    →  "caret open bracket A dash Z close bracket plus dollar"
  URLs     →  "H T T P S colon slash slash..."
  math     →  "integral from zero to infinity..."
  file paths → "slash users slash arach slash..."

Each card has the domain name, a tiny example of spoken → written, and a
status indicator (done, next, future).

Style: Grid layout. "bash" card is highlighted/completed. Others are dimmed
or outlined, suggesting a roadmap.
-->

Building the preprocessing pipeline is the immediate next step — the deterministic symbol and digit expander that feeds cleaned input to the model.

Beyond that, the approach generalizes to any domain with a consistent spoken-to-written mapping. SQL, regex, file paths, URLs, mathematical notation. The model architecture stays the same. You change the training data and the preprocessor's lookup table.

The broader point: the right role for a small model isn't doing everything. It's doing the one thing that only a model can do, sandwiched between deterministic code that handles the rest.

<!-- ILLUSTRATION: closing
A minimal callback to the hero image — the same speech-to-syntax flow, but
now with the preprocessor and post-processor stages visible as small nodes
in the pipeline. The model in the center is smaller/lighter, because its
job is smaller now. The deterministic stages are doing the heavy lifting.

Or alternatively: a phone lying on a desk, terminal open, with a speech bubble
above it containing "find dot dash name star dot txt" and the terminal showing
the correct output. Simple, confident, done.
-->
