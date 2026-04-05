#!/usr/bin/env python3
"""Zero-training normalizer pipeline.

Architecture:
  Raw transcript
    → Protocol detector (is it already in protocol format?)
    → IF protocol: strip filler procedurally → processor
    → IF NOT protocol: LLM normalize → processor
    → Final syntax output

The LLM only handles non-protocol input (fuzzy dictation, natural language).
Protocol-format input bypasses the LLM entirely for deterministic handling.
"""

import json
import sys
import time
import re
import os
import argparse
from collections import defaultdict

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

# Import the procedural processor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'processor'))
from procedural import process_dictation

# ── Protocol detection ───────────────────────────────────────────────────

# Words that are part of the protocol vocabulary (not filler)
PROTOCOL_VOCAB = {
    'space', 'dash', 'dot', 'slash', 'pipe', 'star', 'bang', 'hash',
    'tilde', 'at', 'dollar', 'percent', 'caret', 'ampersand', 'equals',
    'plus', 'colon', 'semicolon', 'underscore', 'comma', 'backslash',
    'quote', 'backtick', 'redirect', 'append',
    'capital', 'camel', 'snake', 'pascal', 'kebab', 'screaming',
}

# Common conversational filler patterns to strip
FILLER_PREFIXES = [
    r"^okay\s+so\s+(?:the\s+command\s+is\s+|like\s+)?",
    r"^so\s+(?:the\s+command\s+is\s+|like\s+|it's\s+)?",
    r"^um+\s+(?:so\s+)?(?:the\s+)?",
    r"^(?:I\s+wanna?|I\s+want\s+to)\s+(?:\w+\s+)*?(?:to\s+|is\s+)?",
    r"^can\s+you\s+(?:type\s+(?:out\s+)?)?",
    r"^(?:let's\s+(?:do|see|try)\s+)",
    r"^basically\s+(?:run\s+|do\s+|type\s+)?",
    r"^(?:and\s+then|then)\s+",
    r"^right\s+so\s+",
    r"^(?:type\s+(?:out\s+)?)",
    r"^okay\s+(?:let\s+me\s+type\s+)?(?:the\s+)?(?:\w+\s+)?(?:command\s+)?(?:so\s+)?(?:it's\s+)?",
    r"^I\s+think\s+we\s+need\s+",
    r"^(?:so\s+)?for\s+the\s+\w+\s+(?:variable\s+)?(?:it's\s+)?",
    r"^I\s+want\s+to\s+run\s+",
]

FILLER_SUFFIXES = [
    r"\s+I\s+think$",
    r"\s+right$",
    r"\s+yeah$",
]


FILLER_WORDS = {
    'okay', 'ok', 'so', 'um', 'uh', 'like', 'basically', 'actually',
    'i', 'the', 'can', 'right', 'wait', 'well', 'and',
    'we', 'you', 'hmm', "let's", 'just',
    'then', "i'm", "it's", "that's",
    'should', 'would', 'could', 'maybe',
}

SELF_CORRECTION = {'wait', 'no', 'actually', 'meant', 'not'}


def is_pure_protocol(text):
    """Check if text is pure protocol format (no filler, no corrections).

    Returns True only if:
    1. Input contains "space" as separator (protocol format)
    2. Does NOT start with filler words (conversational)
    3. Does NOT contain self-correction markers
    """
    words = text.lower().split()
    if not words:
        return False

    # Must contain "space" keyword
    if 'space' not in words:
        return False

    # Must not start with filler
    if words[0] in FILLER_WORDS:
        return False

    # Must not contain self-correction patterns
    word_set = set(words)
    if word_set & SELF_CORRECTION:
        return False

    return True


def strip_filler(text):
    """Procedurally strip conversational filler from text."""
    result = text
    for pattern in FILLER_PREFIXES:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    for pattern in FILLER_SUFFIXES:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    return result.strip()


# ── LLM prompt (optimized for non-protocol input) ───────────────────────

SYSTEM_PROMPT = """You normalize voice dictation into clean protocol format for a processor.

YOUR JOB:
1. If the input already contains "space" keywords with conversational filler → strip the filler, output the protocol content VERBATIM
2. If input is natural speech without "space" keywords → normalize it:
   a) Replace synonyms: minus→dash, hyphen→dash, period→dot, forward slash→slash, asterisk→star, hashtag→hash, double dash→dash dash
   b) Insert "space" between separate arguments/tokens
   c) Do NOT insert "space" within: paths (slash-separated), dotted names (file dot txt), compound flags (dash dash verbose)
3. Resolve self-corrections (no wait, actually, I meant) → keep only the FINAL intent
4. Output ONLY protocol words — never output actual symbols like - . / @ etc.

PROTOCOL KEYWORDS (output as words):
Separator: space
Symbols: dash dot slash pipe star bang hash tilde at dollar percent caret ampersand equals plus colon semicolon underscore comma backslash quote backtick redirect append
Multi-word: dash dash, single quote, open/close paren, open/close brace, open/close bracket, less than, question mark, and and, pipe pipe, dot dot, new line
Casing: camel case, snake case, pascal case, kebab case (followed by the words to transform)
Capitalization: capital (next word), all caps (next word)
Numbers: zero through nineteen, twenty/thirty/.../ninety, hundred, thousand

Output ONLY the normalized protocol text. Nothing else."""

FEW_SHOT = [
    # Fuzzy: missing spaces, synonym replacement needed
    {
        "input": "git commit minus m quote fix login bug quote",
        "output": "git space commit space dash m space quote fix space login space bug quote"
    },
    {
        "input": "cat file period txt",
        "output": "cat space file dot txt"
    },
    {
        "input": "ls minus l minus a slash var slash log",
        "output": "ls space dash l space dash a space slash var slash log"
    },
    {
        "input": "docker run minus minus rm minus it ubuntu",
        "output": "docker space run space dash dash rm space dash it space ubuntu"
    },
    {
        "input": "cd forward slash usr forward slash local forward slash bin",
        "output": "cd space slash usr slash local slash bin"
    },
    {
        "input": "python server period py double dash port eight thousand",
        "output": "python space server dot py space dash dash port space eight thousand"
    },
    {
        "input": "git push hyphen u origin main",
        "output": "git space push space dash u space origin space main"
    },
    {
        "input": "npm install hyphen hyphen save dev eslint",
        "output": "npm space install space dash dash save dash dev space eslint"
    },
    # Casing: pass through verbatim, no spaces between words after the directive
    {
        "input": "snake case api response handler",
        "output": "snake case api response handler"
    },
    {
        "input": "camel case is authenticated",
        "output": "camel case is authenticated"
    },
    # Natural: filler around protocol content, strip filler and pass through protocol
    {
        "input": "okay so the command is git space push space dash u space origin space main",
        "output": "git space push space dash u space origin space main"
    },
    {
        "input": "can you type out docker space run space dash dash rm space nginx",
        "output": "docker space run space dash dash rm space nginx"
    },
    {
        "input": "I wanna set the variable name to camel case get user profile",
        "output": "camel case get user profile"
    },
    {
        "input": "the path should be slash usr slash local slash bin",
        "output": "slash usr slash local slash bin"
    },
    {
        "input": "um the flag is dash dash verbose",
        "output": "dash dash verbose"
    },
    {
        "input": "so for the environment variable it's all caps AWS underscore SECRET underscore ACCESS underscore KEY",
        "output": "all caps AWS underscore SECRET underscore ACCESS underscore KEY"
    },
    # Chaotic: self-corrections
    {
        "input": "dash dash no wait just dash v",
        "output": "dash v"
    },
    {
        "input": "run it on port three thousand",
        "output": "three thousand"
    },
    {
        "input": "wait no not dash dash force I meant dash dash force dash with dash lease",
        "output": "dash dash force dash with dash lease"
    },
    {
        "input": "so we need to... actually let's just do git stash",
        "output": "git space stash"
    },
]


def build_prompt(tokenizer, user_input):
    """Build the full prompt with system instructions, few-shot examples, and the user input."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for ex in FEW_SHOT:
        messages.append({"role": "user", "content": ex["input"]})
        messages.append({"role": "assistant", "content": ex["output"]})

    messages.append({"role": "user", "content": user_input})

    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )


def llm_normalize(model, tokenizer, raw_input, max_tokens=200):
    """Use the LLM to normalize raw dictation into protocol format."""
    prompt = build_prompt(tokenizer, raw_input)
    sampler = make_sampler(temp=0.0)
    output = generate(
        model, tokenizer, prompt=prompt,
        max_tokens=max_tokens, verbose=False,
        sampler=sampler,
    )
    # Clean up: strip whitespace, remove any wrapping quotes/backticks
    result = output.strip()
    result = result.strip('`').strip('"').strip("'")
    # Remove markdown code blocks if present
    result = re.sub(r'^```\w*\n?', '', result)
    result = re.sub(r'\n?```$', '', result)
    return result.strip()


def run_pipeline(model, tokenizer, raw_input):
    """Full pipeline: detect format → normalize if needed → processor."""
    t0 = time.perf_counter()

    if is_pure_protocol(raw_input):
        # Already in protocol format — strip filler procedurally, skip LLM
        protocol_text = strip_filler(raw_input)
        used_llm = False
    else:
        # Needs LLM normalization
        protocol_text = llm_normalize(model, tokenizer, raw_input)
        used_llm = True

    t_norm = time.perf_counter()
    final_output = process_dictation(protocol_text)
    t_proc = time.perf_counter()

    return {
        'protocol': protocol_text,
        'output': final_output,
        'used_llm': used_llm,
        'norm_ms': (t_norm - t0) * 1000,
        'proc_ms': (t_proc - t_norm) * 1000,
        'total_ms': (t_proc - t0) * 1000,
    }


def main():
    parser = argparse.ArgumentParser(description='Zero-training normalizer pipeline evaluation')
    parser.add_argument('eval_file', help='Path to evaluation JSON file')
    parser.add_argument('--model', default='mlx-community/Qwen2.5-1.5B-Instruct-4bit',
                        help='MLX model to use')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit number of entries to evaluate (0 = all)')
    parser.add_argument('--show-all', action='store_true',
                        help='Show all results, not just errors')
    parser.add_argument('--show-protocol', action='store_true',
                        help='Show normalized protocol output for each entry')
    args = parser.parse_args()

    # Load model
    print(f'Loading model: {args.model}')
    model, tokenizer = load(args.model)
    print(f'Model loaded.\n')

    # Load eval data
    data = json.load(open(args.eval_file))
    if args.limit:
        data = data[:args.limit]

    n = len(data)
    exact = ws = 0
    llm_calls = 0
    errors = []
    by_difficulty = defaultdict(list)
    latencies = []

    print(f'Evaluating {n} entries from {args.eval_file}')
    print(f'Pipeline: Protocol Detect → LLM ({args.model.split("/")[-1]}) / Filler Strip → Processor')
    print('=' * 70)

    for idx, d in enumerate(data):
        result = run_pipeline(model, tokenizer, d['dictated'])
        if result['used_llm']:
            llm_calls += 1

        expected = d['expected']
        got = result['output']

        ws_got = re.sub(r'\s+', ' ', got.strip())
        ws_exp = re.sub(r'\s+', ' ', expected.strip())
        is_exact = got == expected
        is_ws = ws_got == ws_exp

        if is_exact:
            exact += 1
        if is_ws:
            ws += 1

        diff = d.get('difficulty', 'unknown')
        by_difficulty[diff].append(is_exact)
        latencies.append(result['total_ms'])

        marker = '.' if is_exact else 'x'
        sys.stdout.write(marker)
        sys.stdout.flush()
        if (idx + 1) % 50 == 0:
            sys.stdout.write(f' [{idx+1}/{n}]\n')
            sys.stdout.flush()

        if args.show_all or (args.show_protocol and not is_exact):
            llm_tag = 'LLM' if result['used_llm'] else 'SKIP'
            print(f'\n  [{diff:>7}] [{d.get("category", "")}] {"PASS" if is_exact else "FAIL"} ({llm_tag})')
            print(f'    input:    {d["dictated"][:120]}')
            if args.show_protocol:
                print(f'    protocol: {result["protocol"][:120]}')
            print(f'    expected: {expected[:100]}')
            print(f'    got:      {got[:100]}')
            print(f'    latency:  {result["total_ms"]:.0f}ms')

        if not is_exact:
            errors.append({
                'dictated': d['dictated'][:120],
                'expected': expected[:100],
                'got': got[:100],
                'protocol': result['protocol'][:120],
                'category': d.get('category', ''),
                'difficulty': diff,
                'used_llm': result['used_llm'],
                'latency_ms': result['total_ms'],
            })

    # Ensure newline after progress dots
    if n % 50 != 0:
        print(f' [{n}/{n}]')
    print()

    # ── Results ──
    print(f'NORMALIZER PIPELINE — {args.eval_file}')
    print(f'Model: {args.model}')
    print('=' * 70)
    print(f'  Exact:   {exact}/{n} ({exact/n*100:.1f}%)')
    print(f'  WS-norm: {ws}/{n} ({ws/n*100:.1f}%)')
    print(f'  LLM calls: {llm_calls}/{n} ({llm_calls/n*100:.0f}% needed LLM)')
    print()

    if len(by_difficulty) > 1 or 'unknown' not in by_difficulty:
        print('BY DIFFICULTY:')
        for diff in ['clean', 'fuzzy', 'natural', 'chaotic', 'unknown']:
            if diff in by_difficulty:
                results = by_difficulty[diff]
                ex = sum(results)
                tot = len(results)
                print(f'  {diff:>10}: {ex}/{tot} ({ex/tot*100:.0f}%)')
        print()

    avg_lat = sum(latencies) / len(latencies) if latencies else 0
    p50 = sorted(latencies)[len(latencies) // 2] if latencies else 0
    p95 = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
    print(f'LATENCY:')
    print(f'  avg: {avg_lat:.0f}ms  p50: {p50:.0f}ms  p95: {p95:.0f}ms')
    print()

    print(f'ERRORS ({len(errors)}, showing first 25):')
    print('-' * 70)
    for e in errors[:25]:
        llm_tag = 'LLM' if e['used_llm'] else 'SKIP'
        print(f'  [{e["difficulty"]:>7}] [{e["category"]}] ({llm_tag})')
        print(f'    input:    {e["dictated"]}')
        print(f'    protocol: {e["protocol"]}')
        print(f'    expected: {e["expected"]}')
        print(f'    got:      {e["got"]}')
        print()


if __name__ == '__main__':
    main()
