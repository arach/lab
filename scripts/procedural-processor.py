#!/usr/bin/env python3
"""Compatibility wrapper for the canonical processor entry point."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import runpy

CANONICAL_PATH = Path(__file__).resolve().parents[1] / "processor" / "procedural.py"

spec = spec_from_file_location("training_lab_procedural", CANONICAL_PATH)
module = module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

for name in dir(module):
    if not name.startswith("__"):
        globals()[name] = getattr(module, name)

if __name__ == "__main__":
    runpy.run_path(str(CANONICAL_PATH), run_name="__main__")
