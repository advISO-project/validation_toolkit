"""Versioned machine-readable schemas distributed with adviso-compare."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


_SCHEMA_RESOURCES = (
    ("configuration", "1.0", "comparison-configuration-v1.0.schema.json"),
    ("results", "1.0", "comparison-results-v1.0.schema.json"),
)


def load_schema(family: str, version: str) -> dict[str, Any]:
    """Load a supported schema by family and version from local resources."""
    for known_family, known_version, filename in _SCHEMA_RESOURCES:
        if (family, version) == (known_family, known_version):
            resource = files("adviso_compare.schemas").joinpath(filename)
            document = json.loads(resource.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("packaged schema root must be an object")
            return document
    raise ValueError("unsupported schema family or version")
