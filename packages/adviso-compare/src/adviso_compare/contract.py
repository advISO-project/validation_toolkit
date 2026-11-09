"""Assess the configured data contract without blocking unaffected content."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping, TypeAlias

from adviso_compare.configuration import EffectiveConfiguration, FieldDefinition
from adviso_compare.inputs import (
    InputFormat,
    InputSide,
    JsonLocation,
    ParsedDataset,
    SourceLocation,
    TabularLocation,
)
from adviso_compare.records import KeyedRecord, RecordKey, RecordModel
from adviso_compare.translation import (
    TranslatedValue,
    TranslationIssueCode,
    ValueDisposition,
    translate_field_value,
)


class ContractPhaseStatus(str, Enum):
    """Completion state of the contract phase."""

    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class FieldAssessment:
    """Translation outcome for one configured field on one source record."""

    side: InputSide
    record: KeyedRecord
    canonical_field: str
    source_field: str
    translated: TranslatedValue

    @property
    def disposition(self) -> ValueDisposition:
        """Return whether this field is valid, absent, or not assessable."""
        return self.translated.disposition

    @property
    def location(self) -> SourceLocation:
        """Return the field location, or containing record when absent."""
        if self.record.record.has_field(self.source_field):
            return self.record.record.location_for(self.source_field)
        return self.record.record.location


@dataclass(frozen=True, slots=True)
class ContractFinding:
    """One causal contract issue retained for later evidence construction."""

    code: str
    side: InputSide
    canonical_field: str
    review_priority: str
    record: KeyedRecord | None
    assessment: FieldAssessment | None

    @property
    def classification(self) -> str:
        """Return the fixed classification for contract translation issues."""
        return "assessment_issue"

    @property
    def phase(self) -> str:
        """Return the phase in which this issue was detected."""
        return "contract"

    @property
    def location(self) -> SourceLocation | None:
        """Return the attributable source location when a record exists."""
        if self.assessment is None:
            return None
        return self.assessment.location


@dataclass(frozen=True, slots=True)
class ConfiguredFieldExclusion:
    """One deliberately declared but out-of-scope canonical field."""

    canonical_field: str

    @property
    def code(self) -> str:
        """Return the stable exclusion code."""
        return "configured_field_excluded"


@dataclass(frozen=True, slots=True)
class UndeclaredFieldExclusion:
    """One observed source field not represented by a field definition."""

    side: InputSide
    source_field: str
    record_count: int

    @property
    def code(self) -> str:
        """Return the stable exclusion code."""
        return "undeclared_field_excluded"


FieldExclusion: TypeAlias = ConfiguredFieldExclusion | UndeclaredFieldExclusion
AssessmentIndex: TypeAlias = Mapping[
    tuple[InputSide, RecordKey, str], FieldAssessment
]


@dataclass(frozen=True, slots=True)
class ContractResult:
    """Complete contract outcomes needed by later comparison phases."""

    status: ContractPhaseStatus
    assessments: tuple[FieldAssessment, ...]
    findings: tuple[ContractFinding, ...]
    exclusions: tuple[FieldExclusion, ...]
    _assessment_index: AssessmentIndex

    def assessment(
        self,
        side: InputSide,
        record_key: RecordKey,
        canonical_field: str,
    ) -> FieldAssessment:
        """Return one field assessment by side, record key, and canonical name."""
        return self._assessment_index[(side, record_key, canonical_field)]


def assess_contract(
    configuration: EffectiveConfiguration,
    *,
    reference: ParsedDataset,
    query: ParsedDataset,
    reference_records: RecordModel,
    query_records: RecordModel,
) -> ContractResult:
    """Assess every applicable field contract and consolidate exclusions."""
    assessments: list[FieldAssessment] = []
    findings: list[ContractFinding] = []

    for side, model in (
        (InputSide.REFERENCE, reference_records),
        (InputSide.QUERY, query_records),
    ):
        for keyed_record in sorted(
            model.records,
            key=lambda item: item.canonical_identity,
        ):
            for canonical_field in sorted(configuration.in_scope):
                field = configuration.field(canonical_field)
                source_field = _for_side(field, side)
                source = (
                    keyed_record.record.value(source_field)
                    if keyed_record.record.has_field(source_field)
                    else None
                )
                translated = translate_field_value(source, field, side)
                assessment = FieldAssessment(
                    side=side,
                    record=keyed_record,
                    canonical_field=canonical_field,
                    source_field=source_field,
                    translated=translated,
                )
                assessments.append(assessment)
                if translated.disposition is ValueDisposition.NOT_ASSESSABLE:
                    findings.append(_finding_for(assessment, field))

        findings.extend(
            _zero_record_header_findings(
                configuration,
                reference if side is InputSide.REFERENCE else query,
                side,
                model,
            )
        )

    findings.sort(key=_finding_sort_key)
    exclusions = _collect_exclusions(configuration, reference, query)
    index = {
        (assessment.side, assessment.record.key, assessment.canonical_field): assessment
        for assessment in assessments
    }
    return ContractResult(
        status=ContractPhaseStatus.COMPLETE,
        assessments=tuple(assessments),
        findings=tuple(findings),
        exclusions=exclusions,
        _assessment_index=MappingProxyType(index),
    )


def _finding_for(
    assessment: FieldAssessment,
    field: FieldDefinition,
) -> ContractFinding:
    """Build the one causal finding for a failed field translation."""
    issue = assessment.translated.issue
    if issue is None:
        raise AssertionError("not-assessable translation has no causal issue")
    return ContractFinding(
        code=issue.code.value,
        side=assessment.side,
        canonical_field=assessment.canonical_field,
        review_priority=field.review_priority,
        record=assessment.record,
        assessment=assessment,
    )


def _zero_record_header_findings(
    configuration: EffectiveConfiguration,
    dataset: ParsedDataset,
    side: InputSide,
    model: RecordModel,
) -> list[ContractFinding]:
    """Assess required fields exposed by an empty tabular dataset's header."""
    if model.records:
        return []
    if dataset.provenance.format is InputFormat.JSON:
        return []

    findings: list[ContractFinding] = []
    for canonical_field in sorted(configuration.in_scope):
        field = configuration.field(canonical_field)
        source_field = _for_side(field, side)
        required = (
            field.required.reference
            if side is InputSide.REFERENCE
            else field.required.query
        )
        if required and source_field not in dataset.field_names:
            findings.append(
                ContractFinding(
                    code=TranslationIssueCode.MISSING_REQUIRED_FIELD.value,
                    side=side,
                    canonical_field=canonical_field,
                    review_priority=field.review_priority,
                    record=None,
                    assessment=None,
                )
            )
    return findings


def _collect_exclusions(
    configuration: EffectiveConfiguration,
    reference: ParsedDataset,
    query: ParsedDataset,
) -> tuple[FieldExclusion, ...]:
    """Return configured and undeclared exclusions in their specified order."""
    exclusions: list[FieldExclusion] = [
        ConfiguredFieldExclusion(canonical_field=name)
        for name in sorted(set(configuration.fields) - set(configuration.in_scope))
    ]
    for side, dataset in (
        (InputSide.REFERENCE, reference),
        (InputSide.QUERY, query),
    ):
        represented = {
            _for_side(field, side) for field in configuration.fields.values()
        }
        for source_field in sorted(set(dataset.field_names) - represented):
            exclusions.append(
                UndeclaredFieldExclusion(
                    side=side,
                    source_field=source_field,
                    record_count=sum(
                        record.has_field(source_field) for record in dataset.records
                    ),
                )
            )
    return tuple(exclusions)


def _finding_sort_key(finding: ContractFinding) -> tuple[object, ...]:
    """Apply the relevant prefix of the canonical total finding order."""
    code_order = {
        "missing_required_field": 2,
        "type_mismatch": 3,
        "invalid_field_value": 4,
        "null_policy_violation": 5,
        "mapping_failure": 6,
    }
    side_order = {InputSide.REFERENCE: 0, InputSide.QUERY: 1}
    return (
        finding.record is not None,
        finding.record.canonical_identity if finding.record is not None else (),
        finding.canonical_field,
        code_order[finding.code],
        side_order[finding.side],
        _location_sort_key(finding.location),
    )


def _location_sort_key(location: SourceLocation | None) -> tuple[object, ...]:
    """Return a deterministic order key for a possibly absent location."""
    if location is None:
        return (0,)
    if isinstance(location, TabularLocation):
        return (
            1,
            location.record_number,
            location.line_number,
            location.field_name or "",
        )
    if isinstance(location, JsonLocation):
        return (1, location.pointer)
    raise AssertionError("unknown source-location type")


def _for_side(field: FieldDefinition, side: InputSide) -> str:
    """Return one field's source name for the selected dataset side."""
    if side is InputSide.REFERENCE:
        return field.source_fields.reference
    return field.source_fields.query
