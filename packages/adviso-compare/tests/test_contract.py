"""Behavioural tests for contract assessment and exclusions."""

from __future__ import annotations

from pathlib import Path

import yaml

from adviso_compare.application import PreparedComparison, prepare_comparison
from adviso_compare.contract import (
    ConfiguredFieldExclusion,
    ContractPhaseStatus,
    ContractResult,
    UndeclaredFieldExclusion,
    assess_contract,
)
from adviso_compare.inputs import InputSide
from adviso_compare.invocation import ComparisonInvocation
from adviso_compare.translation import ValueDisposition
from tests.support.documents import JsonObject, minimal_configuration


def _write(path: Path, text: str) -> Path:
    """Write one controlled UTF-8 document."""
    path.write_text(text, encoding="utf-8")
    return path


def _field(
    reference_name: str,
    query_name: str,
    *,
    logical_type: str = "decimal",
    required_reference: bool = True,
    required_query: bool = True,
    review_priority: str | None = None,
) -> JsonObject:
    """Create one typed field declaration for a contract fixture."""
    field: JsonObject = {
        "source_fields": {
            "reference": reference_name,
            "query": query_name,
        },
        "required": {
            "reference": required_reference,
            "query": required_query,
        },
        "logical_type": logical_type,
        "null_policy": {"allowed": False, "nulls_equal": False},
        "comparator": {"name": "typed_exact"},
    }
    if review_priority is not None:
        field["review_priority"] = review_priority
    return field


def _mixed_configuration() -> JsonObject:
    """Declare every contract outcome alongside unaffected and excluded fields."""
    document = minimal_configuration()
    fields = document["fields"]
    definitions = fields["definitions"]
    fields["in_scope"] = [
        "record_id",
        "measured_value",
        "required_field",
        "typed_field",
        "invalid_field",
        "null_field",
        "mapped_field",
        "optional_field",
    ]
    definitions["required_field"] = _field(
        "required_reference",
        "required_query",
        review_priority="high",
    )
    definitions["typed_field"] = _field(
        "typed_reference",
        "typed_query",
        review_priority="low",
    )
    definitions["invalid_field"] = _field(
        "invalid_reference",
        "invalid_query",
    )
    definitions["null_field"] = _field(
        "null_reference",
        "null_query",
        review_priority="high",
    )
    definitions["mapped_field"] = _field(
        "mapped_reference",
        "mapped_query",
        logical_type="string",
        review_priority="low",
    )
    definitions["mapped_field"]["value_mapping"] = {
        "reference": [
            {
                "from": {"category": "string", "value": "known"},
                "to": {"category": "string", "value": "canonical"},
            }
        ],
        "query": [
            {
                "from": {"category": "string", "value": "known"},
                "to": {"category": "string", "value": "canonical"},
            }
        ],
    }
    definitions["optional_field"] = _field(
        "optional_reference",
        "optional_query",
        required_reference=False,
        required_query=False,
    )
    definitions["excluded_field"] = _field(
        "excluded_reference",
        "excluded_query",
    )
    return document


def _prepare_mixed_comparison(tmp_path: Path) -> PreparedComparison:
    """Create two aligned heterogeneous datasets with independent defects."""
    reference = _write(
        tmp_path / "reference.json",
        (
            '[{"reference_id":"S1","expected_value":1,'
            '"required_reference":1,"typed_reference":true,'
            '"invalid_reference":"NaN","null_reference":1,'
            '"mapped_reference":"unknown","excluded_reference":1,'
            '"common_extra":"r1","reference_extra":"only"},'
            '{"reference_id":"S2","expected_value":2,'
            '"required_reference":2,"typed_reference":2,'
            '"invalid_reference":"2","null_reference":2,'
            '"mapped_reference":"known","excluded_reference":2,'
            '"common_extra":"r2"}]'
        ),
    )
    query = _write(
        tmp_path / "query.json",
        (
            '[{"query_id":"S1","observed_value":1,'
            '"typed_query":[],"invalid_query":"1",'
            '"null_query":null,"mapped_query":"known",'
            '"excluded_query":1,"common_extra":"q1",'
            '"query_extra":"first"},'
            '{"query_id":"S2","observed_value":2,'
            '"required_query":2,"typed_query":2,"invalid_query":"2",'
            '"null_query":2,"mapped_query":"known","excluded_query":2,'
            '"query_extra":"second"}]'
        ),
    )
    configuration = _write(
        tmp_path / "configuration.yaml",
        yaml.safe_dump(_mixed_configuration(), sort_keys=False),
    )
    return prepare_comparison(
        ComparisonInvocation(
            reference=reference,
            query=query,
            output=tmp_path / "evidence",
            configuration=configuration,
        )
    )


def _assess(prepared: PreparedComparison) -> ContractResult:
    """Pass a prepared comparison's domain inputs to the contract boundary."""
    return assess_contract(
        prepared.configuration,
        reference=prepared.reference,
        query=prepared.query,
        reference_records=prepared.reference_records,
        query_records=prepared.query_records,
    )


def test_mixed_contract_collects_every_causal_finding_and_continues(
    tmp_path: Path,
) -> None:
    """Independent defects block only their values and retain valid assessments."""
    prepared = _prepare_mixed_comparison(tmp_path)

    result = _assess(prepared)

    assert result.status is ContractPhaseStatus.COMPLETE
    observed = [
        (
            finding.code,
            finding.side,
            finding.canonical_field,
            finding.review_priority,
            finding.record.canonical_identity if finding.record else None,
        )
        for finding in result.findings
    ]
    assert observed == [
        (
            "invalid_field_value",
            InputSide.REFERENCE,
            "invalid_field",
            "normal",
            ("S1",),
        ),
        ("mapping_failure", InputSide.REFERENCE, "mapped_field", "low", ("S1",)),
        ("null_policy_violation", InputSide.QUERY, "null_field", "high", ("S1",)),
        ("missing_required_field", InputSide.QUERY, "required_field", "high", ("S1",)),
        ("type_mismatch", InputSide.REFERENCE, "typed_field", "low", ("S1",)),
        ("type_mismatch", InputSide.QUERY, "typed_field", "low", ("S1",)),
    ]
    assert all(
        finding.classification == "assessment_issue" for finding in result.findings
    )
    assert all(finding.phase == "contract" for finding in result.findings)
    assert all(finding.location is not None for finding in result.findings)

    key = prepared.reference_records.records[0].key
    assert result.assessment(InputSide.REFERENCE, key, "invalid_field").disposition is (
        ValueDisposition.NOT_ASSESSABLE
    )
    assert result.assessment(InputSide.QUERY, key, "required_field").disposition is (
        ValueDisposition.NOT_ASSESSABLE
    )
    measured = result.assessment(InputSide.REFERENCE, key, "measured_value")
    assert measured.disposition is ValueDisposition.VALID
    second_key = prepared.reference_records.records[1].key
    mapped = result.assessment(InputSide.REFERENCE, second_key, "mapped_field")
    optional = result.assessment(InputSide.QUERY, second_key, "optional_field")
    assert mapped.disposition is ValueDisposition.VALID
    assert optional.disposition is ValueDisposition.ABSENT

    assessment_identities = [
        (
            assessment.side,
            assessment.record.canonical_identity,
            assessment.canonical_field,
        )
        for assessment in result.assessments
    ]
    assert len(assessment_identities) == 32
    assert len(set(assessment_identities)) == 32

    blocked = {
        (
            assessment.side,
            assessment.record.key,
            assessment.canonical_field,
        )
        for assessment in result.assessments
        if assessment.disposition is ValueDisposition.NOT_ASSESSABLE
    }
    causal_findings = {
        (finding.side, finding.record.key, finding.canonical_field)
        for finding in result.findings
        if finding.record is not None
    }
    assert blocked == causal_findings
    assert len(blocked) == len(result.findings) == 6

    unaffected = [
        assessment
        for assessment in result.assessments
        if assessment.record.canonical_identity == ("S2",)
    ]
    assert len(unaffected) == 16
    assert {assessment.disposition for assessment in unaffected} == {
        ValueDisposition.VALID,
        ValueDisposition.ABSENT,
    }


def test_contract_consolidates_configured_and_undeclared_exclusions(
    tmp_path: Path,
) -> None:
    """Out-of-scope fields produce ordered summaries rather than per-record findings."""
    prepared = _prepare_mixed_comparison(tmp_path)

    result = _assess(prepared)

    assert result.exclusions == (
        ConfiguredFieldExclusion(canonical_field="excluded_field"),
        UndeclaredFieldExclusion(
            side=InputSide.REFERENCE,
            source_field="common_extra",
            record_count=2,
        ),
        UndeclaredFieldExclusion(
            side=InputSide.REFERENCE,
            source_field="reference_extra",
            record_count=1,
        ),
        UndeclaredFieldExclusion(
            side=InputSide.QUERY,
            source_field="common_extra",
            record_count=1,
        ),
        UndeclaredFieldExclusion(
            side=InputSide.QUERY,
            source_field="query_extra",
            record_count=2,
        ),
    )
    assert all(
        assessment.canonical_field != "excluded_field"
        for assessment in result.assessments
    )
    assert len(result.findings) == 6


def test_zero_record_headers_support_dataset_contract_checks_and_zero_counts(
    tmp_path: Path,
) -> None:
    """Tabular structure remains assessable without inventing record opportunities."""
    document = minimal_configuration()
    document["fields"]["definitions"]["header_only_excluded"] = _field(
        "excluded_reference",
        "excluded_query",
    )
    reference = _write(
        tmp_path / "reference.csv",
        "reference_id,header_extra\n",
    )
    query = _write(
        tmp_path / "query.tsv",
        "query_id\tobserved_value\tquery_extra\n",
    )
    configuration = _write(
        tmp_path / "configuration.yaml",
        yaml.safe_dump(document, sort_keys=False),
    )
    prepared = prepare_comparison(
        ComparisonInvocation(
            reference=reference,
            query=query,
            output=tmp_path / "evidence",
            configuration=configuration,
        )
    )

    result = _assess(prepared)

    assert result.status is ContractPhaseStatus.COMPLETE
    assert result.assessments == ()
    assert [
        (finding.code, finding.side, finding.canonical_field, finding.record)
        for finding in result.findings
    ] == [
        ("missing_required_field", InputSide.REFERENCE, "measured_value", None),
    ]
    assert result.findings[0].location is None
    assert result.exclusions == (
        ConfiguredFieldExclusion(canonical_field="header_only_excluded"),
        UndeclaredFieldExclusion(
            side=InputSide.REFERENCE,
            source_field="header_extra",
            record_count=0,
        ),
        UndeclaredFieldExclusion(
            side=InputSide.QUERY,
            source_field="query_extra",
            record_count=0,
        ),
    )


def test_empty_json_exposes_no_structure_for_dataset_missing_field_findings(
    tmp_path: Path,
) -> None:
    """Custom configuration permits empty JSON without inferring field absence."""
    reference = _write(tmp_path / "reference.json", "[]")
    query = _write(tmp_path / "query.json", "[]")
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

    result = _assess(prepared)

    assert result.status is ContractPhaseStatus.COMPLETE
    assert result.assessments == ()
    assert result.findings == ()
    assert result.exclusions == ()


def test_automatic_configuration_drives_contract_assessment_and_exclusions(
    tmp_path: Path,
) -> None:
    """Generated correspondence assesses common fields and excludes side-only ones."""
    reference = _write(
        tmp_path / "reference.json",
        '[{"record_id":"S1","shared":1,"reference_only":"context"}]',
    )
    query = _write(
        tmp_path / "query.json",
        '[{"record_id":"S1","shared":1,"query_only":"context"}]',
    )
    prepared = prepare_comparison(
        ComparisonInvocation(
            reference=reference,
            query=query,
            output=tmp_path / "evidence",
        )
    )

    result = _assess(prepared)

    assert result.status is ContractPhaseStatus.COMPLETE
    assert result.findings == ()
    assert [
        (
            assessment.side,
            assessment.record.canonical_identity,
            assessment.canonical_field,
            assessment.disposition,
        )
        for assessment in result.assessments
    ] == [
        (InputSide.REFERENCE, ("S1",), "record_id", ValueDisposition.VALID),
        (InputSide.REFERENCE, ("S1",), "shared", ValueDisposition.VALID),
        (InputSide.QUERY, ("S1",), "record_id", ValueDisposition.VALID),
        (InputSide.QUERY, ("S1",), "shared", ValueDisposition.VALID),
    ]
    assert result.exclusions == (
        UndeclaredFieldExclusion(
            side=InputSide.REFERENCE,
            source_field="reference_only",
            record_count=1,
        ),
        UndeclaredFieldExclusion(
            side=InputSide.QUERY,
            source_field="query_only",
            record_count=1,
        ),
    )
