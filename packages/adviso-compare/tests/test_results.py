"""Behavioural tests for canonical result assembly and validation."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
import yaml

from adviso_compare.alignment import align_records
from adviso_compare.application import PreparedComparison, prepare_comparison
from adviso_compare.contract import assess_contract
from adviso_compare.invocation import ComparisonInvocation
from adviso_compare.results import (
    ResultValidationError,
    RuntimeIdentity,
    assemble_result,
    current_runtime_identity,
    serialize_result,
    validate_result,
)
from adviso_compare.values import compare_values
from tests.support.documents import JsonObject, minimal_configuration
from tests.support.schemas import results_validator


RUN_ID = UUID("123e4567-e89b-42d3-a456-426614174000")
COMPLETED_AT = datetime(2026, 11, 9, 12, 34, 56, tzinfo=timezone.utc)
RUNTIME = RuntimeIdentity(
    python="cpython-3.12.7",
    platform="linux-x86_64",
    unicode_version="15.1.0",
)


def _write(path: Path, text: str) -> Path:
    """Write one controlled UTF-8 document."""
    path.write_text(text, encoding="utf-8")
    return path


def _prepare(
    tmp_path: Path,
    reference_text: str,
    query_text: str,
    configuration: JsonObject | None = None,
) -> PreparedComparison:
    """Prepare one custom or automatic comparison."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    reference = _write(tmp_path / "reference.json", reference_text)
    query = _write(tmp_path / "query.json", query_text)
    configuration_path = None
    if configuration is not None:
        configuration_path = _write(
            tmp_path / "configuration.yaml",
            yaml.safe_dump(configuration, sort_keys=False),
        )
    return prepare_comparison(
        ComparisonInvocation(
            reference=reference,
            query=query,
            output=tmp_path / "evidence",
            configuration=configuration_path,
        )
    )


def _assemble(prepared: PreparedComparison) -> JsonObject:
    """Run the three phases and assemble deterministic test evidence."""
    contract = assess_contract(
        prepared.configuration,
        reference=prepared.reference,
        query=prepared.query,
        reference_records=prepared.reference_records,
        query_records=prepared.query_records,
    )
    records = align_records(prepared.reference_records, prepared.query_records)
    values = compare_values(prepared.configuration, contract, records)
    return assemble_result(
        prepared,
        contract,
        records,
        values,
        run_id=RUN_ID,
        completed_at=COMPLETED_AT,
        software_version="1.2.3",
        runtime=RUNTIME,
    )


def test_complete_result_reconciles_findings_summaries_and_provenance(
    tmp_path: Path,
) -> None:
    """A complete mixed comparison becomes coherent canonical evidence."""
    prepared = _prepare(
        tmp_path,
        (
            '[{"reference_id":"S2","expected_value":2,"reference_note":"r"},'
            '{"reference_id":"S1","expected_value":1}]'
        ),
        (
            '[{"query_id":"S3","observed_value":3,"query_note":"q"},'
            '{"query_id":"S1","observed_value":2}]'
        ),
        minimal_configuration(),
    )

    result = _assemble(prepared)

    results_validator().validate(result)
    assert result["run"] == {
        "id": str(RUN_ID),
        "status": "complete",
        "completed_at": "2026-11-09T12:34:56Z",
    }
    assert result["phases"] == {
        "contract": "complete",
        "records": "complete",
        "values": "complete",
    }
    assert result["summary"]["records"] == {
        "reference": 2,
        "query": 2,
        "matched": 1,
        "missing": 1,
        "extra": 1,
    }
    assert result["summary"]["values"] == {
        "matched": 0,
        "mismatched": 1,
        "not_assessable": 0,
    }
    assert [finding["code"] for finding in result["findings"]] == [
        "missing_record",
        "extra_record",
        "value_mismatch",
    ]
    assert [finding["id"] for finding in result["findings"]] == [
        "F000001",
        "F000002",
        "F000003",
    ]
    assert result["findings"][2]["values"] == {
        "reference": {
            "state": "present",
            "source": {"category": "integer", "value": "1"},
            "canonical": {"logical_type": "decimal", "value": "1"},
        },
        "query": {
            "state": "present",
            "source": {"category": "integer", "value": "2"},
            "canonical": {"logical_type": "decimal", "value": "2"},
        },
    }
    assert result["summary"]["findings"]["by_classification"] == {
        "comparison_difference": 3,
        "assessment_issue": 0,
    }
    assert result["summary"]["findings"]["by_review_priority"] == {
        "low": 0,
        "normal": 1,
        "high": 0,
        "unassigned": 2,
    }
    assert result["exclusions"] == [
        {
            "code": "undeclared_field_excluded",
            "side": "reference",
            "source_field": "reference_note",
            "record_count": 1,
        },
        {
            "code": "undeclared_field_excluded",
            "side": "query",
            "source_field": "query_note",
            "record_count": 1,
        },
    ]
    assert result["inputs"]["reference"]["basename"] == "reference.json"
    assert result["inputs"]["reference"]["digest"]["value"] == (
        prepared.reference.provenance.sha256
    )


def test_incomplete_result_retains_causal_evidence_without_duplicate_finding(
    tmp_path: Path,
) -> None:
    """A failed prerequisite makes values incomplete and remains causal evidence."""
    prepared = _prepare(
        tmp_path,
        '[{"reference_id":"S1","expected_value":1}]',
        '[{"query_id":"S1"}]',
        minimal_configuration(),
    )

    result = _assemble(prepared)

    results_validator().validate(result)
    assert result["run"]["status"] == "incomplete"
    assert result["phases"]["values"] == "incomplete"
    assert result["summary"]["values"] == {
        "matched": 0,
        "mismatched": 0,
        "not_assessable": 1,
    }
    assert [finding["code"] for finding in result["findings"]] == [
        "missing_required_field"
    ]
    finding = result["findings"][0]
    assert finding["values"] == {
        "reference": {"state": "present"},
        "query": {"state": "absent"},
    }
    assert finding["record_identity"] == {
        "reference": ["S1"],
        "query": ["S1"],
        "canonical": ["S1"],
    }


@pytest.mark.parametrize(
    ("case", "query_value", "expected_code", "source_category", "has_canonical"),
    [
        ("ordinary", "true", "type_mismatch", "boolean", False),
        ("ordinary", '".5"', "invalid_field_value", "string", False),
        ("ordinary", "null", "null_policy_violation", "null", True),
        ("untyped_null", "null", "null_policy_violation", "null", False),
        ("mapping", '"unknown"', "mapping_failure", "string", False),
    ],
)
def test_contract_finding_registry_renders_code_specific_value_evidence(
    tmp_path: Path,
    case: str,
    query_value: str,
    expected_code: str,
    source_category: str,
    has_canonical: bool,
) -> None:
    """Contract finding forms retain only their permitted causal evidence."""
    configuration = minimal_configuration()
    reference_value = "1"
    if case == "mapping":
        reference_value = '"known"'
        field = configuration["fields"]["definitions"]["measured_value"]
        field["logical_type"] = "string"
        field["comparator"] = {"name": "typed_exact"}
        field["value_mapping"] = {
            "query": [
                {
                    "from": {"category": "string", "value": "known"},
                    "to": {"category": "string", "value": "known"},
                }
            ]
        }
    elif case == "untyped_null":
        field = configuration["fields"]["definitions"]["measured_value"]
        field.pop("logical_type")
        field["comparator"] = {"name": "preserved_exact"}
    prepared = _prepare(
        tmp_path,
        f'[{{"reference_id":"S1","expected_value":{reference_value}}}]',
        f'[{{"query_id":"S1","observed_value":{query_value}}}]',
        configuration,
    )

    result = _assemble(prepared)

    assert [finding["code"] for finding in result["findings"]] == [expected_code]
    evidence = result["findings"][0]["values"]["query"]
    assert evidence["state"] == "present"
    assert evidence["source"]["category"] == source_category
    assert ("canonical" in evidence) is has_canonical
    if has_canonical:
        assert evidence["canonical"] == {
            "logical_type": "decimal",
            "value": None,
        }


def test_dataset_level_missing_field_uses_the_distinct_compact_finding_form(
    tmp_path: Path,
) -> None:
    """An empty table can report a missing required column without a record."""
    reference = _write(tmp_path / "reference.csv", "reference_id\n")
    query = _write(tmp_path / "query.tsv", "query_id\tobserved_value\n")
    configuration = _write(
        tmp_path / "configuration.yaml",
        yaml.safe_dump(minimal_configuration(), sort_keys=False),
    )
    prepared = prepare_comparison(
        ComparisonInvocation(
            reference=reference,
            query=query,
            output=tmp_path / "evidence",
            configuration=configuration,
        )
    )

    result = _assemble(prepared)

    assert result["run"]["status"] == "complete"
    assert result["summary"]["values"] == {
        "matched": 0,
        "mismatched": 0,
        "not_assessable": 0,
    }
    assert result["findings"] == [
        {
            "id": "F000001",
            "classification": "assessment_issue",
            "code": "missing_required_field",
            "phase": "contract",
            "message": "Required reference field 'measured_value' is absent.",
            "affected_side": "reference",
            "field": "measured_value",
            "review_priority": "normal",
        }
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda result: result["run"].update(status="incomplete"),
        lambda result: result["summary"]["records"].update(reference=99),
        lambda result: result["summary"]["findings"].update(total=99),
        lambda result: result["findings"][0].update(id="F000009"),
        lambda result: result["record_key_fields"].update(canonical=["wrong"]),
    ],
)
def test_semantic_validation_rejects_internally_incoherent_results(
    tmp_path: Path,
    mutation: object,
) -> None:
    """Schema-valid-looking contradictions cannot pass self-validation."""
    prepared = _prepare(
        tmp_path,
        '[{"reference_id":"S1","expected_value":1}]',
        '[{"query_id":"S1","observed_value":2}]',
        minimal_configuration(),
    )
    result = _assemble(prepared)
    invalid = deepcopy(result)
    mutation(invalid)  # type: ignore[operator]

    with pytest.raises(ResultValidationError):
        validate_result(invalid, prepared=prepared)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda result: result["summary"]["values"].update(matched=2),
        lambda result: (
            result["run"].update(status="incomplete"),
            result["phases"].update(values="incomplete"),
        ),
    ],
)
def test_semantic_validation_reconciles_opportunities_and_values_status(
    tmp_path: Path,
    mutation: object,
) -> None:
    """Value totals and completion status agree without phase-domain context."""
    prepared = _prepare(
        tmp_path,
        '[{"reference_id":"S1","expected_value":1}]',
        '[{"query_id":"S1","observed_value":1}]',
        minimal_configuration(),
    )
    invalid = deepcopy(_assemble(prepared))
    mutation(invalid)  # type: ignore[operator]

    with pytest.raises(ResultValidationError):
        validate_result(invalid, prepared=prepared)


def test_finding_total_order_coalesces_duplicates_before_assigning_ids(
    tmp_path: Path,
) -> None:
    """Classification, scope, identity, and coalescence determine local IDs."""
    reference = _write(tmp_path / "reference.csv", "reference_id\n")
    query = _write(
        tmp_path / "query.json",
        (
            '[{"query_id":"S2","observed_value":"invalid"},'
            '{"query_id":"S1","observed_value":"invalid"}]'
        ),
    )
    configuration = _write(
        tmp_path / "configuration.yaml",
        yaml.safe_dump(minimal_configuration(), sort_keys=False),
    )
    prepared = prepare_comparison(
        ComparisonInvocation(
            reference=reference,
            query=query,
            output=tmp_path / "evidence",
            configuration=configuration,
        )
    )
    contract = assess_contract(
        prepared.configuration,
        reference=prepared.reference,
        query=prepared.query,
        reference_records=prepared.reference_records,
        query_records=prepared.query_records,
    )
    contract_with_duplicate = replace(
        contract,
        findings=contract.findings + (contract.findings[-1],),
    )
    records = align_records(prepared.reference_records, prepared.query_records)
    values = compare_values(prepared.configuration, contract, records)

    result = assemble_result(
        prepared,
        contract_with_duplicate,
        records,
        values,
        run_id=RUN_ID,
        completed_at=COMPLETED_AT,
        software_version="1.2.3",
        runtime=RUNTIME,
    )

    assert [
        (
            finding["id"],
            finding["classification"],
            finding["code"],
            finding.get("record_identity", {}).get("canonical"),
        )
        for finding in result["findings"]
    ] == [
        ("F000001", "comparison_difference", "extra_record", ["S1"]),
        ("F000002", "comparison_difference", "extra_record", ["S2"]),
        ("F000003", "assessment_issue", "missing_required_field", None),
        ("F000004", "assessment_issue", "invalid_field_value", ["S1"]),
        ("F000005", "assessment_issue", "invalid_field_value", ["S2"]),
    ]
    assert result["summary"]["findings"]["total"] == 5


@pytest.mark.parametrize(
    (
        "logical_type",
        "comparator",
        "reference_value",
        "query_value",
        "expected_query_canonical",
    ),
    [
        (
            "integer",
            "typed_exact",
            '"01"',
            '"2"',
            {"logical_type": "integer", "value": "2"},
        ),
        (
            "string",
            "typed_exact",
            '"A"',
            '"B"',
            {"logical_type": "string", "value": "B"},
        ),
        (
            "boolean",
            "typed_exact",
            "true",
            "false",
            {"logical_type": "boolean", "value": False},
        ),
        (
            "date",
            "date_exact",
            '"2026-01-01"',
            '"2026-01-02"',
            {"logical_type": "date", "value": "2026-01-02"},
        ),
        (
            "datetime",
            "datetime_exact",
            '"2026-01-01T00:00:00Z"',
            '"2026-01-01T01:00:00Z"',
            {"logical_type": "datetime", "value": "2026-01-01T01:00:00Z"},
        ),
        (
            {
                "collection_type": "list",
                "element_type": "decimal",
                "element_comparator": {"name": "typed_exact"},
            },
            "list_exact",
            "[1,2]",
            "[1,3]",
            {
                "logical_type": "list",
                "element_type": "decimal",
                "value": ["1", "3"],
            },
        ),
    ],
)
def test_typed_value_evidence_uses_each_canonical_rendering_form(
    tmp_path: Path,
    logical_type: object,
    comparator: str,
    reference_value: str,
    query_value: str,
    expected_query_canonical: JsonObject,
) -> None:
    """Scalar and collection evidence retains its unique canonical form."""
    configuration = minimal_configuration()
    field = configuration["fields"]["definitions"]["measured_value"]
    field["logical_type"] = logical_type
    field["comparator"] = {"name": comparator}
    if isinstance(logical_type, dict):
        field["collection_representation"] = {
            "reference": {"format": "json_array"},
            "query": {"format": "json_array"},
        }
    prepared = _prepare(
        tmp_path,
        f'[{{"reference_id":"S1","expected_value":{reference_value}}}]',
        f'[{{"query_id":"S1","observed_value":{query_value}}}]',
        configuration,
    )

    result = _assemble(prepared)

    assert result["findings"][0]["values"]["query"]["canonical"] == (
        expected_query_canonical
    )


def test_untyped_recursive_source_evidence_is_lossless_and_ordered(
    tmp_path: Path,
) -> None:
    """Preserved arrays and objects retain recursively typed source evidence."""
    prepared = _prepare(
        tmp_path,
        (
            '[{"record_id":"S1","payload":'
            '{"z":[1,null],"a":true}}]'
        ),
        (
            '[{"record_id":"S1","payload":'
            '{"a":false,"z":[1,null]}}]'
        ),
    )

    result = _assemble(prepared)

    query_evidence = result["findings"][0]["values"]["query"]
    assert "canonical" not in query_evidence
    assert query_evidence["source"] == {
        "category": "object",
        "value": {
            "a": {"category": "boolean", "value": False},
            "z": {
                "category": "array",
                "value": [
                    {"category": "integer", "value": "1"},
                    {"category": "null"},
                ],
            },
        },
    }


def test_default_run_and_runtime_metadata_use_live_normalized_values(
    tmp_path: Path,
) -> None:
    """Ordinary assembly creates a UUID, UTC timestamp, and runtime identity."""
    prepared = _prepare(
        tmp_path,
        '[{"reference_id":"S1","expected_value":1}]',
        '[{"query_id":"S1","observed_value":1}]',
        minimal_configuration(),
    )
    contract = assess_contract(
        prepared.configuration,
        reference=prepared.reference,
        query=prepared.query,
        reference_records=prepared.reference_records,
        query_records=prepared.query_records,
    )
    records = align_records(prepared.reference_records, prepared.query_records)
    values = compare_values(prepared.configuration, contract, records)

    result = assemble_result(prepared, contract, records, values)

    assert UUID(result["run"]["id"]).version == 4
    assert result["run"]["completed_at"].endswith("Z")
    runtime = current_runtime_identity()
    assert result["runtime"] == {
        "python": runtime.python,
        "platform": runtime.platform,
        "unicode_version": runtime.unicode_version,
    }


def test_canonical_serialization_is_utf8_ordered_and_newline_terminated(
    tmp_path: Path,
) -> None:
    """Canonical JSON has stable layout and emits non-ASCII text directly."""
    source_configuration = minimal_configuration()
    source_configuration["metadata"]["title"] = "Café comparison"
    source_fields = source_configuration["fields"]
    source_definitions = source_fields["definitions"]
    source_fields["definitions"] = {
        "record_id": source_definitions["record_id"],
        "measured_value": source_definitions["measured_value"],
    }
    configuration = {
        "fields": source_fields,
        "metadata": {
            "revision": source_configuration["metadata"]["revision"],
            "title": source_configuration["metadata"]["title"],
            "id": source_configuration["metadata"]["id"],
        },
        "schema_version": source_configuration["schema_version"],
    }
    prepared = _prepare(
        tmp_path,
        '[{"reference_id":"S1","expected_value":1}]',
        '[{"query_id":"S1","observed_value":1}]',
        configuration,
    )
    result = _assemble(prepared)

    rendered = serialize_result(result)

    embedded = result["comparison_configuration"]["document"]
    assert list(embedded) == ["schema_version", "metadata", "fields"]
    assert list(embedded["metadata"]) == ["id", "revision", "title"]
    assert list(embedded["fields"]["definitions"]) == [
        "measured_value",
        "record_id",
    ]
    assert rendered.startswith(b'{\n  "results_schema_version": "1.0",\n')
    assert b'Caf\xc3\xa9 comparison' in rendered
    assert b"\\u00e9" not in rendered
    assert b"\r" not in rendered
    assert rendered.endswith(b"\n") and not rendered.endswith(b"\n\n")
    assert json.loads(rendered) == result


def test_repeated_and_record_reordered_runs_preserve_the_comparison_outcome(
    tmp_path: Path,
) -> None:
    """Only permitted byte provenance and location evidence vary with order."""
    first = _prepare(
        tmp_path / "first",
        (
            '[{"record_id":"S3","value":3},{"record_id":"S1","value":1},'
            '{"record_id":"S2","value":2}]'
        ),
        (
            '[{"record_id":"S4","value":4},{"record_id":"S2","value":2},'
            '{"record_id":"S1","value":9}]'
        ),
    )
    reordered = _prepare(
        tmp_path / "reordered",
        (
            '[{"record_id":"S2","value":2},{"record_id":"S1","value":1},'
            '{"record_id":"S3","value":3}]'
        ),
        (
            '[{"record_id":"S1","value":9},{"record_id":"S2","value":2},'
            '{"record_id":"S4","value":4}]'
        ),
    )

    first_result = _assemble(first)
    repeated_result = _assemble(first)
    reordered_result = _assemble(reordered)

    assert serialize_result(first_result) == serialize_result(repeated_result)
    assert (
        first_result["comparison_configuration"]
        == reordered_result["comparison_configuration"]
    )
    assert _comparison_outcome(first_result) == _comparison_outcome(
        reordered_result
    )
    assert first_result["inputs"] != reordered_result["inputs"]
    assert [
        finding["source_locations"] for finding in first_result["findings"]
    ] != [
        finding["source_locations"] for finding in reordered_result["findings"]
    ]


def _comparison_outcome(result: JsonObject) -> JsonObject:
    """Extract the specification's location-independent comparison outcome."""
    return {
        "run_status": result["run"]["status"],
        "phases": result["phases"],
        "summary": result["summary"],
        "exclusions": result["exclusions"],
        "findings": [
            {
                name: value
                for name, value in finding.items()
                if name not in {"id", "message", "source_locations"}
            }
            for finding in result["findings"]
        ],
    }
