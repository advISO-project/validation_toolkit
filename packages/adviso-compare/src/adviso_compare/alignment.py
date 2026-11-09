"""Align validated reference and query records by canonical identity."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from adviso_compare.inputs import InputSide, SourceLocation
from adviso_compare.records import KeyedRecord, RecordKey, RecordModel


class RecordsPhaseStatus(str, Enum):
    """Completion state of the records phase."""

    COMPLETE = "complete"


class RecordDisposition(str, Enum):
    """Relationship of one canonical key across the two datasets."""

    MATCHED = "matched"
    MISSING = "missing"
    EXTRA = "extra"


@dataclass(frozen=True, slots=True)
class RecordAlignment:
    """Reference and query records sharing one canonical key, where present."""

    key: RecordKey
    reference: KeyedRecord | None
    query: KeyedRecord | None
    disposition: RecordDisposition

    @property
    def canonical_identity(self) -> tuple[str, ...]:
        """Return the canonical textual key components in configured order."""
        record = self.reference if self.reference is not None else self.query
        if record is None:
            raise AssertionError("record alignment has neither side")
        return record.canonical_identity


@dataclass(frozen=True, slots=True)
class RecordFinding:
    """One missing- or extra-record difference for later evidence construction."""

    alignment: RecordAlignment

    @property
    def code(self) -> str:
        """Return the stable finding code implied by the alignment."""
        if self.alignment.disposition is RecordDisposition.MISSING:
            return "missing_record"
        if self.alignment.disposition is RecordDisposition.EXTRA:
            return "extra_record"
        raise AssertionError("matched alignment cannot produce a record finding")

    @property
    def classification(self) -> str:
        """Return the fixed classification for record differences."""
        return "comparison_difference"

    @property
    def phase(self) -> str:
        """Return the phase in which this difference was detected."""
        return "records"

    @property
    def affected_side(self) -> InputSide:
        """Return the side from which the aligned record is absent."""
        if self.alignment.disposition is RecordDisposition.MISSING:
            return InputSide.QUERY
        if self.alignment.disposition is RecordDisposition.EXTRA:
            return InputSide.REFERENCE
        raise AssertionError("matched alignment cannot affect a side")

    @property
    def reference_location(self) -> SourceLocation | None:
        """Return the reference record location, or None when it is absent."""
        if self.alignment.reference is None:
            return None
        return self.alignment.reference.record.location

    @property
    def query_location(self) -> SourceLocation | None:
        """Return the query record location, or None when it is absent."""
        if self.alignment.query is None:
            return None
        return self.alignment.query.record.location


@dataclass(frozen=True, slots=True)
class RecordCounts:
    """Reconciled record counts for later canonical summary generation."""

    reference: int
    query: int
    matched: int
    missing: int
    extra: int


@dataclass(frozen=True, slots=True)
class RecordsResult:
    """Complete deterministic alignment of two valid record models."""

    status: RecordsPhaseStatus
    alignments: tuple[RecordAlignment, ...]
    findings: tuple[RecordFinding, ...]
    counts: RecordCounts
    _alignment_index: Mapping[RecordKey, RecordAlignment]

    def alignment(self, record_key: RecordKey) -> RecordAlignment:
        """Return the alignment for one canonical record key."""
        return self._alignment_index[record_key]

    @property
    def matched(self) -> tuple[RecordAlignment, ...]:
        """Return safely aligned records available to the values phase."""
        return tuple(
            alignment
            for alignment in self.alignments
            if alignment.disposition is RecordDisposition.MATCHED
        )


def align_records(
    reference: RecordModel,
    query: RecordModel,
) -> RecordsResult:
    """Classify the union of two valid record-key indexes."""
    keys = set(reference.by_key) | set(query.by_key)
    ordered_keys = sorted(
        keys,
        key=lambda key: tuple(component.text for component in key),
    )
    alignments: list[RecordAlignment] = []
    findings: list[RecordFinding] = []

    for key in ordered_keys:
        reference_record = reference.by_key.get(key)
        query_record = query.by_key.get(key)
        if reference_record is not None and query_record is not None:
            disposition = RecordDisposition.MATCHED
        elif reference_record is not None:
            disposition = RecordDisposition.MISSING
        elif query_record is not None:
            disposition = RecordDisposition.EXTRA
        else:
            raise AssertionError("record-key union contains no record")
        alignment = RecordAlignment(
            key=key,
            reference=reference_record,
            query=query_record,
            disposition=disposition,
        )
        alignments.append(alignment)
        if disposition is not RecordDisposition.MATCHED:
            findings.append(RecordFinding(alignment))

    matched = sum(
        alignment.disposition is RecordDisposition.MATCHED
        for alignment in alignments
    )
    missing = sum(
        alignment.disposition is RecordDisposition.MISSING
        for alignment in alignments
    )
    extra = sum(
        alignment.disposition is RecordDisposition.EXTRA
        for alignment in alignments
    )
    alignment_tuple = tuple(alignments)
    return RecordsResult(
        status=RecordsPhaseStatus.COMPLETE,
        alignments=alignment_tuple,
        findings=tuple(findings),
        counts=RecordCounts(
            reference=len(reference.records),
            query=len(query.records),
            matched=matched,
            missing=missing,
            extra=extra,
        ),
        _alignment_index=MappingProxyType(
            {alignment.key: alignment for alignment in alignment_tuple}
        ),
    )
