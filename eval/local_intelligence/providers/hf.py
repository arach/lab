from __future__ import annotations

from .base import BaseProvider, ProviderResponse
from .shared import extract_chat_content, load_token, post_json

_TOKEN_KEYS = [
    "HF_TOKEN",
    "HUGGINGFACE_TOKEN",
    "HUGGING_FACE_TOKEN",
    "HUGGING_FACE_HUB_TOKEN",
    "HF_API_TOKEN",
]


class HuggingFaceProvider(BaseProvider):
    name = "hf"

    def __init__(self, model_name: str | None, token: str | None = None, timeout_seconds: int = 90):
        if not model_name:
            raise ValueError("HF provider requires --model.")
        self.model_name = model_name
        self.token = token or load_token(_TOKEN_KEYS)
        self.timeout_seconds = timeout_seconds

    def generate(self, card: dict, messages: list[dict[str, str]], prompt_text: str) -> ProviderResponse:
        payload, latency_ms = post_json(
            "https://router.huggingface.co/v1/chat/completions",
            {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "stream": False,
            },
            {"Content-Type": "application/json", **({"Authorization": f"Bearer {self.token}"} if self.token else {})},
            self.timeout_seconds,
        )
        return ProviderResponse(
            raw_text=extract_chat_content(payload),
            latency_ms=latency_ms,
            metadata={"model": self.model_name},
        )
