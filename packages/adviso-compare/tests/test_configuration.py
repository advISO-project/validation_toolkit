"""Behavioural tests for custom comparison-configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest
import yaml

from adviso_compare.application import prepare_comparison
from adviso_compare.configuration import (
    ConfigurationError,
    load_comparison_configuration,
)
from adviso_compare.inputs import InputSide, ParsedDataset
from adviso_compare.invocation import ComparisonInvocation
from tests.support.documents import JsonObject, minimal_configuration


ConfigurationMutation = Callable[[JsonObject], None]


def _write_yaml(path: Path, document: JsonObject) -> Path:
    """Write a controlled YAML configuration and return its path."""
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def _load_document(tmp_path: Path, document: JsonObject):
    """Load one mapping through the production YAML boundary."""
    return load_comparison_configuration(_write_yaml(tmp_path / "rules.yaml", document))


def _add_mapping_field(document: JsonObject) -> JsonObject:
    """Return a configuration containing one mapped string field."""
    field = document["fields"]["definitions"]["measured_value"]
    field["logical_type"] = "string"
    field["comparator"] = {"name": "typed_exact"}
    field["value_mapping"] = {
        "reference": [
            {
                "from": {"category": "string", "value": "positive"},
                "to": {"category": "string", "value": "detected"},
            }
        ]
    }
    return document


def _add_collection_field(document: JsonObject) -> JsonObject:
    """Return a configuration containing one set-valued field."""
    field = document["fields"]["definitions"]["measured_value"]
    field["logical_type"] = {
        "collection_type": "set",
        "element_type": "string",
        "element_comparator": {"name": "typed_exact"},
    }
    field["comparator"] = {"name": "set_exact"}
    field["collection_representation"] = {
        "query": {
            "format": "delimited_text",
            "delimiter": "/",
            "element_normalisation": [{"operation": "case_fold"}],
            "element_mapping": [
                {
                    "from": {"category": "string", "value": "wild_type"},
                    "to": {"category": "string", "value": "WT"},
                }
            ],
        }
    }
    return document


def test_valid_configuration_resolves_immutable_defaults_without_altering_document(
    tmp_path: Path,
) -> None:
    """Omitted processing state resolves without adding embedded placeholders."""
    original = minimal_configuration()

    configuration = _load_document(tmp_path, original)

    assert configuration.schema_version == "1.0"
    assert configuration.metadata.id == "org.example.synthetic-exact-comparison"
    assert configuration.record_key == ("record_id",)
    assert configuration.in_scope == ("record_id", "measured_value")
    measured = configuration.field("measured_value")
    assert measured.review_priority == "normal"
    assert measured.source_normalisation.reference == ()
    assert measured.source_normalisation.query == ()
    assert measured.value_mapping.reference == ()
    assert measured.value_mapping.query == ()
    assert measured.typed_normalisation == ()
    assert measured.null_policy.missing_tokens.reference == ()
    assert measured.null_policy.missing_tokens.query == ()
    assert "review_priority" not in configuration.document["fields"]["definitions"][
        "measured_value"
    ]

    returned_document = configuration.document
    returned_document["metadata"]["id"] = "changed"
    assert configuration.document == original


def test_collection_representation_resolves_omitted_side_to_json_array(
    tmp_path: Path,
) -> None:
    """Collection-side defaults are explicit in immutable application state."""
    configuration = _load_document(
        tmp_path, _add_collection_field(minimal_configuration())
    )

    field = configuration.field("measured_value")
    representations = field.collection_representation
    assert representations is not None
    assert representations.reference.format == "json_array"
    assert representations.reference.delimiter is None
    assert representations.reference.element_normalisation == ()
    assert representations.query.format == "delimited_text"
    assert representations.query.delimiter == "/"
    assert representations.query.element_normalisation[0].name == (
        "case_fold"
    )


def test_valid_mapping_and_normalisation_declarations_resolve_in_order(
    tmp_path: Path,
) -> None:
    """A representative scalar adaptor becomes ordered immutable application state."""
    document = _add_mapping_field(minimal_configuration())
    field = document["fields"]["definitions"]["measured_value"]
    field["source_normalisation"] = {
        "reference": [
            {"operation": "trim", "parameters": {"side": "both"}},
            {"operation": "case_fold"},
        ]
    }
    field["review_priority"] = "high"

    configuration = _load_document(tmp_path, document)

    resolved = configuration.field("measured_value")
    operation_names = tuple(
        operation.name for operation in resolved.source_normalisation.reference
    )
    assert operation_names == ("trim", "case_fold")
    assert resolved.value_mapping.reference[0].source.value == "positive"
    assert resolved.value_mapping.reference[0].destination.value == "detected"
    assert resolved.value_mapping.query == ()
    assert resolved.review_priority == "high"


def test_yaml_12_core_scalars_do_not_apply_yaml_11_boolean_or_timestamp_rules(
    tmp_path: Path,
) -> None:
    """Common YAML 1.1 words and dates remain strings under YAML 1.2 rules."""
    text = yaml.safe_dump(minimal_configuration(), sort_keys=False)
    text = text.replace(
        "  revision: 1.0.0\n",
        "  revision: 1.0.0\n  title: yes\n  description: 2026-11-06\n",
    )
    path = tmp_path / "rules.yaml"
    path.write_text(text, encoding="utf-8")

    configuration = load_comparison_configuration(path)

    assert configuration.document["metadata"]["title"] == "yes"
    assert configuration.document["metadata"]["description"] == "2026-11-06"


def test_yaml_12_leading_zero_integer_is_decimal_not_yaml_11_octal(
    tmp_path: Path,
) -> None:
    """YAML 1.2 decimal construction is used after implicit scalar resolution."""
    document = minimal_configuration()
    field = document["fields"]["definitions"]["measured_value"]
    field["typed_normalisation"] = [
        {
            "operation": "decimal_quantise",
            "parameters": {"places": 1, "rounding": "half_even"},
        }
    ]
    text = yaml.safe_dump(document, sort_keys=False).replace("places: 1", "places: 01")
    path = tmp_path / "rules.yaml"
    path.write_text(text, encoding="utf-8")

    configuration = load_comparison_configuration(path)

    operation = configuration.field("measured_value").typed_normalisation[0]
    assert operation.parameters == {"places": 1, "rounding": "half_even"}


@pytest.mark.parametrize(
    "text",
    [
        'schema_version: "1.0"\nschema_version: "1.0"\n',
        'metadata: &metadata\n  id: "example"\ncopy: *metadata\n',
        'metadata: !!map {id: "example"}\n',
        'metadata:\n  <<: {id: "example"}\n',
        '---\nschema_version: "1.0"\n---\nschema_version: "1.0"\n',
        'payload: !!python/object/apply:os.system ["false"]\n',
    ],
    ids=["duplicate", "anchor-alias", "explicit-tag", "merge", "multiple", "unsafe"],
)
def test_forbidden_yaml_features_are_invalid_syntax(
    tmp_path: Path,
    text: str,
) -> None:
    """The loader rejects ambiguous or executable YAML features before validation."""
    path = tmp_path / "rules.yaml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigurationError) as raised:
        load_comparison_configuration(path)

    assert raised.value.code == "invalid_syntax"
    assert raised.value.path == "$"
    assert raised.value.diagnostic.startswith(
        "ERROR [configuration.invalid_syntax]: $: "
    )


def _unknown_source_operation(document: JsonObject) -> None:
    document["fields"]["definitions"]["measured_value"][
        "source_normalisation"
    ] = {"reference": [{"operation": "invented"}]}


def _invalid_numeric_tolerance(document: JsonObject) -> None:
    document["fields"]["definitions"]["measured_value"]["comparator"] = {
        "name": "numeric_tolerance",
        "parameters": {
            "absolute_tolerance": "0.1",
            "relative_tolerance": "0.1",
        },
    }


def _null_mapping_source(document: JsonObject) -> None:
    field = _add_mapping_field(document)["fields"]["definitions"]["measured_value"]
    field["value_mapping"]["reference"][0]["from"] = {"category": "null"}


def _preserved_field_with_processing(document: JsonObject) -> None:
    field = document["fields"]["definitions"]["measured_value"]
    field.pop("logical_type")
    field["comparator"] = {"name": "preserved_exact"}
    field["source_normalisation"] = {
        "reference": [{"operation": "case_fold"}]
    }


def _collection_with_field_processing(document: JsonObject) -> None:
    field = _add_collection_field(document)["fields"]["definitions"][
        "measured_value"
    ]
    field["source_normalisation"] = {
        "reference": [{"operation": "case_fold"}]
    }


@pytest.mark.parametrize(
    ("mutation", "expected_path"),
    [
        (lambda document: document.update({"unknown": True}), "$.unknown"),
        (lambda document: document["metadata"].pop("revision"), "$.metadata.revision"),
        (lambda document: document["metadata"].update({"id": None}), "$.metadata.id"),
        (
            lambda document: document["fields"]["definitions"][
                "measured_value"
            ].update({"source_normalisation": {}}),
            "$.fields.definitions.measured_value.source_normalisation",
        ),
        (
            lambda document: document["fields"]["definitions"][
                "measured_value"
            ].update({"review_priority": "urgent"}),
            "$.fields.definitions.measured_value.review_priority",
        ),
        (
            _unknown_source_operation,
            "$.fields.definitions.measured_value.source_normalisation.reference[0]",
        ),
        (
            _invalid_numeric_tolerance,
            "$.fields.definitions.measured_value.comparator",
        ),
        (
            _null_mapping_source,
            "$.fields.definitions.measured_value.value_mapping.reference[0].from",
        ),
        (
            _preserved_field_with_processing,
            "$.fields.definitions.measured_value",
        ),
        (
            _collection_with_field_processing,
            "$.fields.definitions.measured_value",
        ),
    ],
    ids=[
        "unknown",
        "required",
        "null",
        "empty-optional",
        "enum",
        "unknown-operation",
        "tolerance-parameters",
        "null-mapping-source",
        "preserved-processing",
        "collection-field-processing",
    ],
)
def test_schema_violations_report_the_relevant_configuration_path(
    tmp_path: Path,
    mutation: ConfigurationMutation,
    expected_path: str,
) -> None:
    """Structural failures are distinct and point to the affected property."""
    document = minimal_configuration()
    mutation(document)

    with pytest.raises(ConfigurationError) as raised:
        _load_document(tmp_path, document)

    assert raised.value.code == "schema_violation"
    assert raised.value.path == expected_path
    assert expected_path in raised.value.diagnostic


def _key_names_unknown(document: JsonObject) -> None:
    document["fields"]["record_key"] = ["unknown"]


def _scope_name_unknown(document: JsonObject) -> None:
    document["fields"]["in_scope"].append("unknown")


def _key_not_in_scope(document: JsonObject) -> None:
    document["fields"]["in_scope"].remove("record_id")


def _key_not_required(document: JsonObject) -> None:
    document["fields"]["definitions"]["record_id"]["required"]["query"] = False


def _key_allows_null(document: JsonObject) -> None:
    field = document["fields"]["definitions"]["record_id"]
    field["null_policy"] = {"allowed": True, "nulls_equal": True}


def _key_is_collection(document: JsonObject) -> None:
    field = document["fields"]["definitions"]["record_id"]
    field["logical_type"] = {
        "collection_type": "set",
        "element_type": "string",
        "element_comparator": {"name": "typed_exact"},
    }
    field["comparator"] = {"name": "set_exact"}


def _key_comparator_not_typed_exact(document: JsonObject) -> None:
    field = document["fields"]["definitions"]["record_id"]
    field["logical_type"] = "integer"
    field["comparator"] = {"name": "numeric_exact"}


def _incompatible_comparator(document: JsonObject) -> None:
    document["fields"]["definitions"]["measured_value"]["comparator"] = {
        "name": "date_exact"
    }


def _incompatible_normalisation(document: JsonObject) -> None:
    document["fields"]["definitions"]["measured_value"][
        "typed_normalisation"
    ] = [
        {
            "operation": "datetime_truncate",
            "parameters": {"precision": "second"},
        }
    ]


def _normalised_string_without_operation(document: JsonObject) -> None:
    field = document["fields"]["definitions"]["measured_value"]
    field["logical_type"] = "string"
    field["comparator"] = {"name": "normalised_string"}


def _duplicate_reference_source(document: JsonObject) -> None:
    fields = document["fields"]["definitions"]
    fields["measured_value"]["source_fields"]["reference"] = "reference_id"


def _duplicate_query_source(document: JsonObject) -> None:
    fields = document["fields"]["definitions"]
    fields["measured_value"]["source_fields"]["query"] = "query_id"


def _reserved_identifier(document: JsonObject) -> None:
    document["metadata"]["id"] = "org.adviso.automatic-strict-exact"


def _duplicate_mapping_source(document: JsonObject) -> None:
    field = _add_mapping_field(document)["fields"]["definitions"]["measured_value"]
    field["value_mapping"]["reference"].append(
        {
            "from": {"category": "string", "value": "positive"},
            "to": {"category": "string", "value": "present"},
        }
    )


def _mapping_sources_collide_after_normalisation(document: JsonObject) -> None:
    field = _add_mapping_field(document)["fields"]["definitions"]["measured_value"]
    field["value_mapping"]["reference"][0]["from"]["value"] = " É "
    field["source_normalisation"] = {
        "reference": [
            {"operation": "unicode_normalise", "parameters": {"form": "NFC"}},
            {"operation": "trim", "parameters": {"side": "both"}},
            {"operation": "case_fold"},
        ]
    }
    field["value_mapping"]["reference"].append(
        {
            "from": {"category": "string", "value": "e\u0301"},
            "to": {"category": "string", "value": "present"},
        }
    )


def _numeric_mapping_sources_are_equal(document: JsonObject) -> None:
    field = document["fields"]["definitions"]["measured_value"]
    field["value_mapping"] = {
        "reference": [
            {
                "from": {"category": "decimal", "value": "1.0"},
                "to": {"category": "decimal", "value": "1.0"},
            },
            {
                "from": {"category": "decimal", "value": "1.00"},
                "to": {"category": "decimal", "value": "2.0"},
            },
        ]
    }


def _mapping_source_is_missing_token(document: JsonObject) -> None:
    field = _add_mapping_field(document)["fields"]["definitions"]["measured_value"]
    field["null_policy"] = {
        "allowed": True,
        "nulls_equal": True,
        "missing_tokens": {
            "reference": [{"category": "string", "value": "positive"}]
        },
    }


def _element_mapping_sources_collide(document: JsonObject) -> None:
    field = _add_collection_field(document)["fields"]["definitions"][
        "measured_value"
    ]
    field["collection_representation"]["query"]["element_mapping"].append(
        {
            "from": {"category": "string", "value": "WILD_TYPE"},
            "to": {"category": "string", "value": "wild"},
        }
    )


@pytest.mark.parametrize(
    ("mutation", "expected_path", "expected_reason"),
    [
        (
            _key_names_unknown,
            "$.fields.record_key[0]",
            "record-key field has no field definition",
        ),
        (
            _scope_name_unknown,
            "$.fields.in_scope[2]",
            "in-scope field has no field definition",
        ),
        (
            _key_not_in_scope,
            "$.fields.record_key[0]",
            "record-key field is not included in fields.in_scope",
        ),
        (
            _key_not_required,
            "$.fields.definitions.record_id.required.query",
            "record-key field must be required on both sides",
        ),
        (
            _key_allows_null,
            "$.fields.definitions.record_id.null_policy.allowed",
            "record-key field must not allow null",
        ),
        (
            _key_is_collection,
            "$.fields.definitions.record_id.logical_type",
            "record-key field must have a scalar logical type",
        ),
        (
            _key_comparator_not_typed_exact,
            "$.fields.definitions.record_id.comparator.name",
            "record-key field must use typed_exact",
        ),
        (
            _incompatible_comparator,
            "$.fields.definitions.measured_value.comparator.name",
            "comparator is incompatible with the field logical type",
        ),
        (
            _incompatible_normalisation,
            "$.fields.definitions.measured_value.typed_normalisation[0].operation",
            "typed normalisation is incompatible with the field logical type",
        ),
        (
            _normalised_string_without_operation,
            "$.fields.definitions.measured_value.comparator.name",
            "normalised_string requires a configured string normalisation",
        ),
        (
            _duplicate_reference_source,
            "$.fields.definitions.measured_value.source_fields.reference",
            "source field is already used by canonical field",
        ),
        (
            _duplicate_query_source,
            "$.fields.definitions.measured_value.source_fields.query",
            "source field is already used by canonical field",
        ),
        (
            _reserved_identifier,
            "$.metadata.id",
            "identifier is reserved for automatically generated configurations",
        ),
        (
            _duplicate_mapping_source,
            "$.fields.definitions.measured_value.value_mapping.reference[1].from",
            "mapping source duplicates another source after normalisation",
        ),
        (
            _mapping_sources_collide_after_normalisation,
            "$.fields.definitions.measured_value.value_mapping.reference[1].from",
            "mapping source duplicates another source after normalisation",
        ),
        (
            _numeric_mapping_sources_are_equal,
            "$.fields.definitions.measured_value.value_mapping.reference[1].from",
            "mapping source duplicates another source after normalisation",
        ),
        (
            _mapping_source_is_missing_token,
            "$.fields.definitions.measured_value.value_mapping.reference[0].from",
            "mapping source is unreachable because it is a missing token",
        ),
        (
            _element_mapping_sources_collide,
            "$.fields.definitions.measured_value.collection_representation.query."
            "element_mapping[1].from",
            "element mapping source duplicates another source after normalisation",
        ),
    ],
    ids=[
        "key-reference",
        "scope-reference",
        "key-scope",
        "key-contract",
        "key-null",
        "key-collection",
        "key-comparator",
        "comparator-type",
        "normalisation-type",
        "normalised-string",
        "source-reuse",
        "source-reuse-query",
        "reserved-id",
        "mapping-duplicate",
        "mapping-normalised-duplicate",
        "mapping-numeric-duplicate",
        "mapping-unreachable",
        "element-mapping-normalised-duplicate",
    ],
)
def test_semantic_violations_report_the_specific_configuration_path(
    tmp_path: Path,
    mutation: ConfigurationMutation,
    expected_path: str,
    expected_reason: str,
) -> None:
    """Cross-property failures are detected only after structural validation."""
    document = minimal_configuration()
    mutation(document)

    with pytest.raises(ConfigurationError) as raised:
        _load_document(tmp_path, document)

    assert raised.value.code == "semantic_violation"
    assert raised.value.path == expected_path
    assert expected_reason in raised.value.message
    assert expected_path in raised.value.diagnostic
    assert expected_reason in raised.value.diagnostic


def test_unsupported_version_and_unreadable_file_have_distinct_errors(
    tmp_path: Path,
) -> None:
    """Version negotiation and filesystem access retain their taxonomy."""
    unsupported = minimal_configuration()
    unsupported["schema_version"] = "2.0"

    with pytest.raises(ConfigurationError) as version_error:
        _load_document(tmp_path, unsupported)
    with pytest.raises(ConfigurationError) as read_error:
        load_comparison_configuration(tmp_path / "missing.yaml")

    assert version_error.value.code == "unsupported_version"
    assert version_error.value.path == "$.schema_version"
    assert read_error.value.code == "unreadable"
    assert read_error.value.path == "$"
    assert str(tmp_path) not in read_error.value.diagnostic


def test_invalid_utf8_and_non_mapping_root_are_classified_separately(
    tmp_path: Path,
) -> None:
    """Byte/YAML failures precede schema validation of a parsed root value."""
    invalid_utf8 = tmp_path / "encoding.yaml"
    invalid_utf8.write_bytes(b"\xff")
    sequence_root = tmp_path / "sequence.yaml"
    sequence_root.write_text("- item\n", encoding="utf-8")

    with pytest.raises(ConfigurationError) as encoding_error:
        load_comparison_configuration(invalid_utf8)
    with pytest.raises(ConfigurationError) as root_error:
        load_comparison_configuration(sequence_root)

    assert encoding_error.value.code == "invalid_syntax"
    assert root_error.value.code == "schema_violation"
    assert root_error.value.path == "$"


def test_custom_configuration_failure_precedes_all_dataset_access(
    tmp_path: Path,
) -> None:
    """Orchestration cannot inspect an input before custom rules are trustworthy."""
    document = minimal_configuration()
    _reserved_identifier(document)
    configuration_path = _write_yaml(tmp_path / "invalid.yaml", document)
    invocation = ComparisonInvocation(
        reference=tmp_path / "missing-reference.csv",
        query=tmp_path / "missing-query.json",
        output=tmp_path / "evidence",
        configuration=configuration_path,
    )

    def unexpected_dataset_loader(path: Path, side: InputSide) -> ParsedDataset:
        raise AssertionError(f"dataset loader accessed {side.value}: {path!r}")

    with pytest.raises(ConfigurationError) as raised:
        prepare_comparison(invocation, dataset_loader=unexpected_dataset_loader)

    assert raised.value.code == "semantic_violation"
    assert raised.value.path == "$.metadata.id"
