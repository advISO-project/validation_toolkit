"""Behavioural tests for deterministic record alignment."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from adviso_compare.alignment import (
    RecordDisposition,
    RecordsResult,
    RecordsPhaseStatus,
    align_records,
)
from adviso_compare.application import PreparedComparison, prepare_comparison
from adviso_compare.inputs import InputSide, JsonLocation
from adviso_compare.invocation import ComparisonInvocation
from tests.support.documents import JsonObject, minimal_configuration


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
    """Prepare two JSON datasets with an optional custom configuration."""
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


def _align(prepared: PreparedComparison) -> RecordsResult:
    """Align the prepared record models through the records-phase boundary."""
    return align_records(
        prepared.reference_records,
        prepared.query_records,
    )


def test_reordered_inputs_have_the_same_complete_alignment(tmp_path: Path) -> None:
    """Input occurrence order does not affect matches or canonical ordering."""
    first = _prepare(
        tmp_path,
        '[{"record_id":"S2","value":2},{"record_id":"S1","value":1}]',
        '[{"record_id":"S1","value":1},{"record_id":"S2","value":2}]',
    )
    second_path = tmp_path / "reordered"
    second_path.mkdir()
    second = _prepare(
        second_path,
        '[{"record_id":"S1","value":1},{"record_id":"S2","value":2}]',
        '[{"record_id":"S2","value":2},{"record_id":"S1","value":1}]',
    )

    first_result = _align(first)
    second_result = _align(second)

    assert first_result.status is RecordsPhaseStatus.COMPLETE
    assert first_result.findings == second_result.findings == ()
    assert [
        (alignment.canonical_identity, alignment.disposition)
        for alignment in first_result.alignments
    ] == [
        (("S1",), RecordDisposition.MATCHED),
        (("S2",), RecordDisposition.MATCHED),
    ]
    assert [
        (alignment.canonical_identity, alignment.disposition)
        for alignment in second_result.alignments
    ] == [
        (("S1",), RecordDisposition.MATCHED),
        (("S2",), RecordDisposition.MATCHED),
    ]
    assert first_result.counts == second_result.counts


def test_composite_keys_preserve_multiple_records_for_one_sample(
    tmp_path: Path,
) -> None:
    """Ordered composite identity aligns distinct records sharing a sample ID."""
    configuration = minimal_configuration()
    fields = configuration["fields"]
    fields["record_key"] = ["record_id", "batch"]
    fields["in_scope"].insert(1, "batch")
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
    prepared = _prepare(
        tmp_path,
        (
            '[{"reference_id":"S1","reference_batch":"01"},'
            '{"reference_id":"S1","reference_batch":"02"}]'
        ),
        (
            '[{"query_id":"S1","query_batch":"2"},'
            '{"query_id":"S1","query_batch":"1"}]'
        ),
        configuration,
    )

    result = _align(prepared)

    assert [alignment.canonical_identity for alignment in result.alignments] == [
        ("S1", "1"),
        ("S1", "2"),
    ]
    assert all(
        alignment.disposition is RecordDisposition.MATCHED
        for alignment in result.alignments
    )
    assert [
        (
            alignment.reference.source_identity,
            alignment.query.source_identity,
        )
        for alignment in result.alignments
        if alignment.reference is not None and alignment.query is not None
    ] == [
        (("S1", "01"), ("S1", "1")),
        (("S1", "02"), ("S1", "2")),
    ]


def test_missing_and_extra_records_are_all_reported_deterministically(
    tmp_path: Path,
) -> None:
    """The union retains its matched intersection and every one-sided record."""
    prepared = _prepare(
        tmp_path,
        (
            '[{"record_id":"S3"},{"record_id":"S1"},'
            '{"record_id":"S2"}]'
        ),
        (
            '[{"record_id":"S5"},{"record_id":"S1"},'
            '{"record_id":"S4"}]'
        ),
    )

    result = _align(prepared)
    reordered_path = tmp_path / "reordered"
    reordered_path.mkdir()
    reordered = _prepare(
        reordered_path,
        (
            '[{"record_id":"S2"},{"record_id":"S3"},'
            '{"record_id":"S1"}]'
        ),
        (
            '[{"record_id":"S4"},{"record_id":"S5"},'
            '{"record_id":"S1"}]'
        ),
    )
    reordered_result = _align(reordered)

    assert result.status is RecordsPhaseStatus.COMPLETE
    alignment_outcome = [
        (alignment.canonical_identity, alignment.disposition)
        for alignment in result.alignments
    ]
    assert alignment_outcome == [
        (("S1",), RecordDisposition.MATCHED),
        (("S2",), RecordDisposition.MISSING),
        (("S3",), RecordDisposition.MISSING),
        (("S4",), RecordDisposition.EXTRA),
        (("S5",), RecordDisposition.EXTRA),
    ]
    assert [
        (alignment.canonical_identity, alignment.disposition)
        for alignment in reordered_result.alignments
    ] == alignment_outcome
    finding_outcome = [
        (
            finding.code,
            finding.affected_side,
            finding.alignment.canonical_identity,
            finding.alignment.reference.source_identity
            if finding.alignment.reference is not None
            else None,
            finding.alignment.query.source_identity
            if finding.alignment.query is not None
            else None,
        )
        for finding in result.findings
    ]
    assert finding_outcome == [
        ("missing_record", InputSide.QUERY, ("S2",), ("S2",), None),
        ("missing_record", InputSide.QUERY, ("S3",), ("S3",), None),
        ("extra_record", InputSide.REFERENCE, ("S4",), None, ("S4",)),
        ("extra_record", InputSide.REFERENCE, ("S5",), None, ("S5",)),
    ]
    assert [
        (
            finding.code,
            finding.affected_side,
            finding.alignment.canonical_identity,
            finding.alignment.reference.source_identity
            if finding.alignment.reference is not None
            else None,
            finding.alignment.query.source_identity
            if finding.alignment.query is not None
            else None,
        )
        for finding in reordered_result.findings
    ] == finding_outcome
    assert all(
        finding.classification == "comparison_difference"
        and finding.phase == "records"
        for finding in result.findings
    )
    assert result.findings[0].reference_location == JsonLocation("/2")
    assert result.findings[0].query_location is None
    assert result.findings[-1].reference_location is None
    assert result.findings[-1].query_location == JsonLocation("/0")
    assert [
        (finding.reference_location, finding.query_location)
        for finding in reordered_result.findings
    ] != [
        (finding.reference_location, finding.query_location)
        for finding in result.findings
    ]
    assert result.matched == (result.alignments[0],)
    assert result.alignment(result.matched[0].key) is result.matched[0]
    assert reordered_result.counts == result.counts
    assert result.counts.reference == result.counts.matched + result.counts.missing
    assert result.counts.query == result.counts.matched + result.counts.extra
    assert (
        result.counts.reference,
        result.counts.query,
        result.counts.matched,
        result.counts.missing,
        result.counts.extra,
    ) == (3, 3, 1, 2, 2)


@pytest.mark.parametrize(
    ("reference_text", "query_text", "expected_counts", "finding_codes"),
    [
        ("[]", "[]", (0, 0, 0, 0, 0), ()),
        (
            '[{"reference_id":"S1"}]',
            "[]",
            (1, 0, 0, 1, 0),
            ("missing_record",),
        ),
        (
            "[]",
            '[{"query_id":"S1"}]',
            (0, 1, 0, 0, 1),
            ("extra_record",),
        ),
    ],
)
def test_empty_and_one_sided_datasets_reconcile_without_special_cases(
    tmp_path: Path,
    reference_text: str,
    query_text: str,
    expected_counts: tuple[int, int, int, int, int],
    finding_codes: tuple[str, ...],
) -> None:
    """The same union rules cover empty, reference-only, and query-only inputs."""
    prepared = _prepare(
        tmp_path,
        reference_text,
        query_text,
        minimal_configuration(),
    )

    result = _align(prepared)

    assert result.status is RecordsPhaseStatus.COMPLETE
    assert (
        result.counts.reference,
        result.counts.query,
        result.counts.matched,
        result.counts.missing,
        result.counts.extra,
    ) == expected_counts
    assert tuple(finding.code for finding in result.findings) == finding_codes
