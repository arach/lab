#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import os
import textwrap
from pathlib import Path

from huggingface_hub import HfApi, run_job

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
    parser = argparse.ArgumentParser(description="Launch the news summarization eval as a Hugging Face Job.")
    parser.add_argument("--source-repo-id", default="arach/training-lab")
    parser.add_argument("--source-repo-type", default="model")
    parser.add_argument("--results-repo-id")
    parser.add_argument("--results-repo-type", default="model")
    parser.add_argument("--results-path-prefix", default="eval/news_summarization/results/jobs")
    parser.add_argument("--image", default="pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel")
    parser.add_argument("--flavor", default="a10g-small")
    parser.add_argument("--timeout", default="2h")
    parser.add_argument("--token")
    parser.add_argument("--namespace")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--prompt-style", default="simple", choices=["simple", "helpful", "detailed"])
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--max-new-tokens", type=int, default=220)
    parser.add_argument("--max-article-chars", type=int, default=8000)
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--disable-rouge", action="store_true")
    parser.add_argument("--disable-bertscore", action="store_true")
    parser.add_argument("--bertscore-model", default="roberta-large")
    parser.add_argument("--sync-code", action="store_true")
    return parser.parse_args()


def sync_news_eval_to_hf(source_repo_id: str, source_repo_type: str, token: str) -> None:
    api = HfApi(token=token)
    root = Path(__file__).resolve().parents[2]
    eval_dir = Path(__file__).resolve().parent
    for rel in [
        "run_news_summary_pilot.py",
        "run_hf_transformers.py",
        "launch_hf_job.py",
        "README.md",
        "COLAB_QUICKSTART.md",
        "requirements.txt",
        "notebook.ipynb",
    ]:
        api.upload_file(
            repo_id=source_repo_id,
            repo_type=source_repo_type,
            path_or_fileobj=str(eval_dir / rel),
            path_in_repo=f"eval/news_summarization/{rel}",
            commit_message="Sync news summarization eval harness",
        )


def encode_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> int:
    args = parse_args()
    token = resolve_token(args.token)
    source_repo_id = args.source_repo_id
    source_repo_type = args.source_repo_type
    results_repo_id = args.results_repo_id or source_repo_id
    results_repo_type = args.results_repo_type

    if args.sync_code:
        sync_news_eval_to_hf(source_repo_id, source_repo_type, token)

    eval_dir = Path(__file__).resolve().parent
    embedded_files = {
        "eval/news_summarization/run_news_summary_pilot.py": encode_file(eval_dir / "run_news_summary_pilot.py"),
        "eval/news_summarization/run_hf_transformers.py": encode_file(eval_dir / "run_hf_transformers.py"),
    }
    embedded_payload = repr(embedded_files)

    flags = [
        f"--model {args.model}",
        f"--limit {args.limit}",
        f"--seed {args.seed}",
        f"--prompt-style {args.prompt_style}",
        f"--dtype {args.dtype}",
        f"--device-map {args.device_map}",
        f"--max-new-tokens {args.max_new_tokens}",
        f"--max-article-chars {args.max_article_chars}",
        "--save-every 1",
        "--verbose",
    ]
    if args.trust_remote_code:
        flags.append("--trust-remote-code")
    if args.disable_rouge:
        flags.append("--disable-rouge")
    if args.disable_bertscore:
        flags.append("--disable-bertscore")
    else:
        flags.append(f"--bertscore-model {args.bertscore_model}")

    job_script = textwrap.dedent(
        f"""
        set -euo pipefail
        python -m pip install -q huggingface_hub transformers accelerate sentencepiece rouge-score bert-score
        python - <<'PY'
        import base64
        from pathlib import Path

        root = Path('/workspace/training-lab')
        for relative_path, encoded in {embedded_payload}.items():
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(encoded.encode('ascii')))
        PY
        cd /workspace/training-lab
        mkdir -p {args.results_path_prefix}/$JOB_ID
        python eval/news_summarization/run_hf_transformers.py {' '.join(flags)} --output {args.results_path_prefix}/$JOB_ID/results.json
        python - <<'PY'
        import os
        from huggingface_hub import HfApi
        api = HfApi(token=os.environ['HF_TOKEN'])
        job_id = os.environ['JOB_ID']
        folder_path = f"{args.results_path_prefix}/" + job_id
        api.upload_folder(
            repo_id='{results_repo_id}',
            repo_type='{results_repo_type}',
            folder_path=folder_path,
            path_in_repo=folder_path,
            commit_message=f'Upload news summarization eval results for {{job_id}}',
        )
        PY
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
