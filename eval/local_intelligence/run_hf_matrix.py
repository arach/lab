#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_MODELS = [
    "google/gemma-4-E4B-it",
    "nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1",
    "Qwen/Qwen3.5-4B-Instruct-2507",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local-intelligence eval pack across a small HF model matrix.")
    parser.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--tier")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--dtype", default="auto")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--attn-implementation")
    parser.add_argument("--results-dir")
    parser.add_argument("--keep-going", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script = Path(__file__).with_name("run_hf_transformers.py")
    failures = 0

    for model in args.models:
        cmd = [
            sys.executable,
            str(script),
            "--model",
            model,
            "--output-prefix",
            "hf-matrix",
            "--max-new-tokens",
            str(args.max_new_tokens),
            "--dtype",
            args.dtype,
            "--device-map",
            args.device_map,
        ]
        if args.limit is not None:
            cmd += ["--limit", str(args.limit)]
        if args.tier:
            cmd += ["--tier", args.tier]
        if args.attn_implementation:
            cmd += ["--attn-implementation", args.attn_implementation]
        if args.trust_remote_code:
            cmd.append("--trust-remote-code")
        if args.results_dir:
            result_name = model.lower().replace("/", "-").replace(".", "-") + ".json"
            cmd += ["--output", str(Path(args.results_dir) / result_name)]

        print(f"\n=== Running {model} ===")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            failures += 1
            if not args.keep_going:
                return result.returncode

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
