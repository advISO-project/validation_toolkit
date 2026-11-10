"""Behavioural tests for the direct AdvISO Compare command line."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from importlib.metadata import version
from pathlib import Path

import pytest
import yaml

import adviso_compare.cli as cli
from adviso_compare.cli import main, parse_invocation
from adviso_compare.configuration import ConfigurationError
from adviso_compare.inputs import InputError, InputSide
from adviso_compare.invocation import ComparisonInvocation, ComparisonOutcome
from adviso_compare.records import RecordKeyError
from adviso_compare.reporting import OutputError
from adviso_compare.results import ResultValidationError
from tests.support.documents import minimal_configuration


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


def test_main_dispatches_the_invocation_through_an_injected_executor(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI orchestration passes one domain value to an independently testable core."""
    received: list[ComparisonInvocation] = []

    def execute(invocation: ComparisonInvocation) -> ComparisonOutcome:
        received.append(invocation)
        return ComparisonOutcome(
            run_status="complete",
            output=invocation.output,
            comparison_differences=2,
            assessment_issues=1,
        )

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

    assert exit_code == 0
    assert received == [
        ComparisonInvocation(
            reference=Path("reference.csv"),
            query=Path("query.tsv"),
            output=Path("evidence"),
        )
    ]
    assert capsys.readouterr().out.endswith("Evidence package: evidence\n")


@pytest.mark.parametrize(
    (
        "automatic",
        "incomplete",
        "expected_exit",
        "expected_status",
        "expected_differences",
        "expected_issues",
    ),
    [
        (False, False, 0, "complete", 1, 0),
        (False, True, 1, "incomplete", 0, 1),
        (True, False, 0, "complete", 1, 0),
    ],
)
def test_cli_executes_custom_automatic_and_incomplete_comparisons_end_to_end(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    automatic: bool,
    incomplete: bool,
    expected_exit: int,
    expected_status: str,
    expected_differences: int,
    expected_issues: int,
) -> None:
    """The default executor writes evidence and reports a non-sensitive summary."""
    if automatic:
        reference_text = '[{"record_id":"S1","result":1}]'
        query_text = '[{"record_id":"S1","result":2}]'
        configuration_arguments: list[str] = []
    else:
        reference_text = '[{"reference_id":"S1","expected_value":1}]'
        query_text = (
            '[{"query_id":"S1"}]'
            if incomplete
            else '[{"query_id":"S1","observed_value":2}]'
        )
        configuration = tmp_path / "configuration.yaml"
        configuration.write_text(
            yaml.safe_dump(minimal_configuration(), sort_keys=False),
            encoding="utf-8",
        )
        configuration_arguments = ["--configuration", str(configuration)]
    reference = tmp_path / "reference.json"
    query = tmp_path / "query.json"
    output = tmp_path / "evidence"
    reference.write_text(reference_text, encoding="utf-8")
    query.write_text(query_text, encoding="utf-8")

    exit_code = main(
        [
            "--reference",
            str(reference),
            "--query",
            str(query),
            "--output",
            str(output),
            *configuration_arguments,
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == expected_exit
    assert captured.err == ""
    assert captured.out == (
        f"Run status: {expected_status}\n"
        f"Comparison differences: {expected_differences}\n"
        f"Assessment issues: {expected_issues}\n"
        f"Evidence package: {output.name}\n"
    )
    assert str(tmp_path) not in captured.out
    assert sorted(path.name for path in output.iterdir()) == [
        "comparison-report.html",
        "comparison-results.json",
    ]


@pytest.mark.parametrize(
    ("error", "expected_diagnostic"),
    [
        (
            ConfigurationError("schema_violation", "rules.yaml", "is invalid"),
            "ERROR [configuration.schema_violation]: rules.yaml: is invalid\n",
        ),
        (
            InputError("invalid_syntax", InputSide.QUERY, "query input is invalid"),
            "ERROR [input.invalid_syntax]: query input is invalid\n",
        ),
        (
            RecordKeyError("no automatic record key could be established"),
            "ERROR [input.invalid_record_key]: no automatic record key could be established\n",
        ),
        (
            OutputError("invalid_destination", "output already exists"),
            "ERROR [output.invalid_destination]: output already exists\n",
        ),
    ],
)
def test_expected_execution_errors_have_stable_diagnostics_and_exit_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
    expected_diagnostic: str,
) -> None:
    """Classified operational failures publish nothing and omit tracebacks."""
    output = tmp_path / "evidence"

    def fail(_: ComparisonInvocation) -> ComparisonOutcome:
        raise error

    exit_code = main(
        [
            "--reference",
            "reference.json",
            "--query",
            "query.json",
            "--output",
            str(output),
        ],
        executor=fail,
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == expected_diagnostic
    assert "Traceback" not in captured.err
    assert not output.exists()


def test_default_executor_reports_an_input_error_without_partial_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An integrated operational failure uses the same safe error boundary."""
    output = tmp_path / "evidence"

    exit_code = main(
        [
            "--reference",
            str(tmp_path / "missing-reference.json"),
            "--query",
            str(tmp_path / "unused-query.json"),
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == (
        "ERROR [input.unreadable]: reference input could not be read\n"
    )
    assert not output.exists()


@pytest.mark.parametrize(
    ("error", "expected_diagnostic", "expected_exit"),
    [
        (
            MemoryError(),
            "ERROR [resource.exhausted]: available memory was exhausted; "
            "reduce input size and retry\n",
            2,
        ),
        (
            ResultValidationError("sensitive implementation detail"),
            "ERROR [internal.unexpected]: an unexpected internal error occurred; "
            "rerun and report the failure if it persists\n",
            3,
        ),
    ],
)
def test_resource_exhaustion_and_unexpected_failures_are_safely_isolated(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
    expected_diagnostic: str,
    expected_exit: int,
) -> None:
    """Boundary failures expose neither traceback nor exception content."""
    output = tmp_path / "evidence"

    def fail(_: ComparisonInvocation) -> ComparisonOutcome:
        raise error

    exit_code = main(
        [
            "--reference",
            "reference.json",
            "--query",
            "query.json",
            "--output",
            str(output),
        ],
        executor=fail,
    )

    captured = capsys.readouterr()
    assert exit_code == expected_exit
    assert captured.out == ""
    assert captured.err == expected_diagnostic
    assert "Traceback" not in captured.err
    assert "sensitive implementation detail" not in captured.err
    assert not output.exists()


def test_unexpected_parser_failure_uses_the_internal_error_boundary(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-argparse failures before execution produce no traceback or details."""
    sensitive_detail = "sensitive parser implementation detail"

    def fail_parser(_: object = None) -> ComparisonInvocation:
        raise RuntimeError(sensitive_detail)

    monkeypatch.setattr(cli, "parse_invocation", fail_parser)

    exit_code = main([])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert captured.out == ""
    assert captured.err == (
        "ERROR [internal.unexpected]: an unexpected internal error occurred; "
        "rerun and report the failure if it persists\n"
    )
    assert sensitive_detail not in captured.err
    assert "Traceback" not in captured.err


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

    def unexpected_executor(invocation: ComparisonInvocation) -> ComparisonOutcome:
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

    def unexpected_executor(invocation: ComparisonInvocation) -> ComparisonOutcome:
        raise AssertionError(f"executor received invalid invocation: {invocation!r}")

    with pytest.raises(SystemExit) as error:
        main(arguments, executor=unexpected_executor)

    captured = capsys.readouterr()
    assert error.value.code == 2
    assert captured.out == ""
    assert captured.err == (
        "ERROR [invocation.invalid_arguments]: invalid command-line arguments; "
        "use --help for usage\n"
    )


def test_invalid_argument_diagnostic_does_not_repeat_argument_text(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unknown argument text cannot disclose an identifier in a diagnostic."""
    sensitive_argument = "patient-identifier-123"

    with pytest.raises(SystemExit) as error:
        main(
            [
                "--reference",
                "reference.csv",
                "--query",
                "query.csv",
                "--output",
                "evidence",
                sensitive_argument,
            ]
        )

    captured = capsys.readouterr()
    assert error.value.code == 2
    assert sensitive_argument not in captured.err
    assert captured.err == (
        "ERROR [invocation.invalid_arguments]: invalid command-line arguments; "
        "use --help for usage\n"
    )


def test_help_documents_the_complete_direct_interface_and_user_guide(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Help works alone and describes every version 1 command-line option."""

    def unexpected_executor(invocation: ComparisonInvocation) -> ComparisonOutcome:
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

    def unexpected_executor(invocation: ComparisonInvocation) -> ComparisonOutcome:
        raise AssertionError(f"executor was called for version: {invocation!r}")

    with pytest.raises(SystemExit) as error:
        main(["--version"], executor=unexpected_executor)

    captured = capsys.readouterr()
    assert error.value.code == 0
    assert captured.err == ""
    assert captured.out == f"adviso-compare {version('adviso-compare')}\n"
