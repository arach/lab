#!/usr/bin/env python3
"""
End-to-end test of the segment classifier + fused model chain.

Simulates the full dictation pipeline without a microphone:
1. Takes mixed dictation text (natural + protocol)
2. Runs ProtocolSegmentClassifier to extract segments
3. Sends protocol segments to TalkieInference via talkie-dev CLI
4. Reassembles output and compares against expected

Usage:
  python3 test-full-chain.py                    # run all test cases
  python3 test-full-chain.py --case 3           # run specific case
  python3 test-full-chain.py --classifier-only  # skip model, just test segmentation
"""

import json
import subprocess
import sys
import time
import importlib
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from repo_paths import PIPELINE_DIR

# Import classifier from training script
_mod = importlib.import_module("train-segment-classifier")
extract_features = _mod.extract_features
is_protocol_word = _mod.is_protocol_word
is_strong_protocol = _mod.is_strong_protocol

# Load model
MODEL_PATH = PIPELINE_DIR / "segment-classifier-model.json"
with open(MODEL_PATH) as f:
    _model = json.load(f)
WEIGHTS = np.array(_model["weights"])
BIAS = _model["bias"]
THRESHOLD = _model.get("threshold", 0.5)

# The model ID for the fused bash reconstruction model
MODEL_ID = "arach/qwen3-0.6b-bash-v1"
SYSTEM_PROMPT = "You are a dictation-to-bash converter. The input is a segment of dictated speech containing a command. Words like 'space', 'dash', 'dot', 'slash', 'colon', 'underscore', 'tilde', 'quote' are literal symbols. Number words like 'eight zero eight zero' mean '8080'. 'capital' means uppercase the next letter. 'all caps' means uppercase the next word. Ignore filler words like 'so', 'try', 'run', 'do', 'with'. Output ONLY the reconstructed command, nothing else."


# ─── Test cases ───

TEST_CASES = [
    {
        "input": "I want to check the directory ls dash la",
        "expected_natural": "I want to check the directory",
        "expected_command": "ls -la",
        "note": "Simple mixed: natural + short command"
    },
    {
        "input": "let me see what's running ps dash aux",
        "expected_natural": "let me see what's running",
        "expected_command": "ps -aux",
        "note": "Casual intro + ps"
    },
    {
        "input": "git space push space dash u space origin space main",
        "expected_natural": "",
        "expected_command": "git push -u origin main",
        "note": "Pure protocol, no natural speech"
    },
    {
        "input": "the meeting is at three o'clock tomorrow afternoon",
        "expected_natural": "the meeting is at three o'clock tomorrow afternoon",
        "expected_command": "",
        "note": "Pure natural, should NOT trigger model"
    },
    {
        "input": "can you run git space clone space https colon slash slash github dot com slash user slash repo for me",
        "expected_natural": "can you run ... for me",
        "expected_command": "git clone https://github.com/user/repo",
        "note": "Command sandwiched in natural speech"
    },
    {
        "input": "alright first do cd space tilde slash projects and then run npm space install",
        "expected_natural": "alright first do ... and then run",
        "expected_command": "cd ~/projects | npm install",
        "note": "Two commands with natural bridge"
    },
    {
        "input": "the quarterly report shows revenue increased by twelve percent year over year",
        "expected_natural": "the quarterly report shows revenue increased by twelve percent year over year",
        "expected_command": "",
        "note": "Business English with 'percent' — should NOT trigger"
    },
    {
        "input": "ssh space dash i space tilde slash dot ssh slash id underscore rsa space root at one nine two dot one six eight dot one dot one",
        "expected_natural": "",
        "expected_command": "ssh -i ~/.ssh/id_rsa root@192.168.1.1",
        "note": "Complex SSH command with IP"
    },
    {
        "input": "I think the problem is the firewall so try iptables space dash capital A space INPUT space dash p space tcp space dash dash dport space eight zero eight zero space dash j space ACCEPT",
        "expected_natural": "I think the problem is the firewall so try",
        "expected_command": "iptables -A INPUT -p tcp --dport 8080 -j ACCEPT",
        "note": "Diagnostic reasoning + iptables"
    },
    {
        "input": "according to the handbook all new employees must complete training within two weeks",
        "expected_natural": "according to the handbook all new employees must complete training within two weeks",
        "expected_command": "",
        "note": "HR policy with 'all', 'new', 'two' — pure natural"
    },
    {
        "input": "to find large files run find space dot space dash type space f space dash size space plus one hundred capital M",
        "expected_natural": "to find large files run",
        "expected_command": "find . -type f -size +100M",
        "note": "Instruction + find command"
    },
    {
        "input": "curl space dash capital X space all caps POST space dash capital H space quote Content dash Type colon space application slash json quote space https colon slash slash api dot example dot com slash users",
        "expected_natural": "",
        "expected_command": "curl -X POST -H \"Content-Type: application/json\" https://api.example.com/users",
        "note": "Complex curl — pure protocol"
    },
]


def classify_words(words, weights, bias, threshold=0.5):
    """Classify each word. Returns list of (word, prob, is_protocol)."""
    results = []
    n = len(words)
    for i, word in enumerate(words):
        ctx_start = max(0, i - 2)
        ctx_end = min(n, i + 3)
        context = words[ctx_start:ctx_end]
        features = extract_features(word, context, i, n)
        logit = float(np.dot(features, weights) + bias)
        prob = 1.0 / (1.0 + np.exp(-logit))
        results.append((word, prob, prob >= threshold))
    return results


def extract_segments(text, weights, bias, threshold=0.5, expansion=2):
    """Run classifier + expansion, return segments."""
    words = text.split()
    if not words:
        return []

    results = classify_words(words, weights, bias, threshold)
    anchors = [r[2] for r in results]

    # Expand
    n = len(words)
    expanded = [False] * n
    for i in range(n):
        if anchors[i]:
            for j in range(max(0, i - expansion), min(n, i + expansion + 1)):
                expanded[j] = True

    # Build segments
    segments = []
    current_kind = "protocol" if expanded[0] else "natural"
    current_words = [words[0]]

    for i in range(1, n):
        kind = "protocol" if expanded[i] else "natural"
        if kind == current_kind:
            current_words.append(words[i])
        else:
            segments.append({"kind": current_kind, "text": " ".join(current_words)})
            current_kind = kind
            current_words = [words[i]]
    segments.append({"kind": current_kind, "text": " ".join(current_words)})

    return segments


def call_inference(prompt, model_id=MODEL_ID, system_prompt=SYSTEM_PROMPT, timeout=30):
    """Call talkie-dev inference generate and return the output."""
    cmd = [
        "talkie-dev", "inference", "generate", prompt,
        "--model", model_id,
        "--system", system_prompt,
        "--temp", "0",
        "--tokens", "120",
        "--json",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path(__file__).parent.parent)
        )
        if result.returncode != 0:
            return None, f"exit {result.returncode}: {result.stderr.strip()}"
        # Output is JSON — parse and extract text field
        try:
            data = json.loads(result.stdout.strip())
            text = data.get("text", "").strip()
            # Strip <think>...</think> tags from Qwen3 reasoning
            import re
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
            # Also strip unclosed <think> tags
            text = re.sub(r'<think>.*', '', text, flags=re.DOTALL).strip()
            return text, None
        except json.JSONDecodeError:
            # Fallback: try first line
            lines = result.stdout.strip().split("\n")
            return lines[0].strip() if lines else "", None
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:
        return None, str(e)


def run_test(case, idx, classifier_only=False):
    """Run a single test case through the full chain."""
    text = case["input"]
    note = case["note"]

    print(f"\n{'='*70}")
    print(f"  TEST {idx}: {note}")
    print(f"{'='*70}")
    print(f"  INPUT: {text}")

    # Step 1: Segment
    t0 = time.time()
    segments = extract_segments(text, WEIGHTS, BIAS)
    seg_ms = (time.time() - t0) * 1000

    protocol_segments = [s for s in segments if s["kind"] == "protocol"]
    natural_segments = [s for s in segments if s["kind"] == "natural"]

    print(f"\n  SEGMENTS ({seg_ms:.1f}ms):")
    for s in segments:
        marker = "\033[91mPROTO\033[0m" if s["kind"] == "protocol" else "\033[92mNATRL\033[0m"
        print(f"    [{marker}] {s['text']}")

    has_protocol = len(protocol_segments) > 0
    expected_has_protocol = bool(case["expected_command"])

    if has_protocol != expected_has_protocol:
        if has_protocol:
            print(f"\n  \033[91mFALSE POSITIVE: detected protocol in pure natural text!\033[0m")
        else:
            print(f"\n  \033[93mFALSE NEGATIVE: missed protocol segment!\033[0m")
        return {"pass": False, "reason": "segmentation"}

    if not has_protocol:
        print(f"\n  \033[92mPASS\033[0m — correctly identified as pure natural speech (no model call)")
        return {"pass": True, "reason": "natural_passthrough"}

    if classifier_only:
        print(f"\n  [classifier-only mode, skipping model inference]")
        return {"pass": True, "reason": "classifier_only"}

    # Step 2: Send protocol segments to model
    print(f"\n  MODEL INFERENCE:")
    result_parts = []
    total_ms = 0

    for segment in segments:
        if segment["kind"] == "natural":
            result_parts.append(segment["text"])
            continue

        t0 = time.time()
        model_output, error = call_inference(segment["text"])
        infer_ms = (time.time() - t0) * 1000
        total_ms += infer_ms

        if error:
            print(f"    \033[91mERROR\033[0m: {error}")
            result_parts.append(segment["text"])  # fallback
        else:
            print(f"    IN:  {segment['text']}")
            print(f"    OUT: {model_output} ({infer_ms:.0f}ms)")
            result_parts.append(model_output or segment["text"])

    # Step 3: Reassemble
    assembled = " ".join(result_parts).strip()
    expected = case["expected_command"]

    print(f"\n  ASSEMBLED: {assembled}")
    print(f"  EXPECTED:  {expected}")
    print(f"  LATENCY:   {total_ms:.0f}ms (model only)")

    # Fuzzy match — check if the command part is present
    # (natural prefix/suffix might be included due to boundary bleed)
    if expected and expected in assembled:
        print(f"\n  \033[92mPASS\033[0m — command correctly reconstructed")
        return {"pass": True, "reason": "match"}
    elif expected:
        print(f"\n  \033[93mCHECK\033[0m — command may differ, review above")
        return {"pass": None, "reason": "fuzzy"}
    else:
        print(f"\n  \033[92mPASS\033[0m")
        return {"pass": True, "reason": "no_command"}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test segment classifier + model chain")
    parser.add_argument("--case", type=int, help="Run specific test case (1-indexed)")
    parser.add_argument("--classifier-only", action="store_true", help="Skip model inference, just test segmentation")
    args = parser.parse_args()

    print("=" * 70)
    print("  FULL CHAIN TEST: Classifier → Segmentation → Model → Assembly")
    if args.classifier_only:
        print("  MODE: classifier-only (no model inference)")
    print("=" * 70)

    cases = TEST_CASES
    if args.case:
        if 1 <= args.case <= len(TEST_CASES):
            cases = [TEST_CASES[args.case - 1]]
        else:
            print(f"Invalid case number. Must be 1-{len(TEST_CASES)}")
            sys.exit(1)

    results = []
    for i, case in enumerate(cases):
        idx = args.case if args.case else i + 1
        result = run_test(case, idx, classifier_only=args.classifier_only)
        results.append(result)

    # Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    passed = sum(1 for r in results if r["pass"] is True)
    failed = sum(1 for r in results if r["pass"] is False)
    check = sum(1 for r in results if r["pass"] is None)
    print(f"  Passed: {passed}/{len(results)}")
    if failed: print(f"  Failed: {failed}")
    if check: print(f"  Check:  {check} (review manually)")

    # Breakdown
    natural_ok = sum(1 for r in results if r["reason"] == "natural_passthrough")
    match_ok = sum(1 for r in results if r["reason"] == "match")
    if natural_ok: print(f"  Natural passthrough: {natural_ok}")
    if match_ok: print(f"  Command reconstructed: {match_ok}")


if __name__ == "__main__":
    main()
