#!/usr/bin/env python3
"""Evaluate a fine-tuned normalizer model.

Dual metrics:
  - Protocol accuracy: normalizer output vs expected protocol (isolates normalizer errors)
  - End-to-end accuracy: final bash vs expected bash (what the user sees)

Reports by difficulty tier (clean/fuzzy/natural/chaotic).

Usage:
  # Evaluate fine-tuned normalizer
  python3 datasets/eval-normalizer.py datasets/eval-normalizer.json \
    --model mlx-community/Qwen2.5-1.5B-Instruct-4bit \
    --adapter datasets/finetune/adapters/qwen-1.5b-normalizer-v1

  # Compare to zero-training baseline (no adapter)
  python3 datasets/eval-normalizer.py datasets/eval-normalizer.json \
    --model mlx-community/Qwen2.5-1.5B-Instruct-4bit
"""

import json
import sys
import time
import re
import argparse
from collections import defaultdict

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

# Import the procedural processor
sys.path.insert(0, 'datasets')
from importlib import import_module
proc = import_module('procedural-processor')
process_dictation = proc.process_dictation

# ── System prompts ──────────────────────────────────────────────────────

# Full prompt for zero-training baseline (same as normalizer-pipeline.py)
SYSTEM_PROMPT_ZERO = """You normalize voice dictation into clean protocol format for a processor.

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

# Simple prompt for fine-tuned model (rules are internalized)
SYSTEM_PROMPT_FINETUNED = (
    "Normalize dictated input into clean protocol format. "
    "Output only the clean protocol text."
)

# Few-shot examples for zero-training mode
FEW_SHOT = [
    {
        "input": "git commit minus m quote fix login bug quote",
        "output": "git space commit space dash m space quote fix space login space bug quote"
    },
    {
        "input": "ls minus l minus a slash var slash log",
        "output": "ls space dash l space dash a space slash var slash log"
    },
    {
        "input": "okay so the command is git space push space dash u space origin space main",
        "output": "git space push space dash u space origin space main"
    },
    {
        "input": "dash dash no wait just dash v",
        "output": "dash v"
    },
]


def build_prompt(tokenizer, user_input, use_fewshot=False):
    """Build prompt for the normalizer."""
    system = SYSTEM_PROMPT_ZERO if use_fewshot else SYSTEM_PROMPT_FINETUNED
    messages = [{"role": "system", "content": system}]

    if use_fewshot:
        for ex in FEW_SHOT:
            messages.append({"role": "user", "content": ex["input"]})
            messages.append({"role": "assistant", "content": ex["output"]})

    messages.append({"role": "user", "content": user_input})

    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )


def normalize(model, tokenizer, raw_input, use_fewshot=False, max_tokens=200):
    """Run the normalizer on a single input."""
    prompt = build_prompt(tokenizer, raw_input, use_fewshot=use_fewshot)
    sampler = make_sampler(temp=0.0)
    output = generate(
        model, tokenizer, prompt=prompt,
        max_tokens=max_tokens, verbose=False,
        sampler=sampler,
    )
    # Clean up
    result = output.strip()
    result = result.strip('`').strip('"').strip("'")
    result = re.sub(r'^```\w*\n?', '', result)
    result = re.sub(r'\n?```$', '', result)
    return result.strip()


def main():
    parser = argparse.ArgumentParser(description='Evaluate fine-tuned normalizer')
    parser.add_argument('eval_file', help='Path to normalizer eval JSON (eval-normalizer.json)')
    parser.add_argument('--model', default='mlx-community/Qwen2.5-1.5B-Instruct-4bit',
                        help='MLX model to use')
    parser.add_argument('--adapter', default=None,
                        help='Path to LoRA adapter (omit for zero-training baseline)')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit number of entries (0 = all)')
    parser.add_argument('--show-errors', action='store_true',
                        help='Show detailed error output')
    args = parser.parse_args()

    # Load model
    print(f'Loading model: {args.model}')
    if args.adapter:
        print(f'Loading adapter: {args.adapter}')
        model, tokenizer = load(args.model, adapter_path=args.adapter)
    else:
        print('No adapter — zero-training baseline mode')
        model, tokenizer = load(args.model)
    print('Model loaded.\n')

    # Determine mode
    use_fewshot = args.adapter is None  # Few-shot only for zero-training

    # Load eval data
    data = json.load(open(args.eval_file))
    if args.limit:
        data = data[:args.limit]

    n = len(data)
    protocol_exact = 0
    e2e_exact = 0
    e2e_ws = 0
    by_difficulty = defaultdict(lambda: {'protocol': [], 'e2e': [], 'e2e_ws': []})
    latencies = []
    errors = []

    print(f'Evaluating {n} entries from {args.eval_file}')
    mode = 'fine-tuned' if args.adapter else 'zero-training'
    print(f'Mode: {mode}')
    print('=' * 70)

    for idx, entry in enumerate(data):
        raw_input = entry['dictated']
        expected_protocol = entry['expected_protocol']
        expected_bash = entry['expected_bash']
        difficulty = entry.get('difficulty', 'unknown')

        t0 = time.perf_counter()
        normalized = normalize(model, tokenizer, raw_input, use_fewshot=use_fewshot)
        t1 = time.perf_counter()

        # Protocol accuracy
        is_proto = normalized == expected_protocol
        if is_proto:
            protocol_exact += 1

        # End-to-end: run through procedural processor
        final_bash = process_dictation(normalized)
        is_e2e = final_bash == expected_bash
        ws_bash = re.sub(r'\s+', ' ', final_bash.strip())
        ws_expected = re.sub(r'\s+', ' ', expected_bash.strip())
        is_e2e_ws = ws_bash == ws_expected

        if is_e2e:
            e2e_exact += 1
        if is_e2e_ws:
            e2e_ws += 1

        by_difficulty[difficulty]['protocol'].append(is_proto)
        by_difficulty[difficulty]['e2e'].append(is_e2e)
        by_difficulty[difficulty]['e2e_ws'].append(is_e2e_ws)

        latency = (t1 - t0) * 1000
        latencies.append(latency)

        marker = '.' if is_e2e else 'x'
        sys.stdout.write(marker)
        sys.stdout.flush()
        if (idx + 1) % 50 == 0:
            sys.stdout.write(f' [{idx+1}/{n}]\n')
            sys.stdout.flush()

        if not is_e2e:
            errors.append({
                'dictated': raw_input[:120],
                'expected_proto': expected_protocol[:100],
                'got_proto': normalized[:100],
                'expected_bash': expected_bash[:80],
                'got_bash': final_bash[:80],
                'difficulty': difficulty,
                'category': entry.get('category', ''),
                'latency_ms': latency,
            })

    # Ensure newline after progress dots
    if n % 50 != 0:
        print(f' [{n}/{n}]')
    print()

    # ── Results ──
    print(f'NORMALIZER EVALUATION — {args.eval_file}')
    print(f'Model: {args.model}')
    if args.adapter:
        print(f'Adapter: {args.adapter}')
    else:
        print(f'Mode: zero-training baseline (few-shot)')
    print('=' * 70)

    print(f'  Protocol exact: {protocol_exact}/{n} ({protocol_exact/n*100:.1f}%)')
    print(f'  E2E exact:      {e2e_exact}/{n} ({e2e_exact/n*100:.1f}%)')
    print(f'  E2E WS-norm:    {e2e_ws}/{n} ({e2e_ws/n*100:.1f}%)')
    print()

    # By difficulty
    if len(by_difficulty) > 1 or 'unknown' not in by_difficulty:
        print('BY DIFFICULTY:')
        print(f'  {"":>10}  {"Protocol":>12}  {"E2E":>12}  {"E2E WS":>12}')
        for diff in ['clean', 'fuzzy', 'natural', 'chaotic', 'unknown']:
            if diff in by_difficulty:
                d = by_difficulty[diff]
                tot = len(d['protocol'])
                pe = sum(d['protocol'])
                ee = sum(d['e2e'])
                ew = sum(d['e2e_ws'])
                print(f'  {diff:>10}: {pe:>3}/{tot} ({pe/tot*100:>4.0f}%)  '
                      f'{ee:>3}/{tot} ({ee/tot*100:>4.0f}%)  '
                      f'{ew:>3}/{tot} ({ew/tot*100:>4.0f}%)')
        print()

    # Latency
    if latencies:
        avg = sum(latencies) / len(latencies)
        p50 = sorted(latencies)[len(latencies) // 2]
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f'LATENCY:')
        print(f'  avg: {avg:.0f}ms  p50: {p50:.0f}ms  p95: {p95:.0f}ms')
        print()

    # Errors
    print(f'ERRORS ({len(errors)}, showing first 20):')
    print('-' * 70)
    for e in errors[:20]:
        print(f'  [{e["difficulty"]:>7}] [{e["category"]}]')
        print(f'    input:      {e["dictated"]}')
        print(f'    exp_proto:  {e["expected_proto"]}')
        print(f'    got_proto:  {e["got_proto"]}')
        print(f'    exp_bash:   {e["expected_bash"]}')
        print(f'    got_bash:   {e["got_bash"]}')
        print()


if __name__ == '__main__':
    main()
