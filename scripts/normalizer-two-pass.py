#!/usr/bin/env python3
"""Two-pass normalizer experiments.

Technique A: LLM → LLM (rough normalize → refine spacing)
Technique B: Procedural → LLM → Procedural (sandwich)

Usage:
  python3 datasets/normalizer-two-pass.py datasets/eval-fuzzy.json --technique A
  python3 datasets/normalizer-two-pass.py datasets/eval-fuzzy.json --technique B
"""

import json
import sys
import time
import re
import argparse
from collections import defaultdict

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

sys.path.insert(0, 'datasets')
from importlib import import_module
proc = import_module('procedural-processor')
process_dictation = proc.process_dictation
np = import_module('normalizer-pipeline')
replace_synonyms = np.replace_synonyms
strip_filler = np.strip_filler
is_pure_protocol = np.is_pure_protocol

# ── Technique A: LLM → LLM ─────────────────────────────────────────────

PROMPT_A_PASS1 = """You normalize voice dictation into clean protocol format.

Replace synonyms: minus→dash, hyphen→dash, period→dot, forward slash→slash, asterisk→star, hashtag→hash, double dash→dash dash, at sign→at, equals sign→equals.
Insert "space" between separate arguments.
Do NOT insert "space" within paths (slash-separated), dotted names (file dot txt), or compound flags (dash dash verbose).
Strip conversational filler.
Resolve self-corrections (keep only the final intent).
Pass casing directives (camel case, snake case, etc.) through verbatim.

Output ONLY the normalized protocol text."""

FEWSHOT_A_PASS1 = [
    {"input": "git commit minus m quote fix login bug quote",
     "output": "git space commit space dash m space quote fix space login space bug quote"},
    {"input": "docker run minus minus rm minus it ubuntu",
     "output": "docker space run space dash dash rm space dash it space ubuntu"},
    {"input": "ls minus l minus a slash var slash log",
     "output": "ls space dash l space dash a space slash var slash log"},
    {"input": "okay so the command is git space push space dash u space origin space main",
     "output": "git space push space dash u space origin space main"},
    {"input": "dash dash no wait just dash v",
     "output": "dash v"},
    {"input": "snake case api response handler",
     "output": "snake case api response handler"},
]

PROMPT_A_PASS2 = """Fix the spacing in this protocol text. The word "space" must appear between every separate argument.

RULES:
- Every command, flag, path, and value must be separated by "space"
- Do NOT add "space" within: paths (slash-separated), dotted names (file dot txt), flags after dash (dash l a), compound flags (dash dash verbose)
- Do NOT change any words — only add or remove "space" keywords
- If the input looks correct, output it unchanged

Output ONLY the fixed protocol text."""

FEWSHOT_A_PASS2 = [
    # Missing spaces at start
    {"input": "gitcommit space dash m space quote fix space login space bug quote",
     "output": "git space commit space dash m space quote fix space login space bug quote"},
    # Missing space between command and first arg
    {"input": "docker space run space dash dash rm space dashit space ubuntu",
     "output": "docker space run space dash dash rm space dash it space ubuntu"},
    # Already correct — pass through
    {"input": "ls space dash l space dash a space slash var slash log",
     "output": "ls space dash l space dash a space slash var slash log"},
    # Missing spaces throughout
    {"input": "kubectl get pods space dash n space default space dash dash output space json",
     "output": "kubectl space get space pods space dash n space default space dash dash output space json"},
    # Missing space before path
    {"input": "cat file dot txt",
     "output": "cat space file dot txt"},
    # Extra space in compound token
    {"input": "find space dot space dash name space star space dot py space dash type space f",
     "output": "find space dot space dash name space star dot py space dash type space f"},
]

# ── Technique B: Procedural → LLM → Procedural ─────────────────────────

PROMPT_B = """Insert the word "space" between each separate argument in this command dictation.

RULES:
- Every argument boundary gets "space": "git commit dash m" → "git space commit space dash m"
- Do NOT insert "space" within compound tokens:
  - Paths: slash usr slash local (slashes join)
  - Dotted names: file dot txt (dots join)
  - Flags: dash l a (letters after dash join)
  - Long flags: dash dash verbose (dash dash joins with the word)
- Casing directives (camel case, snake case, etc.) → pass through with their arguments
- Do NOT add or remove any words other than "space"

PROTOCOL KEYWORDS (these represent symbols):
dash dot slash pipe star bang hash tilde at dollar percent caret ampersand equals plus colon semicolon underscore comma backslash quote backtick redirect append
dash dash, single quote, open/close paren/brace/bracket, less than, question mark, and and, pipe pipe
capital, all caps, camel case, snake case, pascal case, kebab case

Output ONLY the text with "space" inserted at argument boundaries."""

FEWSHOT_B = [
    {"input": "git commit dash m quote fix login bug quote",
     "output": "git space commit space dash m space quote fix space login space bug quote"},
    {"input": "docker run dash dash rm dash it ubuntu",
     "output": "docker space run space dash dash rm space dash it space ubuntu"},
    {"input": "kubectl get pods dash n default dash dash output json",
     "output": "kubectl space get space pods space dash n space default space dash dash output space json"},
    {"input": "find dot dash name star dot py dash type f",
     "output": "find space dot space dash name space star dot py space dash type space f"},
    {"input": "cat file dot txt",
     "output": "cat space file dot txt"},
    {"input": "ls dash l dash a slash var slash log",
     "output": "ls space dash l space dash a space slash var slash log"},
    {"input": "tar dash xzf backup dot tar dot gz",
     "output": "tar space dash xzf space backup dot tar dot gz"},
    {"input": "chmod seven five five script dot sh",
     "output": "chmod space seven five five space script dot sh"},
    {"input": "ssh dash i tilde slash dot ssh slash key dot pem user at server",
     "output": "ssh space dash i space tilde slash dot ssh slash key dot pem space user at server"},
    {"input": "snake case api response handler",
     "output": "snake case api response handler"},
    {"input": "kebab case my awesome component",
     "output": "kebab case my awesome component"},
]


# Procedural post-fix: catch common spacing errors
def procedural_postfix(text):
    """Fix common spacing errors in protocol output."""
    words = text.split()
    result = []
    i = 0
    n = len(words)

    while i < n:
        w = words[i]

        # Fix merged words: if a word contains a protocol keyword fused with
        # other text, try to split it (e.g., "gitcommit" → can't fix,
        # but "dashit" → "dash it" if we detect the pattern)

        # Ensure "space" exists between standalone words that aren't
        # part of compound tokens
        result.append(w)
        i += 1

    # Simple fix: if output has no "space" keywords but has multiple words,
    # it's likely missing spaces entirely. Insert them.
    if 'space' not in words and len(words) > 1:
        # Check if this looks like it should have spaces
        # (has protocol keywords mixed with regular words)
        protocol_words = {
            'dash', 'dot', 'slash', 'pipe', 'star', 'bang', 'hash',
            'tilde', 'at', 'dollar', 'percent', 'caret', 'ampersand',
            'equals', 'plus', 'colon', 'semicolon', 'underscore',
            'comma', 'backslash', 'quote', 'backtick', 'redirect',
            'append', 'capital', 'all',
        }
        has_protocol = any(w in protocol_words for w in words)
        if has_protocol:
            # Try to insert spaces at argument boundaries
            # Simple heuristic: space before each dash/flag
            fixed = []
            for j, w in enumerate(words):
                if j > 0 and w == 'dash' and (j == 0 or words[j-1] != 'dash'):
                    fixed.append('space')
                fixed.append(w)
            return ' '.join(fixed)

    return text


# ── Shared inference ────────────────────────────────────────────────────

def llm_call(model, tokenizer, system_prompt, few_shot, user_input, max_tokens=200):
    """Single LLM call with system prompt, few-shot, and user input."""
    messages = [{"role": "system", "content": system_prompt}]
    for ex in few_shot:
        messages.append({"role": "user", "content": ex["input"]})
        messages.append({"role": "assistant", "content": ex["output"]})
    messages.append({"role": "user", "content": user_input})

    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    sampler = make_sampler(temp=0.0)
    output = generate(
        model, tokenizer, prompt=prompt,
        max_tokens=max_tokens, verbose=False,
        sampler=sampler,
    )
    result = output.strip()
    result = result.strip('`').strip('"').strip("'")
    result = re.sub(r'^```\w*\n?', '', result)
    result = re.sub(r'\n?```$', '', result)
    return result.strip()


def run_technique_a(model, tokenizer, raw_input):
    """Technique A: LLM rough → LLM refine."""
    t0 = time.perf_counter()

    if is_pure_protocol(raw_input):
        protocol_text = strip_filler(raw_input)
        llm_calls = 0
    else:
        # Pass 1: rough normalization
        rough = llm_call(model, tokenizer, PROMPT_A_PASS1, FEWSHOT_A_PASS1, raw_input)
        # Pass 2: refine spacing
        protocol_text = llm_call(model, tokenizer, PROMPT_A_PASS2, FEWSHOT_A_PASS2, rough)
        llm_calls = 2

    t_norm = time.perf_counter()
    final_output = process_dictation(protocol_text)
    t_proc = time.perf_counter()

    return {
        'protocol': protocol_text,
        'output': final_output,
        'llm_calls': llm_calls,
        'total_ms': (t_proc - t0) * 1000,
    }


def run_technique_b(model, tokenizer, raw_input):
    """Technique B: Procedural → LLM → Procedural."""
    t0 = time.perf_counter()

    if is_pure_protocol(raw_input):
        protocol_text = strip_filler(raw_input)
        llm_calls = 0
    else:
        # Step 1: procedural pre-processing
        cleaned = replace_synonyms(raw_input)
        cleaned = strip_filler(cleaned)

        # Step 2: LLM space insertion
        rough = llm_call(model, tokenizer, PROMPT_B, FEWSHOT_B, cleaned)

        # Step 3: procedural post-fix
        protocol_text = procedural_postfix(rough)
        llm_calls = 1

    t_norm = time.perf_counter()
    final_output = process_dictation(protocol_text)
    t_proc = time.perf_counter()

    return {
        'protocol': protocol_text,
        'output': final_output,
        'llm_calls': llm_calls,
        'total_ms': (t_proc - t0) * 1000,
    }


def main():
    parser = argparse.ArgumentParser(description='Two-pass normalizer experiments')
    parser.add_argument('eval_file', help='Path to evaluation JSON')
    parser.add_argument('--technique', choices=['A', 'B'], required=True,
                        help='A=LLM→LLM, B=Procedural→LLM→Procedural')
    parser.add_argument('--model', default='mlx-community/Qwen2.5-1.5B-Instruct-4bit')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    run_fn = run_technique_a if args.technique == 'A' else run_technique_b
    label = 'A (LLM→LLM)' if args.technique == 'A' else 'B (Proc→LLM→Proc)'

    print(f'Loading model: {args.model}')
    model, tokenizer = load(args.model)
    print(f'Model loaded.\n')

    data = json.load(open(args.eval_file))
    if args.limit:
        data = data[:args.limit]

    n = len(data)
    exact = 0
    total_llm_calls = 0
    by_difficulty = defaultdict(list)
    latencies = []
    errors = []

    print(f'Technique {label}')
    print(f'Evaluating {n} entries from {args.eval_file}')
    print('=' * 70)

    for idx, d in enumerate(data):
        result = run_fn(model, tokenizer, d['dictated'])
        total_llm_calls += result['llm_calls']

        expected = d['expected']
        got = result['output']
        is_exact = got == expected

        if is_exact:
            exact += 1

        diff = d.get('difficulty', 'unknown')
        by_difficulty[diff].append(is_exact)
        latencies.append(result['total_ms'])

        marker = '.' if is_exact else 'x'
        sys.stdout.write(marker)
        sys.stdout.flush()
        if (idx + 1) % 50 == 0:
            sys.stdout.write(f' [{idx+1}/{n}]\n')
            sys.stdout.flush()

        if not is_exact:
            errors.append({
                'dictated': d['dictated'][:120],
                'expected': expected[:80],
                'got': got[:80],
                'protocol': result['protocol'][:120],
                'difficulty': diff,
                'category': d.get('category', ''),
            })

    if n % 50 != 0:
        print(f' [{n}/{n}]')
    print()

    # Results
    print(f'TECHNIQUE {label} — {args.eval_file}')
    print(f'Model: {args.model}')
    print('=' * 70)
    print(f'  Exact:     {exact}/{n} ({exact/n*100:.1f}%)')
    print(f'  LLM calls: {total_llm_calls} ({total_llm_calls/n:.1f} per entry)')
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

    if latencies:
        avg = sum(latencies) / len(latencies)
        p50 = sorted(latencies)[len(latencies) // 2]
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f'LATENCY:')
        print(f'  avg: {avg:.0f}ms  p50: {p50:.0f}ms  p95: {p95:.0f}ms')
        print()

    print(f'ERRORS ({len(errors)}, showing first 20):')
    print('-' * 70)
    for e in errors[:20]:
        print(f'  [{e["difficulty"]:>7}] [{e["category"]}]')
        print(f'    input:    {e["dictated"]}')
        print(f'    protocol: {e["protocol"]}')
        print(f'    expected: {e["expected"]}')
        print(f'    got:      {e["got"]}')
        print()


if __name__ == '__main__':
    main()
