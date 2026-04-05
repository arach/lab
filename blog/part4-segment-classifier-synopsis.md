# Part 4: Splitting the Stream

> The whole-text classifier asks "should this go to the model?" The segment classifier asks "which words?"

<!-- METADATA
slug: splitting-the-stream
series: teaching-a-tiny-model-to-hear-bash
part: 4
date: TBD
tags: classifier, segmentation, on-device-ml, voice, dictation, logistic-regression
author: Arach
-->

## Series context

- **Part 1** — Fine-tuned a 1.5B model to reconstruct bash from dictation. 97% accuracy, 3GB RAM, 0.7s inference.
- **Part 2** — Split architecture: deterministic processor for symbols, LLM for language understanding.
- **Part 3** — A classifier trained in 40ms gates whether input needs an LLM at all. 100% accuracy on held-out data.
- **Part 4** (this post) — Mixed dictations break the gate. A per-word classifier segments the stream so only the command parts hit the model.

## The problem Part 3 didn't solve

Part 3's classifier works on whole utterances. Clean protocol input goes to the processor. Fuzzy input goes to the LLM. But real dictation isn't one or the other — it's both at once.

"I want to check the directory ls dash la and then we can talk about the project timeline."

If you send all of that to the fused model — a quantized 0.6B fine-tuned exclusively on bash reconstruction — you get hallucinated garbage where the natural speech was. The model has never seen conversational English. It tries to reconstruct "I want to check the directory" as if it were dictated protocol and produces something unrecognizable.

If you skip the model entirely, the protocol segment "ls dash la" passes through as raw dictated text. The user sees the words "ls dash la" instead of `ls -la`.

The gate needs to operate inside the sentence, not around it.

## First attempt: heuristics

The obvious approach: maintain a set of protocol words ("dash", "dot", "slash", "space"), scan the text, mark any word that matches, expand a window around matches to capture adjacent command tokens like "ls" or "git".

This works for the simple cases. Then it breaks:

- "at three o'clock" — "at" is in protocol vocab (for @), "three" is a number word. Flagged as protocol. Now the model tries to reconstruct a meeting time as bash.
- "the performance numbers look really good" — clean pass. Correct.
- "talkie-dev dash-help" — hyphens embedded in words. The heuristic checks for standalone "dash" but not for syntax characters inside words. Missed.

Every edge case is another rule. Every rule has its own edge cases. This is the exact problem the Part 3 classifier solved for whole-text routing. Same insight applies here — learn the boundary instead of coding it.

## The vocabulary split

The key insight that made training work: not all protocol words are equally diagnostic.

"dash" almost never appears in natural English speech. If someone says "dash", they mean a hyphen. Strong signal.

"at" appears constantly in natural speech. "I arrived at the office at nine." Two uses of "at", zero protocol intent. Weak signal.

Split the vocabulary into two tiers:

**Strong protocol** (28 words): dash, dot, slash, space, colon, underscore, tilde, hash, pipe, backtick, semicolon, equals, backslash, capital, caps, camel, snake, pascal, kebab, paren, brace, bracket, ampersand, percent, caret, dollar, minus, asterisk.

**Weak protocol** (30 words): at, star, bang, question, comma, quote, plus, open, close, new, line, all, case, one, two, three, four, five, six, seven, eight, nine, ten, zero, back, sign, mark, double, single, less.

A strong protocol word is almost always protocol. A weak protocol word is only protocol when it appears near strong ones. "at" next to "tilde slash dot" is protocol. "at" next to "the office" is not.

## Per-word features

14 features per word, extracted with a ±2 context window:

| # | Feature | What it captures |
|---|---------|-----------------|
| 0 | is_strong_protocol | Unambiguous protocol word |
| 1 | is_weak_protocol | Ambiguous protocol word |
| 2 | is_expanded_symbol | Already-converted symbol (-, ., /) |
| 3 | has_syntax_chars | Contains syntax characters |
| 4 | word_length_norm | Length / 10 |
| 5 | is_short_word | Length <= 3 |
| 6 | context_strong_density | Fraction of ±2 window that's strong protocol |
| 7 | context_any_density | Fraction of ±2 window that's any protocol |
| 8 | left_is_strong | Left neighbor is strong protocol |
| 9 | right_is_strong | Right neighbor is strong protocol |
| 10 | is_number_like | Number word or digit |
| 11 | strong_neighbor_count | Raw count of strong protocol in window |
| 12 | is_all_lower | All lowercase letters |
| 13 | position_ratio | Position / total words |

The most powerful feature: `strong_neighbor_count` (weight +1.04). Being near unambiguous protocol words is the single strongest signal that a word is part of a command. This is the learned version of the ±2 expansion heuristic — but the model decides how much weight to give it rather than a hard-coded rule.

## Training

Synthetic mixed dictations: natural English fragments (from user manuals, business writing, HR policies, medical literature) concatenated with actual bash command dictations. 600 examples producing ~8,000 labeled words.

Same logistic regression as Part 3. Same gradient descent. Trains in under a second.

## Two-pass architecture

The classifier identifies protocol **anchor words** — the unambiguous markers that a command is present. Then a deterministic expansion captures adjacent command tokens (the "ls" next to "dash la", the "git" before "dash dash help").

```
"I want to check the directory ls dash la and then discuss the timeline"
                                    ↓ ML classifier
Word scores:  0.1 0.1 0.1 0.1 0.1 0.2 0.3 [0.9] 0.4 0.1 0.1 0.1 0.1 0.1
                                                ↑ anchor: "dash"
                                    ↓ ±2 expansion
Segments:  [natural: "I want to check the directory"]
           [protocol: "ls dash la"]
           [natural: "and then discuss the timeline"]
```

Only the protocol segment goes to the fused model. Natural speech passes through untouched.

## Results

Evaluated on 50 hand-labeled mixed dictations — real-world patterns from documentation, business writing, legal text, and technical manuals mixed with bash commands.

```
WORD-LEVEL
  Accuracy:   92.5%
  Precision:  84.7%
  Recall:     99.4%
  F1:         0.915

EXAMPLE-LEVEL
  Pure natural text:  19/21 perfect (90%)
  Mixed text:         protocol segments found in all 29 cases

FALSE POSITIVE RATE: 12.2%
FALSE NEGATIVE RATE:  0.6%
```

The asymmetry is deliberate. A false negative means a protocol segment passes through as raw text — the user sees "dash la" instead of `-la`. Annoying but comprehensible. A false positive means natural speech gets sent to the fused model — the model hallucinates on English and produces garbage. Much worse.

So we optimized for recall (99.4%) at the cost of precision (84.7%). Miss almost nothing, accept some boundary bleed.

The false positives are almost entirely transition words at command boundaries — "with", "run", "use", "to" — words that sit right before the command starts. Including them in the protocol segment is harmless; the fused model ignores them.

## The two-classifier architecture

This is the full routing stack now:

```
Raw transcription
      |
      v
  [ NeedsLLMClassifier ]     ← whole-text: "does this need cleanup?"
      |                          → routes to frontier model (Claude, GPT)
      v
  [ ProtocolSegmentClassifier ] ← per-word: "which words are commands?"
      |                          → routes segments to fused Qwen3 0.6B
      v
  Output: natural speech untouched, commands reconstructed
```

Two classifiers, two jobs, two scales:
- **NeedsLLMClassifier**: whole-dictation gate for quality cleanup with a large model
- **ProtocolSegmentClassifier**: per-word segmentation for fast on-device command reconstruction

Both are logistic regression. Both are under 1KB of weights. Both run in microseconds. The expensive operations — the LLM inference, the embedding lookup — only happen when the classifiers say they should.

## The procedural processor

The segment classifier decides *which words* go to the model. But what does the model actually replace? A deterministic procedural processor that needs no neural network at all.

The processor is a token scanner with a symbol vocabulary:
- "dash" → `-`, "dot" → `.`, "slash" → `/`, "pipe" → `|`
- Two-word: "open paren" → `(`, "dash dash" → `--`, "and and" → `&&`
- Numbers: "eight zero eight zero" → `8080`, "forty two" → `42`
- Casing: "capital A" → `A`, "all caps POST" → `POST`, "camel case get user" → `getUserProfile`
- "space" as explicit token separator

A test harness validates the processor against 100 real commands across 31 categories (git, docker, curl, ssh, kubernetes, terraform, etc.) plus 92 isolated unit tests for every feature:

```
UNIT TESTS: 92/92 (100%)
  symbols, synonyms, two-word, three-word, numbers,
  casing, directives, spacing, mixed commands, redirects

EVAL TESTS: 100 commands across 31 categories
  Exact match:      96/100 (96.0%)
  Case-insensitive: 100/100 (100.0%)
  Median latency:   11us per command

  git: 8/8  docker: 7/7  kubernetes: 5/5  ssh: 3/3
  python: 6/6  rust: 3/3  go: 3/3  brew: 4/4  ...
```

The 4 non-exact matches are all casing edge cases — `all caps` scope interacting with adjacent `capital` directives. Every symbol, number, and structural transformation is correct. At 11 microseconds per command, the processor adds essentially zero latency.

This is the piece the fused model is meant to replace for fuzzy input. When the dictation is clean protocol, the processor handles it directly — no model needed. The model only activates for segments where the dictation is ambiguous or natural-sounding.

## End-to-end chain test

The full pipeline runs without a microphone — synthetic test cases simulate mixed dictations through every stage:

```
Dictation text
      |
      v
  [ ProtocolSegmentClassifier ]  ← ML: which words are commands?
      |
      v
  [ Procedural Processor ]       ← deterministic: symbols, numbers, casing
      or
  [ Fused Model (Qwen3 0.6B) ]  ← neural: ambiguous reconstructions
      |
      v
  Reassembled output
```

12 test cases covering simple commands, pure protocol, pure natural speech, sandwiched commands, two-command bridges, and complex multi-flag commands (SSH with IPs, iptables, curl with headers):

```
CLASSIFIER SEGMENTATION: 12/12 correct
  - 3 pure natural correctly passed through (no model call)
  - 9 command cases correctly detected protocol segments

MODEL INFERENCE:
  - Simple commands (ls -la, ps -aux): correct
  - Medium commands (git push, npm install): correct
  - Complex commands (iptables, curl): drops arguments
```

The classifier is the strong link. The model is the current bottleneck on complex commands — a 0.6B model can reconstruct simple-to-medium bash but struggles with long multi-flag commands. This is a training data and model capacity issue, not a pipeline issue.

## What's next

1. **Better training data.** The current training set is synthetic — programmatically assembled from fragments. Real mixed dictations from actual users would capture patterns the synthetic data misses.

2. **Model capacity.** The 0.6B fused model handles simple commands well but drops arguments on complex ones (iptables, curl with headers). Either more targeted training data or stepping up to 1.5B for the fused model.

3. **Number word bridging.** Removing number words from protocol vocabulary eliminated false positives on natural speech ("the board voted six to three") but created a gap: isolated number sequences between protocol anchors (like IP address digits) can fall outside the ±2 expansion window.

The classifier is deployed and running in Talkie's live dictation pipeline. Every dictation in iTerm2 now goes through the segment classifier before hitting the fused model. Natural speech stays natural. Commands get reconstructed. The user doesn't know which words went where.

## Code references

- `datasets/train-segment-classifier.py` — training pipeline, synthetic data generation
- `datasets/eval-segment-classifier.py` — evaluation harness with boundary analysis
- `datasets/eval-segment-classifier.json` — 50 labeled mixed dictation examples
- `datasets/test-protocol-processor.py` — processor test harness (92 unit tests + 100 eval commands)
- `datasets/test-full-chain.py` — end-to-end chain test (classifier + model + reassembly)
- `datasets/procedural-processor.py` — deterministic protocol processor
- `datasets/eval-independent.json` — 100 labeled dictation-to-command pairs across 31 categories
- `macOS/TalkieKit/Sources/TalkieKit/ProtocolSegmentClassifier.swift` — deployed classifier
- `macOS/TalkieKit/Sources/TalkieKit/NeedsLLMClassifier.swift` — whole-text classifier (Part 3)
