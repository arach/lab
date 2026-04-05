# Part 2: When Fine-Tuning Isn't the Answer (Yet)

> Follow-up to "Teaching a Tiny Model to Hear Bash"
> Working title — refine before publishing

## Narrative arc

Part 1 ended on a high: 97% accuracy, 3GB RAM, under a second. But there's a catch we glossed over — that 97% is on **clean protocol input**. When users speak naturally ("okay so the command is...") or make corrections mid-sentence ("dash dash no wait just dash v"), the model falls apart.

This post is about what we tried next, what we learned, and the architectural insight that changed our approach.

## Key beats

### 1. The 97% Illusion

The fine-tuned model is great... if you speak its language perfectly. Real users don't.

Four difficulty levels:
- **Clean**: "git space push space dash u space origin space main" → 93% (processor alone)
- **Fuzzy**: "git commit minus m quote fix login bug quote" → 0% (no "space" keywords)
- **Natural**: "okay so the command is git push dash u origin main" → 0% (filler)
- **Chaotic**: "dash dash no wait just dash v" → 0% (self-corrections)

The training data was clean. Reality isn't.

### 2. The Procedural Processor Discovery

Before throwing more ML at it, we asked: how much of this task is deterministic?

Answer: almost all of it. "dash" always means "-". "dot" always means ".". A rule-based token scanner gets **93% on clean input** with zero hallucination, zero latency, zero training.

This raised the question: what is the LLM actually contributing? It's memorizing fixed mappings. The 11,207 times "dash" appears in training — the model learned them all, but a dictionary lookup does the same job.

### 3. The Split Architecture

The insight: **use each tool for what it's good at.**

```
Raw speech → LLM (language understanding) → Protocol text → Processor (deterministic) → Final syntax
```

The LLM's job shrinks dramatically:
- Strip conversational filler
- Resolve self-corrections ("no wait, actually...")
- Insert "space" keywords between arguments
- Replace synonyms (minus→dash, period→dot)

It never outputs symbols. It never makes the dash-to-minus conversion. It just cleans up natural language into a constrained protocol format, and the processor handles the rest.

### 4. Zero-Training Results

We tested this with pure prompting (no fine-tuning) across 3 models:

| Model | Clean | Fuzzy | Natural | Chaotic | Overall |
|---|---|---|---|---|---|
| Processor only | 92% | 0% | 0% | 2% | 23.5% |
| Qwen 2.5 1.5B | 90% | 20% | 54% | 24% | 47% |
| Qwen 2.5 0.5B | 90% | 12% | 44% | 20% | 41.5% |
| Llama 3.2 1B | 92% | 14% | 34% | 10% | 37.5% |

Key findings:
- 2x baseline with zero training
- Clean input maintained at 90%+ (protocol bypass — if input already has "space" keywords, skip the LLM entirely)
- Natural/chaotic show real improvement (filler stripping, self-correction resolution work)
- Fuzzy is the bottleneck (20%) — inserting "space" keywords requires understanding command structure

### 5. The Hybrid Architecture

The winning trick: **don't send everything through the LLM.**

```python
if input contains "space" keywords and no filler:
    → bypass LLM, send directly to processor
else:
    → LLM normalizes, then processor converts
```

This gives us:
- 96% on clean independent eval (up from 93% processor baseline)
- Near-zero latency for protocol-format input
- LLM only called when genuinely needed (26% of inputs bypassed)

### 6. Where Prompting Hits Its Ceiling

Fuzzy normalization is the hard problem. The LLM needs to understand:
- `cat file period txt` → "cat" and "file.txt" are separate tokens (need "space")
- But within "file.txt", "file" + "dot" + "txt" concatenate (no "space")
- `dash dash verbose` → compound flag, stays together
- `dash u space origin` → flag and argument, need "space"

This requires understanding command structure — which words are commands, flags, paths, filenames. A 1.5B model can't learn this from 12 few-shot examples. But it CAN learn it from 5,000 training examples.

### 7. The Path Forward

The fine-tuning task just got dramatically simpler:
- Old task: dictated text → final syntax (model must learn ALL symbol mappings)
- New task: dictated text → protocol text (model only learns WHERE to put "space")

Same training data. Same model. Much simpler output space. The processor handles the rest.

## Themes to emphasize

- **Don't teach an LLM what a dictionary can do.** Deterministic mappings belong in code.
- **Split tasks at the boundary of language understanding.** The LLM handles ambiguity; code handles rules.
- **Zero-training experiments reveal architecture.** Prompting told us exactly where the value is (filler stripping, correction resolution) and where it isn't (symbol conversion, space insertion).
- **Evaluation infrastructure matters.** The 4-difficulty eval set (clean/fuzzy/natural/chaotic) made it possible to see WHERE each approach fails, not just a single accuracy number.

## Data to include

- The results table above (all 3 models x 4 difficulties)
- Architecture diagram (raw → LLM → protocol → processor → syntax)
- Comparison: end-to-end fine-tuning vs split pipeline
- Error examples showing what the LLM gets right and wrong
- Latency numbers (2.5s with LLM vs ~0ms bypassed)

## Code references

All code in the datasets/ directory:
- `procedural-processor.py` — the deterministic backbone
- `normalizer-pipeline.py` — the zero-training pipeline
- `eval-fuzzy.json` — 200 entries, 4 difficulty levels
- `eval-independent.json` — 100 clean protocol entries
- Fine-tuning infrastructure in `finetune/` (from Part 1)

## Open questions for Part 3

- How much does fine-tuning the normalizer improve fuzzy accuracy?
- Can we generate training data programmatically? (take clean protocol, randomly drop "space" keywords, add filler)
- Is there a sweet spot between prompting and fine-tuning? (e.g., fine-tune on 100 examples instead of 5000)
- Should the normalizer be a separate model from the transcription engine?
