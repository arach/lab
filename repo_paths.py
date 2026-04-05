from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

EVAL_DIR = REPO_ROOT / "eval"
LOCAL_INTELLIGENCE_EVAL_DIR = EVAL_DIR / "local_intelligence"
PIPELINE_DIR = REPO_ROOT / "pipeline"
PROCESSOR_DIR = REPO_ROOT / "processor"
SCRIPTS_DIR = REPO_ROOT / "scripts"
TRAINING_DIR = REPO_ROOT / "training"
TRAINING_DATA_DIR = TRAINING_DIR / "data"
TRAINING_CONVERTERS_DIR = TRAINING_DIR / "converters"
TRAINING_FINETUNE_DIR = TRAINING_DIR / "finetune"


def first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]
