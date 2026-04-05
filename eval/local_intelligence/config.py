from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from repo_paths import EVAL_DIR  # noqa: E402

LOCAL_INTELLIGENCE_DIR = EVAL_DIR / "local_intelligence"
CARDS_PATH = LOCAL_INTELLIGENCE_DIR / "cards.json"
RESULTS_DIR = LOCAL_INTELLIGENCE_DIR / "results"
NOTEBOOK_PATH = LOCAL_INTELLIGENCE_DIR / "notebook.ipynb"
EXPORT_DIR = REPO_ROOT / "docs" / "evals" / "local-intelligence" / "v1"
JSONL_EXPORT_PATH = EXPORT_DIR / "hf_local_intelligence_eval_v1.jsonl"
MANIFEST_EXPORT_PATH = EXPORT_DIR / "hf_local_intelligence_eval_manifest_v1.json"

DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


@dataclass(frozen=True)
class EvalCard:
    payload: dict

    @property
    def id(self) -> str:
        return self.payload["id"]

    @property
    def tier(self) -> str:
        return self.payload["tier"]

    @property
    def title(self) -> str:
        return self.payload["title"]

    @property
    def test_input(self) -> dict:
        return self.payload["testCase"]["input"]

    @property
    def assertions(self) -> list[str]:
        return self.payload["testCase"]["assertions"]


def load_cards(cards_path: Path = CARDS_PATH) -> list[EvalCard]:
    data = json.loads(cards_path.read_text())
    return [EvalCard(item) for item in data]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
