"""Helpers for loading and validating packaged version 1 schemas."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


CONFIGURATION_SCHEMA_FILE = "comparison-configuration-v1.0.schema.json"
RESULTS_SCHEMA_FILE = "comparison-results-v1.0.schema.json"
SCHEMA_PACKAGE = "adviso_compare.schemas"

JsonObject = dict[str, Any]


def load_packaged_schema(filename: str) -> JsonObject:
    """Load a schema through the installed-package resource interface."""
    resource = files(SCHEMA_PACKAGE).joinpath(filename)
    return json.loads(resource.read_text(encoding="utf-8"))


def schema_registry(*schemas: JsonObject) -> Registry:
    """Return a registry containing each schema under its canonical identifier."""
    registry = Registry()
    for schema in schemas:
        registry = registry.with_resource(
            schema["$id"], Resource.from_contents(schema)
        )
    return registry


def configuration_validator() -> Draft202012Validator:
    """Return the version 1 comparison-configuration validator."""
    schema = load_packaged_schema(CONFIGURATION_SCHEMA_FILE)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def results_validator() -> Draft202012Validator:
    """Return the version 1 canonical-results validator with references resolved."""
    configuration = load_packaged_schema(CONFIGURATION_SCHEMA_FILE)
    results = load_packaged_schema(RESULTS_SCHEMA_FILE)
    registry = schema_registry(configuration, results)
    return Draft202012Validator(
        results,
        registry=registry,
        format_checker=FormatChecker(),
    )

