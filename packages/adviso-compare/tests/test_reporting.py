"""Behavioural tests for HTML rendering and evidence-package publication."""

from __future__ import annotations

import errno
import json
import os
import stat
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier
from typing import Any
from uuid import UUID

import pytest
import yaml

import adviso_compare.reporting as reporting
from adviso_compare.alignment import align_records
from adviso_compare.application import prepare_comparison
from adviso_compare.contract import assess_contract
from adviso_compare.invocation import ComparisonInvocation
from adviso_compare.reporting import (
    OutputError,
    publish_evidence_package,
    render_html_report,
)
from adviso_compare.results import (
    CanonicalResult,
    RuntimeIdentity,
    assemble_result,
)
from adviso_compare.values import compare_values
from tests.support.documents import minimal_configuration, minimal_result


def _generated_evidence(
    tmp_path: Path,
    *,
    incomplete: bool = False,
    automatic: bool = False,
    run_id: UUID = UUID("123e4567-e89b-42d3-a456-426614174000"),
) -> CanonicalResult:
    """Generate canonical evidence through all three comparison phases."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    if automatic:
        reference_text = '[{"record_id":"S1","result":1}]'
        query_text = '[{"record_id":"S1","result":2}]'
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


def _publish(parent: Path, result: CanonicalResult) -> Path:
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


def test_html_report_is_a_self_contained_view_of_canonical_json() -> None:
    """The report presents all interpretive sections using JSON facts alone."""
    result = minimal_result(status="incomplete")
    result["exclusions"] = [
        {
            "code": "undeclared_field_excluded",
            "side": "query",
            "source_field": "unreported<script>",
            "record_count": 1,
        }
    ]

    report = render_html_report(result).decode("utf-8")

    assert report.startswith("<!doctype html>\n")
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


def test_automatic_mode_report_explains_its_limits(tmp_path: Path) -> None:
    """Automatic-mode evidence prominently directs attention to exclusions."""
    result = _generated_evidence(tmp_path, automatic=True).document()

    report = render_html_report(result).decode("utf-8")

    assert "Automatic strict-exact mode" in report
    assert "identically named fields observed on both sides" in report
    assert "Review the exclusions" in report


@pytest.mark.parametrize("status", ["complete", "incomplete"])
@pytest.mark.parametrize("parent_exists", [False, True])
def test_publication_creates_exact_private_two_file_package(
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
    ).read_bytes() == render_html_report(result)
    if parent_mode is not None:
        assert parent.stat().st_mode == parent_mode
    if os.name == "posix":
        if not parent_exists:
            assert stat.S_IMODE(parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(selected.stat().st_mode) == 0o700
        for member in selected.iterdir():
            assert stat.S_IMODE(member.stat().st_mode) == 0o600
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


def test_failed_initial_write_publishes_nothing_and_cleans_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A staging fault leaves at most an empty parent without evidence."""
    evidence = _generated_evidence(tmp_path / "inputs")
    parent = tmp_path / "evidence"
    real_write = reporting._write_atomic_member
    writes = 0

    def fail_second_member(path: Path, content: bytes) -> None:
        nonlocal writes
        writes += 1
        if os.name == "posix":
            assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        if writes == 2:
            raise OSError("injected write fault")
        real_write(path, content)

    monkeypatch.setattr(reporting, "_write_atomic_member", fail_second_member)

    with pytest.raises(OutputError) as raised:
        _publish(parent, evidence)

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

    def publish(result: CanonicalResult) -> Path:
        ready.wait()
        return _publish(parent, result)

    with ThreadPoolExecutor(max_workers=2) as executor:
        selected = list(executor.map(publish, evidence))

    assert len(set(selected)) == 2
    assert set(parent.iterdir()) == set(selected)
    for child, result in zip(selected, evidence):
        assert child.parent == parent
        assert sorted(path.name for path in child.iterdir()) == [
            "comparison-report.html", "comparison-results.json"
        ]
        assert (
            child / "comparison-results.json"
        ).read_bytes() == result.json_bytes
        assert (
            child / "comparison-report.html"
        ).read_bytes() == render_html_report(result.document())
    assert not list(tmp_path.glob(".evidence.*"))
