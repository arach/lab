from __future__ import annotations

from .base import BaseProvider, ProviderResponse
from .shared import extract_chat_content, load_token, post_json

_TOKEN_KEYS = [
    "GITHUB_TOKEN",
    "GH_TOKEN",
]


class GitHubModelsProvider(BaseProvider):
    name = "github_models"

    def __init__(self, model_name: str | None, token: str | None = None, timeout_seconds: int = 90):
        if not model_name:
            raise ValueError("GitHub Models provider requires --model.")
        self.model_name = model_name
        self.token = token or load_token(_TOKEN_KEYS)
        if not self.token:
            raise ValueError("No GitHub token found. Set GITHUB_TOKEN/GH_TOKEN or add one to ~/.env.local.")
        self.timeout_seconds = timeout_seconds

    def generate(self, card: dict, messages: list[dict[str, str]], prompt_text: str) -> ProviderResponse:
        payload, latency_ms = post_json(
            "https://models.github.ai/inference/chat/completions",
            {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0,
                "stream": False,
            },
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2026-03-10",
                "Content-Type": "application/json",
            },
            self.timeout_seconds,
        )
        return ProviderResponse(
            raw_text=extract_chat_content(payload),
            latency_ms=latency_ms,
            metadata={"model": self.model_name},
        )
