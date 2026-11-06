"""Application orchestration boundary for AdvISO Compare."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from adviso_compare.configuration import (
    EffectiveConfiguration,
    load_comparison_configuration,
)
from adviso_compare.inputs import InputSide, ParsedDataset, load_dataset
from adviso_compare.invocation import ComparisonInvocation


@dataclass(frozen=True, slots=True)
class PreparedComparison:
    """Validated configuration selection and losslessly parsed input datasets."""

    invocation: ComparisonInvocation
    configuration: EffectiveConfiguration | None
    reference: ParsedDataset
    query: ParsedDataset


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
    return PreparedComparison(
        invocation=invocation,
        configuration=configuration,
        reference=reference,
        query=query,
    )


def execute_comparison(invocation: ComparisonInvocation) -> int:
    """Execute a comparison once later implementation increments supply the core."""
    raise NotImplementedError(
        "comparison execution is not available at this implementation stage"
    )
