#!/usr/bin/env python3
"""Validate normalizer task with a frontier model via API.

Tests whether the fuzzy→protocol task is solvable by a capable model,
to confirm the bottleneck is 1.5B model capacity, not task definition.

Usage:
  python3 datasets/validate-with-frontier.py fuzzy
  python3 datasets/validate-with-frontier.py fuzzy clean natural
  python3 datasets/validate-with-frontier.py fuzzy --provider openai --model gpt-4o-mini
"""

import json
import sys
import os
import time
import re
import argparse
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, 'datasets')
from importlib import import_module
proc = import_module('procedural-processor')
process_dictation = proc.process_dictation
np_mod = import_module('normalizer-pipeline')
replace_synonyms = np_mod.replace_synonyms
is_pure_protocol = np_mod.is_pure_protocol
strip_filler = np_mod.strip_filler

# Load keys from datasets/.env
def load_env():
    env_path = Path(__file__).parent / '.env'
    keys = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                keys[k.strip()] = v.strip()
    return keys

PROVIDERS = {
    'xai': {
        'url': 'https://api.x.ai/v1/chat/completions',
        'key_env': 'XAI_API_KEY',
        'default_model': 'grok-3-mini',
    },
    'openai': {
        'url': 'https://api.openai.com/v1/chat/completions',
        'key_env': 'OPENAI_API_KEY',
        'default_model': 'gpt-4o-mini',
    },
    'minimax': {
        'url': 'https://api.minimaxi.chat/v1/text/chatcompletion_v2',
        'key_env': 'MINIMAX_API_KEY',
        'default_model': 'MiniMax-Text-01',
    },
}

SYSTEM_PROMPT = """You normalize voice dictation into clean protocol format for a processor.

YOUR JOB:
1. Insert the word "space" between each separate argument/token
   "git commit dash m" → "git space commit space dash m"
2. Do NOT insert "space" within compound tokens:
   - Paths: slash usr slash local (slashes join path segments)
   - Dotted names: file dot txt (dots join filename parts)
   - Flags after dash: dash l a (letters concatenate after dash)
   - Compound flags: dash dash verbose (dash dash stays with the flag word)
3. Strip conversational filler (okay, so, um, can you type, I want to run, etc.)
4. Resolve self-corrections (no wait, actually, I meant) → keep only the FINAL intent
5. Casing directives (camel case, snake case, pascal case, kebab case) → pass through verbatim
6. Do NOT invent content not present in the input

PROTOCOL KEYWORDS (these are special — they map to symbols):
Separator: space
Symbols: dash dot slash pipe star bang hash tilde at dollar percent caret ampersand equals plus colon semicolon underscore comma backslash quote backtick redirect append
Multi-word: dash dash, single quote, open/close paren, open/close brace, open/close bracket, less than, question mark, and and, pipe pipe, dot dot, new line
Capitalization: capital (next word), all caps (next word)
Numbers: zero through nineteen, twenty/thirty/.../ninety, hundred, thousand

Output ONLY the normalized protocol text. Nothing else."""

FEW_SHOT = [
    {"input": "git commit dash m quote fix login bug quote",
     "output": "git space commit space dash m space quote fix space login space bug quote"},
    {"input": "docker run dash dash rm dash it ubuntu",
     "output": "docker space run space dash dash rm space dash it space ubuntu"},
    {"input": "tar dash xzf backup dot tar dot gz",
     "output": "tar space dash xzf space backup dot tar dot gz"},
    {"input": "cat file dot txt",
     "output": "cat space file dot txt"},
    {"input": "ls dash l dash a slash var slash log",
     "output": "ls space dash l space dash a space slash var slash log"},
    {"input": "cd slash usr slash local slash bin",
     "output": "cd space slash usr slash local slash bin"},
    {"input": "find dot dash name star dot py dash type f",
     "output": "find space dot space dash name space star dot py space dash type space f"},
    {"input": "ssh dash i tilde slash dot ssh slash key dot pem user at server",
     "output": "ssh space dash i space tilde slash dot ssh slash key dot pem space user at server"},
    {"input": "snake case api response handler",
     "output": "snake case api response handler"},
]


def api_call(api_url, api_key, model, user_input):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for ex in FEW_SHOT:
        messages.append({"role": "user", "content": ex["input"]})
        messages.append({"role": "assistant", "content": ex["output"]})
    messages.append({"role": "user", "content": user_input})

    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 300,
    }).encode()

    req = urllib.request.Request(
        api_url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    content = data["choices"][0]["message"]["content"].strip()
    content = content.strip('`').strip('"').strip("'")
    content = re.sub(r'^```\w*\n?', '', content)
    content = re.sub(r'\n?```$', '', content)
    return content.strip()


def main():
    parser = argparse.ArgumentParser(description='Validate normalizer with frontier model')
    parser.add_argument('tiers', nargs='*', default=['fuzzy'],
                        help='Difficulty tiers to test (default: fuzzy)')
    parser.add_argument('--provider', default='xai', choices=PROVIDERS.keys())
    parser.add_argument('--model', default=None, help='Model name (default: provider default)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests (seconds)')
    args = parser.parse_args()

    env = load_env()
    provider = PROVIDERS[args.provider]
    api_key = env.get(provider['key_env']) or os.environ.get(provider['key_env'])
    if not api_key:
        print(f"ERROR: {provider['key_env']} not found in datasets/.env or environment")
        sys.exit(1)

    model = args.model or provider['default_model']
    api_url = provider['url']

    # Quick test
    print(f"Testing API ({args.provider}/{model})...")
    try:
        test = api_call(api_url, api_key, model, "cat file dot txt")
        print(f'  "cat file dot txt" → "{test}"')
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)
    print()

    data = json.load(open('datasets/eval-fuzzy.json'))
    entries = [d for d in data if d.get('difficulty') in args.tiers]

    print(f"Validating {len(entries)} entries (tiers: {', '.join(args.tiers)})")
    print(f"Model: {model} via {args.provider}")
    print("=" * 70)

    exact = 0
    errors = []
    by_diff = defaultdict(list)

    for idx, d in enumerate(entries):
        raw = d['dictated']

        if is_pure_protocol(raw):
            protocol_text = strip_filler(raw)
        else:
            cleaned = replace_synonyms(raw)
            try:
                protocol_text = api_call(api_url, api_key, model, cleaned)
            except Exception as e:
                protocol_text = f"ERROR: {e}"

        got = process_dictation(protocol_text)
        expected = d['expected']
        is_exact = got == expected
        diff = d.get('difficulty', 'unknown')
        by_diff[diff].append(is_exact)

        if is_exact:
            exact += 1
            sys.stdout.write('.')
        else:
            sys.stdout.write('x')
            errors.append({
                'dictated': raw[:120],
                'cleaned': replace_synonyms(raw)[:120] if not is_pure_protocol(raw) else '(skip)',
                'protocol': protocol_text[:150],
                'expected': expected[:100],
                'got': got[:100],
                'difficulty': diff,
                'category': d.get('category', ''),
            })
        sys.stdout.flush()

        if (idx + 1) % 50 == 0:
            sys.stdout.write(f' [{idx+1}/{len(entries)}]\n')
            sys.stdout.flush()

        time.sleep(args.delay)

    print(f' [{len(entries)}/{len(entries)}]')
    print()

    n = len(entries)
    print(f"FRONTIER VALIDATION ({args.provider}/{model})")
    print("=" * 70)
    print(f"  Exact: {exact}/{n} ({exact/n*100:.1f}%)")
    print()

    if len(by_diff) > 1:
        print("BY DIFFICULTY:")
        for diff in ['clean', 'fuzzy', 'natural', 'chaotic']:
            if diff in by_diff:
                results = by_diff[diff]
                ex = sum(results)
                tot = len(results)
                print(f"  {diff:>10}: {ex}/{tot} ({ex/tot*100:.0f}%)")
        print()

    print(f"ERRORS ({len(errors)}):")
    print("-" * 70)
    for e in errors:
        print(f'  [{e["difficulty"]:>7}] [{e["category"]}]')
        print(f'    input:    {e["dictated"]}')
        if e['cleaned'] != '(skip)':
            print(f'    cleaned:  {e["cleaned"]}')
        print(f'    protocol: {e["protocol"]}')
        print(f'    expected: {e["expected"]}')
        print(f'    got:      {e["got"]}')
        print()


if __name__ == '__main__':
    main()
