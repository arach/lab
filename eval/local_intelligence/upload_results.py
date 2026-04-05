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
    parser = argparse.ArgumentParser(description="Upload eval result files back to the Hugging Face repo.")
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--repo-type", default="model")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--path-in-repo", required=True)
    parser.add_argument("--token")
    parser.add_argument("--commit-message", default="Upload local-intelligence eval results")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        raise SystemExit(f"Missing source dir: {source_dir}")

    api = HfApi(token=resolve_token(args.token))
    api.upload_folder(
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        folder_path=str(source_dir),
        path_in_repo=args.path_in_repo,
        commit_message=args.commit_message,
    )
    print(f"Uploaded {source_dir} -> {args.repo_id}/{args.path_in_repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
