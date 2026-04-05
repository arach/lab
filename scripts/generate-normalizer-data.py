#!/usr/bin/env python3
"""Generate normalizer training data by degrading clean protocol dictations.

Takes 4,977 clean protocol dictations from bash-v3/minimal/train.jsonl and
generates degraded variants to train a normalizer model.

Variants:
  - Fuzzy (2x): Remove 30-70% of "space" keywords, replace synonyms
  - Natural (1x): Add conversational filler prefix + light fuzzy
  - Chaotic (1x): Insert self-corrections at random points + filler
  - Clean passthrough (1x): Identity — teach model to leave clean input alone

Output: ~25k training pairs in datasets/finetune/normalizer-v1/{train,valid,test}.jsonl
"""

import json
import random
from pathlib import Path
from collections import Counter

SEED = 42

# ── System prompt for normalizer ─────────────────────────────────────────

SYSTEM_PROMPT = (
    "Normalize dictated input into clean protocol format. "
    "Insert 'space' between arguments. "
    "Replace synonyms (minus→dash, period→dot, forward slash→slash, hyphen→dash, "
    "asterisk→star, hashtag→hash, double dash→dash dash, minus minus→dash dash). "
    "Strip conversational filler. "
    "Resolve self-corrections (keep only final intent). "
    "Output only the clean protocol text."
)

# ── Synonym replacement tables ───────────────────────────────────────────

# Protocol word → possible fuzzy alternatives
SYNONYM_REPLACEMENTS = {
    'dash': ['minus', 'hyphen'],
    'dot': ['period'],
    'slash': ['forward slash'],
    'star': ['asterisk'],
    'hash': ['hashtag'],
    'bang': ['exclamation mark'],
    'redirect': ['greater than'],
    'colon': ['colon sign'],
}

# Two-word protocol → fuzzy alternatives
TWO_WORD_REPLACEMENTS = {
    'dash dash': ['double dash', 'minus minus'],
}

# ── Filler prefixes ─────────────────────────────────────────────────────

FILLER_PREFIXES = [
    "okay so the command is ",
    "so the command is ",
    "can you type ",
    "can you type out ",
    "type ",
    "type out ",
    "um so ",
    "um the command is ",
    "okay let me type ",
    "so we need to run ",
    "basically run ",
    "let's do ",
    "let's see ",
    "I wanna run ",
    "I want to type ",
    "right so ",
    "okay ",
    "so ",
    "um ",
    "the command is ",
    "we need ",
    "just run ",
    "go ahead and type ",
    "I think it's ",
    "the next command should be ",
    "for this one it's ",
    "and then we do ",
]

FILLER_SUFFIXES = [
    " I think",
    " right",
    " yeah",
    " okay",
    "",
    "",
    "",
    "",
    "",
    "",  # Weight toward no suffix
]

# ── Self-correction patterns ────────────────────────────────────────────

CORRECTIONS = [
    "no wait ",
    "wait no ",
    "actually ",
    "no no ",
    "scratch that ",
    "I meant ",
    "hmm actually ",
    "wait ",
    "no actually ",
    "sorry I meant ",
    "no not that ",
]

# Wrong segments inserted before a correction
WRONG_SEGMENTS = [
    "dash dash force",
    "dash dash verbose",
    "dash dash help",
    "slash usr",
    "slash tmp",
    "dash r",
    "dash a",
    "dash l",
    "dot txt",
    "dot log",
    "dash n",
    "dash dash rm",
    "quote test quote",
    "star",
    "pipe",
]


def fuzzy_degrade(clean_protocol, rng):
    """Remove random 'space' keywords and replace synonyms.

    Creates a "fuzzy" variant: the protocol words are mostly there but
    spaces are missing and some words use synonyms.
    """
    # First pass: two-word replacements
    result_text = clean_protocol
    for proto, alternatives in TWO_WORD_REPLACEMENTS.items():
        if proto in result_text and rng.random() < 0.5:
            replacement = rng.choice(alternatives)
            # Only replace the first occurrence to keep things realistic
            result_text = result_text.replace(proto, replacement, 1)

    words = result_text.split()
    removal_rate = rng.uniform(0.3, 0.7)
    result = []

    for w in words:
        # Remove some "space" keywords
        if w == 'space' and rng.random() < removal_rate:
            continue

        # Replace synonyms
        if w in SYNONYM_REPLACEMENTS and rng.random() < 0.4:
            replacement = rng.choice(SYNONYM_REPLACEMENTS[w])
            # "forward slash" is two words — just append
            result.append(replacement)
        else:
            result.append(w)

    return ' '.join(result)


def natural_degrade(clean_protocol, rng):
    """Add conversational filler around clean or lightly fuzzified protocol."""
    words = clean_protocol.split()
    result = []

    # Light fuzzy: remove only 0-20% of spaces, occasional synonym swap
    for w in words:
        if w == 'space' and rng.random() < 0.15:
            continue
        if w in SYNONYM_REPLACEMENTS and rng.random() < 0.15:
            result.append(rng.choice(SYNONYM_REPLACEMENTS[w]))
        else:
            result.append(w)

    core = ' '.join(result)
    prefix = rng.choice(FILLER_PREFIXES)
    suffix = rng.choice(FILLER_SUFFIXES)

    return prefix + core + suffix


def chaotic_degrade(clean_protocol, rng):
    """Insert self-corrections and filler into the protocol."""
    words = clean_protocol.split()

    if len(words) < 4:
        # Too short for meaningful correction — just add filler
        prefix = rng.choice(FILLER_PREFIXES[:10])
        return prefix + clean_protocol

    # Pick a random insertion point in the first half
    insert_pos = rng.randint(1, max(1, len(words) // 2))

    wrong = rng.choice(WRONG_SEGMENTS)
    correction = rng.choice(CORRECTIONS)

    before = ' '.join(words[:insert_pos])
    after = ' '.join(words[insert_pos:])

    # Also apply some fuzzy degradation on the remaining part
    after_words = after.split()
    after_result = []
    for w in after_words:
        if w == 'space' and rng.random() < 0.25:
            continue
        if w in SYNONYM_REPLACEMENTS and rng.random() < 0.3:
            after_result.append(rng.choice(SYNONYM_REPLACEMENTS[w]))
        else:
            after_result.append(w)
    after = ' '.join(after_result)

    # Sometimes add filler prefix too
    prefix = rng.choice(FILLER_PREFIXES) if rng.random() < 0.4 else ""

    return f"{prefix}{before} {wrong} {correction}{after}"


def main():
    rng = random.Random(SEED)

    # Load clean protocol dictations from bash-v3 training data
    train_path = Path("datasets/finetune/bash-v3/minimal/train.jsonl")

    clean_protocols = []
    with open(train_path) as f:
        for line in f:
            entry = json.loads(line)
            # User content is the clean protocol dictation
            user_content = entry['messages'][1]['content']
            clean_protocols.append(user_content)

    print(f"Loaded {len(clean_protocols)} clean protocol dictations")

    # Generate degraded variants
    pairs = []
    variant_counts = Counter()

    for clean in clean_protocols:
        # Clean passthrough (1x): identity
        pairs.append({
            'input': clean,
            'output': clean,
            'variant': 'clean',
        })
        variant_counts['clean'] += 1

        # Fuzzy (2x): different degradation each time
        for _ in range(2):
            fuzzy = fuzzy_degrade(clean, rng)
            if fuzzy != clean:  # Only add if actually degraded
                pairs.append({
                    'input': fuzzy,
                    'output': clean,
                    'variant': 'fuzzy',
                })
                variant_counts['fuzzy'] += 1

        # Natural (1x): filler prefix + light fuzzy
        natural = natural_degrade(clean, rng)
        pairs.append({
            'input': natural,
            'output': clean,
            'variant': 'natural',
        })
        variant_counts['natural'] += 1

        # Chaotic (1x): self-corrections + filler
        chaotic = chaotic_degrade(clean, rng)
        pairs.append({
            'input': chaotic,
            'output': clean,
            'variant': 'chaotic',
        })
        variant_counts['chaotic'] += 1

    print(f"\nGenerated {len(pairs)} training pairs:")
    for variant, count in sorted(variant_counts.items()):
        print(f"  {variant}: {count}")

    # Shuffle
    rng.shuffle(pairs)

    # Split 90/5/5
    n = len(pairs)
    test_size = max(1, n // 20)      # 5%
    valid_size = max(1, n // 20)     # 5%
    train_size = n - test_size - valid_size  # 90%

    train = pairs[:train_size]
    valid = pairs[train_size:train_size + valid_size]
    test = pairs[train_size + valid_size:]

    print(f"\nSplits: train={len(train)}, valid={len(valid)}, test={len(test)}")

    # Write output
    out_dir = Path("datasets/finetune/normalizer-v1")
    out_dir.mkdir(parents=True, exist_ok=True)

    def write_jsonl(path, data):
        with open(path, 'w') as f:
            for item in data:
                entry = {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": item['input']},
                        {"role": "assistant", "content": item['output']},
                    ]
                }
                f.write(json.dumps(entry) + '\n')

    write_jsonl(out_dir / "train.jsonl", train)
    write_jsonl(out_dir / "valid.jsonl", valid)
    write_jsonl(out_dir / "test.jsonl", test)

    print(f"\nWrote to {out_dir}/")

    # Show samples
    print(f"\n{'='*70}")
    print("  SAMPLE PAIRS")
    print(f"{'='*70}\n")

    for variant in ['clean', 'fuzzy', 'natural', 'chaotic']:
        examples = [p for p in pairs if p['variant'] == variant][:2]
        for ex in examples:
            print(f"  [{variant}]")
            print(f"    input:  {ex['input'][:120]}")
            print(f"    output: {ex['output'][:120]}")
            print()


if __name__ == '__main__':
    main()
