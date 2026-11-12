"""Application orchestration boundary for adviso-compare."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from adviso_compare.alignment import align_records
from adviso_compare.configuration import (
    EffectiveConfiguration,
    load_comparison_configuration,
)
from adviso_compare.contract import assess_contract
from adviso_compare.inputs import InputSide, ParsedDataset, load_dataset
from adviso_compare.invocation import ComparisonInvocation, ComparisonOutcome
from adviso_compare.records import (
    RecordModel,
    build_record_model,
    generate_automatic_configuration,
)
from adviso_compare.reporting import publish_evidence_package
from adviso_compare.results import assemble_result
from adviso_compare.values import compare_values


@dataclass(frozen=True, slots=True)
class PreparedComparison:
    """Validated configuration selection and losslessly parsed input datasets."""

    invocation: ComparisonInvocation
    configuration: EffectiveConfiguration
    reference: ParsedDataset
    query: ParsedDataset
    reference_records: RecordModel
    query_records: RecordModel


def prepare_comparison(
    invocation: ComparisonInvocation,
    *,
    configuration_loader: Callable[
        [Path], EffectiveConfiguration
    ] = load_comparison_configuration,
    dataset_loader: Callable[[Path, InputSide], ParsedDataset] = load_dataset,
) -> PreparedComparison:
    """Validate any custom configuration before accessing either dataset."""
    configuration = None
    if invocation.configuration is not None:
        configuration = configuration_loader(invocation.configuration)
    reference = dataset_loader(invocation.reference, InputSide.REFERENCE)
    query = dataset_loader(invocation.query, InputSide.QUERY)
    if configuration is None:
        configuration = generate_automatic_configuration(reference, query)
    reference_records = build_record_model(
        reference,
        configuration,
        InputSide.REFERENCE,
    )
    query_records = build_record_model(
        query,
        configuration,
        InputSide.QUERY,
    )
    return PreparedComparison(
        invocation=invocation,
        configuration=configuration,
        reference=reference,
        query=query,
        reference_records=reference_records,
        query_records=query_records,
    )


def execute_comparison(invocation: ComparisonInvocation) -> ComparisonOutcome:
    """Run every comparison phase and publish its validated evidence package."""
    prepared = prepare_comparison(invocation)
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
    document = result.document()
    finding_counts = document["summary"]["findings"]["by_classification"]
    published = publish_evidence_package(invocation.output, result)
    return ComparisonOutcome(
        run_status=document["run"]["status"],
        output=published,
        comparison_differences=finding_counts["comparison_difference"],
        assessment_issues=finding_counts["assessment_issue"],
    )
