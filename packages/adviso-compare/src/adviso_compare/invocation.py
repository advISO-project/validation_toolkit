"""Domain values at the command-line application boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class ComparisonInvocation:
    """User-selected paths and overwrite authorization for one comparison."""

    reference: Path
    query: Path
    output: Path
    configuration: Path | None = None
    overwrite: bool = False


@dataclass(frozen=True, slots=True)
class ComparisonOutcome:
    """Non-sensitive facts needed by the command-line completion summary."""

    run_status: Literal["complete", "incomplete"]
    output: Path
    comparison_differences: int
    assessment_issues: int

    @property
    def exit_code(self) -> int:
        """Return the stable process code for a non-error comparison."""
        return 0 if self.run_status == "complete" else 1


class ComparisonExecutor(Protocol):
    """Callable application boundary used by the command-line adapter."""

    def __call__(self, invocation: ComparisonInvocation) -> ComparisonOutcome:
        """Execute one comparison and return its non-sensitive outcome."""
        ...
