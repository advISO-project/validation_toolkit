"""Behavioural tests for record identity and automatic configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pytest
import yaml

from adviso_compare.application import prepare_comparison
from adviso_compare.configuration import EffectiveConfiguration
from adviso_compare.inputs import InputSide, JsonLocation, TabularLocation
from adviso_compare.invocation import ComparisonInvocation
from adviso_compare.records import RecordKeyError
from tests.support.documents import JsonObject, minimal_configuration


def _write(path: Path, text: str) -> Path:
    """Write one controlled UTF-8 test document."""
    path.write_text(text, encoding="utf-8")
    return path


def _write_configuration(tmp_path: Path, document: JsonObject) -> Path:
    """Write one controlled custom configuration."""
    return _write(
        tmp_path / "configuration.yaml",
        yaml.safe_dump(document, sort_keys=False),
    )


def _invocation(
    tmp_path: Path,
    reference: Path,
    query: Path,
    configuration: Path | None = None,
) -> ComparisonInvocation:
    """Build an invocation whose unused output remains inside the test directory."""
    return ComparisonInvocation(
        reference=reference,
        query=query,
        output=tmp_path / "evidence",
        configuration=configuration,
    )


def _composite_configuration() -> JsonObject:
    """Declare aliased, normalized string and parsed integer key components."""
    document = minimal_configuration()
    fields = document["fields"]
    fields["record_key"] = ["record_id", "batch"]
    fields["in_scope"].insert(1, "batch")
    key = fields["definitions"]["record_id"]
    key["source_normalisation"] = {
        "reference": [
            {"operation": "trim", "parameters": {"side": "both"}},
            {"operation": "case_fold"},
        ],
        "query": [{"operation": "case_fold"}],
    }
    fields["definitions"]["batch"] = {
        "source_fields": {
            "reference": "reference_batch",
            "query": "query_batch",
        },
        "required": {"reference": True, "query": True},
        "logical_type": "integer",
        "null_policy": {"allowed": False, "nulls_equal": False},
        "comparator": {"name": "typed_exact"},
    }
    return document


def test_custom_aliases_and_composite_key_processing_create_matching_identities(
    tmp_path: Path,
) -> None:
    """Each custom key component uses its declared source name and translation."""
    reference = _write(
        tmp_path / "reference.csv",
        "reference_id,reference_batch\n S1 ,01\n",
    )
    query = _write(
        tmp_path / "query.json",
        '[{"query_id":"s1","query_batch":"1"}]',
    )
    configuration = _write_configuration(tmp_path, _composite_configuration())

    prepared = prepare_comparison(
        _invocation(tmp_path, reference, query, configuration)
    )

    reference_record = prepared.reference_records.records[0]
    query_record = prepared.query_records.records[0]
    assert reference_record.key == query_record.key
    assert reference_record.source_identity == (" S1 ", "01")
    assert query_record.source_identity == ("s1", "1")
    assert reference_record.canonical_identity == ("s1", "1")
    assert prepared.configuration.record_key == ("record_id", "batch")


def _missing_key(document: JsonObject) -> None:
    """Leave the required reference alias absent from a JSON record."""


def _null_key(document: JsonObject) -> None:
    """No configuration mutation is needed for a prohibited source null."""


def _invalid_key(document: JsonObject) -> None:
    """Use the composite declaration so its integer component can be invalid."""
    composite = _composite_configuration()
    document.clear()
    document.update(composite)


@pytest.mark.parametrize(
    ("mutation", "reference_text", "message_fragment", "location"),
    [
        (
            _missing_key,
            '[{"expected_value":"1"}]',
            "reference key field 'reference_id' is missing",
            JsonLocation("/0"),
        ),
        (
            _null_key,
            '[{"reference_id":null}]',
            "reference key field 'reference_id' is null",
            JsonLocation("/0/reference_id"),
        ),
        (
            _invalid_key,
            (
                "reference_id,reference_batch\n"
                "S1,not-an-integer\n"
            ),
            "reference key field 'reference_batch' is invalid",
            TabularLocation(1, 2, "reference_batch"),
        ),
    ],
)
def test_missing_null_and_invalid_custom_keys_are_attributable_input_errors(
    tmp_path: Path,
    mutation: Callable[[JsonObject], None],
    reference_text: str,
    message_fragment: str,
    location: object,
) -> None:
    """A custom key defect stops record-model construction at its source location."""
    document = minimal_configuration()
    mutation(document)
    suffix = "csv" if reference_text.startswith("reference_id,") else "json"
    reference = _write(tmp_path / f"reference.{suffix}", reference_text)
    query = _write(tmp_path / "query.csv", "query_id\nS1\n")
    configuration = _write_configuration(tmp_path, document)

    with pytest.raises(RecordKeyError) as raised:
        prepare_comparison(
            _invocation(tmp_path, reference, query, configuration)
        )

    error = raised.value
    assert error.code == "invalid_record_key"
    assert error.side is InputSide.REFERENCE
    assert message_fragment in error.message
    assert error.locations == (location,)
    assert "not-an-integer" not in error.diagnostic


@pytest.mark.parametrize(
    "duplicate_side",
    [InputSide.REFERENCE, InputSide.QUERY],
)
def test_duplicate_canonical_keys_report_both_locations_without_overwriting(
    tmp_path: Path,
    duplicate_side: InputSide,
) -> None:
    """Explicit normalization can reveal a duplicate without losing either record."""
    document = minimal_configuration()
    key = document["fields"]["definitions"]["record_id"]
    key["source_normalisation"] = {
        "reference": [{"operation": "case_fold"}],
        "query": [{"operation": "case_fold"}],
    }
    duplicate = "S1\ns1\n"
    singleton = "s1\n"
    reference = _write(
        tmp_path / "reference.csv",
        "reference_id\n"
        + (duplicate if duplicate_side is InputSide.REFERENCE else singleton),
    )
    query = _write(
        tmp_path / "query.csv",
        "query_id\n"
        + (duplicate if duplicate_side is InputSide.QUERY else singleton),
    )
    configuration = _write_configuration(tmp_path, document)

    with pytest.raises(RecordKeyError) as raised:
        prepare_comparison(
            _invocation(tmp_path, reference, query, configuration)
        )

    error = raised.value
    assert error.side is duplicate_side
    assert "duplicate record key" in error.message
    assert error.locations == (
        TabularLocation(1, 2),
        TabularLocation(2, 3),
    )
    assert "S1" not in error.diagnostic
    assert "s1" not in error.diagnostic


def test_key_error_diagnostic_escapes_control_characters_in_json_pointer(
    tmp_path: Path,
) -> None:
    """An exact structured location cannot introduce a diagnostic line break."""
    document = minimal_configuration()
    document["fields"]["definitions"]["record_id"]["source_fields"][
        "reference"
    ] = "id\nline"
    reference = _write(
        tmp_path / "reference.json",
        json.dumps([{"id\nline": None}]),
    )
    query = _write(tmp_path / "query.csv", "query_id\nS1\n")
    configuration = _write_configuration(tmp_path, document)

    with pytest.raises(RecordKeyError) as raised:
        prepare_comparison(
            _invocation(tmp_path, reference, query, configuration)
        )

    assert raised.value.locations == (JsonLocation("/0/id\nline"),)
    assert "\n" not in raised.value.diagnostic
    assert r"\n" in raised.value.diagnostic


def test_automatic_record_id_generates_strict_exact_shared_fields_and_exclusions(
    tmp_path: Path,
) -> None:
    """Shared record_id is preferred and only exact same-name fields are declared."""
    reference = _write(
        tmp_path / "reference.json",
        '[{"record_id":"S1","z":1,"a":"x","reference_note":"r"}]',
    )
    query = _write(
        tmp_path / "query.csv",
        "record_id,a,z,query_note\nS1,x,1,q\n",
    )

    prepared = prepare_comparison(_invocation(tmp_path, reference, query))

    configuration = prepared.configuration
    assert configuration.metadata.id == "org.adviso.automatic-strict-exact"
    assert configuration.metadata.revision == "1.0"
    assert configuration.record_key == ("record_id",)
    assert configuration.in_scope == ("record_id", "a", "z")
    assert tuple(configuration.fields) == ("record_id", "a", "z")
    key = configuration.field("record_id")
    assert key.logical_type == "string"
    assert key.required.reference and key.required.query
    assert not key.null_policy.allowed
    for field_name in ("a", "z"):
        field = configuration.field(field_name)
        assert field.logical_type is None
        assert field.comparator.name == "preserved_exact"
        assert not field.required.reference and not field.required.query
        assert field.null_policy.allowed and field.null_policy.nulls_equal
    assert "reference_note" not in configuration.fields
    assert "query_note" not in configuration.fields
    assert configuration.document["fields"]["definitions"]["a"] == {
        "source_fields": {"reference": "a", "query": "a"},
        "required": {"reference": False, "query": False},
        "null_policy": {"allowed": True, "nulls_equal": True},
        "comparator": {"name": "preserved_exact"},
    }


def test_automatic_discovery_selects_the_only_exact_shared_string_candidate(
    tmp_path: Path,
) -> None:
    """A non-record_id candidate requires completeness, uniqueness, and overlap."""
    reference = _write(
        tmp_path / "reference.json",
        '[{"sample":"S1","value":"a"},{"sample":"S2","value":"b"}]',
    )
    query = _write(
        tmp_path / "query.json",
        '[{"sample":"S1","value":"x"},{"sample":"S3","value":"y"}]',
    )

    prepared = prepare_comparison(_invocation(tmp_path, reference, query))

    assert prepared.configuration.record_key == ("sample",)
    assert prepared.reference_records.records[0].canonical_identity == ("S1",)


@pytest.mark.parametrize(
    ("reference_text", "query_text", "message_fragment", "candidates"),
    [
        (
            '[{"sample":"R1","value":1}]',
            '[{"sample":"Q1","value":1}]',
            "no field satisfied the automatic record-key criteria",
            (),
        ),
        (
            '[{"sample":"S1","accession":"A1"}]',
            '[{"sample":"S1","accession":"A1"}]',
            "automatic record-key selection is ambiguous",
            ("accession", "sample"),
        ),
        (
            (
                '[{"part_a":"A","part_b":"1"},'
                '{"part_a":"A","part_b":"2"},'
                '{"part_a":"B","part_b":"1"},'
                '{"part_a":"B","part_b":"2"}]'
            ),
            (
                '[{"part_a":"A","part_b":"1"},'
                '{"part_a":"A","part_b":"2"},'
                '{"part_a":"B","part_b":"1"},'
                '{"part_a":"B","part_b":"2"}]'
            ),
            "no field satisfied the automatic record-key criteria",
            (),
        ),
    ],
)
def test_automatic_discovery_rejects_zero_or_multiple_candidates_without_values(
    tmp_path: Path,
    reference_text: str,
    query_text: str,
    message_fragment: str,
    candidates: tuple[str, ...],
) -> None:
    """Automatic discovery neither guesses nor ranks otherwise valid candidates."""
    reference = _write(tmp_path / "reference.json", reference_text)
    query = _write(tmp_path / "query.json", query_text)

    with pytest.raises(RecordKeyError) as raised:
        prepare_comparison(_invocation(tmp_path, reference, query))

    error = raised.value
    assert error.side is None
    assert message_fragment in error.message
    assert error.candidate_fields == candidates
    assert "S1" not in error.diagnostic
    assert "A1" not in error.diagnostic


def test_invalid_automatic_candidates_are_ignored_without_coercion(
    tmp_path: Path,
) -> None:
    """Only a complete, non-null, unique parser-native string can be selected."""
    reference = _write(
        tmp_path / "reference.json",
        (
            '[{"sample":"S1","numeric":1,"nullable":"x",'
            '"sometimes":"p","duplicate":"d"},'
            '{"sample":"S2","numeric":2,"nullable":null,'
            '"duplicate":"d"}]'
        ),
    )
    query = _write(
        tmp_path / "query.json",
        (
            '[{"sample":"S1","numeric":1,"nullable":"x",'
            '"sometimes":"p","duplicate":"d"},'
            '{"sample":"S3","numeric":3,"nullable":"y",'
            '"sometimes":"q","duplicate":"d"}]'
        ),
    )

    prepared = prepare_comparison(_invocation(tmp_path, reference, query))

    assert prepared.configuration.record_key == ("sample",)


@pytest.mark.parametrize(
    ("query_text", "message_fragment"),
    [
        (
            (
                '[{"record_id":"Q1","sample":"S1"},'
                '{"sample":"S2"}]'
            ),
            "is missing",
        ),
        ('[{"record_id":null,"sample":"S1"}]', "is null"),
        ('[{"record_id":1,"sample":"S1"}]', "is not a parser-native string"),
        (
            (
                '[{"record_id":"Q1","sample":"S1"},'
                '{"record_id":"Q1","sample":"S2"}]'
            ),
            "duplicate record key",
        ),
    ],
)
def test_invalid_shared_record_id_never_falls_back_to_another_candidate(
    tmp_path: Path,
    query_text: str,
    message_fragment: str,
) -> None:
    """Every preferred-key defect is fatal even when sample could identify records."""
    reference = _write(
        tmp_path / "reference.json",
        (
            '[{"record_id":"R1","sample":"S1"},'
            '{"record_id":"R2","sample":"S2"}]'
        ),
    )
    query = _write(tmp_path / "query.json", query_text)

    with pytest.raises(RecordKeyError) as raised:
        prepare_comparison(_invocation(tmp_path, reference, query))

    error = raised.value
    assert error.side is InputSide.QUERY
    assert error.key_fields == ("record_id",)
    assert message_fragment in error.message
    assert "sample" not in error.message


def test_header_only_record_id_is_valid_but_empty_json_has_no_automatic_key(
    tmp_path: Path,
) -> None:
    """Tabular headers expose record_id while empty JSON exposes no fields."""
    reference_csv = _write(tmp_path / "reference.csv", "record_id,value\n")
    query_tsv = _write(tmp_path / "query.tsv", "record_id\tvalue\n")

    prepared = prepare_comparison(
        _invocation(tmp_path, reference_csv, query_tsv)
    )

    assert prepared.configuration.record_key == ("record_id",)
    assert prepared.reference_records.records == ()
    assert prepared.query_records.records == ()

    empty_reference = _write(tmp_path / "empty-reference.json", "[]")
    empty_query = _write(tmp_path / "empty-query.json", "[]")
    with pytest.raises(RecordKeyError) as raised:
        prepare_comparison(
            _invocation(tmp_path, empty_reference, empty_query)
        )
    assert "no field satisfied" in raised.value.message


def test_generated_document_is_schema_valid_and_reserved_id_remains_internal(
    tmp_path: Path,
) -> None:
    """Automatic configuration is valid but cannot be supplied as custom YAML."""
    reference = _write(tmp_path / "reference.csv", "record_id\nS1\n")
    query = _write(tmp_path / "query.csv", "record_id\nS1\n")
    prepared = prepare_comparison(_invocation(tmp_path, reference, query))
    generated = prepared.configuration.document
    custom_path = _write_configuration(tmp_path, generated)

    from adviso_compare.configuration import (  # local to emphasize the boundary
        ConfigurationError,
        load_comparison_configuration,
    )

    with pytest.raises(ConfigurationError) as raised:
        load_comparison_configuration(custom_path)

    assert raised.value.code == "semantic_violation"
    assert raised.value.path == "$.metadata.id"
    assert isinstance(prepared.configuration, EffectiveConfiguration)
