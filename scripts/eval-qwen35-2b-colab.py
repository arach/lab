#!/usr/bin/env python3
"""
Evaluate Qwen3.5-2B fine-tuned adapter on full test set.
Adapter: arach/qwen35-2b-bash-v1 (PEFT/LoRA on unsloth/Qwen3.5-2B)
Test data: arach/training-lab (training/data/bash-v3/minimal/test.jsonl)
"""

import json
import re
import time
from difflib import SequenceMatcher
from huggingface_hub import hf_hub_download
from unsloth import FastLanguageModel

# --- Load test data ---
test_path = hf_hub_download(
    "arach/training-lab",
    "training/data/bash-v3/minimal/test.jsonl",
)

tests = []
with open(test_path) as f:
    for line in f:
        msg = json.loads(line)["messages"]
        tests.append({
            "system": msg[0]["content"],
            "dictated": msg[1]["content"],
            "expected": msg[2]["content"],
        })

print(f"Loaded {len(tests)} test cases\n")

# --- Load model + adapter ---
print("Loading model + adapter...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="arach/qwen35-2b-bash-v1",
    max_seq_length=256,
    load_in_4bit=True,
)
FastLanguageModel.for_inference(model)

# Qwen3.5 tokenizer is a VL Processor — bypass to inner text tokenizer
text_tok = tokenizer.tokenizer if hasattr(tokenizer, "tokenizer") else tokenizer
print("Model loaded.\n")


def similarity(a, b):
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    return SequenceMatcher(None, a, b).ratio()


# --- Run eval ---
results = []
total_time = 0
errors = []
SYSTEM = tests[0]["system"]

for i, t in enumerate(tests):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": t["dictated"]},
    ]

    prompt = text_tok.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )

    inputs = text_tok(prompt, return_tensors="pt").to(model.device)

    start = time.perf_counter()
    outputs = model.generate(
        **inputs,
        max_new_tokens=120,
        do_sample=False,
        temperature=1.0,
        top_p=1.0,
    )
    elapsed = time.perf_counter() - start
    total_time += elapsed

    generated = outputs[0][inputs["input_ids"].shape[1]:]
    got = text_tok.decode(generated, skip_special_tokens=True).strip()
    got = re.sub(r"<think>.*?</think>", "", got, flags=re.DOTALL).strip()

    sim = similarity(got, t["expected"])
    exact = got == t["expected"]

    if exact:
        category = "exact"
    elif sim > 0.9:
        category = "near"
    elif sim > 0.7:
        category = "partial"
    else:
        category = "wrong"

    results.append({
        "exact": exact,
        "similarity": sim,
        "category": category,
        "got": got,
        "expected": t["expected"],
        "dictated": t["dictated"],
        "time": elapsed,
    })

    if not exact:
        errors.append((i, t, got, sim))

    if (i + 1) % 50 == 0:
        exact_so_far = sum(1 for r in results if r["exact"])
        print(f"  [{i+1}/{len(tests)}] exact: {exact_so_far}/{i+1} ({exact_so_far/(i+1)*100:.1f}%)")

# --- Results ---
total = len(results)
exact_count = sum(1 for r in results if r["category"] == "exact")
near_count = sum(1 for r in results if r["category"] == "near")
partial_count = sum(1 for r in results if r["category"] == "partial")
wrong_count = sum(1 for r in results if r["category"] == "wrong")
effective = exact_count + near_count

print(f"\n{'='*60}")
print(f"  QWEN3.5-2B EVALUATION — {total} cases")
print(f"{'='*60}\n")
print(f"  Exact match:        {exact_count}/{total} ({exact_count/total*100:.1f}%)")
print(f"  Near (>90% sim):    {near_count}/{total} ({near_count/total*100:.1f}%)")
print(f"  Partial (70-90%):   {partial_count}/{total} ({partial_count/total*100:.1f}%)")
print(f"  Wrong (<70%):       {wrong_count}/{total} ({wrong_count/total*100:.1f}%)")
print(f"  Effective accuracy: {effective}/{total} ({effective/total*100:.1f}%)")
print(f"  Avg latency:        {total_time/total*1000:.0f}ms")
print(f"  Total time:         {total_time:.1f}s")

print(f"\n  WORST ERRORS (by similarity):")
print(f"  {'-'*56}")
worst = sorted(errors, key=lambda x: x[3])[:20]
for i, t, got, sim in worst:
    print(f"  [{sim:.0%}] \"{t['dictated'][:50]}\"")
    print(f"       expected: {t['expected'][:60]}")
    print(f"       got:      {got[:60]}")
    print()
