"""Thin command-line adapter for adviso-compare."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version
from pathlib import Path
from typing import NoReturn, Sequence

from adviso_compare.configuration import ConfigurationError
from adviso_compare.inputs import InputError
from adviso_compare.invocation import ComparisonExecutor, ComparisonInvocation
from adviso_compare.records import RecordKeyError
from adviso_compare.reporting import OutputError


class _ArgumentParser(argparse.ArgumentParser):
    """Argument parser that emits the stable invocation-error diagnostic."""

    def error(self, message: str) -> NoReturn:
        """Report invalid command-line syntax without touching comparison inputs."""
        if not message.startswith("the following arguments are required:"):
            message = "invalid command-line arguments; use --help for usage"
        self.exit(2, f"ERROR [invocation.invalid_arguments]: {message}\n")


def _build_parser() -> argparse.ArgumentParser:
    """Construct the version 1 direct comparison interface."""
    parser = _ArgumentParser(
        prog="adviso-compare",
        description=(
            "Compare a reference dataset with a query dataset and write a "
            "three-file evidence package."
        ),
        epilog=(
            "Full user guide: share/doc/adviso-compare/user-guide.md in the "
            "Python installation."
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
        help="parent directory under which to create a new run directory",
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
    return parser


def parse_invocation(arguments: Sequence[str] | None = None) -> ComparisonInvocation:
    """Parse command-line text into an immutable comparison invocation."""
    namespace = _build_parser().parse_args(arguments)
    return ComparisonInvocation(
        reference=namespace.reference,
        query=namespace.query,
        output=namespace.output,
        configuration=namespace.configuration,
    )


def _display_output_path(path: Path) -> str:
    """Render a run path with its parent context but no absolute path."""
    if not path.is_absolute():
        return str(path)
    return str(Path(path.parent.name) / path.name)


def main(
    arguments: Sequence[str] | None = None,
    *,
    executor: ComparisonExecutor | None = None,
) -> int:
    """Execute one invocation behind the stable command-line error boundary."""
    try:
        invocation = parse_invocation(arguments)
        if executor is None:
            from adviso_compare.application import execute_comparison

            executor = execute_comparison
        outcome = executor(invocation)
    except (ConfigurationError, InputError, RecordKeyError, OutputError) as error:
        print(error.diagnostic, file=sys.stderr)
        return 2
    except MemoryError:
        print(
            "ERROR [resource.exhausted]: available memory was exhausted; "
            "reduce input size and retry",
            file=sys.stderr,
        )
        return 2
    except Exception:
        print(
            "ERROR [internal.unexpected]: an unexpected internal error occurred; "
            "rerun and report the failure if it persists",
            file=sys.stderr,
        )
        return 3

    print(f"Run status: {outcome.run_status}")
    print(f"Comparison differences: {outcome.comparison_differences}")
    print(f"Assessment issues: {outcome.assessment_issues}")
    print(f"Evidence package: {_display_output_path(outcome.output)}")
    return outcome.exit_code
