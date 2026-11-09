"""Compare every assessable non-key value in safely aligned records."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from adviso_compare.alignment import RecordAlignment, RecordsResult
from adviso_compare.comparators import compare_translated_values
from adviso_compare.configuration import EffectiveConfiguration
from adviso_compare.contract import ContractResult, FieldAssessment
from adviso_compare.inputs import InputSide, SourceLocation
from adviso_compare.translation import ValueDisposition


class ValuesPhaseStatus(str, Enum):
    """Completion state of the values phase."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class ValueOpportunityDisposition(str, Enum):
    """Outcome of one aligned, in-scope, non-key field opportunity."""

    MATCHED = "matched"
    MISMATCHED = "mismatched"
    NOT_ASSESSABLE = "not_assessable"


@dataclass(frozen=True, slots=True)
class ValueOpportunity:
    """One field comparison opportunity across an aligned record pair."""

    alignment: RecordAlignment
    canonical_field: str
    reference: FieldAssessment
    query: FieldAssessment
    disposition: ValueOpportunityDisposition


@dataclass(frozen=True, slots=True)
class ValueFinding:
    """One post-translation value difference for later evidence construction."""

    opportunity: ValueOpportunity
    review_priority: str

    @property
    def code(self) -> str:
        """Return the stable value-difference finding code."""
        return "value_mismatch"

    @property
    def classification(self) -> str:
        """Return the fixed classification for post-translation differences."""
        return "comparison_difference"

    @property
    def phase(self) -> str:
        """Return the phase in which the difference was detected."""
        return "values"

    @property
    def affected_side(self) -> Literal["both"]:
        """Return the fixed two-sided scope of a value comparison."""
        return "both"

    @property
    def canonical_field(self) -> str:
        """Return the compared canonical field name."""
        return self.opportunity.canonical_field

    @property
    def reference_location(self) -> SourceLocation:
        """Return the reference field or containing-record location."""
        return self.opportunity.reference.location

    @property
    def query_location(self) -> SourceLocation:
        """Return the query field or containing-record location."""
        return self.opportunity.query.location


@dataclass(frozen=True, slots=True)
class ValueCounts:
    """Complete counts of in-scope non-key value opportunities."""

    matched: int
    mismatched: int
    not_assessable: int


@dataclass(frozen=True, slots=True)
class ValuesResult:
    """All deterministic values-phase outcomes for safely aligned records."""

    status: ValuesPhaseStatus
    opportunities: tuple[ValueOpportunity, ...]
    findings: tuple[ValueFinding, ...]
    counts: ValueCounts


def compare_values(
    configuration: EffectiveConfiguration,
    contract: ContractResult,
    records: RecordsResult,
) -> ValuesResult:
    """Classify every aligned in-scope non-key value opportunity exactly once."""
    compared_fields = sorted(
        set(configuration.in_scope) - set(configuration.record_key)
    )
    opportunities: list[ValueOpportunity] = []
    findings: list[ValueFinding] = []

    for alignment in records.matched:
        if alignment.reference is None or alignment.query is None:
            raise AssertionError("matched alignment does not contain both records")
        for canonical_field in compared_fields:
            reference = contract.assessment(
                InputSide.REFERENCE,
                alignment.key,
                canonical_field,
            )
            query = contract.assessment(
                InputSide.QUERY,
                alignment.key,
                canonical_field,
            )
            disposition = _compare_opportunity(
                configuration,
                canonical_field,
                reference,
                query,
            )
            opportunity = ValueOpportunity(
                alignment=alignment,
                canonical_field=canonical_field,
                reference=reference,
                query=query,
                disposition=disposition,
            )
            opportunities.append(opportunity)
            if disposition is ValueOpportunityDisposition.MISMATCHED:
                findings.append(
                    ValueFinding(
                        opportunity=opportunity,
                        review_priority=configuration.field(
                            canonical_field
                        ).review_priority,
                    )
                )

    matched = sum(
        item.disposition is ValueOpportunityDisposition.MATCHED
        for item in opportunities
    )
    mismatched = sum(
        item.disposition is ValueOpportunityDisposition.MISMATCHED
        for item in opportunities
    )
    not_assessable = sum(
        item.disposition is ValueOpportunityDisposition.NOT_ASSESSABLE
        for item in opportunities
    )
    status = (
        ValuesPhaseStatus.INCOMPLETE
        if not_assessable
        else ValuesPhaseStatus.COMPLETE
    )
    return ValuesResult(
        status=status,
        opportunities=tuple(opportunities),
        findings=tuple(findings),
        counts=ValueCounts(
            matched=matched,
            mismatched=mismatched,
            not_assessable=not_assessable,
        ),
    )


def _compare_opportunity(
    configuration: EffectiveConfiguration,
    canonical_field: str,
    reference: FieldAssessment,
    query: FieldAssessment,
) -> ValueOpportunityDisposition:
    """Classify one opportunity from its two contract assessments."""
    if (
        reference.disposition is ValueDisposition.NOT_ASSESSABLE
        or query.disposition is ValueDisposition.NOT_ASSESSABLE
    ):
        return ValueOpportunityDisposition.NOT_ASSESSABLE
    if (
        reference.disposition is ValueDisposition.ABSENT
        and query.disposition is ValueDisposition.ABSENT
    ):
        return ValueOpportunityDisposition.MATCHED
    if (
        reference.disposition is ValueDisposition.ABSENT
        or query.disposition is ValueDisposition.ABSENT
    ):
        return ValueOpportunityDisposition.MISMATCHED
    if (
        reference.disposition is not ValueDisposition.VALID
        or query.disposition is not ValueDisposition.VALID
    ):
        raise AssertionError("value opportunity has an unexpected contract state")
    matches = compare_translated_values(
        configuration.field(canonical_field),
        reference.translated,
        query.translated,
    )
    if matches:
        return ValueOpportunityDisposition.MATCHED
    return ValueOpportunityDisposition.MISMATCHED
