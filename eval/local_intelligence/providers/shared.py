from __future__ import annotations

import json
import os
from pathlib import Path
import random
import time
import urllib.error
import urllib.request
from typing import Iterable


ENV_CANDIDATES = (
    Path.cwd() / ".env.local",
    Path.cwd() / ".env",
    Path.home() / ".env.local",
)


def load_token(token_keys: Iterable[str], env_candidates: Iterable[Path] = ENV_CANDIDATES) -> str | None:
    for key in token_keys:
        value = os.environ.get(key)
        if value:
            return value

    wanted_keys = set(token_keys)
    for env_path in env_candidates:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in wanted_keys and value:
                return value
    return None


def post_json(
    url: str,
    body: dict,
    headers: dict[str, str],
    timeout_seconds: int,
    *,
    max_attempts: int = 4,
    base_backoff_seconds: float = 1.5,
) -> tuple[dict, float]:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            latency_ms = (time.perf_counter() - start) * 1000
            return payload, latency_ms
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt == max_attempts:
                raise
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt == max_attempts:
                raise
        sleep_seconds = base_backoff_seconds * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
        time.sleep(sleep_seconds)
    assert last_error is not None
    raise last_error


def extract_chat_content(payload: dict) -> str:
    return payload["choices"][0]["message"]["content"].strip()
