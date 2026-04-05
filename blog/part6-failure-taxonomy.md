# Part 6: What a 0.6B Model Can't Learn

> You can iterate forever on training data. At some point you have to ask whether the model is the right tool for the job.

<!-- METADATA
slug: what-a-small-model-cant-learn
series: teaching-a-tiny-model-to-hear-bash
part: 6
date: TBD
tags: fine-tuning, model-capacity, failure-analysis, on-device-ml, voice, dictation
author: Arach
-->

## Series context

- **Part 1** — Fine-tuned a 1.5B model to reconstruct bash from dictation. 97% accuracy, 3GB RAM, 0.7s inference.
- **Part 2** — Split architecture: deterministic processor for symbols, LLM for language understanding.
- **Part 3** — A classifier trained in 40ms gates whether input needs an LLM at all. 100% accuracy on held-out data.
- **Part 4** — Per-word classifier segments mixed speech so only command fragments hit the model.
- **Part 5** — Six training runs took accuracy from 18% to 79%. Every fix was in the data.
- **Part 6** (this post) — A taxonomy of what the model still gets wrong, and why some failures can't be trained away.

## The remaining 20%

At 79% exact match, the model handles simple-to-medium commands perfectly. Git, npm, python, systemd, terraform — all at 100%. The failures live in specific structural patterns that a 1.7B model can't reliably reconstruct.

I categorized every failure across the last three training runs. The failures don't just cluster by command category — they cluster by *structural pattern*.

## Pattern 1: The spacing ambiguity

"dash s capital l" should produce `-sL`. The model produces `-s L` or `-s  L`.

"dot slash logs slash" should produce `./logs/`. The model produces `. /logs/`.

The model has to decide: does this word join the previous token with no space, or does it start a new token? The dictation protocol uses "space" as an explicit separator, so absence of "space" means "join". But the model doesn't reliably learn this absence-of-signal as a positive instruction.

This is the most common failure class. 8 of 20 remaining errors are spacing.

The challenge: the model sees `dash s capital l` as three tokens and has to output two characters joined to one letter with no spaces between any of them. That's a precise structural transformation that fights against the model's natural inclination to separate tokens with spaces.

Training helps — we went from ~50% to ~90% on these patterns — but full reliability requires more examples than the model can absorb without forgetting other patterns.

## Pattern 2: Context-dependent symbols

"dash" usually means `-`. But in "cask dash fonts", it means the hyphen *inside a compound word*: `cask-fonts`. In "dash dash tail", it means the first half of `--`. In "dash dash space dash dash", it means `-- --` (two separate double-dashes).

The model has to distinguish:
- `dash` as single flag prefix: `dash f` → `-f`
- `dash` as compound word joiner: `cask dash fonts` → `cask-fonts`
- `dash dash` as long flag prefix: `dash dash recursive` → `--recursive`
- `dash` as part of a word: `describe dash instances` → `describe-instances`

Each meaning requires looking at the surrounding words. A strong model learns this from context. A 1.7B model learns the most common pattern and gets confused on the rest.

The see-saw effect from Part 5 shows up here: adding more `cask-fonts` examples makes the model better at compound-word dashes but worse at flag dashes in nearby contexts. The model doesn't have enough capacity to hold both patterns with full confidence.

## Pattern 3: Long-distance dependencies

```
ssh -i ~/.ssh/id_rsa ubuntu@192.168.1.100
```

This command has 15 protocol words in the input. By the time the model reaches "one hundred" at the end, it needs to remember it's building an IP address octet, not a standalone number. The model truncates: `192.168.1.10` instead of `192.168.1.100`.

Same pattern with trailing paths:
```
# Expected
scp -r user@host:/var/log/ ./logs/

# Got
scp -r user@host:/var/log/ . /logs/
```

The model handles the first 80% of the command correctly, then loses coherence on the final tokens. This is attention span, and it's a function of model size. The 1.7B model's effective context for precise token reconstruction is about 10-12 protocol words. Beyond that, accuracy degrades.

## Pattern 4: Nested quoting

```
sed -i '' 's/old/new/g' file.txt
```

This requires the model to produce two consecutive single quotes (`''`) as an empty string argument, followed by a quoted sed expression. The model outputs `sed -i '' s/old/new/g ' file.txt` — it drops the opening quote of the second argument.

The jq examples show the same pattern:

```
# Expected
jq '.data[] | .name' response.json

# Got
jq '.data[] | .name' .json
```

The model gets the quoted expression right but then loses the file argument — as if the closing quote consumed its attention budget and it rushes to end the output.

Complex quoting requires tracking matched pairs across multiple characters. This is a pattern that benefits disproportionately from model scale.

## Pattern 5: Directive scope

"capital" uppercases the next word. "all caps" uppercases the next word. But what happens with:

```
cmake -DCMAKE_BUILD_TYPE=RELEASE
```

The input is: `dash capital d all caps cmake underscore all caps build underscore all caps type equals all caps release`

That's `capital` applied to one letter (D), then four consecutive `all caps` directives each scoped to one word, with underscore joins between them. The model has to track: capital applies to the next single character, all caps applies to the next full word, and underscores join without spaces.

The model produces `cmake -DCMAKE_BUILD_TYPE=RELEASE` sometimes and `cmMake-Build-Debug` other times. It's not consistent because the pattern requires tracking directive scope across multiple transformations — and each training run emphasizes different parts of this pattern.

## The taxonomy

| Pattern | Failure Count | Trainable? |
|---------|--------------|------------|
| Spacing ambiguity | 8 | Partially — improvements see-saw |
| Context-dependent symbols | 4 | Limited by capacity |
| Long-distance dependencies | 3 | Needs larger context window |
| Nested quoting | 3 | Needs more model capacity |
| Directive scope | 2 | Partially with more examples |

"Trainable" means: can we fix this with more training data? The answer for most is "yes, but at the cost of something else." The model's weight budget is zero-sum.

## What this means for the architecture

The Part 2 insight holds: the model doesn't need to handle everything. The procedural processor handles clean protocol input at 96% accuracy and 11 microseconds. The model is the fallback for ambiguous input — input where the dictation doesn't follow strict protocol.

For strict protocol input ("git space push space dash u space origin space main"), the processor is faster, cheaper, and more accurate. The model should only activate when the segment classifier detects fuzzy boundaries.

At 79%, the model handles the fuzzy case well enough. The remaining 20% are edge cases that a user could clarify by being more explicit in their dictation. "dash s capital l" is ambiguous; "dash s l" processed by the procedural engine is not.

The right question isn't "how do we get the model to 100%?" It's "which 20% of cases actually appear in real dictation, and do they need a model at all?"

## The cost accounting

Each training run: 20 minutes on a Mac mini, 4.6GB peak memory, 934MB model on disk.

Six runs to go from 18% to 79%. Total training time: 2 hours. Total human time: an afternoon of analysis, data fixing, and waiting.

The insight density was highest in the first three runs:
- Run 1: Fix eval bugs (regex, system prompt) — free accuracy
- Run 2: Fix training data bugs (capitalization) — ten points from grep
- Run 3: Targeted augmentation — biggest single accuracy jump

After run 3, we hit diminishing returns. Each subsequent run added 1-3 points while shifting failures around. The model told us it was done learning from patches; we just weren't listening.

## Rules for small-model fine-tuning

From six iterations of the same loop:

1. **Fix the eval before fixing the model.** A broken eval sends you chasing ghosts.

2. **System prompt is architecture.** Treat it as a hyperparameter, not a string. Match exactly between training and inference.

3. **Training data must demonstrate transformation.** If input equals output, the model learns nothing. Audit for identity functions in your data.

4. **Targeted augmentation has a half-life.** The first patch adds 10 points. The fifth patch adds 1 point and takes away 2 from something else.

5. **Watch the per-category stability.** When fixing SSH breaks Docker, you've hit the capacity ceiling. Stop augmenting.

6. **A model doesn't need to do everything.** Pair it with deterministic systems that handle the cases it can't. The best accuracy comes from not using the model at all, when you don't have to.

## Code references

- `datasets/finetune/bash-v{3-6}/train.jsonl` — training data evolution
- `datasets/eval-independent.json` — 100 labeled eval pairs
- `datasets/procedural-processor.py` — deterministic processor
- `datasets/test-protocol-processor.py` — processor test harness (92 unit tests + 100 eval)
- `datasets/test-full-chain.py` — end-to-end pipeline test
