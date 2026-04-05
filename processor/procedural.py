#!/usr/bin/env python3
"""Procedural dictation → syntax processor.

No LLM needed. Just token scanning with a symbol vocabulary.

Rules:
  1. "space" → literal space
  2. Symbol words → their character (dash→-, dot→., etc.)
  3. Synonyms: minus→-, period→., forward slash→/, etc.
  4. Number words → digits (one→1, forty two→42, hundred→00, thousand→000)
  5. Casing directives: camel case, snake case, pascal case, kebab case
  6. "capital X" → X (uppercase), "all caps word" → WORD
  7. Everything else → pass through literally
"""

import json
import re
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from repo_paths import EVAL_DIR, PIPELINE_DIR

# ── Symbol vocabulary ────────────────────────────────────────────────────

SYMBOLS = {
    # Primary protocol words
    'dash': '-',
    'dot': '.',
    'slash': '/',
    'pipe': '|',
    'redirect': '>',
    'append': '>>',
    'less': None,  # needs lookahead for "less than"
    'star': '*',
    'bang': '!',
    'hash': '#',
    'tilde': '~',
    'at': '@',
    'dollar': '$',
    'percent': '%',
    'caret': '^',
    'ampersand': '&',
    'equals': '=',
    'plus': '+',
    'colon': ':',
    'semicolon': ';',
    'underscore': '_',
    'comma': ',',
    'backslash': '\\',
    'quote': '"',
    'backtick': '`',
    'question': None,  # needs lookahead for "question mark"

    # Synonyms — common alternatives people use
    'minus': '-',
    'hyphen': '-',
    'period': '.',
    'asterisk': '*',
    'hashtag': '#',
}

# Two-word symbols (checked before single-word)
TWO_WORD_SYMBOLS = {
    ('single', 'quote'): "'",
    ('open', 'paren'): '(',
    ('close', 'paren'): ')',
    ('open', 'brace'): '{',
    ('close', 'brace'): '}',
    ('open', 'bracket'): '[',
    ('close', 'bracket'): ']',
    ('open', 'angle'): '<',
    ('close', 'angle'): '>',
    ('open', 'curly'): '{',
    ('close', 'curly'): '}',
    ('less', 'than'): '<',
    ('question', 'mark'): '?',
    ('dash', 'dash'): '--',
    ('double', 'dash'): '--',
    ('minus', 'minus'): '--',
    ('and', 'and'): '&&',
    ('pipe', 'pipe'): '||',
    ('dot', 'dot'): '..',
    ('two', 'redirect'): '2>',
    ('forward', 'slash'): '/',
    ('back', 'slash'): '\\',
    ('equals', 'sign'): '=',
    ('at', 'sign'): '@',
    ('dollar', 'sign'): '$',
    ('open', 'parenthesis'): '(',
    ('close', 'parenthesis'): ')',
    ('new', 'line'): '\n',
}

# Three-word symbols
THREE_WORD_SYMBOLS = {
    ('two', 'redirect', 'ampersand'): '2>&',
}

# ── Number words ─────────────────────────────────────────────────────────

ONES = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
    'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19,
}

TENS = {
    'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
    'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
}

MULTIPLIERS = {
    'hundred': 100,
    'thousand': 1000,
}

ALL_NUMBER_WORDS = set(ONES.keys()) | set(TENS.keys()) | set(MULTIPLIERS.keys())


def is_number_word(w):
    return w in ALL_NUMBER_WORDS


def consume_number(words, i):
    """Try to consume a number starting at position i.

    Handles:
    - Single: "five" → 5
    - Teens: "twelve" → 12
    - Compound: "forty two" → 42
    - Multipliers: "three thousand" → 3000, "one hundred" → 100
    - Digit sequences: "one nine two" → 192 (when 3+ single digits)
    - Mixed: "eight thousand" → 8000
    """
    w = words[i]

    # Tens word: twenty, thirty, etc.
    if w in TENS:
        val = TENS[w]
        j = i + 1
        # "forty two" compound
        if j < len(words) and words[j] in ONES and ONES[words[j]] < 10:
            val += ONES[words[j]]
            j += 1
        # Check for multiplier: "forty thousand"
        if j < len(words) and words[j] in MULTIPLIERS:
            val *= MULTIPLIERS[words[j]]
            j += 1
        return str(val), j

    # Single/teens: zero through nineteen
    if w in ONES:
        val = ONES[w]
        j = i + 1

        # Check for multiplier: "three thousand", "one hundred"
        if j < len(words) and words[j] in MULTIPLIERS:
            val *= MULTIPLIERS[words[j]]
            j += 1
            # "three thousand two hundred" etc — keep consuming
            # But keep it simple for now
            return str(val), j

        # Check for digit sequence: "one nine two" → "192"
        # Only if next word is ALSO a single digit (0-9)
        result = str(val)
        while j < len(words) and words[j] in ONES and ONES[words[j]] < 10:
            result += str(ONES[words[j]])
            j += 1
        if j > i + 1:
            return result, j

        return str(val), i + 1

    return None, i


# ── Casing directives ───────────────────────────────────────────────────

CASING_DIRECTIVES = {'camel', 'snake', 'pascal', 'kebab', 'screaming'}


def consume_casing(words, i):
    """Try to consume a casing directive and its arguments.

    "camel case get user profile" → "getUserProfile"
    "snake case api key" → "api_key"
    "pascal case my component" → "MyComponent"
    "kebab case my component" → "my-component"

    Consumes words until "space" or end of input.
    Returns (result, new_i) or (None, i).
    """
    w = words[i].lower()
    if w not in CASING_DIRECTIVES:
        return None, i
    if i + 1 >= len(words) or words[i + 1].lower() != 'case':
        return None, i

    style = w
    j = i + 2

    # Consume words until "space" or end or another directive/symbol
    parts = []
    while j < len(words):
        next_w = words[j]
        if next_w == 'space':
            break
        if next_w in SYMBOLS:
            break
        if next_w in CASING_DIRECTIVES and j + 1 < len(words) and words[j + 1] == 'case':
            break
        if next_w in TWO_WORD_SYMBOLS or next_w == 'all' or next_w == 'capital':
            break
        parts.append(next_w.lower())
        j += 1

    if not parts:
        return None, i

    if style == 'camel':
        result = parts[0] + ''.join(p.capitalize() for p in parts[1:])
    elif style == 'pascal':
        result = ''.join(p.capitalize() for p in parts)
    elif style == 'snake':
        result = '_'.join(parts)
    elif style == 'kebab':
        result = '-'.join(parts)
    elif style == 'screaming':
        result = '_'.join(p.upper() for p in parts)
    else:
        return None, i

    return result, j


# ── ML-based needs_llm detector ─────────────────────────────────────────
# Replaces the old heuristic is_protocol(). Loads weights from
# pipeline/needs-llm-model.json and does feature extraction + dot product +
# sigmoid. No sklearn needed at runtime.

import math as _math

_NLM_MODEL = None  # cached on first call


def _load_nlm_model():
    """Load the trained model weights from JSON (cached)."""
    global _NLM_MODEL
    if _NLM_MODEL is not None:
        return _NLM_MODEL

    model_path = PIPELINE_DIR / 'needs-llm-model.json'
    with open(model_path) as f:
        _NLM_MODEL = json.load(f)
    # Convert lists to frozensets for fast lookup
    _NLM_MODEL['_protocol_vocab'] = frozenset(_NLM_MODEL['protocol_vocab'])
    _NLM_MODEL['_filler_words'] = frozenset(_NLM_MODEL['filler_words'])
    _NLM_MODEL['_casing_starters'] = frozenset(_NLM_MODEL['casing_starters'])
    return _NLM_MODEL


def _extract_features(text, model):
    """Extract 10 numeric features from dictated text."""
    words = text.lower().split()
    n = len(words)
    if n == 0:
        return [0.0] * 10

    protocol_vocab = model['_protocol_vocab']
    filler_words = model['_filler_words']
    casing_starters = model['_casing_starters']
    intent_phrases = model['intent_phrases']
    correction_phrases = model['correction_phrases']

    space_count = words.count('space')
    space_ratio = space_count / n
    space_present = 1.0 if space_count > 0 else 0.0
    protocol_count = sum(1 for w in words if w in protocol_vocab)
    protocol_ratio = protocol_count / n
    filler_count = sum(1 for w in words if w in filler_words)

    text_lower = text.lower()
    intent_count = sum(1 for p in intent_phrases if p in text_lower)
    correction_count = sum(1 for p in correction_phrases if p in text_lower)

    starts_casing = 1.0 if words[0] in casing_starters else 0.0
    word_count = n / 20.0
    non_protocol_ratio = 1.0 - protocol_ratio
    avg_word_len = sum(len(w) for w in words) / n

    return [
        space_ratio, space_present, protocol_ratio, filler_count,
        intent_count, correction_count, starts_casing, word_count,
        non_protocol_ratio, avg_word_len,
    ]


def needs_llm(text):
    """Does this dictated input need LLM normalization?

    Returns True if the input is fuzzy/natural/chaotic and needs LLM.
    Returns False if the input is clean protocol and the processor can handle it.

    Uses a trained logistic regression model (10 features, dot product + sigmoid).
    """
    model = _load_nlm_model()
    features = _extract_features(text, model)
    weights = model['weights']
    bias = model['bias']
    threshold = model['threshold']

    logit = sum(f * w for f, w in zip(features, weights)) + bias
    prob = 1.0 / (1.0 + _math.exp(-logit))
    return prob >= threshold


def process_dictation(text):
    """Convert dictated text to syntax using purely procedural rules."""
    # Normalize alternative casing/caps forms before splitting
    text = re.sub(r'\bcamel[-_]?case\b', 'camel case', text, flags=re.IGNORECASE)
    text = re.sub(r'\bpascal[-_]?case\b', 'pascal case', text, flags=re.IGNORECASE)
    text = re.sub(r'\bsnake[-_]?case\b', 'snake case', text, flags=re.IGNORECASE)
    text = re.sub(r'\bkebab[-_]?case\b', 'kebab case', text, flags=re.IGNORECASE)
    text = re.sub(r'\bscreaming[-_]?case\b', 'screaming case', text, flags=re.IGNORECASE)
    text = re.sub(r'\ball[-_]caps\b', 'all caps', text, flags=re.IGNORECASE)

    words = text.split()
    output = []
    i = 0
    n = len(words)
    in_quote = False
    last_was_word = False

    while i < n:
        w = words[i]

        # ── "space" → literal space ──
        if w == 'space':
            output.append(' ')
            last_was_word = False
            i += 1
            continue

        # ── Three-word symbols ──
        if i + 2 < n:
            triple = (words[i], words[i+1], words[i+2])
            if triple in THREE_WORD_SYMBOLS:
                output.append(THREE_WORD_SYMBOLS[triple])
                last_was_word = False
                i += 3
                continue

        # ── Casing directives ──
        cased, new_i = consume_casing(words, i)
        if cased is not None:
            output.append(cased)
            last_was_word = False
            i = new_i
            continue

        # ── Two-word symbols ──
        if i + 1 < n:
            pair = (words[i], words[i+1])
            if pair in TWO_WORD_SYMBOLS:
                sym = TWO_WORD_SYMBOLS[pair]
                output.append(sym)
                if sym in ('"', "'"):
                    in_quote = not in_quote
                last_was_word = False
                i += 2
                continue

        # ── "all caps <word>" ──
        if w == 'all' and i + 2 < n and words[i+1] == 'caps':
            output.append(words[i+2].upper())
            last_was_word = False
            i += 3
            continue

        # ── "capital <letter or word>" ──
        if w == 'capital' and i + 1 < n:
            next_w = words[i+1]
            if len(next_w) == 1:
                output.append(next_w.upper())
            else:
                output.append(next_w[0].upper() + next_w[1:])
            last_was_word = False
            i += 2
            continue

        # ── Single-word symbols ──
        if w in SYMBOLS and SYMBOLS[w] is not None:
            sym = SYMBOLS[w]
            output.append(sym)
            if sym in ('"', "'"):
                in_quote = not in_quote
            last_was_word = False
            i += 1
            continue

        # ── Number words ──
        if is_number_word(w):
            num_str, new_i = consume_number(words, i)
            if num_str is not None:
                output.append(num_str)
                last_was_word = False
                i = new_i
                continue

        # ── Regular word → pass through ──
        # Inside quotes, insert spaces between consecutive regular words
        if in_quote and last_was_word:
            output.append(' ')
        output.append(w)
        last_was_word = True
        i += 1

    return ''.join(output)


# ── Main: evaluate ──────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    from collections import defaultdict

    eval_file = Path(sys.argv[1]) if len(sys.argv) > 1 else EVAL_DIR / 'independent.json'
    data = json.load(open(eval_file))

    n = len(data)
    exact = ws = wsc = 0
    errors = []
    cat_results = defaultdict(lambda: {'exact': 0, 'total': 0})

    # Group by difficulty if present
    by_difficulty = defaultdict(list)

    for d in data:
        got = process_dictation(d['dictated'])
        expected = d['expected']

        ws_got = re.sub(r'\s+', ' ', got.strip())
        ws_exp = re.sub(r'\s+', ' ', expected.strip())
        is_exact = got == expected
        is_ws = ws_got == ws_exp
        is_wsc = ws_got.lower() == ws_exp.lower()

        if is_exact: exact += 1
        if is_ws: ws += 1
        if is_wsc: wsc += 1

        diff = d.get('difficulty', 'unknown')
        by_difficulty[diff].append(is_exact)

        if not is_exact:
            errors.append({
                'dictated': d['dictated'][:80],
                'expected': expected[:60],
                'got': got[:60],
                'category': d.get('category', ''),
                'difficulty': diff,
            })

    print(f'PROCEDURAL PROCESSOR — {eval_file}')
    print('=' * 70)
    print(f'  Exact:   {exact}/{n} ({exact/n*100:.1f}%)')
    print(f'  WS-norm: {ws}/{n} ({ws/n*100:.1f}%)')
    print(f'  WS+case: {wsc}/{n} ({wsc/n*100:.1f}%)')
    print()

    if len(by_difficulty) > 1:
        print('BY DIFFICULTY:')
        for diff in ['clean', 'fuzzy', 'natural', 'chaotic', 'unknown']:
            if diff in by_difficulty:
                results = by_difficulty[diff]
                ex = sum(results)
                tot = len(results)
                print(f'  {diff:>10}: {ex}/{tot} ({ex/tot*100:.0f}%)')
        print()

    print(f'ERRORS ({len(errors)}, showing first 15):')
    print('-' * 70)
    for e in errors[:15]:
        print(f'  [{e["difficulty"]:>7}] [{e["category"]}]')
        print(f'    expected: {e["expected"]}')
        print(f'    got:      {e["got"]}')
        print()
