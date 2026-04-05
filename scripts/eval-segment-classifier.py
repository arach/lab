#!/usr/bin/env python3
"""
Evaluate the ProtocolSegmentClassifier against labeled mixed dictation examples.

Measures:
1. Word-level accuracy (is each word correctly classified?)
2. Segment boundary accuracy (does the classifier find the right start/end?)
3. False positive rate on pure natural text
4. False negative rate on protocol segments
"""

import json
import numpy as np
from pathlib import Path
import importlib

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from repo_paths import EVAL_DIR, PIPELINE_DIR

_mod = importlib.import_module("train-segment-classifier")
extract_features = _mod.extract_features
is_protocol_word = _mod.is_protocol_word
is_strong_protocol = _mod.is_strong_protocol
STRONG_PROTOCOL = _mod.STRONG_PROTOCOL
WEAK_PROTOCOL = _mod.WEAK_PROTOCOL
EXPANDED_SYMBOLS = _mod.EXPANDED_SYMBOLS


def load_model(path: str) -> tuple[np.ndarray, float]:
    """Load trained model from JSON."""
    with open(path) as f:
        model = json.load(f)
    return np.array(model["weights"]), model["bias"]


def classify_words(words: list[str], weights: np.ndarray, bias: float, threshold: float = 0.5) -> list[tuple[str, float, bool]]:
    """Classify each word and return (word, probability, is_protocol)."""
    results = []
    n = len(words)
    for i, word in enumerate(words):
        ctx_start = max(0, i - 2)
        ctx_end = min(n, i + 3)
        context = words[ctx_start:ctx_end]
        features = extract_features(word, context, i, n)
        logit = np.dot(features, weights) + bias
        prob = 1.0 / (1.0 + np.exp(-logit))
        results.append((word, prob, prob >= threshold))
    return results


def expand_anchors(is_anchor: list[bool], n: int, radius: int = 2) -> list[bool]:
    """Expand anchor words ±radius to capture adjacent command tokens."""
    expanded = [False] * n
    for i in range(n):
        if is_anchor[i]:
            for j in range(max(0, i - radius), min(n, i + radius + 1)):
                expanded[j] = True
    return expanded


def build_segments(words: list[str], in_protocol: list[bool]) -> list[tuple[str, str]]:
    """Build (kind, text) segments from word-level classifications."""
    segments = []
    current_kind = "protocol" if in_protocol[0] else "natural"
    current_words = [words[0]]

    for i in range(1, len(words)):
        kind = "protocol" if in_protocol[i] else "natural"
        if kind == current_kind:
            current_words.append(words[i])
        else:
            segments.append((current_kind, " ".join(current_words)))
            current_kind = kind
            current_words = [words[i]]
    segments.append((current_kind, " ".join(current_words)))
    return segments


def label_words_from_example(example: dict) -> list[int]:
    """
    Label each word in the text as natural (0) or protocol (1)
    based on the 'natural' and 'protocol' fields.

    The protocol field may contain ||| to indicate multiple protocol segments.
    The natural field may contain ||| to indicate natural segments between protocol segments.
    """
    text = example["text"]
    words = text.split()
    natural_parts = [p.strip() for p in example["natural"].split("|||") if p.strip()]
    protocol_parts = [p.strip() for p in example["protocol"].split("|||") if p.strip()]

    labels = [0] * len(words)

    # Mark protocol words
    for proto_part in protocol_parts:
        proto_words = proto_part.split()
        if not proto_words:
            continue

        # Find this sequence in the text
        plen = len(proto_words)
        for start in range(len(words) - plen + 1):
            if words[start:start + plen] == proto_words:
                for j in range(start, start + plen):
                    labels[j] = 1
                break

    return labels


def evaluate(eval_path: str, model_path: str):
    """Run full evaluation."""
    with open(eval_path) as f:
        examples = json.load(f)

    weights, bias = load_model(model_path)

    print("=" * 70)
    print("PROTOCOL SEGMENT CLASSIFIER EVALUATION")
    print(f"  Model: {model_path}")
    print(f"  Eval set: {len(examples)} examples")
    print("=" * 70)

    # Aggregate metrics
    total_words = 0
    correct_words = 0
    tp = fp = fn = tn = 0

    # Per-category tracking
    pure_natural_count = 0
    pure_natural_correct = 0
    mixed_count = 0
    mixed_correct = 0

    # Detailed results
    errors = []

    for ex in examples:
        text = ex["text"]
        words = text.split()
        n = len(words)
        is_pure_natural = not ex["protocol"].strip()

        # Get ground truth labels
        gt_labels = label_words_from_example(ex)

        # Classify
        results = classify_words(words, weights, bias)
        anchors = [r[2] for r in results]
        predicted = expand_anchors(anchors, n)

        # Word-level metrics
        for i in range(n):
            pred = 1 if predicted[i] else 0
            gt = gt_labels[i]
            total_words += 1
            if pred == gt:
                correct_words += 1
            if pred == 1 and gt == 1:
                tp += 1
            elif pred == 1 and gt == 0:
                fp += 1
            elif pred == 0 and gt == 1:
                fn += 1
            else:
                tn += 1

        # Example-level tracking
        example_correct = all(
            (1 if predicted[i] else 0) == gt_labels[i]
            for i in range(n)
        )

        if is_pure_natural:
            pure_natural_count += 1
            if example_correct:
                pure_natural_correct += 1
        else:
            mixed_count += 1
            if example_correct:
                mixed_correct += 1

        # Collect errors for display
        if not example_correct:
            pred_segments = build_segments(words, predicted)
            gt_segments = build_segments(words, [bool(l) for l in gt_labels])
            errors.append({
                "id": ex["id"],
                "note": ex.get("note", ""),
                "words": words,
                "gt": gt_labels,
                "pred": [1 if p else 0 for p in predicted],
                "pred_segments": pred_segments,
                "gt_segments": gt_segments,
            })

    # Print results
    word_acc = correct_words / total_words if total_words else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"\n{'WORD-LEVEL METRICS':─^70}")
    print(f"  Accuracy:   {word_acc:.1%} ({correct_words}/{total_words})")
    print(f"  Precision:  {precision:.1%} (protocol words correctly identified)")
    print(f"  Recall:     {recall:.1%} (protocol words found)")
    print(f"  F1:         {f1:.3f}")
    print(f"  Confusion:  TP={tp}  FP={fp}  FN={fn}  TN={tn}")

    print(f"\n{'EXAMPLE-LEVEL METRICS':─^70}")
    print(f"  Pure natural (no protocol):  {pure_natural_correct}/{pure_natural_count} perfect")
    print(f"  Mixed (natural + protocol):  {mixed_correct}/{mixed_count} perfect")
    total_ex = pure_natural_count + mixed_count
    total_correct = pure_natural_correct + mixed_correct
    print(f"  Overall:                     {total_correct}/{total_ex} perfect ({100*total_correct/total_ex:.0f}%)")

    # Show errors
    if errors:
        print(f"\n{'ERRORS':─^70}")
        for err in errors:
            print(f"\n  #{err['id']}: {err['note']}")
            # Show words with color coding
            parts = []
            for i, word in enumerate(err["words"]):
                gt = err["gt"][i]
                pred = err["pred"][i]
                if gt == pred:
                    if gt == 1:
                        parts.append(f"\033[92m{word}\033[0m")  # green = correct protocol
                    else:
                        parts.append(word)  # plain = correct natural
                elif pred == 1 and gt == 0:
                    parts.append(f"\033[91m[FP:{word}]\033[0m")  # red = false positive
                else:
                    parts.append(f"\033[93m[FN:{word}]\033[0m")  # yellow = false negative
            print(f"    {' '.join(parts)}")

    # Summary
    print(f"\n{'SUMMARY':─^70}")
    fp_rate = fp / (fp + tn) if (fp + tn) > 0 else 0
    fn_rate = fn / (fn + tp) if (fn + tp) > 0 else 0
    print(f"  False positive rate: {fp_rate:.1%} (natural words misclassified as protocol)")
    print(f"  False negative rate: {fn_rate:.1%} (protocol words missed)")
    print(f"  Key concern: FP on natural text → model hallucinates on speech")
    print(f"  Secondary:   FN on protocol → falls through as raw dictation")

    return word_acc, precision, recall, f1


if __name__ == "__main__":
    eval_path = EVAL_DIR / "segment-classifier.json"
    model_path = PIPELINE_DIR / "segment-classifier-model.json"
    evaluate(str(eval_path), str(model_path))
