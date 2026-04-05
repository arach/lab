#!/usr/bin/env python3
"""
Train a per-word protocol segment classifier.

Purpose: Given a mixed dictation like "I want to check the directory ls dash la",
classify each word as protocol (1) or natural (0), so we can extract segments
to send to the fused Qwen3 model.

Architecture:
- Per-word logistic regression with contextual features
- Context window of ±2 words
- Output: weights + bias → port to Swift as ProtocolSegmentClassifier

Training data: Synthetic mixed dictations combining natural speech fragments
with protocol command dictations from eval-fuzzy.json.
"""

import json
import numpy as np
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from repo_paths import PIPELINE_DIR

# ─── Protocol vocabulary split into strong/weak ───
# Strong: almost never appear in natural speech
# Weak: frequently appear in natural speech, only protocol in context

STRONG_PROTOCOL = {
    # Symbol words (unambiguous)
    "dash", "dot", "slash", "pipe", "tilde", "hash", "dollar",
    "caret", "ampersand", "equals", "underscore", "backslash",
    "backtick", "semicolon", "colon",
    # Synonyms
    "minus", "hyphen", "asterisk", "hashtag",
    # Brackets (unambiguous components)
    "paren", "brace", "bracket", "parenthesis", "curly",
    # Casing directives
    "capital", "caps", "camel", "snake", "pascal", "kebab", "screaming",
    # Space as protocol
    "space",
    # Redirect
    "redirect", "append",
}

WEAK_PROTOCOL = {
    # These appear frequently in natural speech
    "at", "star", "bang", "exclamation", "question", "comma", "quote",
    "period", "plus", "percent",
    # Multi-word components that are also common English
    "single", "open", "close", "angle", "forward", "back", "sign",
    "double", "mark", "than", "less", "new", "line", "all", "case",
    # Number words REMOVED — too ambiguous in natural speech.
    # Numbers near protocol words get captured by ±2 expansion instead.
}

PROTOCOL_VOCAB = STRONG_PROTOCOL | WEAK_PROTOCOL

# Expanded symbols (after symbolic mapping runs)
EXPANDED_SYMBOLS = {
    "-", ".", "/", "\\", "_", "|", "~", "@", "#", "*",
    "+", "=", ":", ";", "&", "%", "^", "!", "?", "`",
    "$", "<", ">", "--", "&&", "||",
}

SYNTAX_CHARS = set("-./\\_|~@#:=")

# ─── Natural speech fragments ───

NATURAL_PHRASES = [
    "I want to check the directory",
    "can you run this command for me",
    "let's see what happens when we",
    "okay so basically I need to",
    "the next thing I want to do is",
    "alright let me try",
    "I think we should also look at",
    "and then after that",
    "go ahead and type out",
    "so the idea is to",
    "I was thinking maybe we could",
    "hold on let me think about this",
    "what if we try something different",
    "actually no wait",
    "right so the problem is",
    "I need to figure out why",
    "let's debug this real quick",
    "the output should show us",
    "and that would give us",
    "basically what I'm trying to do is",
    "so first we need to",
    "and then we can see if",
    "alright this is important",
    "I want to emphasize",
    "the reason I'm doing this is",
    "so we did have a classifier",
    "wasn't that part of the mission",
    "like if we run all of a long dictation",
    "I mean we'd be lucky to get",
    "there's some stuff happening",
    "that was not at all what I said",
    "my last dictation was",
    "we're not trying to do any list extraction",
    "can you give me a few different test commands",
    "I don't really understand",
    "we should be able to fix that",
    "alright let's do a proper dictation",
    "the whole point is that",
    "I think the idea would be",
    "we want to build a new one",
    "so yeah I think like we want to",
    "and that would be a cleanup job",
    "with maybe a bigger model",
    "right so I think the plan is",
    "let me explain what's going on",
    "this is getting really interesting",
    "okay perfect that works",
    "no that's not right",
    "wait what happened there",
    "I'm gonna try again",
]

# ─── Protocol command dictations ───

PROTOCOL_COMMANDS = [
    # Simple commands
    "ls dash la",
    "git dash dash help",
    "cd dot dot",
    "rm dash rf",
    "mkdir dash p",
    "cat slash etc slash hosts",
    "chmod seven five five",
    "grep dash r",
    "find dot dash name",
    "ps aux",
    "kill dash nine",
    # Medium commands
    "git space push space dash u space origin space main",
    "docker space run space dash dash rm space dash p space eight zero eight zero colon eight zero",
    "npm space install space dash capital D space typescript",
    "ssh space dash i space tilde slash dot ssh slash id underscore rsa",
    "curl space dash capital X space all caps POST",
    "kubectl space get space pods space dash n space kube dash system",
    "brew space install space dash dash cask",
    "pip space install space dash r space requirements dot txt",
    "python space dash m space pytest space dash v",
    "cargo space build space dash dash release",
    # Complex commands with paths
    "rsync space dash avz space dash e space ssh space dot slash dist slash",
    "export space all caps DATABASE underscore URL equals quote postgres colon slash slash admin",
    "redis dash cli space dash h space one two seven dot zero dot zero dot one",
    "terraform space plan space dash var dash file equals production dot tfvars",
    # Short fragments
    "dash dash help",
    "dash la",
    "dot slash",
    "slash usr slash local slash bin",
    "tilde slash dot config",
    "star dot js",
    "dollar sign open paren",
    # Tool names with hyphens
    "talkie dash dev",
    "visual dash studio dash code",
    "docker dash compose",
    "kube dash system",
    "type dash script",
]

# Additional pure natural sentences — includes words that overlap with protocol vocab
# (at, three, one, new, line, back, sign, case, all, open, close, etc.)
PURE_NATURAL = [
    "I was just thinking about how to approach this problem differently",
    "the meeting is at three o'clock tomorrow afternoon",
    "can you send me the link to that document",
    "I'll get back to you on that later today",
    "the project deadline is next Friday",
    "we should probably discuss this with the rest of the team",
    "that's a great idea I hadn't thought of that",
    "let me know if you need anything else from me",
    "I think the best approach would be to start from scratch",
    "have you seen the latest updates to the design",
    "the performance numbers look really good",
    "we might need to reconsider our strategy here",
    "I'll set up a call with the engineering team",
    "the documentation needs to be updated before release",
    "this reminds me of a similar issue we had last month",
    # Sentences with ambiguous protocol words used naturally
    "I arrived at the office at nine this morning",
    "there are three new cases to review today",
    "we need to go back and sign the contract",
    "one of the most important things is to stay open",
    "all of the line items need to be double checked",
    "the new sign at the front of the building looks great",
    "I need to close out all the open tickets by five",
    "she gave us a star review which was really nice",
    "the question mark at the end was confusing",
    "he made a plus sized version of the original",
    "we should open a new line of inquiry",
    "there were less than ten people at the event",
    "I'm going to mark this case as resolved",
    "go back to the previous page and forward it to me",
    "we had one single issue in all of last quarter",
    "the angle of the photo makes it look close to the sign",
    "I'll be back at four thirty with the new draft",
    "that's a great point about the new direction",
    "we need all hands on deck for this one",
    "the bottom line is we need more time",
    "let me quote you on that",
    "he was at a loss for words",
    "the new employee starts on day one next week",
    "all in all it was a pretty good quarter",
    "the case study shows a ten percent improvement",
    "I need to sign off on this before close of business",
    "the angle was all wrong for that particular shot",
]


def is_protocol_word(word: str) -> bool:
    """Check if a word is a protocol word."""
    lower = word.lower().strip(".,!?;:'\"")
    if lower in PROTOCOL_VOCAB:
        return True
    if word.strip() in EXPANDED_SYMBOLS:
        return True
    # Contains syntax characters (but not contractions)
    if any(c in SYNTAX_CHARS for c in lower):
        if "'" not in word and "\u2019" not in word:
            # Not just a trailing period on a normal word
            if not (word.endswith(".") and "." not in word[:-1]):
                return True
    return False


def label_words(words: list[str], labels: list[int]) -> list[dict]:
    """Create labeled word entries with context features."""
    entries = []
    n = len(words)
    for i, (word, label) in enumerate(zip(words, labels)):
        entry = {
            "word": word,
            "label": label,
            "position": i,
            "total_words": n,
        }
        entries.append(entry)
    return entries


def generate_mixed_examples(n_examples: int = 500, seed: int = 42) -> list[dict]:
    """Generate synthetic mixed dictations with word-level labels."""
    rng = np.random.RandomState(seed)
    all_labeled = []

    # Pattern 1: Natural + Protocol + Natural (sandwich)
    for _ in range(n_examples // 3):
        nat1 = rng.choice(NATURAL_PHRASES)
        cmd = rng.choice(PROTOCOL_COMMANDS)
        nat2 = rng.choice(NATURAL_PHRASES)

        nat1_words = nat1.split()
        cmd_words = cmd.split()
        nat2_words = nat2.split()

        words = nat1_words + cmd_words + nat2_words
        labels = [0] * len(nat1_words) + [1] * len(cmd_words) + [0] * len(nat2_words)
        all_labeled.extend(label_words(words, labels))

    # Pattern 2: Protocol only (full command dictation)
    for _ in range(n_examples // 4):
        cmd = rng.choice(PROTOCOL_COMMANDS)
        words = cmd.split()
        labels = [1] * len(words)
        all_labeled.extend(label_words(words, labels))

    # Pattern 3: Natural only (pure speech, no protocol)
    for _ in range(n_examples // 4):
        nat = rng.choice(PURE_NATURAL + NATURAL_PHRASES)
        words = nat.split()
        labels = [0] * len(words)
        all_labeled.extend(label_words(words, labels))

    # Pattern 4: Natural + Protocol (command at end)
    for _ in range(n_examples // 6):
        nat = rng.choice(NATURAL_PHRASES)
        cmd = rng.choice(PROTOCOL_COMMANDS)
        nat_words = nat.split()
        cmd_words = cmd.split()
        words = nat_words + cmd_words
        labels = [0] * len(nat_words) + [1] * len(cmd_words)
        all_labeled.extend(label_words(words, labels))

    # Pattern 5: Protocol + Natural (command at start, explanation after)
    for _ in range(n_examples // 6):
        cmd = rng.choice(PROTOCOL_COMMANDS)
        nat = rng.choice(NATURAL_PHRASES)
        cmd_words = cmd.split()
        nat_words = nat.split()
        words = cmd_words + nat_words
        labels = [1] * len(cmd_words) + [0] * len(nat_words)
        all_labeled.extend(label_words(words, labels))

    return all_labeled


def is_strong_protocol(word: str) -> bool:
    """Check if a word is an unambiguous protocol word."""
    lower = word.lower().strip(".,!?;:'\"")
    if lower in STRONG_PROTOCOL:
        return True
    if word.strip() in EXPANDED_SYMBOLS:
        return True
    return False


def extract_features(word: str, context: list[str], position: int, total: int) -> list[float]:
    """
    Extract features for a single word with its context.

    Features (14 total):
    0.  is_strong_protocol     — word is an unambiguous protocol word (dash, dot, slash...)
    1.  is_weak_protocol       — word is an ambiguous protocol word (at, three, one...)
    2.  is_expanded_symbol     — word is an expanded symbol (-, ., /)
    3.  has_syntax_chars       — word contains syntax characters
    4.  word_length_norm       — word length / 10 (normalized)
    5.  is_short_word          — len <= 3 (commands: ls, cd, rm)
    6.  context_strong_density — fraction of ±2 context words that are STRONG protocol
    7.  context_any_density    — fraction of ±2 context words that are any protocol
    8.  left_is_strong         — immediate left neighbor is strong protocol
    9.  right_is_strong        — immediate right neighbor is strong protocol
    10. is_number_like         — word looks like a number or number word
    11. strong_neighbor_count  — count of strong protocol words in ±2 window
    12. is_all_lower           — all lowercase
    13. position_ratio         — position / total
    """
    lower = word.lower().strip(".,!?;:'\"")
    stripped = word.strip()

    # Feature 0: is_strong_protocol
    f_strong = 1.0 if lower in STRONG_PROTOCOL else 0.0

    # Feature 1: is_weak_protocol
    f_weak = 1.0 if lower in WEAK_PROTOCOL else 0.0

    # Feature 2: is_expanded_symbol
    f_symbol = 1.0 if stripped in EXPANDED_SYMBOLS else 0.0

    # Feature 3: has_syntax_chars
    f_syntax = 0.0
    if any(c in SYNTAX_CHARS for c in lower):
        if "'" not in word and "\u2019" not in word:
            if not (word.endswith(".") and "." not in word[:-1]):
                f_syntax = 1.0

    # Feature 4: word_length_norm
    f_len = len(word) / 10.0

    # Feature 5: is_short_word
    f_short = 1.0 if len(lower) <= 3 else 0.0

    # Feature 6: context_strong_density
    ctx_strong = sum(1 for w in context if is_strong_protocol(w))
    f_ctx_strong = ctx_strong / max(len(context), 1)

    # Feature 7: context_any_density
    ctx_any = sum(1 for w in context if is_protocol_word(w))
    f_ctx_any = ctx_any / max(len(context), 1)

    # Feature 8: left_is_strong
    f_left = 0.0
    if position > 0 and len(context) > 0:
        ctx_center = min(position, 2)
        if ctx_center > 0 and ctx_center - 1 < len(context):
            f_left = 1.0 if is_strong_protocol(context[ctx_center - 1]) else 0.0

    # Feature 9: right_is_strong
    f_right = 0.0
    if position < total - 1 and len(context) > 0:
        ctx_center = min(position, 2)
        if ctx_center + 1 < len(context):
            f_right = 1.0 if is_strong_protocol(context[ctx_center + 1]) else 0.0

    # Feature 10: is_number_like
    number_words = {"zero", "one", "two", "three", "four", "five", "six",
                    "seven", "eight", "nine", "ten"}
    f_number = 1.0 if (lower in number_words or lower.isdigit()) else 0.0

    # Feature 11: strong_neighbor_count — raw count, not ratio
    f_strong_neighbors = float(ctx_strong)

    # Feature 12: is_all_lower
    f_lower = 1.0 if word.isalpha() and word == word.lower() else 0.0

    # Feature 13: position_ratio
    f_pos = position / max(total - 1, 1)

    return [
        f_strong,           # 0
        f_weak,             # 1
        f_symbol,           # 2
        f_syntax,           # 3
        f_len,              # 4
        f_short,            # 5
        f_ctx_strong,       # 6
        f_ctx_any,          # 7
        f_left,             # 8
        f_right,            # 9
        f_number,           # 10
        f_strong_neighbors, # 11
        f_lower,            # 12
        f_pos,              # 13
    ]


def build_dataset(labeled_words: list[dict], all_words_by_sentence=None):
    """Build feature matrix and label vector from labeled words."""
    # Group by sentence (consecutive entries with same total_words)
    sentences = []
    current = []
    for entry in labeled_words:
        if current and (entry["position"] == 0 or entry["total_words"] != current[0]["total_words"]):
            sentences.append(current)
            current = []
        current.append(entry)
    if current:
        sentences.append(current)

    X = []
    y = []

    for sentence in sentences:
        words = [e["word"] for e in sentence]
        for entry in sentence:
            pos = entry["position"]
            # Build context window ±2
            ctx_start = max(0, pos - 2)
            ctx_end = min(len(words), pos + 3)
            context = words[ctx_start:ctx_end]

            features = extract_features(
                entry["word"], context, pos, entry["total_words"]
            )
            X.append(features)
            y.append(entry["label"])

    return np.array(X), np.array(y)


def train_logistic_regression(X, y, lr=0.05, lambda_reg=0.1, max_epochs=500, tol=1e-6):
    """Train logistic regression with L2 regularization via batch gradient descent."""
    n_samples, n_features = X.shape
    weights = np.zeros(n_features)
    bias = 0.0

    prev_loss = float("inf")

    for epoch in range(max_epochs):
        # Forward pass
        logits = X @ weights + bias
        probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -500, 500)))

        # Loss (binary cross-entropy + L2)
        eps = 1e-15
        loss = -np.mean(
            y * np.log(probs + eps) + (1 - y) * np.log(1 - probs + eps)
        ) + 0.5 * lambda_reg * np.sum(weights ** 2)

        # Convergence check
        if abs(prev_loss - loss) < tol:
            print(f"  Converged at epoch {epoch}, loss={loss:.6f}")
            break
        prev_loss = loss

        # Gradients
        error = probs - y
        grad_w = (X.T @ error) / n_samples + lambda_reg * weights
        grad_b = np.mean(error)

        # Update
        weights -= lr * grad_w
        bias -= lr * grad_b

        if epoch % 50 == 0:
            acc = np.mean((probs >= 0.5) == y)
            print(f"  Epoch {epoch}: loss={loss:.4f}, acc={acc:.3f}")

    # Final accuracy
    probs = 1.0 / (1.0 + np.exp(-np.clip(X @ weights + bias, -500, 500)))
    acc = np.mean((probs >= 0.5) == y)
    print(f"  Final: loss={prev_loss:.4f}, acc={acc:.3f}")

    return weights, bias


def evaluate(X, y, weights, bias, threshold=0.5):
    """Evaluate classifier and print metrics."""
    logits = X @ weights + bias
    probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -500, 500)))
    preds = (probs >= threshold).astype(int)

    acc = np.mean(preds == y)
    tp = np.sum((preds == 1) & (y == 1))
    fp = np.sum((preds == 1) & (y == 0))
    fn = np.sum((preds == 0) & (y == 1))
    tn = np.sum((preds == 0) & (y == 0))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"\n  Accuracy:  {acc:.3f} ({int(acc * len(y))}/{len(y)})")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall:    {recall:.3f}")
    print(f"  F1:        {f1:.3f}")
    print(f"  Confusion: TP={tp} FP={fp} FN={fn} TN={tn}")

    return acc, precision, recall, f1


def test_mixed_examples(weights, bias):
    """Test on hand-crafted mixed dictation examples."""
    test_cases = [
        # (text, expected_protocol_words)
        ("I want to check the directory ls dash la", {"ls", "dash", "la"}),
        ("can you run git dash dash help for me", {"git", "dash", "help"}),
        ("alright let me try talkie dash dev dash dash help", {"talkie", "dash", "dev", "help"}),
        ("the meeting is at three o'clock tomorrow afternoon", set()),
        ("I think we should also look at cd dot dot slash src", {"cd", "dot", "slash", "src"}),
        ("so basically npm space install space dash capital D", {"npm", "space", "install", "dash", "capital", "D"}),
        ("let me know if you need anything else from me", set()),
        ("okay go ahead and type out chmod seven five five", {"chmod", "seven", "five"}),
        ("the performance numbers look really good", set()),
        ("ssh dash i tilde slash dot ssh slash id underscore rsa", {"ssh", "dash", "i", "tilde", "slash", "dot", "id", "underscore", "rsa"}),
    ]

    print("\n─── Test Cases ───")
    for text, expected_protocol in test_cases:
        words = text.split()
        preds = []
        for i, word in enumerate(words):
            ctx_start = max(0, i - 2)
            ctx_end = min(len(words), i + 3)
            context = words[ctx_start:ctx_end]
            features = extract_features(word, context, i, len(words))
            logit = np.dot(features, weights) + bias
            prob = 1.0 / (1.0 + np.exp(-logit))
            preds.append((word, prob, prob >= 0.5))

        detected = {w for w, p, is_proto in preds if is_proto}
        natural = {w for w, p, is_proto in preds if not is_proto}

        # Color output
        colored = []
        for w, p, is_proto in preds:
            if is_proto:
                colored.append(f"\033[91m{w}\033[0m")  # red = protocol
            else:
                colored.append(f"\033[92m{w}\033[0m")  # green = natural
        print(f"  {' '.join(colored)}")

        # Check accuracy
        if expected_protocol:
            correct = detected & expected_protocol
            missed = expected_protocol - detected
            false_pos = detected - expected_protocol
            if missed:
                print(f"    MISSED: {missed}")
            if false_pos:
                print(f"    FALSE+: {false_pos}")
        elif detected:
            print(f"    FALSE+: {detected}")


def export_model(weights, bias, feature_names, output_path):
    """Export model as JSON for porting to Swift."""
    model = {
        "classifier": "ProtocolSegmentClassifier",
        "description": "Per-word logistic regression for protocol segment detection",
        "features": feature_names,
        "weights": weights.tolist(),
        "bias": float(bias),
        "threshold": 0.5,
    }
    with open(output_path, "w") as f:
        json.dump(model, f, indent=2)
    print(f"\nModel exported to {output_path}")


FEATURE_NAMES = [
    "is_strong_protocol",
    "is_weak_protocol",
    "is_expanded_symbol",
    "has_syntax_chars",
    "word_length_norm",
    "is_short_word",
    "context_strong_density",
    "context_any_density",
    "left_is_strong",
    "right_is_strong",
    "is_number_like",
    "strong_neighbor_count",
    "is_all_lower",
    "position_ratio",
]


def main():
    print("=" * 60)
    print("Protocol Segment Classifier Training")
    print("=" * 60)

    # Generate training data
    print("\n1. Generating training data...")
    labeled = generate_mixed_examples(n_examples=600, seed=42)
    print(f"   {len(labeled)} labeled words generated")

    # Count class balance
    n_protocol = sum(1 for e in labeled if e["label"] == 1)
    n_natural = sum(1 for e in labeled if e["label"] == 0)
    print(f"   Protocol: {n_protocol} ({100*n_protocol/len(labeled):.1f}%)")
    print(f"   Natural:  {n_natural} ({100*n_natural/len(labeled):.1f}%)")

    # Build feature matrix
    print("\n2. Extracting features...")
    X, y = build_dataset(labeled)
    print(f"   Feature matrix: {X.shape}")

    # Split train/test (80/20)
    n = len(y)
    indices = np.random.RandomState(42).permutation(n)
    split = int(0.8 * n)
    train_idx, test_idx = indices[:split], indices[split:]
    X_train, y_train = X[train_idx], y[train_idx]
    X_test, y_test = X[test_idx], y[test_idx]
    print(f"   Train: {len(y_train)}, Test: {len(y_test)}")

    # Train
    print("\n3. Training logistic regression...")
    weights, bias = train_logistic_regression(X_train, y_train)

    # Print weights
    print("\n   Weights:")
    for name, w in zip(FEATURE_NAMES, weights):
        print(f"     {name:30s} {w:+.6f}")
    print(f"     {'bias':30s} {bias:+.6f}")

    # Evaluate on test set
    print("\n4. Test set evaluation:")
    evaluate(X_test, y_test, weights, bias)

    # Evaluate on train set (sanity check)
    print("\n5. Train set evaluation (sanity):")
    evaluate(X_train, y_train, weights, bias)

    # Test on hand-crafted mixed examples
    print("\n6. Mixed dictation examples:")
    test_mixed_examples(weights, bias)

    # Export
    output_path = PIPELINE_DIR / "segment-classifier-model.json"
    export_model(weights, bias, FEATURE_NAMES, output_path)

    # Print Swift-ready constants
    print("\n─── Swift Constants ───")
    print(f"private static let weights: [Double] = [")
    for name, w in zip(FEATURE_NAMES, weights):
        print(f"    {w:+.20f},  // {name}")
    print(f"]")
    print(f"private static let bias: Double = {bias:+.20f}")


if __name__ == "__main__":
    main()
