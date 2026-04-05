from __future__ import annotations

import json
from pathlib import Path

from .apple import AppleProvider
from .base import BaseProvider, ProviderResponse
from .github_models import GitHubModelsProvider
from .hf import HuggingFaceProvider
from .mlx import MLXProvider
from .mlx_vlm import MLXVLMProvider
from .nous import NousProvider
from .ollama import OllamaProvider
from .openrouter import OpenRouterProvider


class ReplayProvider(BaseProvider):
    name = "replay"

    def __init__(self, replay_path: Path):
        self._responses: dict[str, dict] = {}
        for line in replay_path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            self._responses[row["card_id"]] = row

    def generate(self, card: dict, messages: list[dict[str, str]], prompt_text: str) -> ProviderResponse:
        row = self._responses[card["id"]]
        return ProviderResponse(
            raw_text=row["raw_text"],
            latency_ms=float(row.get("latency_ms", 0.0)),
            metadata={"source": "replay"},
        )


def create_provider(args) -> BaseProvider:
    if args.provider == "replay":
        return ReplayProvider(Path(args.replay_file))
    if args.provider == "apple":
        return AppleProvider(command=args.apple_command, timeout_seconds=args.timeout)
    if args.provider == "mlx":
        return MLXProvider(model_name=args.model, adapter_path=args.adapter, max_tokens=args.max_tokens)
    if args.provider == "mlx_vlm":
        return MLXVLMProvider(model_name=args.model, max_tokens=args.max_tokens)
    if args.provider == "ollama":
        return OllamaProvider(base_url=args.ollama_url, model_name=args.model, timeout_seconds=args.timeout)
    if args.provider == "openrouter":
        return OpenRouterProvider(model_name=args.model, timeout_seconds=args.timeout)
    if args.provider == "nous":
        return NousProvider(model_name=args.model, timeout_seconds=args.timeout)
    if args.provider == "hf":
        return HuggingFaceProvider(model_name=args.model, token=args.hf_token, timeout_seconds=args.timeout)
    if args.provider == "github_models":
        return GitHubModelsProvider(model_name=args.model, timeout_seconds=args.timeout)
    raise ValueError(f"Unsupported provider: {args.provider}")
