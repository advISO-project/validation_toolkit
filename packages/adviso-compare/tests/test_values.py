"""Behavioural tests for comparators and the values phase."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from adviso_compare.alignment import align_records
from adviso_compare.application import PreparedComparison, prepare_comparison
from adviso_compare.comparators import compare_translated_values
from adviso_compare.configuration import FieldDefinition, load_comparison_configuration
from adviso_compare.contract import ContractResult, assess_contract
from adviso_compare.inputs import InputSide, NativeCategory, NativeValue
from adviso_compare.invocation import ComparisonInvocation
from adviso_compare.translation import ValueDisposition, translate_field_value
from adviso_compare.values import (
    ValueOpportunityDisposition,
    ValuesPhaseStatus,
    compare_values,
)
from tests.support.documents import JsonObject, minimal_configuration


def _write(path: Path, text: str) -> Path:
    """Write one controlled UTF-8 document."""
    path.write_text(text, encoding="utf-8")
    return path


def _scalar_field(
    logical_type: str | None,
    comparator: str,
    *,
    parameters: JsonObject | None = None,
    source_normalisation: JsonObject | None = None,
) -> JsonObject:
    """Create one scalar field declaration for comparator tests."""
    field: JsonObject = {
        "source_fields": {
            "reference": "expected_value",
            "query": "observed_value",
        },
        "required": {"reference": True, "query": True},
        "null_policy": {"allowed": False, "nulls_equal": False},
        "comparator": {"name": comparator},
    }
    if logical_type is not None:
        field["logical_type"] = logical_type
    if parameters is not None:
        field["comparator"]["parameters"] = parameters
    if source_normalisation is not None:
        field["source_normalisation"] = source_normalisation
    return field


def _collection_field(
    collection_type: str,
    element_type: str,
    *,
    element_comparator: str = "typed_exact",
    element_parameters: JsonObject | None = None,
) -> JsonObject:
    """Create one collection field declaration for comparator tests."""
    comparator: JsonObject = {"name": element_comparator}
    if element_parameters is not None:
        comparator["parameters"] = element_parameters
    return {
        "source_fields": {
            "reference": "expected_value",
            "query": "observed_value",
        },
        "required": {"reference": True, "query": True},
        "logical_type": {
            "collection_type": collection_type,
            "element_type": element_type,
            "element_comparator": comparator,
        },
        "null_policy": {"allowed": False, "nulls_equal": False},
        "comparator": {"name": f"{collection_type}_exact"},
    }


def _array(*values: str) -> NativeValue:
    """Create a parser-native array of string elements."""
    return NativeValue(
        NativeCategory.ARRAY,
        tuple(NativeValue(NativeCategory.STRING, value) for value in values),
    )


def _object(*members: tuple[str, NativeValue]) -> NativeValue:
    """Create one parser-native object retaining the supplied member order."""
    return NativeValue(NativeCategory.OBJECT, members)


def _resolved_field(tmp_path: Path, declaration: JsonObject) -> FieldDefinition:
    """Resolve one test field through the normative configuration boundary."""
    document = minimal_configuration()
    document["fields"]["definitions"]["measured_value"] = declaration
    path = _write(
        tmp_path / "configuration.yaml",
        yaml.safe_dump(document, sort_keys=False),
    )
    return load_comparison_configuration(path).field("measured_value")


@pytest.mark.parametrize(
    (
        "declaration",
        "reference_source",
        "query_source",
        "expected",
    ),
    [
        (
            _scalar_field(None, "preserved_exact"),
            _object(
                ("a", NativeValue(NativeCategory.DECIMAL, Decimal("1.0"), "1.0")),
                ("b", _array("x", "y")),
            ),
            _object(
                ("b", _array("x", "y")),
                (
                    "a",
                    NativeValue(
                        NativeCategory.DECIMAL,
                        Decimal("1.00"),
                        "1.00",
                    ),
                ),
            ),
            True,
        ),
        (
            _scalar_field(None, "preserved_exact"),
            _array("x", "y"),
            _array("y", "x"),
            False,
        ),
        (
            _scalar_field(None, "preserved_exact"),
            NativeValue(NativeCategory.STRING, "1"),
            NativeValue(NativeCategory.INTEGER, 1, "1"),
            False,
        ),
        (
            _scalar_field("string", "typed_exact"),
            NativeValue(NativeCategory.STRING, "same"),
            NativeValue(NativeCategory.STRING, "same"),
            True,
        ),
        (
            _scalar_field(
                "string",
                "normalised_string",
                source_normalisation={
                    "reference": [{"operation": "case_fold"}],
                },
            ),
            NativeValue(NativeCategory.STRING, "Alpha"),
            NativeValue(NativeCategory.STRING, "alpha"),
            True,
        ),
        (
            _scalar_field("decimal", "numeric_exact"),
            NativeValue(NativeCategory.STRING, "1.00"),
            NativeValue(NativeCategory.STRING, "1e0"),
            True,
        ),
        (
            _scalar_field("integer", "numeric_exact"),
            NativeValue(NativeCategory.STRING, "01"),
            NativeValue(NativeCategory.STRING, "1"),
            True,
        ),
        (
            _scalar_field("date", "date_exact"),
            NativeValue(NativeCategory.STRING, "2026-11-09"),
            NativeValue(NativeCategory.STRING, "2026-11-09"),
            True,
        ),
        (
            _scalar_field("datetime", "datetime_exact"),
            NativeValue(NativeCategory.STRING, "2026-11-09T12:00:00Z"),
            NativeValue(NativeCategory.STRING, "2026-11-09T13:00:00+01:00"),
            True,
        ),
        (
            _collection_field("list", "integer"),
            _array("1", "2"),
            _array("2", "1"),
            False,
        ),
        (
            _collection_field("list", "integer"),
            _array("1", "2"),
            _array("1"),
            False,
        ),
        (
            _collection_field(
                "list",
                "decimal",
                element_comparator="numeric_tolerance",
                element_parameters={"absolute_tolerance": "0.1"},
            ),
            _array("1.0", "2.0"),
            _array("1.1", "2.1"),
            True,
        ),
        (
            _collection_field("set", "integer"),
            _array("10", "2"),
            _array("2", "10"),
            True,
        ),
        (
            _collection_field("multiset", "string"),
            _array("a", "b", "b"),
            _array("b", "a", "b"),
            True,
        ),
        (
            _collection_field("multiset", "string"),
            _array("a", "b", "b"),
            _array("a", "b"),
            False,
        ),
    ],
    ids=[
        "preserved-object-member-order",
        "preserved-array-order",
        "preserved-native-category",
        "typed-exact",
        "normalised-string",
        "numeric-exact",
        "integer-numeric-exact",
        "date-exact",
        "datetime-exact",
        "list-order",
        "list-length",
        "list-element-tolerance",
        "set-order",
        "multiset-order",
        "multiset-counts",
    ],
)
def test_fixed_comparator_matrix(
    tmp_path: Path,
    declaration: JsonObject,
    reference_source: NativeValue,
    query_source: NativeValue,
    expected: bool,
) -> None:
    """Every registered comparator applies its specified canonical semantics."""
    field = _resolved_field(tmp_path, declaration)
    reference = translate_field_value(reference_source, field, InputSide.REFERENCE)
    query = translate_field_value(query_source, field, InputSide.QUERY)

    assert reference.disposition is ValueDisposition.VALID
    assert query.disposition is ValueDisposition.VALID
    assert compare_translated_values(field, reference, query) is expected


@pytest.mark.parametrize(
    ("parameters", "reference", "query", "expected"),
    [
        ({"absolute_tolerance": "0.1"}, "1", "1.1", True),
        ({"absolute_tolerance": "0.1"}, "1", "0.9", True),
        ({"absolute_tolerance": "0.1"}, "1", "1.1000000000000000001", False),
        ({"relative_tolerance": "0.05"}, "100", "105", True),
        ({"relative_tolerance": "0.05"}, "100", "95", True),
        ({"relative_tolerance": "0.05"}, "100", "105.0000000000000001", False),
        ({"relative_tolerance": "0.05"}, "105.1", "100", True),
        ({"relative_tolerance": "0.05"}, "-100", "-105", True),
        ({"relative_tolerance": "0.05"}, "0", "0", True),
        ({"relative_tolerance": "0.05"}, "0", "0.0000000000000001", False),
    ],
    ids=[
        "absolute-upper-bound", "absolute-lower-bound",
        "above-absolute-bound", "relative-upper-bound",
        "relative-lower-bound", "above-relative-bound",
        "reference-directed-relative-bound", "negative-reference",
        "zero-reference-equal", "zero-reference-unequal",
    ],
)
def test_numeric_tolerance_is_exact_inclusive_and_reference_directed(
    tmp_path: Path,
    parameters: JsonObject,
    reference: str,
    query: str,
    expected: bool,
) -> None:
    """Tolerance arithmetic remains exact at boundaries and around zero."""
    field = _resolved_field(
        tmp_path,
        _scalar_field("decimal", "numeric_tolerance", parameters=parameters),
    )
    reference_value = translate_field_value(
        NativeValue(NativeCategory.STRING, reference),
        field,
        InputSide.REFERENCE,
    )
    query_value = translate_field_value(
        NativeValue(NativeCategory.STRING, query),
        field,
        InputSide.QUERY,
    )

    assert compare_translated_values(field, reference_value, query_value) is expected


def _comparison_field(
    reference_name: str,
    query_name: str,
    *,
    required: bool = True,
    nullable: bool = False,
    nulls_equal: bool = False,
    review_priority: str | None = None,
) -> JsonObject:
    """Create one decimal field for a mixed values-phase fixture."""
    field = _scalar_field("decimal", "numeric_exact")
    field["source_fields"] = {
        "reference": reference_name,
        "query": query_name,
    }
    field["required"] = {"reference": required, "query": required}
    field["null_policy"] = {
        "allowed": nullable,
        "nulls_equal": nulls_equal,
    }
    if review_priority is not None:
        field["review_priority"] = review_priority
    return field


def _mixed_configuration() -> JsonObject:
    """Declare every values-phase disposition plus one excluded field."""
    document = minimal_configuration()
    fields = document["fields"]
    fields["in_scope"] = [
        "record_id",
        "exact_match",
        "difference",
        "blocked",
        "optional_both_absent",
        "optional_one_absent",
        "nullable_both",
        "nullable_mixed",
        "nullable_not_equal",
    ]
    definitions = fields["definitions"]
    definitions.pop("measured_value")
    definitions["exact_match"] = _comparison_field("r_match", "q_match")
    definitions["difference"] = _comparison_field(
        "r_difference",
        "q_difference",
        review_priority="high",
    )
    definitions["blocked"] = _comparison_field("r_blocked", "q_blocked")
    definitions["optional_both_absent"] = _comparison_field(
        "r_optional_both",
        "q_optional_both",
        required=False,
    )
    definitions["optional_one_absent"] = _comparison_field(
        "r_optional_one",
        "q_optional_one",
        required=False,
        review_priority="low",
    )
    definitions["nullable_both"] = _comparison_field(
        "r_nullable_both",
        "q_nullable_both",
        nullable=True,
        nulls_equal=True,
    )
    definitions["nullable_mixed"] = _comparison_field(
        "r_nullable_mixed",
        "q_nullable_mixed",
        nullable=True,
        nulls_equal=True,
    )
    definitions["nullable_not_equal"] = _comparison_field(
        "r_nullable_not_equal",
        "q_nullable_not_equal",
        nullable=True,
        nulls_equal=False,
    )
    definitions["excluded"] = _comparison_field("r_excluded", "q_excluded")
    return document


def _prepare_mixed(tmp_path: Path) -> PreparedComparison:
    """Prepare one aligned record containing every value opportunity state."""
    reference = _write(
        tmp_path / "reference.json",
        (
            '[{"reference_id":"S1","r_match":1,"r_difference":1,'
            '"r_blocked":1,"r_optional_one":1,"r_nullable_both":null,'
            '"r_nullable_mixed":null,"r_nullable_not_equal":null,'
            '"r_excluded":1},'
            '{"reference_id":"S2","r_match":1,"r_difference":1,'
            '"r_blocked":1,"r_nullable_both":null,'
            '"r_nullable_mixed":null,"r_nullable_not_equal":null,'
            '"r_excluded":1}]'
        ),
    )
    query = _write(
        tmp_path / "query.json",
        (
            '[{"query_id":"S1","q_match":1,"q_difference":2,'
            '"q_nullable_both":null,"q_nullable_mixed":1,'
            '"q_nullable_not_equal":null,"q_excluded":1},'
            '{"query_id":"S3","q_match":1,"q_difference":1,'
            '"q_blocked":1,"q_nullable_both":null,"q_nullable_mixed":1,'
            '"q_nullable_not_equal":null,"q_excluded":1}]'
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


def _contract(prepared: PreparedComparison) -> ContractResult:
    """Assess a prepared comparison through the contract boundary."""
    return assess_contract(
        prepared.configuration,
        reference=prepared.reference,
        query=prepared.query,
        reference_records=prepared.reference_records,
        query_records=prepared.query_records,
    )


def test_mixed_values_phase_accounts_for_every_configured_opportunity(
    tmp_path: Path,
) -> None:
    """Blocked values coexist with all assessable matches and differences."""
    prepared = _prepare_mixed(tmp_path)
    contract = _contract(prepared)
    records = align_records(prepared.reference_records, prepared.query_records)

    result = compare_values(prepared.configuration, contract, records)

    assert result.status is ValuesPhaseStatus.INCOMPLETE
    assert (
        records.counts.reference,
        records.counts.query,
        records.counts.matched,
        records.counts.missing,
        records.counts.extra,
    ) == (2, 2, 1, 1, 1)
    assert {
        opportunity.alignment.canonical_identity
        for opportunity in result.opportunities
    } == {("S1",)}
    assert [
        (opportunity.canonical_field, opportunity.disposition)
        for opportunity in result.opportunities
    ] == [
        ("blocked", ValueOpportunityDisposition.NOT_ASSESSABLE),
        ("difference", ValueOpportunityDisposition.MISMATCHED),
        ("exact_match", ValueOpportunityDisposition.MATCHED),
        ("nullable_both", ValueOpportunityDisposition.MATCHED),
        ("nullable_mixed", ValueOpportunityDisposition.MISMATCHED),
        ("nullable_not_equal", ValueOpportunityDisposition.MISMATCHED),
        ("optional_both_absent", ValueOpportunityDisposition.MATCHED),
        ("optional_one_absent", ValueOpportunityDisposition.MISMATCHED),
    ]
    assert (
        result.counts.matched,
        result.counts.mismatched,
        result.counts.not_assessable,
    ) == (3, 4, 1)
    assert len(result.opportunities) == sum(
        (
            result.counts.matched,
            result.counts.mismatched,
            result.counts.not_assessable,
        )
    )
    assert [
        (finding.canonical_field, finding.review_priority)
        for finding in result.findings
    ] == [
        ("difference", "high"),
        ("nullable_mixed", "normal"),
        ("nullable_not_equal", "normal"),
        ("optional_one_absent", "low"),
    ]
    assert all(
        finding.code == "value_mismatch"
        and finding.classification == "comparison_difference"
        and finding.phase == "values"
        and finding.affected_side == "both"
        for finding in result.findings
    )
    assert len(contract.findings) == 1
    assert contract.findings[0].code == "missing_required_field"
    assert "excluded" not in {
        opportunity.canonical_field for opportunity in result.opportunities
    }


def test_automatic_configuration_flows_through_the_values_phase(
    tmp_path: Path,
) -> None:
    """Automatic mode compares shared fields and excludes one-sided context."""
    reference = _write(
        tmp_path / "reference.json",
        (
            '[{"record_id":"S1","same":1,"different":"expected",'
            '"reference_only":"context"}]'
        ),
    )
    query = _write(
        tmp_path / "query.json",
        (
            '[{"record_id":"S1","same":1,"different":"observed",'
            '"query_only":"context"}]'
        ),
    )
    prepared = prepare_comparison(
        ComparisonInvocation(
            reference=reference,
            query=query,
            output=tmp_path / "evidence",
        )
    )
    contract = _contract(prepared)
    result = compare_values(
        prepared.configuration,
        contract,
        align_records(prepared.reference_records, prepared.query_records),
    )

    assert prepared.configuration.in_scope == (
        "record_id",
        "different",
        "same",
    )
    assert {
        exclusion.source_field for exclusion in contract.exclusions
    } == {"query_only", "reference_only"}
    assert [
        (opportunity.canonical_field, opportunity.disposition)
        for opportunity in result.opportunities
    ] == [
        ("different", ValueOpportunityDisposition.MISMATCHED),
        ("same", ValueOpportunityDisposition.MATCHED),
    ]
    assert result.status is ValuesPhaseStatus.COMPLETE
    assert (
        result.counts.matched,
        result.counts.mismatched,
        result.counts.not_assessable,
    ) == (1, 1, 0)
    assert [finding.canonical_field for finding in result.findings] == [
        "different"
    ]


def test_value_mismatches_do_not_make_the_values_phase_incomplete(
    tmp_path: Path,
) -> None:
    """A completed unequal comparison is a finding, not an incomplete assessment."""
    reference = _write(
        tmp_path / "reference.json",
        '[{"reference_id":"S1","expected_value":1}]',
    )
    query = _write(
        tmp_path / "query.json",
        '[{"query_id":"S1","observed_value":2}]',
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
    result = compare_values(
        prepared.configuration,
        _contract(prepared),
        align_records(prepared.reference_records, prepared.query_records),
    )

    assert result.status is ValuesPhaseStatus.COMPLETE
    assert result.counts.mismatched == 1
    assert len(result.findings) == 1
