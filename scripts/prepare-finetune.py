#!/usr/bin/env python3
"""Compatibility wrapper for the canonical finetune data converter."""

from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "training" / "converters" / "prepare-finetune.py"),
    run_name="__main__",
)
