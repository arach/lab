from __future__ import annotations

import json
import subprocess
import time

from .base import BaseProvider, ProviderResponse


class AppleProvider(BaseProvider):
    name = "apple"

    def __init__(self, command: str | None, timeout_seconds: int = 90):
        if not command:
            raise ValueError("Apple provider requires --apple-command to invoke a FoundationModels bridge.")
        self.command = command
        self.timeout_seconds = timeout_seconds

    def generate(self, card: dict, messages: list[dict[str, str]], prompt_text: str) -> ProviderResponse:
        payload = {
            "card_id": card["id"],
            "messages": messages,
            "prompt_text": prompt_text,
            "test_input": card["testCase"]["input"],
        }
        start = time.perf_counter()
        proc = subprocess.run(
            self.command,
            input=json.dumps(payload),
            text=True,
            shell=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=True,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        return ProviderResponse(
            raw_text=proc.stdout.strip(),
            latency_ms=latency_ms,
            metadata={"stderr": proc.stderr.strip()},
        )
