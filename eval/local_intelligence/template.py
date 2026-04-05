from __future__ import annotations

import json
import re
from typing import Any


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True)


def render_template(template: str, values: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return _stringify(values.get(key, ""))

    return re.sub(r"\{\{\s*([^}]+)\s*\}\}", replace, template)


def build_messages(card: dict, test_input: dict[str, Any]) -> list[dict[str, str]]:
    prompt = card["prompt"]
    return [
        {"role": "system", "content": prompt["system"]},
        {"role": "user", "content": render_template(prompt["user"], test_input)},
    ]


def build_prompt_text(card: dict, test_input: dict[str, Any]) -> str:
    prompt = card["prompt"]
    user_prompt = render_template(prompt["user"], test_input)
    return (
        f"TASK:\n{prompt['task']}\n\n"
        f"SYSTEM:\n{prompt['system']}\n\n"
        f"USER:\n{user_prompt}\n"
    )
