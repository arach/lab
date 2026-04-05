#!/usr/bin/env python3
"""Train a binary classifier: does this dictated input need LLM normalization?

Uses hand-crafted features + logistic regression. No bag-of-words, no TF-IDF.
The exported model is 10 weights + a bias — trivially portable to Swift.

Usage:
  python3 datasets/needs-llm-classifier.py              # train + cross-val + export
  python3 datasets/needs-llm-classifier.py --eval FILE   # evaluate on specific file
"""

import json
import math
import os
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedKFold

# ── Vocabulary sets (same as procedural-processor.py) ────────────────────

PROTOCOL_VOCAB = frozenset({
    # Symbol words
    'dash', 'dot', 'slash', 'pipe', 'redirect', 'append', 'less', 'star',
    'bang', 'hash', 'tilde', 'at', 'dollar', 'percent', 'caret', 'ampersand',
    'equals', 'plus', 'colon', 'semicolon', 'underscore', 'comma', 'backslash',
    'quote', 'backtick', 'question',
    # Synonyms
    'minus', 'hyphen', 'period', 'asterisk', 'hashtag',
    # Two-word symbol components
    'single', 'open', 'close', 'paren', 'brace', 'bracket', 'angle', 'curly',
    'than', 'mark', 'double', 'and', 'forward', 'back', 'sign', 'new', 'line',
    'parenthesis',
    # Casing
    'capital', 'all', 'caps', 'camel', 'snake', 'pascal', 'kebab', 'screaming',
    'case',
    # Space
    'space',
    # Number words
    'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
    'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
    'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'thirty', 'forty',
    'fifty', 'sixty', 'seventy', 'eighty', 'ninety', 'hundred', 'thousand',
})

FILLER_WORDS = frozenset({
    'okay', 'ok', 'so', 'um', 'uh', 'umm', 'like', 'basically',
    'actually', 'right', 'alright', 'yeah', 'well', 'hmm',
})

INTENT_PHRASES = (
    'i want', 'i wanna', 'can you', "let's", 'let me', 'we need',
    'type out', 'should be', 'go ahead', 'i need', 'i think',
    'we want', 'the command', 'just do', 'run it', 'make it',
    'change', 'set the', 'for the', 'use the', 'add the',
)

CORRECTION_PHRASES = (
    'no wait', 'wait no', 'scratch', 'not that', 'go back',
    'actually no', 'never mind', 'hold on', 'start over',
)

CASING_STARTERS = frozenset({
    'camel', 'snake', 'pascal', 'kebab', 'screaming',
})

FEATURE_NAMES = [
    'space_ratio',
    'space_present',
    'protocol_ratio',
    'filler_count',
    'intent_count',
    'correction_count',
    'starts_casing',
    'word_count',
    'non_protocol_ratio',
    'avg_word_len',
]


# ── Feature extraction ──────────────────────────────────────────────────

def extract_features(text):
    """Extract 10 numeric features from dictated text."""
    words = text.lower().split()
    n = len(words)
    if n == 0:
        return [0.0] * len(FEATURE_NAMES)

    # 1. space_ratio: count of 'space' tokens / word count
    space_count = words.count('space')
    space_ratio = space_count / n

    # 2. space_present: binary
    space_present = 1.0 if space_count > 0 else 0.0

    # 3. protocol_ratio: protocol vocab words / word count
    protocol_count = sum(1 for w in words if w in PROTOCOL_VOCAB)
    protocol_ratio = protocol_count / n

    # 4. filler_count: count of filler words
    filler_count = sum(1 for w in words if w in FILLER_WORDS)

    # 5. intent_count: count of intent phrases found
    text_lower = text.lower()
    intent_count = sum(1 for p in INTENT_PHRASES if p in text_lower)

    # 6. correction_count: count of correction phrases found
    correction_count = sum(1 for p in CORRECTION_PHRASES if p in text_lower)

    # 7. starts_casing: first word is a casing directive
    starts_casing = 1.0 if words[0] in CASING_STARTERS else 0.0

    # 8. word_count (normalized — divide by 20 to keep scale reasonable)
    word_count = n / 20.0

    # 9. non_protocol_ratio: words NOT in protocol vocab / word count
    non_protocol_ratio = 1.0 - protocol_ratio

    # 10. avg_word_len: mean character length of words
    avg_word_len = sum(len(w) for w in words) / n

    return [
        space_ratio,
        space_present,
        protocol_ratio,
        filler_count,
        intent_count,
        correction_count,
        starts_casing,
        word_count,
        non_protocol_ratio,
        avg_word_len,
    ]


# ── Data loading ────────────────────────────────────────────────────────

def load_eval_data(path):
    """Load eval JSON, return list of (text, label) tuples.

    Label: 0 = clean (no LLM needed), 1 = needs LLM.
    """
    with open(path) as f:
        data = json.load(f)

    pairs = []
    for entry in data:
        text = entry['dictated']
        difficulty = entry.get('difficulty', 'unknown')
        label = 0 if difficulty == 'clean' else 1
        pairs.append((text, label))
    return pairs


def load_all_training_data():
    """Load and combine both eval datasets."""
    base = os.path.dirname(os.path.abspath(__file__))
    pairs = []
    for fname in ['eval-fuzzy.json', 'eval-normalizer.json']:
        path = os.path.join(base, fname)
        if os.path.exists(path):
            pairs.extend(load_eval_data(path))
            print(f'  Loaded {fname}: {len(load_eval_data(path))} entries')
    return pairs


# ── Training ────────────────────────────────────────────────────────────

def train_and_evaluate():
    """Train logistic regression, cross-validate, export model."""
    print('Loading training data...')
    pairs = load_all_training_data()
    print(f'  Total: {len(pairs)} entries')

    # Count classes
    n_clean = sum(1 for _, l in pairs if l == 0)
    n_llm = sum(1 for _, l in pairs if l == 1)
    print(f'  Clean (0): {n_clean}, Needs LLM (1): {n_llm}')
    print()

    # Extract features
    texts = [t for t, _ in pairs]
    labels = [l for _, l in pairs]
    X = np.array([extract_features(t) for t in texts])
    y = np.array(labels)

    # ── Cross-validation ──
    print('5-Fold Stratified Cross-Validation')
    print('=' * 55)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_metrics = []

    for fold, (train_idx, test_idx) in enumerate(skf.split(X, y), 1):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='binary')
        fold_metrics.append((acc, prec, rec, f1))
        print(f'  Fold {fold}: acc={acc:.3f}  prec={prec:.3f}  rec={rec:.3f}  f1={f1:.3f}')

    avg_acc = np.mean([m[0] for m in fold_metrics])
    avg_prec = np.mean([m[1] for m in fold_metrics])
    avg_rec = np.mean([m[2] for m in fold_metrics])
    avg_f1 = np.mean([m[3] for m in fold_metrics])
    print(f'  ─────')
    print(f'  Mean:  acc={avg_acc:.3f}  prec={avg_prec:.3f}  rec={avg_rec:.3f}  f1={avg_f1:.3f}')
    print()

    # ── Train final model on all data ──
    print('Training final model on all data...')
    final_model = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
    final_model.fit(X, y)

    y_pred_all = final_model.predict(X)
    print()
    print('Final Model — Full Dataset')
    print('=' * 55)
    print(classification_report(y, y_pred_all, target_names=['clean', 'needs_llm']))

    # Confusion matrix
    cm = confusion_matrix(y, y_pred_all)
    print('Confusion Matrix:')
    print(f'                 Predicted')
    print(f'              clean  needs_llm')
    print(f'  Actual clean    {cm[0][0]:4d}     {cm[0][1]:4d}')
    print(f'  Actual llm      {cm[1][0]:4d}     {cm[1][1]:4d}')
    print()

    # Feature importances
    weights = final_model.coef_[0]
    bias = final_model.intercept_[0]

    print('Feature Importances (weight magnitude):')
    print('-' * 45)
    importance = sorted(zip(FEATURE_NAMES, weights), key=lambda x: abs(x[1]), reverse=True)
    for name, w in importance:
        direction = 'needs_llm' if w > 0 else 'clean'
        print(f'  {name:>20}: {w:+.4f}  ({direction})')
    print(f'  {"bias":>20}: {bias:+.4f}')
    print()

    # ── Export model ──
    model_data = {
        'weights': weights.tolist(),
        'bias': float(bias),
        'features': FEATURE_NAMES,
        'threshold': 0.5,
        'protocol_vocab': sorted(PROTOCOL_VOCAB),
        'filler_words': sorted(FILLER_WORDS),
        'intent_phrases': list(INTENT_PHRASES),
        'correction_phrases': list(CORRECTION_PHRASES),
        'casing_starters': sorted(CASING_STARTERS),
    }

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'needs-llm-model.json')
    with open(out_path, 'w') as f:
        json.dump(model_data, f, indent=2)
    print(f'Model exported to {out_path}')

    return final_model


def evaluate_file(model_path, eval_path):
    """Evaluate the exported model against an eval file."""
    with open(model_path) as f:
        model_data = json.load(f)

    weights = np.array(model_data['weights'])
    bias = model_data['bias']
    threshold = model_data['threshold']

    pairs = load_eval_data(eval_path)
    print(f'Evaluating {eval_path} ({len(pairs)} entries)')
    print('=' * 55)

    tp = fp = tn = fn = 0
    misclassified = []

    for text, actual in pairs:
        features = np.array(extract_features(text))
        logit = features @ weights + bias
        prob = 1.0 / (1.0 + math.exp(-logit))
        predicted = 1 if prob >= threshold else 0

        if actual == 1 and predicted == 1: tp += 1
        elif actual == 0 and predicted == 0: tn += 1
        elif actual == 0 and predicted == 1: fp += 1
        else:
            fn += 1
            misclassified.append(('needs_llm', 'clean', text[:70], prob))

        if actual == 1 and predicted == 0:
            misclassified.append(('clean', 'needs_llm', text[:70], prob))

    total = tp + tn + fp + fn
    acc = (tp + tn) / total
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0

    print(f'  TP (needs_llm→needs_llm): {tp}')
    print(f'  TN (clean→clean):         {tn}')
    print(f'  FP (clean→needs_llm):     {fp}  ← unnecessary LLM call (safe)')
    print(f'  FN (needs_llm→clean):     {fn}  ← would skip LLM incorrectly!')
    print()
    print(f'  Accuracy:  {acc*100:.1f}%')
    print(f'  Precision: {prec*100:.1f}%')
    print(f'  Recall:    {rec*100:.1f}%')
    print()

    if misclassified:
        print(f'Misclassified ({len(misclassified)}, first 15):')
        for actual, pred, text, prob in misclassified[:15]:
            print(f'  {actual:>9} → {pred:<9}  p={prob:.3f}  {text}')


# ── Main ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if '--eval' in sys.argv:
        idx = sys.argv.index('--eval')
        eval_file = sys.argv[idx + 1]
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'needs-llm-model.json')
        evaluate_file(model_path, eval_file)
    else:
        train_and_evaluate()
