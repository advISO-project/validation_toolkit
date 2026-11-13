"""Behavioural tests for the direct adviso-compare command line."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from importlib.metadata import version
from pathlib import Path
from typing import Iterator

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
from tests.support.evidence import assert_run_package


@pytest.mark.parametrize(
    ("optional_arguments", "expected_configuration"),
    [
        ([], None),
        (["--configuration", "rules.yaml"], Path("rules.yaml")),
    ],
    ids=[
        "automatic-mode", "custom-configuration",
    ],
)
def test_direct_arguments_create_an_immutable_invocation_without_reading_inputs(
    optional_arguments: list[str],
    expected_configuration: Path | None,
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
    )
    with pytest.raises(FrozenInstanceError):
        invocation.output = Path("other")  # type: ignore[misc]


def test_main_dispatches_the_invocation_through_an_injected_executor(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI orchestration passes one domain value to an independently testable core."""
    received: list[ComparisonInvocation] = []

    def execute(invocation: ComparisonInvocation) -> ComparisonOutcome:
        received.append(invocation)
        return ComparisonOutcome(
            run_status="complete",
            output=invocation.output / "selected-run",
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
    expected = Path("evidence") / "selected-run"
    assert capsys.readouterr().out.endswith(f"Evidence package: {expected}\n")


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
    ids=[
        "custom-complete", "custom-incomplete", "automatic-complete",
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
    selected = assert_run_package(output)
    assert captured.out == (
        f"Run status: {expected_status}\n"
        f"Comparison differences: {expected_differences}\n"
        f"Assessment issues: {expected_issues}\n"
        f"Evidence package: {Path(output.name) / selected.name}\n"
    )
    assert str(tmp_path) not in captured.out


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
            OutputError("invalid_destination", "run path already exists"),
            "ERROR [output.invalid_destination]: run path already exists\n",
        ),
    ],
    ids=[
        "configuration-error", "input-error", "record-key-error",
        "output-error",
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
    cleanup_finished = False
    original_args = error.args

    @contextmanager
    def cleanup() -> Iterator[None]:
        nonlocal cleanup_finished
        try:
            yield
        finally:
            cleanup_finished = True

    def fail(_: ComparisonInvocation) -> ComparisonOutcome:
        try:
            with cleanup():
                raise error
        except type(error) as observed:
            assert observed is error
            raise

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
    assert error.args == original_args
    assert cleanup_finished


@pytest.mark.parametrize(
    "failure", ["input", "configuration", "validation", "linkage", "html"]
)
@pytest.mark.parametrize(
    "parent_exists", [False, True],
    ids=[
        "new-parent", "existing-parent",
    ],
)
def test_default_executor_errors_preserve_existing_content_without_new_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    parent_exists: bool,
) -> None:
    """Pre-publication failures leave absent parents and existing data alone."""
    output = tmp_path / "evidence"
    if parent_exists:
        output.mkdir()
        (output / "keep.txt").write_bytes(b"keep")
        mode = output.stat().st_mode
    reference = tmp_path / "reference.json"
    query = tmp_path / "query.json"
    query.write_text('[{"record_id":"S1","result":1}]', encoding="utf-8")
    arguments = [
        "--reference", str(reference), "--query", str(query),
        "--output", str(output),
    ]
    if failure != "input":
        reference.write_bytes(query.read_bytes())
    if failure == "configuration":
        configuration = tmp_path / "configuration.yaml"
        configuration.write_text("[", encoding="utf-8")
        arguments.extend(["--configuration", str(configuration)])
    failure_attempted = False
    if failure in {"validation", "linkage", "html"}:

        def fail(*args: object, **kwargs: object) -> None:
            nonlocal failure_attempted
            if failure == "linkage":
                assert isinstance(kwargs.get("configuration_bytes"), bytes)
            failure_attempted = True
            raise ResultValidationError("sensitive implementation detail")

        target = {
            "validation": "adviso_compare.application.assemble_result",
            "linkage": "adviso_compare.results.validate_result",
            "html": "adviso_compare.reporting.render_html_report",
        }[failure]
        monkeypatch.setattr(target, fail)

    exit_code = main(arguments)

    captured = capsys.readouterr()
    expected_code = {
        "input": "input.unreadable",
        "configuration": "configuration.invalid_syntax",
        "validation": "internal.unexpected",
        "linkage": "internal.unexpected",
        "html": "internal.unexpected",
    }[failure]
    if failure in {"validation", "linkage", "html"}:
        assert failure_attempted
    assert exit_code == (
        3 if failure in {"validation", "linkage", "html"} else 2
    )
    assert captured.out == ""
    assert captured.err.startswith(f"ERROR [{expected_code}]: ")
    assert captured.err.count("\n") == 1
    assert "Traceback" not in captured.err
    assert "sensitive implementation detail" not in captured.err
    assert str(tmp_path) not in captured.err
    if parent_exists:
        assert list(output.iterdir()) == [output / "keep.txt"]
        assert (output / "keep.txt").read_bytes() == b"keep"
        assert output.stat().st_mode == mode
    else:
        assert not output.exists()
    assert not list(tmp_path.glob(".evidence.*"))


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
    ids=[
        "memory-exhaustion", "unexpected-validation-error",
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


@pytest.mark.parametrize(
    "unsupported",
    [
        pytest.param("unexpected-command", id="positional-argument"),
        pytest.param("--unknown-option", id="unknown-option"),
    ],
)
def test_unsupported_arguments_are_rejected_before_execution(
    capsys: pytest.CaptureFixture[str],
    unsupported: str,
) -> None:
    """Unsupported syntax is rejected before comparison execution."""
    arguments = [
        unsupported,
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
        "--help",
        "--version",
    ):
        assert option in captured.out
    assert "user guide" in captured.out.lower()
    assert "share/doc/adviso-compare/USER_GUIDE.md" in captured.out
    assert "subcommand" not in captured.out.lower()
    assert "three-file evidence package" in " ".join(captured.out.split())
    assert "parent" in captured.out.lower()


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


@pytest.mark.parametrize("parent_kind", ["relative", "absolute", "root"])
def test_completion_summary_identifies_the_child_without_absolute_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    parent_kind: str,
) -> None:
    """Summary paths retain parent context without revealing host details."""
    if parent_kind == "relative":
        parent = Path("nested") / "evidence"
        expected = parent / "selected-run"
    elif parent_kind == "absolute":
        parent = tmp_path / "evidence"
        expected = Path("evidence") / "selected-run"
    else:
        parent = Path(tmp_path.anchor)
        expected = Path("selected-run")

    def execute(invocation: ComparisonInvocation) -> ComparisonOutcome:
        assert invocation.output == parent
        return ComparisonOutcome(
            run_status="complete",
            output=parent / "selected-run",
            comparison_differences=0,
            assessment_issues=0,
        )

    exit_code = main(
        ["--reference", "r.csv", "--query", "q.csv", "--output", str(parent)],
        executor=execute,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.endswith(f"Evidence package: {expected}\n")
    assert str(tmp_path) not in captured.out
