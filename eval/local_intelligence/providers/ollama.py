from __future__ import annotations

import json
import time
import urllib.request

from .base import BaseProvider, ProviderResponse


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self, base_url: str, model_name: str | None, timeout_seconds: int = 90):
        if not model_name:
            raise ValueError("Ollama provider requires --model.")
        self.url = base_url.rstrip("/") + "/api/generate"
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def generate(self, card: dict, messages: list[dict[str, str]], prompt_text: str) -> ProviderResponse:
        body = {
            "model": self.model_name,
            "prompt": prompt_text,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        req = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        latency_ms = (time.perf_counter() - start) * 1000
        return ProviderResponse(
            raw_text=payload.get("response", "").strip(),
            latency_ms=latency_ms,
            metadata={"model": self.model_name},
        )
