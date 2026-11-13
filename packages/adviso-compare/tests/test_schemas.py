"""Baseline verification of the authoritative version 1 schemas."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry

from adviso_compare.schemas import load_schema
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
    ids=[
        "configuration", "results",
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
def test_representative_documents_validate_independently_with_format_assertion(
    status: str,
) -> None:
    """Each format validates without registering the other schema."""
    configuration = minimal_configuration()
    result = minimal_result(status=status)

    assert configuration["schema_version"] == "1.0"
    assert result["schema_version"] == "1.0"
    assert set(result) == {
        "schema_version", "run", "phases", "software", "runtime", "inputs",
        "record_key_fields", "comparison_configuration_digest", "summary",
        "exclusions", "findings",
    }
    for filename, document in (
        (CONFIGURATION_SCHEMA_FILE, configuration),
        (RESULTS_SCHEMA_FILE, result),
    ):
        schema = load_packaged_schema(filename)
        assert all(reference.startswith("#") for reference in _references(schema))
        Draft202012Validator(
            schema, registry=Registry(), format_checker=FormatChecker()
        ).validate(document)
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


def _references(value: Any) -> list[str]:
    """Collect schema references to check that validation is self-contained."""
    if isinstance(value, list):
        return [reference for item in value for reference in _references(item)]
    if isinstance(value, dict):
        return [
            item
            for key, item in value.items()
            if key in {"$ref", "$dynamicRef"}
        ] + [
            reference
            for item in value.values()
            for reference in _references(item)
        ]
    return []


@pytest.mark.parametrize(
    ("family", "filename"),
    [
        ("configuration", CONFIGURATION_SCHEMA_FILE),
        ("results", RESULTS_SCHEMA_FILE),
    ],
    ids=[
        "configuration-family", "results-family",
    ],
)
def test_schema_lookup_selects_the_document_family_and_version(
    family: str, filename: str,
) -> None:
    """Equal version strings select different schemas in different families."""
    assert load_schema(family, "1.0") == load_packaged_schema(filename)


@pytest.mark.parametrize(
    ("family", "version"),
    [("configuration", "2.0"), ("results", "2.0"), ("unknown", "1.0")],
    ids=[
        "unknown-configuration-version", "unknown-results-version",
        "unknown-family",
    ],
)
def test_schema_lookup_rejects_unknown_families_and_versions(
    family: str, version: str,
) -> None:
    """Unrecognized selectors never become filenames or network references."""
    with pytest.raises(ValueError):
        load_schema(family, version)


@pytest.mark.parametrize("family", ["configuration", "results"])
@pytest.mark.parametrize(
    'version', [None, "2.0", 1.0, ""],
    ids=[
        "missing-version", "unsupported-version", "numeric-version",
        "empty-version",
    ],
)
def test_each_document_requires_its_own_supported_root_version(
    family: str, version: object,
) -> None:
    """The format discriminator is required and has its specified string value."""
    if family == "configuration":
        document = minimal_configuration()
        validator = configuration_validator()
    else:
        document = minimal_result()
        validator = results_validator()
    if version is None:
        del document["schema_version"]
    else:
        document["schema_version"] = version

    assert not validator.is_valid(document)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda document: document.pop("comparison_configuration_digest"),
        lambda document: document.update(unexpected={}),
        lambda document: document["comparison_configuration_digest"].pop(
            "algorithm"
        ),
        lambda document: document["comparison_configuration_digest"].pop("value"),
        lambda document: document["comparison_configuration_digest"].update(
            algorithm="sha512"
        ),
        lambda document: document["comparison_configuration_digest"].update(
            unexpected="unused"
        ),
    ],
    ids=[
        "missing-digest", "unknown-root-property", "missing-algorithm",
        "missing-value", "unsupported-algorithm", "unknown-digest-property",
    ],
)
def test_configuration_digest_has_exact_required_properties(mutation: Any) -> None:
    """A results document records a closed, complete SHA-256 digest object."""
    document = minimal_result()
    mutation(document)

    assert not results_validator().is_valid(document)


@pytest.mark.parametrize(
    ("digest_field", "value"),
    [
        pytest.param("configuration", "", id="empty"),
        pytest.param("configuration", "0" * 63, id="short"),
        pytest.param("configuration", "0" * 65, id="long"),
        pytest.param("configuration", "A" * 64, id="uppercase"),
        pytest.param("configuration", "0" * 64 + "\n", id="trailing-newline"),
        pytest.param("configuration", 0, id="not-text"),
        pytest.param("input", "A" * 64, id="input-digest-rejection"),
    ],
)
def test_sha256_digests_require_exact_lowercase_hexadecimal_text(
    digest_field: str, value: object,
) -> None:
    """Exercise shared digest constraints and their use in input provenance."""
    document = minimal_result()
    digest = (
        document["comparison_configuration_digest"]
        if digest_field == "configuration"
        else document["inputs"]["reference"]["digest"]
    )
    digest["value"] = value

    assert not results_validator().is_valid(document)
