#!/usr/bin/env python3
"""Evaluate Qwen3.5-2B fine-tuned adapter on full test set using MPS (Apple Silicon)."""

import json
import re
import time
import sys
from difflib import SequenceMatcher

import torch
from transformers import AutoTokenizer, AutoModelForImageTextToText
from peft import PeftModel
from huggingface_hub import hf_hub_download

# --- Load test data ---
test_path = hf_hub_download("arach/training-lab", "training/data/bash-v3/minimal/test.jsonl")
tests = []
with open(test_path) as f:
    for line in f:
        msg = json.loads(line)["messages"]
        tests.append({
            "system": msg[0]["content"],
            "dictated": msg[1]["content"],
            "expected": msg[2]["content"],
        })
print(f"Loaded {len(tests)} test cases")

# --- Load model + adapter ---
print("Loading base model (Qwen3.5-2B VLM)...")
base_model = AutoModelForImageTextToText.from_pretrained(
    "unsloth/Qwen3.5-2B",
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
)
print("Loading LoRA adapter...")
model = PeftModel.from_pretrained(base_model, "arach/qwen35-2b-bash-v1")
model.eval()

# Use text tokenizer (not VL Processor) to avoid image parsing
tokenizer = AutoTokenizer.from_pretrained("unsloth/Qwen3.5-2B", trust_remote_code=True)
print(f"Model loaded. Device: {model.device}")


def similarity(a, b):
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    return SequenceMatcher(None, a, b).ratio()


# --- Run eval ---
results = []
errors = []
total_time = 0
SYSTEM = tests[0]["system"]

for i, t in enumerate(tests):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": t["dictated"]},
    ]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    start = time.perf_counter()
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=120, do_sample=False)
    elapsed = time.perf_counter() - start
    total_time += elapsed

    generated = outputs[0][inputs["input_ids"].shape[1]:]
    got = tokenizer.decode(generated, skip_special_tokens=True).strip()
    got = re.sub(r"<think>.*?</think>", "", got, flags=re.DOTALL).strip()

    sim = similarity(got, t["expected"])
    exact = got == t["expected"]
    cat = "exact" if exact else ("near" if sim > 0.9 else ("partial" if sim > 0.7 else "wrong"))

    results.append({
        "category": cat, "exact": exact, "similarity": sim,
        "got": got, "expected": t["expected"], "dictated": t["dictated"],
    })
    if not exact:
        errors.append((i, t, got, sim))

    if (i + 1) % 50 == 0:
        ec = sum(1 for r in results if r["exact"])
        nc = sum(1 for r in results if r["category"] in ("exact", "near"))
        print(f"  [{i+1}/{len(tests)}] exact:{ec}/{i+1} ({ec/(i+1)*100:.1f}%) eff:{nc}/{i+1} ({nc/(i+1)*100:.1f}%)")
        sys.stdout.flush()

# --- Save results ---
with open("eval_qwen35_2b_results.json", "w") as f:
    json.dump(results, f, indent=2)

# --- Print summary ---
total = len(results)
ec = sum(1 for r in results if r["category"] == "exact")
nc = sum(1 for r in results if r["category"] == "near")
pc = sum(1 for r in results if r["category"] == "partial")
wc = sum(1 for r in results if r["category"] == "wrong")
eff = ec + nc

print(f"\n{'='*60}")
print(f"  QWEN3.5-2B EVALUATION — {total} cases")
print(f"{'='*60}")
print(f"  Exact match:        {ec}/{total} ({ec/total*100:.1f}%)")
print(f"  Near (>90% sim):    {nc}/{total} ({nc/total*100:.1f}%)")
print(f"  Partial (70-90%):   {pc}/{total} ({pc/total*100:.1f}%)")
print(f"  Wrong (<70%):       {wc}/{total} ({wc/total*100:.1f}%)")
print(f"  Effective accuracy: {eff}/{total} ({eff/total*100:.1f}%)")
print(f"  Avg latency:        {total_time/total*1000:.0f}ms")
print(f"  Total time:         {total_time:.1f}s")

print(f"\n  WORST ERRORS (by similarity):")
print(f"  {'-'*56}")
worst = sorted(errors, key=lambda x: x[3])[:20]
for idx, t, got, sim in worst:
    print(f"  [{sim:.0%}] \"{t['dictated'][:50]}\"")
    print(f"       expected: {t['expected'][:60]}")
    print(f"       got:      {got[:60]}")
    print()
