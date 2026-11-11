"""Helpers for loading and validating packaged version 1 schemas."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


CONFIGURATION_SCHEMA_FILE = "comparison-configuration-v1.0.schema.json"
RESULTS_SCHEMA_FILE = "comparison-results-v1.0.schema.json"
SCHEMA_PACKAGE = "adviso_compare.schemas"

JsonObject = dict[str, Any]


def load_packaged_schema(filename: str) -> JsonObject:
    """Load a schema through the installed-package resource interface."""
    resource = files(SCHEMA_PACKAGE).joinpath(filename)
    return json.loads(resource.read_text(encoding="utf-8"))


def configuration_validator() -> Draft202012Validator:
    """Return the version 1 comparison-configuration validator."""
    schema = load_packaged_schema(CONFIGURATION_SCHEMA_FILE)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def results_validator() -> Draft202012Validator:
    """Return the standalone version 1 canonical-results validator."""
    schema = load_packaged_schema(RESULTS_SCHEMA_FILE)
    return Draft202012Validator(schema, format_checker=FormatChecker())
