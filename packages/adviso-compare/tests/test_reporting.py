"""Behavioural tests for HTML rendering and evidence-package publication."""

from __future__ import annotations

import errno
import json
import os
import stat
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from threading import Barrier
from typing import Any
from uuid import UUID

import pytest
import yaml

import adviso_compare.reporting as reporting
from adviso_compare.alignment import align_records
from adviso_compare.application import execute_comparison, prepare_comparison
from adviso_compare.contract import assess_contract
from adviso_compare.invocation import ComparisonInvocation
from adviso_compare.reporting import (
    OutputError,
    publish_evidence_package,
    render_html_report,
)
from adviso_compare.results import (
    ComparisonEvidence,
    ResultValidationError,
    RuntimeIdentity,
    assemble_result,
)
from adviso_compare.values import compare_values
from tests.support.documents import (
    minimal_configuration, minimal_configuration_bytes, minimal_result,
)
from tests.support.schemas import configuration_validator, results_validator


def _generated_evidence(
    tmp_path: Path,
    *,
    incomplete: bool = False,
    automatic: bool = False,
    reference_value: object = 1,
    query_value: object = 2,
    run_id: UUID = UUID("123e4567-e89b-42d3-a456-426614174000"),
) -> ComparisonEvidence:
    """Generate canonical evidence through all three comparison phases."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    if automatic:
        reference_text = json.dumps([
            {"record_id": "S1", "result": reference_value}
        ])
        query_text = json.dumps([
            {"record_id": "S1", "result": query_value}
        ])
        configuration = None
    else:
        reference_text = '[{"reference_id":"S1","expected_value":1}]'
        query_text = (
            '[{"query_id":"S1"}]'
            if incomplete
            else '[{"query_id":"S1","observed_value":2}]'
        )
        configuration = minimal_configuration()
    reference = tmp_path / "reference.json"
    query = tmp_path / "query.json"
    reference.write_text(reference_text, encoding="utf-8")
    query.write_text(query_text, encoding="utf-8")
    configuration_path = None
    if configuration is not None:
        configuration_path = tmp_path / "configuration.yaml"
        configuration_path.write_text(
            yaml.safe_dump(configuration, sort_keys=False),
            encoding="utf-8",
        )
    prepared = prepare_comparison(
        ComparisonInvocation(
            reference=reference,
            query=query,
            output=tmp_path / "unused-evidence",
            configuration=configuration_path,
        )
    )
    contract = assess_contract(
        prepared.configuration,
        reference=prepared.reference,
        query=prepared.query,
        reference_records=prepared.reference_records,
        query_records=prepared.query_records,
    )
    records = align_records(prepared.reference_records, prepared.query_records)
    values = compare_values(prepared.configuration, contract, records)
    result = assemble_result(
        prepared,
        contract,
        records,
        values,
        run_id=run_id,
        completed_at=datetime(2026, 11, 9, 12, 34, 56, tzinfo=timezone.utc),
        software_version="1.2.3",
        runtime=RuntimeIdentity(
            python="cpython-3.12.7",
            platform="linux-x86_64",
            unicode_version="15.1.0",
        ),
    )
    return result


def _publish(parent: Path, result: ComparisonEvidence) -> Path:
    """Publish generated, validated evidence under the selected parent."""
    return publish_evidence_package(parent, result)


def _snapshot(directory: Path) -> dict[str, tuple[int, bytes | str | None]]:
    """Capture names, permissions, and content without following symlinks."""
    snapshot = {}
    for path in (directory, *sorted(directory.rglob("*"))):
        mode = path.lstat().st_mode
        content = None
        if stat.S_ISLNK(mode):
            content = os.readlink(path)
        elif stat.S_ISREG(mode):
            content = path.read_bytes()
        snapshot[str(path.relative_to(directory))] = (mode, content)
    return snapshot


class _ReportView(HTMLParser):
    """Read default-visible text and navigation targets."""

    def __init__(self, report: str) -> None:
        super().__init__()
        self.visible: list[str] = []
        self.findings: list[str] = []
        self.ids: list[str] = []
        self.links: list[str] = []
        self.hidden = 0
        self.in_finding = False
        self.feed(report)

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        if tag == "a" and attributes.get("href", "").startswith("#"):
            self.links.append(attributes["href"][1:])
        if tag in {"details", "style", "script"}:
            self.hidden += 1
        if tag == "article":
            self.in_finding = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"details", "style", "script"}:
            self.hidden -= 1
        if tag == "article":
            self.in_finding = False

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.visible.append(data)
            if self.in_finding:
                self.findings.append(data)


def test_html_report_is_a_self_contained_view_of_both_json_documents() -> None:
    """The report presents facts from the linked result and configuration."""
    result = minimal_result(status="incomplete")
    result["exclusions"] = [
        {
            "code": "undeclared_field_excluded",
            "side": "query",
            "source_field": "unreported<script>",
            "record_count": 1,
        }
    ]

    report = render_html_report(
        result, minimal_configuration()
    ).decode("utf-8")

    assert report.startswith("<!doctype html>\n")
    assert "<title>adviso-compare evidence report</title>" in report
    assert "<h1>adviso-compare evidence report</h1>" in report
    assert "may contain sensitive patient or laboratory information" in report
    assert "Run completeness" in report
    assert "Incomplete" in report
    assert "Comparison differences" in report
    assert "Assessment issues" in report
    assert "Contract" in report and "Records" in report and "Values" in report
    assert "reference.json" in report and "query.json" in report
    assert "org.example.synthetic-exact-comparison" in report
    assert "F000001" in report
    assert "Phase: contract" in report
    assert "Priority: normal" in report
    assert "unreported&lt;script&gt;" in report
    assert "Provenance and reproduction" in report
    assert "External review and approval" in report
    assert "ISO 15189 compliant" not in report
    assert "clinically validated" not in report
    assert "<script" not in report
    assert "http://" not in report and "https://" not in report
    view = _ReportView(report)
    assert len(view.ids) == len(set(view.ids))
    assert view.links and set(view.links) <= set(view.ids)
    assert report.index('id="identities"') < report.index('id="headline"')
    assert report.index('id="coverage"') < report.index('id="findings"')
    assert report.index('id="findings"') < report.index('id="counts"')
    visible = " ".join(view.visible)
    assert result["run"]["completed_at"] in visible
    assert "Not assessable" in visible
    finding_text = " ".join(view.findings)
    assert 'record_id = "sample-1"' in finding_text
    assert "measured_value" in finding_text
    assert "Absent field" in finding_text
    assert "Present; value not recorded" in finding_text
    assert '"record_identity"' not in finding_text


def test_automatic_mode_report_explains_its_limits(tmp_path: Path) -> None:
    """Automatic-mode evidence prominently directs attention to exclusions."""
    evidence = _generated_evidence(tmp_path, automatic=True)
    result = evidence.document()

    report = render_html_report(
        result, evidence.configuration_document()
    ).decode("utf-8")

    assert "Automatic strict-exact mode" in report
    assert "identically named fields observed on both sides" in report
    assert "Review the exclusions" in report


def test_value_mismatch_is_readable_without_expanding_structured_evidence(
    tmp_path: Path,
) -> None:
    """Show the affected record, field, and both value forms directly."""
    evidence = _generated_evidence(tmp_path)
    report = render_html_report(
        evidence.document(), evidence.configuration_document()
    ).decode("utf-8")
    text = " ".join(_ReportView(report).findings)

    assert 'record_id = "S1"' in text
    assert "measured_value" in text
    assert "Source value" in text and "Canonical value" in text
    assert "decimal" in text and "1" in text and "2" in text
    assert "Value mismatch" in text


@pytest.mark.parametrize(
    ("reference", "query", "expected"),
    [
        (None, "", ["Null (present)", '""', "string"]),
        (1, "1", ["integer", "string", '"1"']),
        (True, False, ["boolean", "true", "false"]),
        ([1, None], {"x": [False, "<script>"]},
         ["array", "object", "[1, null]", '<script>']),
    ],
)
def test_untyped_finding_values_preserve_types_and_nested_content(
    tmp_path: Path, reference: object, query: object, expected: list[str]
) -> None:
    """Distinguish null, text, booleans and nested structures."""
    evidence = _generated_evidence(
        tmp_path, automatic=True,
        reference_value=reference, query_value=query,
    )
    report = render_html_report(
        evidence.document(), evidence.configuration_document()
    ).decode("utf-8")
    text = " ".join(_ReportView(report).findings)

    for value in expected:
        assert value in text
    assert "Not applicable (untyped)" in text
    assert "<script" not in report


def test_empty_report_retains_navigation_and_empty_finding_groups() -> None:
    """A zero-finding run still presents coverage and empty groups."""
    report = render_html_report(
        minimal_result(), minimal_configuration()
    ).decode("utf-8")
    view = _ReportView(report)

    assert set(view.links) <= set(view.ids)
    assert not view.findings
    assert "None reported." in " ".join(view.visible)
    assert "No field exclusions were reported." in report


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("missing-record", ["Missing record", "Record absent"]),
        ("dataset-field", ["Dataset-level finding", "measured_value"]),
        ("collection", ["list of string", '["WT", "MUT"]']),
        ("typed-null", ["Null policy violation", "Null (present)", "decimal"]),
    ],
)
def test_finding_forms_show_only_the_available_record_and_value_evidence(
    tmp_path: Path, case: str, expected: list[str]
) -> None:
    """Render record, dataset, collection and null findings directly."""
    configuration = minimal_configuration()
    reference_text = '[{"reference_id":"S1","expected_value":1}]'
    query_text = '[{"query_id":"S1","observed_value":null}]'
    suffix = "json"
    if case == "missing-record":
        query_text = "[]"
    elif case == "dataset-field":
        reference_text = "reference_id,expected_value\n"
        query_text = "query_id\n"
        suffix = "csv"
    elif case == "collection":
        field = configuration["fields"]["definitions"]["measured_value"]
        field["logical_type"] = {
            "collection_type": "list", "element_type": "string",
            "element_comparator": {"name": "typed_exact"},
        }
        field["comparator"] = {"name": "list_exact"}
        reference_text = '[{"reference_id":"S1","expected_value":["WT"]}]'
        query_text = '[{"query_id":"S1","observed_value":["WT","MUT"]}]'
    reference = tmp_path / f"reference.{suffix}"
    query = tmp_path / f"query.{suffix}"
    reference.write_text(reference_text, encoding="utf-8")
    query.write_text(query_text, encoding="utf-8")
    rules = tmp_path / "configuration.yaml"
    rules.write_text(yaml.safe_dump(configuration), encoding="utf-8")
    outcome = execute_comparison(ComparisonInvocation(
        reference=reference, query=query, configuration=rules,
        output=tmp_path / "evidence",
    ))
    report = (outcome.output / "comparison-report.html").read_text("utf-8")
    text = " ".join(_ReportView(report).findings)

    for value in expected:
        assert value in text
    if case == "dataset-field":
        assert "Record absent" not in text
        assert "Source value" not in text


@pytest.mark.parametrize("status", ["complete", "incomplete"])
@pytest.mark.parametrize("parent_exists", [False, True])
def test_publication_creates_exact_private_three_file_package(
    tmp_path: Path,
    status: str,
    parent_exists: bool,
) -> None:
    """Publish exact evidence in a private child named by result metadata."""
    evidence = _generated_evidence(
        tmp_path / "inputs", incomplete=status == "incomplete"
    )
    result = evidence.document()
    parent = tmp_path / f"comparison.{status}.evidence"
    if parent_exists:
        parent.mkdir()
    parent_mode = parent.stat().st_mode if parent_exists else None
    expected = parent / "20261109T123456Z-123e4567-e89b-42d3-a456-426614174000"

    selected = _publish(parent, evidence)

    assert selected == expected
    assert list(parent.iterdir()) == [selected]
    assert sorted(path.name for path in selected.iterdir()) == [
        "comparison-configuration.json",
        "comparison-report.html",
        "comparison-results.json",
    ]
    assert (
        selected / "comparison-results.json"
    ).read_bytes() == evidence.json_bytes
    assert json.loads(
        (selected / "comparison-results.json").read_text(encoding="utf-8")
    ) == result
    assert (
        selected / "comparison-report.html"
    ).read_bytes() == render_html_report(
        result, evidence.configuration_document()
    )
    configuration_bytes = (
        selected / "comparison-configuration.json"
    ).read_bytes()
    assert configuration_bytes == evidence.configuration_bytes
    configuration_validator().validate(json.loads(configuration_bytes))
    assert result["comparison_configuration_digest"] == {
        "algorithm": "sha256",
        "value": sha256(configuration_bytes).hexdigest(),
    }
    if parent_mode is not None:
        assert parent.stat().st_mode == parent_mode
    if os.name == "posix":
        if not parent_exists:
            assert stat.S_IMODE(parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(selected.stat().st_mode) == 0o700
        for member in selected.iterdir():
            assert stat.S_IMODE(member.stat().st_mode) == 0o600
    reporting.validate_evidence_package(selected)
    assert not list(tmp_path.glob(f".{parent.name}.*"))


@pytest.mark.parametrize(
    "parent_kind",
    [
        "file", "symlink", "dangling_symlink",
        "empty_directory", "populated_directory",
    ],
)
def test_output_parent_eligibility_depends_on_its_kind_not_its_contents(
    tmp_path: Path,
    parent_kind: str,
) -> None:
    """Accept arbitrary directory contents and preserve rejected objects."""
    evidence = _generated_evidence(tmp_path / "inputs")
    parent = tmp_path / "evidence"
    if parent_kind == "file":
        parent.write_bytes(b"keep")
    elif parent_kind in {"symlink", "dangling_symlink"}:
        target = tmp_path / "target"
        if parent_kind == "symlink":
            target.mkdir()
            (target / "keep.txt").write_bytes(b"keep")
        parent.symlink_to(target, target_is_directory=True)
    else:
        parent.mkdir()
        if parent_kind == "populated_directory":
            (parent / "comparison-results.json").write_bytes(b"not JSON")
            nested = parent / ".another-run.staging"
            nested.mkdir()
            (nested / "keep.txt").write_bytes(b"keep")
        before = _snapshot(parent)

        selected = _publish(parent, evidence)

        assert selected.parent == parent
        assert selected.is_dir()
        after = _snapshot(parent)
        assert {name: after[name] for name in before} == before
        assert set(after) - set(before) == {
            selected.name,
            f"{selected.name}/comparison-results.json",
            f"{selected.name}/comparison-configuration.json",
            f"{selected.name}/comparison-report.html",
        }
        return

    mode = parent.lstat().st_mode
    with pytest.raises(OutputError) as raised:
        _publish(parent, evidence)
    assert raised.value.code == "invalid_destination"
    assert parent.lstat().st_mode == mode
    if parent_kind == "file":
        assert parent.read_bytes() == b"keep"
    else:
        assert parent.is_symlink()
        assert parent.readlink() == target
        if target.exists():
            assert (target / "keep.txt").read_bytes() == b"keep"
    assert not list(tmp_path.glob(".evidence.*"))


def test_successive_runs_with_the_same_timestamp_preserve_each_package(
    tmp_path: Path,
) -> None:
    """A new UUID creates a sibling while preserving the first package."""
    first = _generated_evidence(tmp_path / "first-inputs")
    second = _generated_evidence(
        tmp_path / "second-inputs",
        incomplete=True,
        run_id=UUID("123e4567-e89b-42d3-a456-426614174001"),
    )
    parent = tmp_path / "evidence"
    original = _publish(parent, first)
    assert original.parent == parent
    before = _snapshot(original)

    selected = _publish(parent, second)

    assert selected == (
        parent / "20261109T123456Z-123e4567-e89b-42d3-a456-426614174001"
    )
    assert set(parent.iterdir()) == {original, selected}
    assert _snapshot(original) == before
    assert (
        selected / "comparison-results.json"
    ).read_bytes() == second.json_bytes


@pytest.mark.parametrize("failure", ["publication", "unsupported_rename"])
def test_failed_second_publication_preserves_content_and_cleans_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    """A fault after staging preserves siblings and unrelated content."""
    first = _generated_evidence(tmp_path / "first-inputs")
    second = _generated_evidence(
        tmp_path / "second-inputs",
        run_id=UUID("123e4567-e89b-42d3-a456-426614174001"),
    )
    parent = tmp_path / "evidence"
    original = _publish(parent, first)
    assert original.parent == parent
    (parent / "keep.txt").write_bytes(b"keep")
    other_stage = parent / ".another-run.staging"
    other_stage.mkdir()
    (other_stage / "keep.txt").write_bytes(b"keep")
    before = _snapshot(parent)
    publication_attempted = False

    def fail_publication(stage: Path, destination: Path) -> None:
        nonlocal publication_attempted
        publication_attempted = True
        assert (
            stage / "comparison-results.json"
        ).read_bytes() == second.json_bytes
        assert (stage / "comparison-report.html").is_file()
        assert (stage / "comparison-configuration.json").read_bytes() == (
            second.configuration_bytes
        )
        assert destination.parent == parent
        raise OSError("injected publication fault")

    if failure == "publication":
        monkeypatch.setattr(reporting, "_publish_new_package", fail_publication)
    else:

        def unsupported_rename(stage: Path, destination: Path) -> None:
            nonlocal publication_attempted
            publication_attempted = True
            assert (stage / "comparison-results.json").is_file()
            raise OSError(errno.ENOTSUP, "exclusive rename unavailable")

        monkeypatch.setattr(reporting, "_rename_exclusively", unsupported_rename)

    with pytest.raises(OutputError) as raised:
        _publish(parent, second)

    assert publication_attempted
    assert raised.value.code == "write_failed"
    assert _snapshot(parent) == before
    assert not list(tmp_path.glob(".evidence.*"))


@pytest.mark.parametrize(
    "failure_member", [
        "comparison-results.json", "comparison-configuration.json",
        "comparison-report.html",
    ],
)
def test_failed_initial_write_publishes_nothing_and_cleans_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_member: str,
) -> None:
    """A staging fault leaves at most an empty parent without evidence."""
    evidence = _generated_evidence(tmp_path / "inputs")
    parent = tmp_path / "evidence"
    real_write = reporting._write_atomic_member
    failure_attempted = False

    def fail_selected_member(path: Path, content: bytes) -> None:
        nonlocal failure_attempted
        if os.name == "posix":
            assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        if path.name == failure_member:
            failure_attempted = True
            raise OSError("injected write fault")
        real_write(path, content)

    monkeypatch.setattr(
        reporting, "_write_atomic_member", fail_selected_member
    )

    with pytest.raises(OutputError) as raised:
        _publish(parent, evidence)

    assert failure_attempted
    assert raised.value.code == "write_failed"
    assert not parent.exists() or list(parent.iterdir()) == []
    assert not list(tmp_path.glob(".evidence.*"))


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFOs are not available")
def test_special_filesystem_output_parent_is_rejected(tmp_path: Path) -> None:
    """A special object cannot be used as an output parent or replaced."""
    evidence = _generated_evidence(tmp_path / "inputs")
    parent = tmp_path / "evidence"
    os.mkfifo(parent)

    with pytest.raises(OutputError) as raised:
        _publish(parent, evidence)

    assert raised.value.code == "invalid_destination"
    assert stat.S_ISFIFO(parent.lstat().st_mode)
    assert not list(tmp_path.glob(".evidence.*"))


@pytest.mark.parametrize(
    "occupied_kind",
    ["file", "empty_directory", "populated_directory", "symlink"],
)
@pytest.mark.parametrize("collision_timing", ["before_staging", "after_staging"])
def test_occupied_run_path_is_preserved_without_renaming_the_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    occupied_kind: str,
    collision_timing: str,
) -> None:
    """An occupied child survives, including a collision after staging."""
    evidence = _generated_evidence(tmp_path / "inputs")
    parent = tmp_path / "evidence"
    parent.mkdir()
    child = parent / "20261109T123456Z-123e4567-e89b-42d3-a456-426614174000"
    snapshots = []

    def occupy() -> None:
        if occupied_kind == "file":
            child.write_bytes(b"keep")
        elif occupied_kind == "symlink":
            child.symlink_to("missing-target", target_is_directory=True)
        else:
            child.mkdir()
            if occupied_kind == "populated_directory":
                (child / "keep.txt").write_bytes(b"keep")
        snapshots.append(_snapshot(child))

    if collision_timing == "before_staging":
        occupy()
    else:
        real_publish = reporting._publish_new_package

        def collide(stage: Path, destination: Path) -> None:
            assert destination == child
            assert (stage / "comparison-results.json").is_file()
            assert (stage / "comparison-report.html").is_file()
            assert (stage / "comparison-configuration.json").is_file()
            occupy()
            real_publish(stage, destination)

        monkeypatch.setattr(reporting, "_publish_new_package", collide)

    with pytest.raises(OutputError) as raised:
        _publish(parent, evidence)

    assert raised.value.code == "invalid_destination"
    assert len(snapshots) == 1
    assert _snapshot(child) == snapshots[0]
    assert list(parent.iterdir()) == [child]
    assert not list(tmp_path.glob(".evidence.*"))


def test_missing_enclosing_directory_is_an_invalid_destination(
    tmp_path: Path,
) -> None:
    """Publication does not create missing ancestors of the parent."""
    evidence = _generated_evidence(tmp_path / "inputs")
    parent = tmp_path / "missing" / "evidence"

    with pytest.raises(OutputError) as raised:
        _publish(parent, evidence)

    assert raised.value.code == "invalid_destination"
    assert not parent.parent.exists()


def test_parent_creation_permission_failure_is_a_write_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failure to create an eligible parent yields a write error."""
    evidence = _generated_evidence(tmp_path / "inputs")
    parent = tmp_path / "evidence"
    real_mkdir = Path.mkdir

    def deny_parent(path: Path, *args: Any, **kwargs: Any) -> None:
        if path == parent:
            raise PermissionError("injected parent permission failure")
        real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", deny_parent)

    with pytest.raises(OutputError) as raised:
        _publish(parent, evidence)

    assert raised.value.code == "write_failed"
    assert not parent.exists()
    assert not list(tmp_path.glob(".evidence.*"))


@pytest.mark.parametrize("parent_exists", [False, True])
def test_concurrent_runs_publish_independently_under_the_same_parent(
    tmp_path: Path,
    parent_exists: bool,
) -> None:
    """Concurrent publishers share a parent and retain distinct evidence."""
    evidence = [
        _generated_evidence(tmp_path / "first-inputs"),
        _generated_evidence(
            tmp_path / "second-inputs",
            run_id=UUID("123e4567-e89b-42d3-a456-426614174001"),
        ),
    ]
    parent = tmp_path / "evidence"
    if parent_exists:
        parent.mkdir()
    ready = Barrier(2, timeout=10)

    def publish(result: ComparisonEvidence) -> Path:
        ready.wait()
        return _publish(parent, result)

    with ThreadPoolExecutor(max_workers=2) as executor:
        selected = list(executor.map(publish, evidence))

    assert len(set(selected)) == 2
    assert set(parent.iterdir()) == set(selected)
    for child, result in zip(selected, evidence):
        assert child.parent == parent
        assert sorted(path.name for path in child.iterdir()) == [
            "comparison-configuration.json", "comparison-report.html",
            "comparison-results.json",
        ]
        assert (
            child / "comparison-results.json"
        ).read_bytes() == result.json_bytes
        assert (
            child / "comparison-report.html"
        ).read_bytes() == render_html_report(
            result.document(), result.configuration_document()
        )
        assert (child / "comparison-configuration.json").read_bytes() == (
            result.configuration_bytes
        )
        digest = result.document()["comparison_configuration_digest"]
        assert digest["value"] == (
            sha256(result.configuration_bytes).hexdigest()
        )
    assert not list(tmp_path.glob(".evidence.*"))


@pytest.mark.parametrize(
    "defect", ["missing", "unreadable", "symlink", "directory", "wrong-name",
               "digest-mismatch"],
)
def test_package_inspection_rejects_invalid_configuration_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    defect: str,
) -> None:
    """Require the fixed regular sibling and its exact byte linkage."""
    package = tmp_path / "package"
    package.mkdir()
    configuration_path = package / "comparison-configuration.json"
    configuration_bytes = minimal_configuration_bytes()
    configuration_path.write_bytes(configuration_bytes)
    result_path = package / "comparison-results.json"
    result_path.write_text(json.dumps(minimal_result()), encoding="utf-8")
    (package / "comparison-report.html").write_text(
        "<!doctype html><html><body>Synthetic report</body></html>",
        encoding="utf-8",
    )
    results_validator().validate(json.loads(result_path.read_bytes()))
    configuration_validator().validate(json.loads(configuration_bytes))
    if defect in {"missing", "symlink", "directory"}:
        configuration_path.unlink()
    if defect == "symlink":
        target = tmp_path / "configuration-target.json"
        target.write_bytes(configuration_bytes)
        configuration_path.symlink_to(target)
    elif defect == "directory":
        configuration_path.mkdir()
    elif defect == "wrong-name":
        configuration_path.rename(package / "different-configuration.json")
    elif defect == "digest-mismatch":
        configuration_path.write_bytes(configuration_bytes + b" ")
    original_paths = set(package.iterdir())
    original_results = result_path.read_bytes()
    read_attempted = False
    if defect == "unreadable":
        real_open = os.open

        def deny_read(path: Path, flags: int, *args: object) -> int:
            nonlocal read_attempted
            if path == configuration_path:
                read_attempted = True
                raise PermissionError("injected read failure")
            return real_open(path, flags, *args)

        monkeypatch.setattr(os, "open", deny_read)

    with pytest.raises(ResultValidationError):
        reporting.validate_evidence_package(package)

    if defect == "unreadable":
        assert read_attempted
    assert set(package.iterdir()) == original_paths
    assert result_path.read_bytes() == original_results
    if defect == "symlink":
        assert configuration_path.is_symlink()
        assert target.read_bytes() == configuration_bytes
