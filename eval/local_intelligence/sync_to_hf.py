#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import HfApi


TOKEN_KEYS = [
    "HF_TOKEN",
    "HUGGINGFACE_TOKEN",
    "HUGGING_FACE_TOKEN",
    "HUGGING_FACE_HUB_TOKEN",
    "HF_API_TOKEN",
]


def resolve_token(cli_token: str | None) -> str:
    if cli_token:
        return cli_token
    for key in TOKEN_KEYS:
        value = os.environ.get(key)
        if value:
            return value
    raise SystemExit("No Hugging Face token found in environment.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload the local-intelligence eval harness to a Hugging Face repo.")
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--repo-type", default="model")
    parser.add_argument("--token")
    parser.add_argument("--path-in-repo", default="eval/local_intelligence")
    parser.add_argument("--include-readme", action="store_true")
    parser.add_argument("--commit-message", default="Sync local-intelligence eval harness")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    eval_dir = Path(__file__).resolve().parent
    api = HfApi(token=resolve_token(args.token))

    api.upload_folder(
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        folder_path=str(eval_dir),
        path_in_repo=args.path_in_repo,
        allow_patterns=[
            "*.py",
            "*.json",
            "*.jsonl",
            "*.md",
            "*.ipynb",
        ],
        ignore_patterns=[
            "__pycache__/*",
            "results/*",
        ],
        commit_message=args.commit_message,
    )

    api.upload_file(
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        path_or_fileobj=str(root / "repo_paths.py"),
        path_in_repo="repo_paths.py",
        commit_message=args.commit_message,
    )

    if args.include_readme:
        api.upload_file(
            repo_id=args.repo_id,
            repo_type=args.repo_type,
            path_or_fileobj=str(root / "README.md"),
            path_in_repo="README.md",
            commit_message=args.commit_message,
        )

    print(f"Synced eval harness to {args.repo_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
