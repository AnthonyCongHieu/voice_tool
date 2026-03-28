"""Utility helpers for the voice pause normalizer."""

from __future__ import annotations

import json
import os
from typing import Dict


def load_punct_map(path_or_default: str, default_map: Dict[str, list[str]]) -> Dict[str, list[str]]:
    """Load punctuation mapping from JSON/YAML file or return default."""
    if path_or_default == "default" or not path_or_default:
        return default_map
    if not os.path.exists(path_or_default):
        raise FileNotFoundError(path_or_default)
    with open(path_or_default, "r", encoding="utf-8") as f:
        if path_or_default.endswith('.json'):
            return json.load(f)
        import yaml  # type: ignore

        return yaml.safe_load(f)
