from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResponse:
    raw_text: str
    latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseProvider:
    name = "base"

    def generate(self, card: dict, messages: list[dict[str, str]], prompt_text: str) -> ProviderResponse:
        raise NotImplementedError
