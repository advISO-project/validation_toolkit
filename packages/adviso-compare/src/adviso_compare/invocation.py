"""Domain values at the command-line application boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ComparisonInvocation:
    """User-selected paths and overwrite authorization for one comparison."""

    reference: Path
    query: Path
    output: Path
    configuration: Path | None = None
    overwrite: bool = False


class ComparisonExecutor(Protocol):
    """Callable application boundary used by the command-line adapter."""

    def __call__(self, invocation: ComparisonInvocation) -> int:
        """Execute one comparison and return its process exit code."""
        ...
