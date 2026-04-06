# v1.1 Card Rewrite

This is the working rewrite for `v1.1`.

The goal is to keep the broad task map from `v1`, but rewrite each card so the
benchmark is:

- winnable for strong off-the-shelf models
- strict about real task quality
- tolerant of harmless schema variation

Each card gets three things:

1. the real question being asked
2. what a good answer should do
3. win criteria for `v1.1`

## Ship-Soon

### 1. `memo-auto-title`

**Question**

Can the model generate a specific, compact memo title that is useful in list
view and search?

**What a good answer should do**

- avoid generic filler like `Voice Memo` or `Thoughts`
- mention the concrete topic or action
- stay reasonably short

**v1.1 win criteria**

- title is non-empty
- title is not generic
- title includes at least one core memo anchor
  - for the test case: `dentist` or `insurance`
- title length is reasonable
  - keep `<= 60` instead of `<= 48`
- confidence and rationale are optional for task success

**Notes**

- This is a good card already.
- The main fix is to stop over-weighting the exact wrapper around the title.

### 2. `memo-type-detection`

**Question**

Can the model classify the memo into a reasonable primary memo type without
pretending certainty when the input is ambiguous?

**What a good answer should do**

- choose a plausible primary type
- expose uncertainty somehow
- avoid over-routing ambiguous reflective speech

**v1.1 win criteria**

- primary type is in an acceptable set
  - for the test case: `journal` or `idea`
- confidence exists and is numeric
- uncertainty is represented in at least one acceptable way
  - `needsReview: true`
  - low confidence
  - explicit uncertainty field or rationale

**Notes**

- Drop the brittle `confidence < 0.8` threshold as a hard correctness rule.
- High confidence can lower `usable` or `contract`, but should not zero the
  task if the type is right.

### 3. `action-item-extraction`

**Question**

Can the model extract at least one plausible task from vague or explicit speech
and preserve the evidence?

**What a good answer should do**

- identify one or more task candidates
- preserve evidence text
- avoid inventing due dates
- mark vague tasks with lower confidence

**v1.1 win criteria**

- at least one task item is present
- item text is non-empty and task-like
- evidence is present for at least one returned item
- due date is null or omitted when not stated
- confidence is numeric when provided
- lower confidence for vague tasks is a soft preference, not a hard fail

**Notes**

- This should accept either:
  - `{ "items": [...] }`
  - or a top-level list of task objects

### 4. `transcript-cleanup-presets`

**Question**

Can the model rewrite a transcript into a cleaner preset style without changing
the concrete facts?

**What a good answer should do**

- preserve numbers
- preserve factual relationships
- remove filler rather than introduce new filler
- follow the requested cleanup style loosely

**v1.1 win criteria**

- output preserves key numbers from the source
  - for the test case: `4` and `3 of 5` or equivalent wording such as
    `3 out of 5`
- output does not introduce filler language
- output is cleaner and readable

**Notes**

- Replace exact phrase checks with fact-preservation checks.
- This card was clearly too brittle in `v1`.

### 5. `what-matters-summary`

**Question**

Can the model compress a note into the three highest-signal points and preserve
why they matter?

**What a good answer should do**

- produce exactly three points or very clearly three grouped items
- include some evidence or grounding
- rank or prioritize the points in some usable way

**v1.1 win criteria**

- returns exactly three summary items
- each item has a substantive point
- each item includes evidence, quote, or grounding text
- priority or rank is represented numerically or ordinally

**Notes**

- Accept `topPoints`, `summary`, `points`, or equivalent list wrappers.
- This is still a good card, but it should stop depending on one field name.

### 6. `calendar-intent-detection`

**Question**

Can the model detect a calendar-worthy event and safely represent the event
intent using the memo timestamp and timezone?

**What a good answer should do**

- identify that an event exists
- resolve the relative date correctly
- preserve the intended participant or event topic
- represent time with timezone awareness

**v1.1 win criteria**

- at least one event or scheduling intent object is present
- resolved date is correct
  - for the test case: `2026-04-05`
- time is represented as `2 PM` / `14:00` / ISO with timezone
- title or participant field refers to `Sam`

**Notes**

- Do not require one exact packet shape.
- Accept:
  - event arrays
  - top-level event objects
  - scheduling-intent packets

### 7. `reminder-normalization`

**Question**

Can the model turn vague spoken reminder language into a clear, actionable
reminder while acknowledging missing time information?

**What a good answer should do**

- produce imperative reminder wording
- remove hedges like `maybe`
- avoid inventing dates
- ask a clarifying question when timing is missing

**v1.1 win criteria**

- reminder text is present and concrete
- reminder text does not contain weak hedge words from the source
  - for the test case: no `maybe`
- reminder text is action-oriented
- if no due date is known:
  - due date is null/omitted
  - and a follow-up question is present

**Notes**

- “starts with a verb” should be treated as a soft style preference, not the
  whole card.

### 8. `private-redaction-pass`

**Question**

Can the model redact sensitive data while preserving memo readability and
reporting what it redacted?

**What a good answer should do**

- remove raw sensitive tokens
- replace them with clear placeholders or masked values
- capture the redacted entities separately

**v1.1 win criteria**

- no raw sensitive tokens remain in the redacted text
  - for the test case: SSN and account number must be absent
- at least two sensitive entities are identified
- redacted output remains readable

**Notes**

- Accept:
  - `redactedTranscript`
  - `redacted_text`
  - equivalent text fields
- Accept:
  - `entities`
  - `redacted_entities`
  - equivalent entity lists

## Current read

The `ship-soon` cards are mostly salvageable.

The largest fixes are:

- remove brittle exact-phrase checks
- accept equivalent schema variants
- separate task success from exact contract obedience
- treat confidence thresholds as soft calibration signals, not absolute truth
