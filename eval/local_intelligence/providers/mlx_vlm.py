from __future__ import annotations

import time

from .base import BaseProvider, ProviderResponse


class MLXVLMProvider(BaseProvider):
    name = "mlx_vlm"

    def __init__(self, model_name: str | None, max_tokens: int = 400):
        if not model_name:
            raise ValueError("MLX-VLM provider requires --model.")
        from mlx_vlm import generate, load  # Imported lazily.

        self._generate = generate
        self._model, self._processor = load(model_name)
        self.model_name = model_name
        self.max_tokens = max_tokens

    def generate(self, card: dict, messages: list[dict[str, str]], prompt_text: str) -> ProviderResponse:
        start = time.perf_counter()
        raw_text = self._generate(
            self._model,
            self._processor,
            prompt=prompt_text,
            max_tokens=self.max_tokens,
            verbose=False,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        return ProviderResponse(
            raw_text=str(raw_text).strip(),
            latency_ms=latency_ms,
            metadata={"model": self.model_name},
        )
