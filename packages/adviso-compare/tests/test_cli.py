"""Behavioural tests for the direct AdvISO Compare command line."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from importlib.metadata import version
from pathlib import Path

import pytest

from adviso_compare.cli import main, parse_invocation
from adviso_compare.invocation import ComparisonInvocation


@pytest.mark.parametrize(
    ("optional_arguments", "expected_configuration", "expected_overwrite"),
    [
        ([], None, False),
        (["--configuration", "rules.yaml", "--overwrite"], Path("rules.yaml"), True),
    ],
)
def test_direct_arguments_create_an_immutable_invocation_without_reading_inputs(
    optional_arguments: list[str],
    expected_configuration: Path | None,
    expected_overwrite: bool,
) -> None:
    """Parsing records paths and flags without requiring any path to exist."""
    arguments = [
        "--reference",
        "does-not-exist-reference.csv",
        "--query",
        "does-not-exist-query.json",
        "--output",
        "does-not-exist-output",
        *optional_arguments,
    ]

    invocation = parse_invocation(arguments)

    assert invocation == ComparisonInvocation(
        reference=Path("does-not-exist-reference.csv"),
        query=Path("does-not-exist-query.json"),
        output=Path("does-not-exist-output"),
        configuration=expected_configuration,
        overwrite=expected_overwrite,
    )
    with pytest.raises(FrozenInstanceError):
        invocation.overwrite = not expected_overwrite  # type: ignore[misc]


def test_main_dispatches_the_invocation_through_an_injected_executor() -> None:
    """CLI orchestration passes one domain value to an independently testable core."""
    received: list[ComparisonInvocation] = []

    def execute(invocation: ComparisonInvocation) -> int:
        received.append(invocation)
        return 17

    exit_code = main(
        [
            "--reference",
            "reference.csv",
            "--query",
            "query.tsv",
            "--output",
            "evidence",
        ],
        executor=execute,
    )

    assert exit_code == 17
    assert received == [
        ComparisonInvocation(
            reference=Path("reference.csv"),
            query=Path("query.tsv"),
            output=Path("evidence"),
        )
    ]


@pytest.mark.parametrize("missing_option", ["--reference", "--query", "--output"])
def test_each_required_argument_is_rejected_before_execution(
    missing_option: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Missing required paths are concise invocation errors and never reach the core."""
    arguments = [
        "--reference",
        "reference.csv",
        "--query",
        "query.csv",
        "--output",
        "evidence",
    ]
    option_index = arguments.index(missing_option)
    del arguments[option_index : option_index + 2]

    def unexpected_executor(invocation: ComparisonInvocation) -> int:
        raise AssertionError(f"executor received invalid invocation: {invocation!r}")

    with pytest.raises(SystemExit) as error:
        main(arguments, executor=unexpected_executor)

    captured = capsys.readouterr()
    assert error.value.code == 2
    assert captured.out == ""
    assert captured.err.startswith("ERROR [invocation.invalid_arguments]: ")
    assert missing_option in captured.err
    assert captured.err.count("\n") == 1


def test_subcommand_syntax_is_rejected_before_execution(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The executable accepts comparison options directly and has no subcommands."""
    arguments = [
        "compare",
        "--reference",
        "reference.csv",
        "--query",
        "query.csv",
        "--output",
        "evidence",
    ]

    def unexpected_executor(invocation: ComparisonInvocation) -> int:
        raise AssertionError(f"executor received invalid invocation: {invocation!r}")

    with pytest.raises(SystemExit) as error:
        main(arguments, executor=unexpected_executor)

    captured = capsys.readouterr()
    assert error.value.code == 2
    assert captured.out == ""
    assert captured.err == (
        "ERROR [invocation.invalid_arguments]: unrecognized arguments: compare\n"
    )


def test_help_documents_the_complete_direct_interface_and_user_guide(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Help works alone and describes every version 1 command-line option."""

    def unexpected_executor(invocation: ComparisonInvocation) -> int:
        raise AssertionError(f"executor was called for help: {invocation!r}")

    with pytest.raises(SystemExit) as error:
        main(["--help"], executor=unexpected_executor)

    captured = capsys.readouterr()
    assert error.value.code == 0
    assert captured.err == ""
    assert "usage: adviso-compare" in captured.out
    for option in (
        "--reference",
        "--query",
        "--output",
        "--configuration",
        "--overwrite",
        "--help",
        "--version",
    ):
        assert option in captured.out
    assert "user guide" in captured.out.lower()
    assert "subcommand" not in captured.out.lower()


def test_version_works_without_comparison_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Version reporting exits successfully without dispatching a comparison."""

    def unexpected_executor(invocation: ComparisonInvocation) -> int:
        raise AssertionError(f"executor was called for version: {invocation!r}")

    with pytest.raises(SystemExit) as error:
        main(["--version"], executor=unexpected_executor)

    captured = capsys.readouterr()
    assert error.value.code == 0
    assert captured.err == ""
    assert captured.out == f"adviso-compare {version('adviso-compare')}\n"

