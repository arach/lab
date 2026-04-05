#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import textwrap
from pathlib import Path

from huggingface_hub import run_job

TOKEN_KEYS = [
    "HF_TOKEN",
    "HUGGINGFACE_TOKEN",
    "HUGGING_FACE_TOKEN",
    "HUGGING_FACE_HUB_TOKEN",
    "HF_API_TOKEN",
]

ENV_CANDIDATES = [
    Path.cwd() / ".env.local",
    Path.cwd() / ".env",
    Path.home() / ".env.local",
]


def load_token_from_env_files() -> str | None:
    for env_path in ENV_CANDIDATES:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in TOKEN_KEYS and value:
                return value
    return None


def resolve_token(cli_token: str | None) -> str:
    if cli_token:
        return cli_token
    for key in TOKEN_KEYS:
        value = os.environ.get(key)
        if value:
            return value
    env_file_token = load_token_from_env_files()
    if env_file_token:
        return env_file_token
    raise SystemExit("No Hugging Face token found. Export one or pass --token.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the local-intelligence bakeoff as a Hugging Face Job.")
    parser.add_argument("--source-repo-id", default="arach/training-lab")
    parser.add_argument("--source-repo-type", default="model")
    parser.add_argument("--results-repo-id")
    parser.add_argument("--results-repo-type", default="model")
    parser.add_argument("--results-path-prefix", default="eval/local_intelligence/results/jobs")
    parser.add_argument("--image", default="pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel")
    parser.add_argument("--flavor", default="a10g-small")
    parser.add_argument("--timeout", default="2h")
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--tier")
    parser.add_argument("--token")
    parser.add_argument("--namespace")
    parser.add_argument("--sync-code", action="store_true")
    parser.add_argument("--include-readme", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--attn-implementation")
    parser.add_argument("--dtype", default="auto")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--models", nargs="*", default=[
        "google/gemma-4-E4B-it",
        "nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1",
        "Qwen/Qwen3.5-4B-Instruct-2507",
    ])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = resolve_token(args.token)
    source_repo_id = args.source_repo_id
    source_repo_type = args.source_repo_type
    results_repo_id = args.results_repo_id or source_repo_id
    results_repo_type = args.results_repo_type
    models = " ".join(f'"{model}"' for model in args.models)
    root = Path(__file__).resolve().parent

    if args.sync_code:
        sync_script = root / "sync_to_hf.py"
        cmd = [
            os.sys.executable,
            str(sync_script),
            "--repo-id",
            source_repo_id,
            "--repo-type",
            source_repo_type,
            "--token",
            token,
        ]
        if args.include_readme:
            cmd.append("--include-readme")
        subprocess.run(cmd, check=True)

    matrix_flags = [
        f"--limit {args.limit}",
        f"--dtype {args.dtype}",
        f"--device-map {args.device_map}",
        "--keep-going",
    ]
    if args.tier:
        matrix_flags.append(f"--tier {args.tier}")
    if args.trust_remote_code:
        matrix_flags.append("--trust-remote-code")
    if args.attn_implementation:
        matrix_flags.append(f"--attn-implementation {args.attn_implementation}")

    job_script = textwrap.dedent(
        f"""
        set -euo pipefail
        python - <<'PY'
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id='{source_repo_id}',
            repo_type='{source_repo_type}',
            local_dir='/workspace/training-lab',
            token='{token}',
            allow_patterns=['repo_paths.py', 'eval/local_intelligence/*'],
        )
        PY
        cd /workspace/training-lab
        mkdir -p {args.results_path_prefix}/$JOB_ID
        python eval/local_intelligence/run_hf_matrix.py --models {models} {' '.join(matrix_flags)} --results-dir {args.results_path_prefix}/$JOB_ID
        python eval/local_intelligence/upload_results.py \
          --repo-id {results_repo_id} \
          --repo-type {results_repo_type} \
          --source-dir {args.results_path_prefix}/$JOB_ID \
          --path-in-repo {args.results_path_prefix}/$JOB_ID \
          --token "$HF_TOKEN" \
          --commit-message "Upload local-intelligence eval results for $JOB_ID"
        """
    ).strip()

    job = run_job(
        image=args.image,
        command=["bash", "-lc", job_script],
        flavor=args.flavor,
        timeout=args.timeout,
        namespace=args.namespace,
        token=token,
        secrets={"HF_TOKEN": token},
    )
    print(f"Job launched: {job.url}")
    print(f"Job id: {job.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
