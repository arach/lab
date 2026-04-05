#!/usr/bin/env python3
"""Test the needs_llm detector against eval data."""

import json, sys, os

# Import needs_llm from procedural-processor without running its __main__
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'procedural-processor.py')).read()
_code = compile(_src, 'procedural-processor.py', 'exec')
_proc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'procedural-processor.py')
_ns = {'__name__': 'procedural_processor', '__file__': _proc_path}
exec(_code, _ns)
needs_llm = _ns['needs_llm']

eval_file = sys.argv[1] if len(sys.argv) > 1 else 'datasets/eval-fuzzy.json'
data = json.load(open(eval_file))

tp = fp = tn = fn = 0
misclassified = []

for d in data:
    actual_needs_llm = d.get('difficulty') != 'clean'
    predicted_needs_llm = needs_llm(d['dictated'])

    if actual_needs_llm and predicted_needs_llm: tp += 1
    elif not actual_needs_llm and not predicted_needs_llm: tn += 1
    elif not actual_needs_llm and predicted_needs_llm: fp += 1; misclassified.append(('clean', 'needs-llm', d['dictated'][:70]))
    else: fn += 1; misclassified.append(('needs-llm', 'clean', d['dictated'][:70]))

print(f'NEEDS_LLM DETECTOR — Binary Classification ({eval_file})')
print('=' * 60)
print(f'  True positives  (needs_llm→needs_llm): {tp}')
print(f'  True negatives  (clean→clean):         {tn}')
print(f'  False positives (clean→needs_llm):     {fp}  ← unnecessary LLM call (safe)')
print(f'  False negatives (needs_llm→clean):     {fn}  ← would skip LLM incorrectly!')
print()
total = tp + tn + fp + fn
acc = (tp+tn)/total
prec = tp/(tp+fp) if (tp+fp) > 0 else 0
rec = tp/(tp+fn) if (tp+fn) > 0 else 0
print(f'  Accuracy:  {acc*100:.0f}%')
print(f'  Precision: {prec*100:.0f}% (when we say needs_llm, how often correct)')
print(f'  Recall:    {rec*100:.0f}% (what % of needs_llm inputs we catch)')
print()

if misclassified:
    print(f'Misclassified ({len(misclassified)}):')
    for actual, pred, text in misclassified[:15]:
        print(f'  {actual:>9} -> {pred:<9}  {text}')
