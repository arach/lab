from __future__ import annotations

import time

from .base import BaseProvider, ProviderResponse


class MLXProvider(BaseProvider):
    name = "mlx"

    def __init__(self, model_name: str | None, adapter_path: str | None = None, max_tokens: int = 400):
        if not model_name:
            raise ValueError("MLX provider requires --model.")
        from mlx_lm import generate, load  # Imported lazily.
        from mlx_lm.sample_utils import make_sampler

        self._generate = generate
        self._sampler = make_sampler(temp=0.0)
        self._model, self._tokenizer = load(model_name, adapter_path=adapter_path)
        self.model_name = model_name
        self.adapter_path = adapter_path
        self.max_tokens = max_tokens

    def generate(self, card: dict, messages: list[dict[str, str]], prompt_text: str) -> ProviderResponse:
        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        start = time.perf_counter()
        raw_text = self._generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=self.max_tokens,
            verbose=False,
            sampler=self._sampler,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        return ProviderResponse(
            raw_text=raw_text.strip(),
            latency_ms=latency_ms,
            metadata={"model": self.model_name, "adapter": self.adapter_path},
        )
