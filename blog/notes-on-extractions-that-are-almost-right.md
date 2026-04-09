# Notes on extractions from voice memos

> Some memo extractions are good drafts and bad finals.

<!-- METADATA
slug: notes-on-extractions-that-are-almost-right
date: 2026-04-08
tags: evals, extraction, uncertainty, benchmark-design, voice-notes
author: Arach
description: Pulling titles and lightweight actions from voice memos, how to measure the result, and what to do when an extraction is useful but not ready to finalize.
hidden: false
-->

<section id="page-1" class="article-page-section">
<div class="article-page-kicker">Part 1</div>

## Cleaning up the memo

The first useful thing an extraction does is make the memo easier to read back
later. A good title helps. A light action label helps. That is already enough
to make a voice memo app feel better.

The trouble starts when the extraction looks clean enough to trust.

Here is one of the clearest cases in the current pack:

```text
memo:
Email the landlord tomorrow and ask whether the lease addendum covers
subletting for the summer.
```

Across the saved runs, `gpt-4.1-mini`, `Claude Sonnet 4.5`, `Haiku 4.5`,
`Hermes-4-70B`, and both hosted Gemma variants all do roughly the same thing:

```json
{
  "title": "Email landlord about subletting in lease addendum",
  "intent": "email",
  "target": "landlord"
}
```

That extraction is useful.

The title is good. The action label is right. If all you wanted was a cleaner
note row or a rough route into an "email" bucket, it works.

It is also not finished.

The note is not about the landlord in general. It is about subletting and the
lease addendum. The target field throws away that part.

That distinction matters because voice memos often arrive in a messy middle
state. They are clear enough to name, sometimes clear enough to route, but not
always clear enough to finalize.

That is the pattern I keep seeing in this pack. A lot of misses are not random
misses. They are draft-quality extractions that get treated like final ones.
</section>

<section id="page-2" class="article-page-section">
<div class="article-page-kicker">Part 2</div>

## Measuring the extraction

The measurement problem is simple.

If I only score the title and the top-level intent label, the landlord example
looks done. The model got the note type right. It even wrote a title most
people would happily keep.

The current pack avoids that by scoring three things separately:

1. title quality
2. intent correctness
3. restraint

That third category matters more than it looked at first.

Take this memo:

```text
memo:
Need to talk to Maya about the deck or maybe just send it over first,
I'm not sure which is less annoying.
```

This is not a clean `call` note. It is not a clean `email` note either. The
memo is still deciding.

On this one, `Claude Sonnet 4.5` returns:

```json
{
  "title": "Decide how to share deck with Maya",
  "intent": "none",
  "target": ""
}
```

That is the right shape.

`gpt-4.1-mini` and `Haiku 4.5` do something more mixed:

```json
{
  "title": "Decide how to share deck with Maya",
  "intent": "none",
  "target": "Maya"
}
```

`Hermes-4-70B` goes farther and turns it into a call:

```json
{
  "title": "Discuss deck with Maya",
  "intent": "call",
  "target": "Maya"
}
```

Those are not the same kind of miss.

The `gpt-4.1-mini` and Haiku outputs are decent drafts. The title is useful.
The label backed off. But the target still leaks structured certainty the memo
did not provide.

The Hermes output is worse. It finalizes the route too early.

That is why I do not think a single blended score is enough. The title can be
good while the extraction is still too eager underneath.
</section>

<section id="page-3" class="article-page-section">
<div class="article-page-kicker">Part 3</div>

## Decisions after extraction

The product question after extraction is not "how confident is the model on a
scale from zero to one."

The product question is "can I finalize this or not."

Another memo in the pack makes that plain:

```text
memo:
Need to figure out the investor update soon because I keep putting it off and
the story still feels muddy.
```

This memo has pressure in it. It does not have a clean action in it.

`gpt-4.1-mini` returns:

```json
{
  "title": "Plan investor update to clarify story",
  "intent": "none",
  "target": ""
}
```

`Claude Sonnet 4.5` returns:

```json
{
  "title": "Figure out investor update story",
  "intent": "none",
  "target": ""
}
```

Those are both fine draft extractions. They clean up the note without inventing
the next step.

`Haiku 4.5` and `Hermes-4-70B` both route the same memo to `research` instead.

That is the decision boundary I care about.

Some extractions should become final structured actions. Some should stay as
drafts. Some should carry one more signal that says the note is not settled
yet.

That is where `needs_review` comes in.

Not as another confidence framework. Not as a decimal score the model made up
about itself.

Just as a small product flag for cases like:

- the title is good but the target is too thin
- the note points toward action but the channel is undecided
- the note sounds urgent but still lacks a clear next step

The next version of this pack should test that directly.

The article is really just one note about that boundary.

Good draft extraction is not the same thing as final extraction.
</section>
