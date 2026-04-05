#!/usr/bin/env python3
"""Convert NL2Bash commands → dictation training pairs for syntax reconstruction.

v3: "Space is a word" model.

Core idea: the word "space" is an explicit token in the dictation that means
"insert a literal space here." Everything else concatenates. This eliminates
the entire class of spacing ambiguity from v2.

v2 problem:
    tail -n1  → "tail dash N one"
    tail -n 1 → "tail dash N one"   ← SAME DICTATION, different output!

v3 fix:
    tail -n1  → "tail space dash N one"        → tail + ' ' + -n1
    tail -n 1 → "tail space dash N space one"   → tail + ' ' + -n + ' ' + 1

Rules for the model:
    1. Map each spoken word to its text form (dash→-, one→1, etc.)
    2. Concatenate everything by default
    3. The word "space" → insert a literal space
"""

import json
import random
import re
from pathlib import Path

SEED = 42

# ── System Prompts ───────────────────────────────────────────────────────

SYSTEM_MINIMAL = (
    "Reconstruct the intended syntax from the dictated text. "
    "The word 'space' means insert a literal space. "
    "Everything else concatenates. "
    "Output only the result."
)

SYSTEM_PROTOCOL = (
    "Reconstruct syntax from dictated text.\n"
    "Default: all words concatenate into one token.\n"
    "The word 'space' inserts a literal space (argument boundary).\n"
    "Symbol words: dash(-) dot(.) slash(/) pipe(|) star(*) bang(!) "
    "hash(#) tilde(~) at(@) dollar($) percent(%) caret(^) equals(=) "
    "plus(+) colon(:) semicolon(;) underscore(_) comma(,) backslash(\\)\n"
    "Quotes: quote(\") single quote(') backtick(`)\n"
    "Brackets: open/close paren()  brace{}  bracket[]  angle<>\n"
    "Pairs: dash dash(--) and and(&&) pipe pipe(||) dot dot(..)\n"
    "Append: append(>>)  Redirect: redirect(>)\n"
    "Numbers: spoken as words (one→1, forty two→42)\n"
    "Flags: letters after dash are lowercase flags (dash L A → -la)\n"
    "Capital: capital X → X (preserves uppercase)\n"
    "Output only the result."
)

# ── Number Words ─────────────────────────────────────────────────────────

ONES = [
    'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
    'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen',
    'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen',
]
TENS = [
    '', '', 'twenty', 'thirty', 'forty', 'fifty',
    'sixty', 'seventy', 'eighty', 'ninety',
]


def number_to_words(num_str: str) -> str:
    """Convert a number string to spoken words.

    Rules:
    - 0-99: natural words (zero, twelve, forty two, ninety nine)
    - 100+: digit-by-digit (one two seven, eight zero eight zero)
    - Leading zeros: always digit-by-digit (zero six four four for 0644)

    Takes string not int to preserve leading zeros.
    """
    # Leading zeros → always digit-by-digit
    if len(num_str) > 1 and num_str[0] == '0':
        return ' '.join(ONES[int(d)] for d in num_str)

    n = int(num_str)

    # 0-99: natural spoken form
    if n < 20:
        return ONES[n]
    if n < 100:
        if n % 10 == 0:
            return TENS[n // 10]
        return f"{TENS[n // 10]} {ONES[n % 10]}"

    # 100+: digit-by-digit
    return ' '.join(ONES[int(d)] for d in num_str)


# ── Single char map ──────────────────────────────────────────────────────

CHAR_MAP = {
    '-': 'dash',
    '.': 'dot',
    '/': 'slash',
    '|': 'pipe',
    '>': 'redirect',
    '<': 'less than',
    '(': 'open paren',
    ')': 'close paren',
    '{': 'open brace',
    '}': 'close brace',
    '[': 'open bracket',
    ']': 'close bracket',
    '"': 'quote',
    "'": 'single quote',
    '`': 'backtick',
    '*': 'star',
    '~': 'tilde',
    '@': 'at',
    '#': 'hash',
    '$': 'dollar',
    '%': 'percent',
    '^': 'caret',
    '&': 'ampersand',
    '=': 'equals',
    '+': 'plus',
    ':': 'colon',
    ';': 'semicolon',
    '?': 'question mark',
    '!': 'bang',
    '\\': 'backslash',
    '_': 'underscore',
    ',': 'comma',
}

# ── Filters ──────────────────────────────────────────────────────────────

SKIP_PATTERNS = [
    re.compile(r'`'),           # backtick subshells
    re.compile(r'\$\('),        # $() subshells
    re.compile(r'\\[nt"\'()]'), # escape sequences
    re.compile(r'\\\\'),        # double backslash
    re.compile(r"awk\s+'"),     # awk scripts
    re.compile(r"sed\s+'"),     # sed scripts
    re.compile(r"sed\s+-"),     # sed with flags
    re.compile(r'\{[0-9]'),     # brace expansion {1..10}
    re.compile(r'<<<'),         # here-strings
    re.compile(r'<<'),          # here-docs
    re.compile(r'\[\['),        # bash test brackets
    re.compile(r'\bif\s'),      # conditionals
    re.compile(r'\bfor\s'),     # loops
    re.compile(r'\bwhile\s'),   # loops
    re.compile(r'\bdo\b'),      # loop body
    re.compile(r'\bdone\b'),    # loop end
    re.compile(r'\bthen\b'),    # conditional body
    re.compile(r'\bfi\b'),      # conditional end
    re.compile(r'\bcase\s'),    # case statements
    re.compile(r'\besac\b'),    # case end
    re.compile(r'\bfunction\b'),# function defs
    re.compile(r'\(\)'),        # function parens
    re.compile(r'printf\s'),    # printf format strings
    re.compile(r'\$\{'),        # parameter expansion
    re.compile(r'[^\x00-\x7F]'), # non-ASCII characters
]


def should_skip(cmd: str) -> bool:
    """Return True if command is too complex for dictation."""
    if len(cmd) > 60:
        return True
    if len(cmd) < 5:
        return True
    if cmd.count('|') > 2:
        return True
    for pat in SKIP_PATTERNS:
        if pat.search(cmd):
            return True
    return False


# ── Token Converter ──────────────────────────────────────────────────────

def emit_word(word: str) -> str:
    """Convert a word to its dictation form with casing qualifiers.

    Casing rules:
    - all lowercase → as-is (default, no qualifier needed)
    - ALL UPPERCASE → "all caps <word>"
    - Capitalized   → "capital <word>"
    - Mixed case    → bail (return None) — too complex to dictate

    The model also learns contextual casing (env vars after $ are uppercase,
    commands are lowercase) so qualifiers aren't always required in practice.
    But the training data should include them so the model knows the convention.
    """
    if word.islower():
        return word
    if word.isupper():
        return f'all caps {word.lower()}'
    if word[0].isupper() and word[1:].islower():
        return f'capital {word.lower()}'
    # Mixed case (camelCase, etc.) — skip for now
    return None


def convert_token(token: str) -> str | None:
    """Convert a single whitespace-delimited bash token to dictation.

    Processes the token character by character, accumulating letter runs
    and converting symbols/numbers to spoken form.

    v3 changes:
    - Casing qualifiers: "capital X", "all caps var"
    - Flag casing preserved: -x → "dash x", -X → "dash capital X"
    - Multi-char uppercase words: VAR → "all caps var"
    - Capitalized words: Foto → "capital foto"

    Returns None if the token contains unconvertible characters.
    """
    parts = []
    i = 0
    n = len(token)

    while i < n:
        c = token[i]

        # ── Multi-char patterns ──
        # && and ||
        if c == '&' and i + 1 < n and token[i + 1] == '&':
            parts.append('and and')
            i += 2
            continue
        if c == '|' and i + 1 < n and token[i + 1] == '|':
            parts.append('pipe pipe')
            i += 2
            continue

        # -- (double dash)
        if c == '-' and i + 1 < n and token[i + 1] == '-':
            parts.append('dash dash')
            i += 2
            continue

        # .. (double dot)
        if c == '.' and i + 1 < n and token[i + 1] == '.':
            parts.append('dot dot')
            i += 2
            continue

        # >> (append redirect)
        if c == '>' and i + 1 < n and token[i + 1] == '>':
            parts.append('append')
            i += 2
            continue

        # 2> (stderr redirect) — only at start of token or after space
        if c == '2' and i + 1 < n and token[i + 1] == '>':
            if i + 2 < n and token[i + 2] == '&':
                parts.append('two redirect ampersand')
                i += 3
            else:
                parts.append('two redirect')
                i += 2
            continue

        # ── Number runs ──
        if c.isdigit():
            num_start = i
            while i < n and token[i].isdigit():
                i += 1
            num_str = token[num_start:i]
            parts.append(number_to_words(num_str))
            continue

        # ── Letter runs ──
        if c.isalpha():
            word_start = i
            while i < n and token[i].isalpha():
                i += 1
            word = token[word_start:i]

            # After a dash, short letter runs are flags — spell out
            # Also handle longer mixed-case flag runs like -aPSHiv
            is_flag = parts and parts[-1] == 'dash'
            is_short = len(word) <= 3
            has_mixed_case = not word.islower() and not word.isupper()

            if is_flag and (is_short or has_mixed_case):
                for ch in word:
                    if ch.isupper():
                        parts.append(f'capital {ch}')
                    else:
                        parts.append(ch)
            elif len(word) == 1:
                # Standalone single letter — preserve case
                if word.isupper():
                    parts.append(f'capital {word}')
                else:
                    parts.append(word)
            else:
                # Multi-char word — use casing qualifiers
                emitted = emit_word(word)
                if emitted is None:
                    return None  # mixed case too complex
                parts.append(emitted)
            continue

        # ── Single symbols ──
        if c in CHAR_MAP:
            parts.append(CHAR_MAP[c])
            i += 1
            continue

        # Unknown character → bail
        return None

    return ' '.join(parts) if parts else None


def bash_to_dictation(cmd: str) -> str | None:
    """Convert a bash command to its dictated form.

    v3 key change: token boundaries are marked with the word "space".

    In v2, `tail -n1` and `tail -n 1` both became "tail dash N one".
    In v3:
        tail -n1  → "tail space dash n one"
        tail -n 1 → "tail space dash n space one"

    The model learns: "space" = literal space, everything else concatenates.
    """
    tokens = cmd.split()
    if not tokens:
        return None

    dictated_tokens = []
    for token in tokens:
        converted = convert_token(token)
        if converted is None:
            return None
        dictated_tokens.append(converted)

    # v3: join with " space " — the word "space" is an explicit token
    result = ' space '.join(dictated_tokens)
    return result if result else None


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    cm_path = Path("datasets/nl2bash-repo/data/bash/all.cm")
    out_dir = Path("datasets/finetune/bash-v3")
    out_dir.mkdir(parents=True, exist_ok=True)

    commands = cm_path.read_text().strip().split('\n')
    print(f"Total commands in NL2Bash: {len(commands)}")

    # Filter and convert
    pairs = []
    skipped_filter = 0
    skipped_convert = 0
    seen = set()

    for cmd in commands:
        cmd = cmd.strip()
        if not cmd:
            continue

        if should_skip(cmd):
            skipped_filter += 1
            continue

        if cmd in seen:
            continue
        seen.add(cmd)

        dictated = bash_to_dictation(cmd)
        if dictated is None:
            skipped_convert += 1
            continue

        # Skip if dictation is too long or too short
        word_count = len(dictated.split())
        if word_count > 50 or word_count < 3:  # bumped from 40 — "space" adds words
            skipped_convert += 1
            continue

        pairs.append({
            "dictated": dictated,
            "expected": cmd,
        })

    print(f"Filtered out (complexity): {skipped_filter}")
    print(f"Filtered out (conversion): {skipped_convert}")
    print(f"Usable pairs: {len(pairs)}")

    # Shuffle and split: 80/10/10
    random.seed(SEED)
    random.shuffle(pairs)

    n = len(pairs)
    test_size = max(1, n // 10)
    valid_size = max(1, n // 10)
    train_size = n - test_size - valid_size

    train = pairs[:train_size]
    valid = pairs[train_size:train_size + valid_size]
    test = pairs[train_size + valid_size:]

    print(f"Train: {len(train)}, Valid: {len(valid)}, Test: {len(test)}")

    # Write BOTH prompt variants
    for label, system_prompt in [("minimal", SYSTEM_MINIMAL), ("protocol", SYSTEM_PROTOCOL)]:
        sub_dir = out_dir / label
        sub_dir.mkdir(exist_ok=True)

        def write_jsonl(path: Path, data: list):
            with open(path, 'w') as f:
                for item in data:
                    entry = {
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": item["dictated"]},
                            {"role": "assistant", "content": item["expected"]},
                        ]
                    }
                    f.write(json.dumps(entry) + '\n')

        write_jsonl(sub_dir / "train.jsonl", train)
        write_jsonl(sub_dir / "valid.jsonl", valid)
        write_jsonl(sub_dir / "test.jsonl", test)
        print(f"  Wrote {label}/ splits")

    # ── Show the key improvement ──
    print(f"\n{'='*70}")
    print("  V3 vs V2: AMBIGUITY RESOLUTION")
    print(f"{'='*70}\n")

    demo_pairs = [
        ("tail -n1", "tail -n 1"),
        ("cut -c1-10", "cut -c 1-10"),
        ("top -b -n1", "top -b -n 1"),
        ("ssh -X user@server", "ssh -x user@server"),
        ("chmod 0644 file.txt", "chmod 644 file.txt"),
    ]

    # Show casing qualifiers
    print(f"\n{'='*70}")
    print("  CASING QUALIFIERS")
    print(f"{'='*70}\n")

    case_examples = [
        "export PATH=/usr/bin",
        "echo $HOME",
        "find ~ -name 'Foto*'",
        "read -n10 -e VAR",
        "ls -la /tmp/MyDir",
        "grep -i ERROR log.txt",
    ]
    for cmd in case_examples:
        d = bash_to_dictation(cmd)
        if d:
            print(f"  {cmd:<35} → {d}")
        else:
            print(f"  {cmd:<35} → SKIPPED")
    print()
    for a, b in demo_pairs:
        da = bash_to_dictation(a)
        db = bash_to_dictation(b)
        same = "SAME ✗" if da == db else "DIFFERENT ✓"
        print(f"  {a:<25} → {da}")
        print(f"  {b:<25} → {db}")
        print(f"  {'':25}   {same}")
        print()

    # Print sample conversions
    print(f"{'='*70}")
    print("  SAMPLE PAIRS (v3 converter)")
    print(f"{'='*70}\n")
    for p in pairs[:15]:
        print(f"  dictated: {p['dictated']}")
        print(f"  expected: {p['expected']}")
        print()


if __name__ == "__main__":
    main()
