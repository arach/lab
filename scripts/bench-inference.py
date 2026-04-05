#!/usr/bin/env python3
"""Benchmark inference latency for LoRA vs DoRA vs base model."""

import time
from mlx_lm import load, generate

SYS = "Convert the dictated text into the exact syntax it represents. Output only the result."

# A few representative samples at different lengths
samples = [
    {"label": "short", "input": "dash dash verbose", "expected": "--verbose"},
    {"label": "medium", "input": "export all caps API underscore KEY equals quote my dash key dash one two three quote", "expected": 'export API_KEY="my-key-123"'},
    {"label": "long", "input": "git add dash A and and git commit dash M quote fix typo quote and and git push", "expected": 'git add -A && git commit -m "fix typo" && git push'},
]

configs = [
    {"label": "Qwen 0.5B (base)", "model": "mlx-community/Qwen2.5-0.5B-Instruct-4bit", "adapter": None},
    {"label": "Qwen 0.5B + LoRA", "model": "mlx-community/Qwen2.5-0.5B-Instruct-4bit", "adapter": "/Users/arach/dev/talkie/datasets/finetune/adapters/qwen-0.5b-lora"},
    {"label": "Qwen 0.5B + DoRA", "model": "mlx-community/Qwen2.5-0.5B-Instruct-4bit", "adapter": "/Users/arach/dev/talkie/datasets/finetune/adapters/qwen-0.5b-dora"},
]

WARMUP = 2
RUNS = 10

for cfg in configs:
    print(f"\n{'='*60}")
    print(f"  {cfg['label']}")
    print(f"{'='*60}")

    kwargs = {"adapter_path": cfg["adapter"]} if cfg["adapter"] else {}
    model, tokenizer = load(cfg["model"], **kwargs)

    for sample in samples:
        messages = [
            {"role": "system", "content": SYS},
            {"role": "user", "content": sample["input"]},
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

        # Warmup
        for _ in range(WARMUP):
            generate(model, tokenizer, prompt=prompt, max_tokens=60, verbose=False)

        # Timed runs
        times = []
        outputs = []
        for _ in range(RUNS):
            t0 = time.perf_counter()
            out = generate(model, tokenizer, prompt=prompt, max_tokens=60, verbose=False)
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)  # ms
            outputs.append(out.strip())

        avg = sum(times) / len(times)
        mn = min(times)
        mx = max(times)
        last_out = outputs[-1]
        match = "✓" if last_out == sample["expected"] else "✗"

        print(f"\n  [{sample['label']}] \"{sample['input'][:50]}{'...' if len(sample['input'])>50 else ''}\"")
        print(f"    avg: {avg:.1f}ms  min: {mn:.1f}ms  max: {mx:.1f}ms  ({RUNS} runs)")
        print(f"    output: {last_out}  {match}")

    del model, tokenizer

print(f"\n{'='*60}")
print("  Done")
print(f"{'='*60}")
