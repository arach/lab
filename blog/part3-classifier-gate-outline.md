# Part 3: The 40-Millisecond Gate

> A trained embedding classifier decides whether to call the LLM — 100% accuracy on held-out data, trained in 40ms on 120 examples.

<!-- METADATA
slug: the-40-millisecond-gate
series: teaching-a-tiny-model-to-hear-bash
part: 3
date: TBD
tags: nlembedding, classifier, on-device-ml, voice, apple, accelerate
author: Arach
-->

## Series context

- **Part 1** — Fine-tuned a 1.5B model to reconstruct bash from dictation. 97% accuracy, 3GB RAM, 0.7s inference.
- **Part 2** — Discovered the split architecture: deterministic processor handles symbols/digits, LLM handles language understanding (filler stripping, corrections, normalization).
- **Part 3** (this post) — The routing decision: does this input even need the LLM? A classifier trained in 40ms answers with 100% accuracy.

## Opening hook

Part 2 ended with a bypass rule: if the input contains "space" keywords and no conversational filler, skip the LLM entirely. But that rule was hand-crafted. It worked for clean protocol input but missed edge cases.

The question: can we learn the routing decision instead of hand-coding it?

## Beat 1: The hand-crafted classifier

We started with `NeedsLLMClassifier` — a rule-based system that scores inputs on:
- Protocol vocabulary density ("space", "dash", "colon", etc.)
- Conversational markers ("okay", "um", "like", "actually")
- Structural patterns (corrections, false starts, hedging)

It's fast (< 0.01ms per classification). On our 40-case eval set spanning four difficulty levels, it hits 95%. Good, but it took significant iteration to build, and every edge case is another rule.

**The question behind the question:** Can we replace human pattern-matching with a trained model that's just as fast but doesn't require hand-tuning?

## Beat 2: The embedding insight

Apple ships `NLEmbedding` as a system framework. It's a 512-dimensional word embedding model, already on every Mac and iPhone. No download. No setup. One API call gives you a feature vector.

The key property: word-averaged embeddings of protocol-heavy input ("git space push space dash u space origin space main") land in a completely different region of embedding space than conversational input ("okay so like the command is git push"). The words "space", "dash", "colon" cluster differently from "um", "actually", "wait".

**The bet:** If the embedding already separates these two classes, a simple linear classifier on top should work. No deep learning. No fine-tuning. Just logistic regression.

## Beat 3: The training data

We already had the eval dataset from Part 2: 200 dictation examples across four difficulty levels.

| Difficulty | Description | needsLLM |
|---|---|---|
| clean | Protocol-formatted, "space"/"dash" keywords | false |
| fuzzy | Synonym substitutions ("minus", "period", "forward slash") | true |
| natural | Conversational wrapping ("okay so the command is...") | true |
| chaotic | Self-corrections, false starts, mid-sentence changes | true |

Split: 120 for training, 40 for testing, 40 held out.

The label is binary: `clean` maps to "doesn't need LLM" (the deterministic processor handles it). Everything else maps to "needs LLM."

## Beat 4: The implementation

Logistic regression on 512-dimensional embeddings. The entire classifier is:
- A weight vector (512 doubles)
- A bias term (1 double)
- A sigmoid activation

Training: batch gradient descent with L2 regularization. Standardize features internally, un-transform weights at the end so the deployed head works on raw embeddings. No data pipeline. No framework. 80 lines of Swift using Apple's Accelerate (BLAS) for the matrix math.

Hyperparameters that mattered:
- **Learning rate 0.1** (not 0.01 — standardized features converge fast)
- **Lambda 0.01** (not 1.0 — light regularization on 512 dims, heavy regularization starves the model)
- First attempt with lr=0.01 and lambda=1.0: 88% accuracy, 2134ms training
- After fix: 100% accuracy, 40ms training

The 50x speedup came from BLAS. The 12-point accuracy jump came from letting the model actually fit the data instead of regularizing it to death.

## Beat 5: The results

```
ACCURACY (vs ground truth labels)
  Hand-Crafted:    95.0% (38/40)
  Trained Head:   100.0% (40/40)

TRAINING
  Cases:          120
  Time:           40ms

LATENCY
  Embedding:      0.05ms median
  Classification: 0.00ms median
```

The trained head beats the hand-crafted classifier on every metric:
- Higher accuracy (100% vs 95%)
- Trained in 40ms (vs hours of manual rule iteration)
- Same inference speed (< 0.1ms total)

Per-difficulty breakdown — where the hand-crafted classifier fails and the trained head doesn't.

## Beat 6: The fan-out insight

The embedding is the expensive part (~0.05ms). The classifier head is essentially free (~0.001ms). This means you can run N different classifier heads on the same embedding for almost no extra cost.

```
Embed once:     0.05ms
1 head:         0.001ms
4 heads:        0.004ms
```

One embedding, multiple decisions:
- Does this need an LLM?
- Is this a command, a variable name, or prose?
- Which domain? (bash, SQL, regex, URL)
- What's the confidence level?

The shared backbone pattern: compute the embedding once, fan out to cheap task-specific heads. Each head is 512 weights + 1 bias, trained in milliseconds.

## Beat 7: What this means architecturally

```
Raw transcription
      |
      v
  [ NLEmbedding ]  ← 0.05ms, system framework, no download
      |
      +--→ [ needsLLM? ]     ← 0.001ms, trained head
      +--→ [ domain? ]       ← 0.001ms, trained head (future)
      +--→ [ confidence? ]   ← 0.001ms, trained head (future)
      |
      v
  Route to:
    - Deterministic processor (clean protocol input)
    - On-device LLM (fuzzy/natural, needs normalization)
    - Cloud LLM (chaotic, high ambiguity)
```

The classifier gate sits between transcription and processing. It costs essentially nothing. It routes inputs to the cheapest processor that can handle them correctly.

For Talkie's keyboard dictation, this means:
- 25% of inputs (clean protocol) get instant results — no LLM, no latency
- 75% of inputs go through the LLM normalizer from Part 2
- The user never notices the routing. They just see fast, correct output.

## Closing: The meta-lesson

Three posts. Three layers of the same insight.

**Part 1:** Don't use a big model when a small one works. (1.5B vs GPT-4)
**Part 2:** Don't use a model when code works. (Processor vs fine-tuned LLM)
**Part 3:** Don't use a model to decide whether to use a model — unless training it takes 40ms. Then do.

The whole pipeline costs less than a single GPT-4 API call. It runs offline. It fits on a phone. And the most expensive operation in the entire stack is a 0.05ms embedding lookup that Apple ships for free.

## Appendix notes

### Code references
- `ClassifierPipelineBenchmark.swift` — benchmark runner, training, eval
- `NeedsLLMClassifier.swift` — hand-crafted classifier (the baseline)
- `eval-fuzzy.json` — 200 labeled examples across 4 difficulties

### Numbers to verify on-device before publishing
- Exact HC accuracy % (currently 95% on 40 cases)
- Exact trained accuracy % (currently 100% on 40 cases)
- Training time range across multiple runs
- Per-difficulty breakdown
- Fan-out latency at N=4, N=8, N=16

### Illustration ideas
- Hero: a fork in the road — one path labeled "LLM" (longer, scenic), one labeled "processor" (short, direct). A tiny gate at the fork.
- Training visualization: 120 dots in 2D (PCA of embeddings), colored by class, with the decision boundary drawn through them.
- Speed comparison: a race track showing 40ms training vs hours of hand-coding rules.
- Fan-out diagram: one embedding node at top, multiple classifier heads branching below, each labeled with a different question.
