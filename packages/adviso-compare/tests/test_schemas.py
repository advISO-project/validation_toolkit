"""Baseline verification of the authoritative version 1 schemas."""

from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from tests.support.documents import minimal_configuration, minimal_result
from tests.support.schemas import (
    CONFIGURATION_SCHEMA_FILE,
    RESULTS_SCHEMA_FILE,
    configuration_validator,
    load_packaged_schema,
    results_validator,
)


CONFIGURATION_SCHEMA_ID = (
    "https://adviso-project.github.io/validation_toolkit/schemas/"
    "comparison-configuration-v1.0.schema.json"
)
RESULTS_SCHEMA_ID = (
    "https://adviso-project.github.io/validation_toolkit/schemas/"
    "comparison-results-v1.0.schema.json"
)


@pytest.mark.parametrize(
    ("filename", "canonical_id"),
    [
        (CONFIGURATION_SCHEMA_FILE, CONFIGURATION_SCHEMA_ID),
        (RESULTS_SCHEMA_FILE, RESULTS_SCHEMA_ID),
    ],
)
def test_authoritative_schemas_are_packaged_valid_draft_2020_12_documents(
    filename: str,
    canonical_id: str,
) -> None:
    """The source-of-truth schemas are loadable resources with stable identities."""
    schema = load_packaged_schema(filename)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == canonical_id
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("status", ["complete", "incomplete"])
def test_representative_documents_validate_with_reference_and_format_assertion(
    status: str,
) -> None:
    """Representative documents exercise both schemas and their external reference."""
    configuration = minimal_configuration()
    result = minimal_result(status=status)

    configuration_validator().validate(configuration)
    results_validator().validate(result)


def test_results_validation_asserts_recognised_formats() -> None:
    """A lexically plausible but impossible RFC 3339 date-time is invalid."""
    result = minimal_result()
    invalid_result = deepcopy(result)
    invalid_result["run"]["completed_at"] = "2026-13-40T03:04:05Z"

    errors = list(results_validator().iter_errors(invalid_result))

    assert errors
    assert any(error.validator == "format" for error in errors)


def test_synthetic_document_builders_are_deterministic_and_independent() -> None:
    """Generated documents are reproducible without sharing mutable state."""
    first_configuration = minimal_configuration()
    second_configuration = minimal_configuration()
    first_result = minimal_result(status="incomplete")
    second_result = minimal_result(status="incomplete")

    assert first_configuration == second_configuration
    assert first_result == second_result

    first_configuration["metadata"]["id"] = "changed"
    first_result["run"]["status"] = "changed"

    assert second_configuration["metadata"]["id"] == (
        "org.example.synthetic-exact-comparison"
    )
    assert second_result["run"]["status"] == "incomplete"
