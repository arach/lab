#!/usr/bin/env python3
"""Convert NL2Bash commands → dictation training pairs for syntax reconstruction.

v2: Improved converter following the Talkie Dictation Protocol.

Key improvements over v1:
- Natural number words (0-99) instead of digit-by-digit
- Smarter flag handling: -la → "dash L A", -name → "dash name"
- Token-level processing: handles tightly-bound tokens like 2>/dev/null
- Consistent spacing: whitespace-separated tokens in bash = word boundaries
- Better multi-char pattern matching
"""

import json
import random
import re
from pathlib import Path

SEED = 42

# ── System Prompts ───────────────────────────────────────────────────────

SYSTEM_MINIMAL = (
    "Reconstruct the intended syntax from the dictated text. "
    "Output only the result."
)

SYSTEM_PROTOCOL = (
    "Convert dictated syntax to code.\n"
    "Symbol words: dash(-) dot(.) slash(/) pipe(|) star(*) bang(!) "
    "hash(#) tilde(~) at(@) dollar($) percent(%) caret(^) equals(=) "
    "plus(+) colon(:) semicolon(;) underscore(_) comma(,) backslash(\\)\n"
    "Quotes: quote(\") single quote(') backtick(`)\n"
    "Brackets: open/close paren()  brace{}  bracket[]  angle<>\n"
    "Pairs: dash dash(--) and and(&&) pipe pipe(||) dot dot(..)\n"
    "Casing: camel case(camelCase) snake case(snake_case) "
    "kebab case(kebab-case) pascal case(PascalCase) all caps(ALLCAPS)\n"
    "Spacing: no space(join words)\n"
    "Letters after dash are flags: dash L A → -la\n"
    "Numbers spoken as words: forty two → 42\n"
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

    # 100+: digit-by-digit (unambiguous, matches how people dictate IPs, ports, etc.)
    return ' '.join(ONES[int(d)] for d in num_str)


# ── Single char map ──────────────────────────────────────────────────────

CHAR_MAP = {
    '-': 'dash',
    '.': 'dot',
    '/': 'slash',
    '|': 'pipe',
    '>': 'greater than',
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

def convert_token(token: str) -> str | None:
    """Convert a single whitespace-delimited bash token to dictation.

    Processes the token character by character, accumulating letter runs
    and converting symbols/numbers to spoken form.

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

            # After a dash, short letter runs (1-3 chars) are flags → spell out
            if len(word) <= 3 and parts and parts[-1] == 'dash':
                parts.extend(ch.upper() for ch in word)
            elif len(word) == 1:
                # Standalone single letter → uppercase
                parts.append(word.upper())
            else:
                # Regular word
                parts.append(word)
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

    Splits by whitespace first (preserving bash token boundaries),
    then converts each token individually. This means spacing in the
    output matches the original command's whitespace exactly.

    Returns None if any token can't be cleanly converted.
    """
    # Split by whitespace, preserving token boundaries
    tokens = cmd.split()
    if not tokens:
        return None

    dictated_tokens = []
    for token in tokens:
        converted = convert_token(token)
        if converted is None:
            return None
        dictated_tokens.append(converted)

    result = ' '.join(dictated_tokens)
    return result if result else None


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    cm_path = Path("datasets/nl2bash-repo/data/bash/all.cm")
    out_dir = Path("datasets/finetune/bash-v2")
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
        if word_count > 40 or word_count < 3:
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

    # Print sample conversions
    print(f"\n{'='*70}")
    print("  SAMPLE PAIRS (v2 converter)")
    print(f"{'='*70}\n")
    for p in pairs[:20]:
        print(f"  dictated: {p['dictated']}")
        print(f"  expected: {p['expected']}")
        print()

    # Show number conversion examples
    print(f"{'='*70}")
    print("  NUMBER HANDLING EXAMPLES")
    print(f"{'='*70}\n")
    examples = ['0', '1', '5', '10', '12', '20', '42', '80', '99',
                '100', '127', '0644', '0755', '255', '443',
                '1024', '3000', '5432', '8080', '9090', '65535']
    for s in examples:
        print(f"  {s:>5} → {number_to_words(s)}")


if __name__ == "__main__":
    main()
