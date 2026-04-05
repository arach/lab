# Core Eval v2 Spec

## Benchmark statement

`core_eval_v2` measures whether a model can turn short spoken notes and
transcripts into small, useful, structured workflow artifacts for Talkie.

The benchmark focuses on:

- capture quality
- action extraction
- light assistant normalization
- compact contextualization

It does **not** attempt to measure broad agency, autonomous planning, or deep
personal reasoning.

## Card set

The initial core set is 10 cards.

### Capture

1. `memo-auto-title`
   - Output: concise title
   - Why it stays: tiny, useful, easy to audit

2. `memo-type-detection`
   - Output: coarse memo category plus uncertainty
   - Why it stays: useful routing signal

3. `transcript-cleanup-presets`
   - Output: cleaned transcript variant
   - Why it stays: real post-capture transformation

4. `private-redaction-pass`
   - Output: redacted transcript plus entity list
   - Why it stays: high-value and safety-sensitive

### Action

5. `action-item-extraction`
   - Output: structured tasks with evidence
   - Why it stays: one of the most product-real tasks

6. `reminder-normalization`
   - Output: reminder phrasing and optional follow-up question
   - Why it stays: small assistant behavior with ambiguity handling

7. `calendar-intent-detection`
   - Output: scheduling intent packet
   - Why it stays: common but needs a looser representation contract

8. `follow-up-question-generator`
   - Output: one clarifying question
   - Why it stays: tests the "ask instead of hallucinate" behavior

### Context

9. `similar-memo-recall`
   - Output: top related memo(s) with rationale
   - Why it stays: concrete memory retrieval task

10. `context-packet-builder`
    - Output: compact downstream context packet
    - Why it stays: good proxy for useful compression and prioritization

## Cards moved out of the core benchmark

These cards are still worth keeping, but not in `core_eval_v2`.

### Keep for stretch benchmark

- `what-matters-summary`
  - likely salvageable, but overlaps with cleanup/context and can return many
    valid shapes
- `project-clustering`
  - useful, but less obviously tiny and single-step
- `next-step-suggestion-engine`
  - more subjective than the current core set
- `hybrid-model-router`
  - operationally useful but more policy-shaped than user-task-shaped
- `conversation-to-checklist`
  - useful, but dependency structure makes it less stable
- `writing-style-memory`
  - interesting, but more personalization than core workflow intelligence
- `catch-me-up-daily-brief`
  - useful but broader than the core scope
- `contradiction-drift-detection`
  - strong candidate for stretch because it mixes judgment and aggregation

### Explicitly stretch / research-y

- `personal-knowledge-graph`
- `momentum-scoring`
- `local-agent-loop`
- `meeting-live-structure`
- `intent-trend-alerts`
- `voice-os-command-layer`

## Scoring model

Each card should produce three scores.

### 1. Task score

Semantic correctness.

Examples:

- the title is specific and non-generic
- the right action item was extracted
- the redaction removes the sensitive material
- the similar memo is actually relevant

### 2. Usability score

Downstream product usability with light normalization.

Examples:

- list output instead of wrapped object is okay
- field aliases are okay
- alternate but equivalent date packet is okay
- ranking or rationale is present in a usable form

### 3. Contract score

Exact preferred schema.

Examples:

- preferred field names
- preferred nesting
- preferred wrapper object
- preferred canonical packet format

## Acceptance rules

### Memo type detection

Should not encode one narrow confidence threshold as correctness. Better checks:

- selected type is in the acceptable set
- confidence is numeric
- uncertainty is represented somehow if the model is unsure

### Transcript cleanup

Should judge preserved facts, not exact phrase matches such as `3 of 5`.

### Calendar intent

Should accept:

- direct event packet
- scheduling intent packet
- event draft with unresolved fields

as long as date/time intent is represented correctly and safely.

### Similar memo recall

Should allow:

- `matches`
- `top_matches`
- equivalent ranking structures

if the right memo is recovered with usable relevance/rationale.

### Context packet

Should reward:

- compactness
- inclusion of decisions, active tasks, or open questions
- usable memo references

without over-binding to one exact object shape.

## Calibration rule

A strong mainstream API model should score clearly well on the core benchmark.

If it does not, the benchmark is still misaligned.

For calibration, the likely anchors are:

- `openai/gpt-4.1` via GitHub Models
- `Hermes-4-70B` via Nous
- one OpenRouter model

## Implementation plan

1. Create a separate `core_eval_v2` card file rather than silently mutating v1
2. Rewrite assertions as semantic and usability-focused checks
3. Add explicit accepted schema variants per card
4. Report `task`, `usable`, and `contract` separately
5. Calibrate on strong API models before broader leaderboard claims

## Current recommendation

Treat the existing `eval/local_intelligence/cards.json` as a useful draft / v1
stretch benchmark.

Build `core_eval_v2` as a new benchmark artifact, not a patch to the old one.
