"""Thin command-line adapter for AdvISO Compare."""

from __future__ import annotations

import argparse
from importlib.metadata import version
from pathlib import Path
from typing import NoReturn, Sequence

from adviso_compare.invocation import ComparisonExecutor, ComparisonInvocation


class _ArgumentParser(argparse.ArgumentParser):
    """Argument parser that emits the stable invocation-error diagnostic."""

    def error(self, message: str) -> NoReturn:
        """Report invalid command-line syntax without touching comparison inputs."""
        self.exit(2, f"ERROR [invocation.invalid_arguments]: {message}\n")


def _build_parser() -> argparse.ArgumentParser:
    """Construct the version 1 direct comparison interface."""
    parser = _ArgumentParser(
        prog="adviso-compare",
        description=(
            "Compare a reference dataset with a query dataset and write a "
            "two-file evidence package."
        ),
        epilog=(
            "See the AdvISO Compare user guide for complete usage, input-format, "
            "and comparison-configuration documentation."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('adviso-compare')}",
        help="show the installed software version and exit",
    )
    parser.add_argument(
        "--reference",
        required=True,
        type=Path,
        metavar="REFERENCE",
        help="reference dataset in CSV, TSV, or JSON format",
    )
    parser.add_argument(
        "--query",
        required=True,
        type=Path,
        metavar="QUERY",
        help="query dataset in CSV, TSV, or JSON format",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        metavar="OUTPUT",
        help="destination directory for the evidence package",
    )
    parser.add_argument(
        "--configuration",
        type=Path,
        metavar="CONFIGURATION",
        help=(
            "custom YAML comparison configuration; omit to use automatic "
            "strict-exact mode"
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing complete version 1 evidence package",
    )
    return parser


def parse_invocation(arguments: Sequence[str] | None = None) -> ComparisonInvocation:
    """Parse command-line text into an immutable comparison invocation."""
    namespace = _build_parser().parse_args(arguments)
    return ComparisonInvocation(
        reference=namespace.reference,
        query=namespace.query,
        output=namespace.output,
        configuration=namespace.configuration,
        overwrite=namespace.overwrite,
    )


def main(
    arguments: Sequence[str] | None = None,
    *,
    executor: ComparisonExecutor | None = None,
) -> int:
    """Parse one invocation and dispatch it to the comparison application."""
    invocation = parse_invocation(arguments)
    if executor is None:
        from adviso_compare.application import execute_comparison

        executor = execute_comparison
    return executor(invocation)

