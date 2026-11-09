"""Behavioural tests for HTML rendering and evidence-package publication."""

from __future__ import annotations

import json
import os
import stat
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
import yaml

import adviso_compare.reporting as reporting
from adviso_compare.alignment import RecordsResult, align_records
from adviso_compare.application import PreparedComparison, prepare_comparison
from adviso_compare.contract import ContractResult, assess_contract
from adviso_compare.invocation import ComparisonInvocation
from adviso_compare.reporting import (
    OutputError,
    publish_evidence_package,
    render_html_report,
)
from adviso_compare.results import (
    ResultValidationError,
    RuntimeIdentity,
    assemble_result,
)
from adviso_compare.values import ValuesResult, compare_values
from tests.support.documents import JsonObject, minimal_configuration, minimal_result


@dataclass(frozen=True, slots=True)
class _Evidence:
    """One generated result and the context required to revalidate it."""

    document: JsonObject
    prepared: PreparedComparison
    contract: ContractResult
    records: RecordsResult
    values: ValuesResult


def _generated_evidence(
    tmp_path: Path,
    *,
    incomplete: bool = False,
    automatic: bool = False,
) -> _Evidence:
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
    document = assemble_result(
        prepared,
        contract,
        records,
        values,
        run_id=UUID("123e4567-e89b-42d3-a456-426614174000"),
        completed_at=datetime(2026, 11, 9, 12, 34, 56, tzinfo=timezone.utc),
        software_version="1.2.3",
        runtime=RuntimeIdentity(
            python="cpython-3.12.7",
            platform="linux-x86_64",
            unicode_version="15.1.0",
        ),
    )
    return _Evidence(document, prepared, contract, records, values)


def _publish(
    destination: Path,
    evidence: _Evidence,
    *,
    overwrite: bool = False,
) -> Path:
    """Publish generated evidence with its mandatory validation context."""
    return publish_evidence_package(
        destination,
        evidence.document,
        prepared=evidence.prepared,
        contract=evidence.contract,
        records=evidence.records,
        values=evidence.values,
        overwrite=overwrite,
    )


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
    result = _generated_evidence(tmp_path, automatic=True).document

    report = render_html_report(result).decode("utf-8")

    assert "Automatic strict-exact mode" in report
    assert "identically named fields observed on both sides" in report
    assert "Review the exclusions" in report


@pytest.mark.parametrize("status", ["complete", "incomplete"])
def test_publication_creates_exact_private_two_file_package(
    tmp_path: Path,
    status: str,
) -> None:
    """Every non-error result publishes only canonical JSON and its HTML view."""
    evidence = _generated_evidence(
        tmp_path / "inputs",
        incomplete=status == "incomplete",
    )
    result = evidence.document
    destination = tmp_path / f"comparison.{status}.evidence"

    selected = _publish(destination, evidence)

    assert selected == destination
    assert sorted(path.name for path in destination.iterdir()) == [
        "comparison-report.html",
        "comparison-results.json",
    ]
    published = json.loads(
        (destination / "comparison-results.json").read_text(encoding="utf-8")
    )
    assert published == result
    assert (destination / "comparison-report.html").read_bytes() == (
        render_html_report(published)
    )
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    for member in destination.iterdir():
        assert stat.S_IMODE(member.stat().st_mode) == 0o600
    assert not list(tmp_path.glob(f".{destination.name}.*"))


@pytest.mark.parametrize(
    "existing_kind",
    [
        "file",
        "symlink",
        "empty_directory",
        "partial_package",
        "invalid_package",
        "extra_entry",
    ],
)
@pytest.mark.parametrize("overwrite", [False, True])
def test_existing_destinations_are_refused_except_complete_authorized_package(
    tmp_path: Path,
    existing_kind: str,
    overwrite: bool,
) -> None:
    """Destination checks reject unsafe replacement targets without mutation."""
    evidence = _generated_evidence(tmp_path / "inputs")
    destination = tmp_path / "evidence"
    if existing_kind == "file":
        destination.write_text("keep", encoding="utf-8")
    elif existing_kind == "symlink":
        target = tmp_path / "target"
        target.mkdir()
        destination.symlink_to(target, target_is_directory=True)
    else:
        destination.mkdir()
        if existing_kind in {
            "partial_package",
            "invalid_package",
            "extra_entry",
        }:
            (destination / "comparison-results.json").write_text(
                "keep", encoding="utf-8"
            )
        if existing_kind in {"invalid_package", "extra_entry"}:
            (destination / "comparison-report.html").write_text(
                "keep", encoding="utf-8"
            )
        if existing_kind == "extra_entry":
            (destination / "extra.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(OutputError) as raised:
        _publish(destination, evidence, overwrite=overwrite)

    assert raised.value.code == "invalid_destination"
    assert destination.exists() or destination.is_symlink()
    assert not list(tmp_path.glob(".evidence.*"))


def test_overwrite_replaces_only_a_complete_version_one_package(
    tmp_path: Path,
) -> None:
    """Explicit overwrite replaces a recognizable package and nothing else."""
    original_evidence = _generated_evidence(tmp_path / "original-inputs")
    replacement_evidence = _generated_evidence(
        tmp_path / "replacement-inputs",
        incomplete=True,
    )
    destination = tmp_path / "evidence"
    original = original_evidence.document
    _publish(destination, original_evidence)
    replacement = replacement_evidence.document

    with pytest.raises(OutputError) as raised:
        _publish(destination, replacement_evidence)
    assert raised.value.code == "invalid_destination"
    assert json.loads(
        (destination / "comparison-results.json").read_text(encoding="utf-8")
    ) == original

    _publish(destination, replacement_evidence, overwrite=True)

    assert json.loads(
        (destination / "comparison-results.json").read_text(encoding="utf-8")
    ) == replacement
    assert not list(tmp_path.glob(".evidence.*"))


def test_failed_replacement_restores_existing_package_and_cleans_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A publication fault leaves the old complete package byte-identical."""
    original_evidence = _generated_evidence(tmp_path / "original-inputs")
    replacement_evidence = _generated_evidence(
        tmp_path / "replacement-inputs",
        incomplete=True,
    )
    destination = tmp_path / "evidence"
    _publish(destination, original_evidence)
    before = {
        member.name: member.read_bytes() for member in destination.iterdir()
    }

    def fail_exchange(_: Path, __: Path) -> bool:
        raise OSError("injected publication fault")

    monkeypatch.setattr(reporting, "_exchange_directories", fail_exchange)

    with pytest.raises(OutputError) as raised:
        _publish(destination, replacement_evidence, overwrite=True)

    assert raised.value.code == "write_failed"
    assert {
        member.name: member.read_bytes() for member in destination.iterdir()
    } == before
    assert not list(tmp_path.glob(".evidence.*"))


def test_overwrite_is_refused_when_atomic_exchange_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unsupported host never exposes the original to non-atomic replacement."""
    original_evidence = _generated_evidence(tmp_path / "original-inputs")
    replacement_evidence = _generated_evidence(tmp_path / "replacement-inputs")
    destination = tmp_path / "evidence"
    _publish(destination, original_evidence)
    before = {member.name: member.read_bytes() for member in destination.iterdir()}
    monkeypatch.setattr(reporting, "_exchange_directories", lambda *_: False)

    with pytest.raises(OutputError) as raised:
        _publish(destination, replacement_evidence, overwrite=True)

    assert raised.value.code == "write_failed"
    after = {member.name: member.read_bytes() for member in destination.iterdir()}
    assert after == before
    assert not list(tmp_path.glob(".evidence.*"))


def test_transient_old_package_cleanup_failure_does_not_misreport_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient cleanup fault is retried after successful atomic publication."""
    original_evidence = _generated_evidence(tmp_path / "original-inputs")
    replacement_evidence = _generated_evidence(tmp_path / "replacement-inputs")
    destination = tmp_path / "evidence"
    _publish(destination, original_evidence)
    replacement = replacement_evidence.document
    real_rmtree = reporting.shutil.rmtree
    failed_once = False

    def fail_old_package_once(path: Path | str, *args: Any, **kwargs: Any) -> None:
        nonlocal failed_once
        candidate = Path(path)
        is_old_package = (
            candidate.name == "package"
            and candidate.parent.name.startswith(".evidence.staging-")
        )
        if not failed_once and is_old_package:
            assert stat.S_IMODE(candidate.parent.stat().st_mode) == 0o700
            failed_once = True
            raise OSError("injected cleanup fault")
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(reporting.shutil, "rmtree", fail_old_package_once)

    _publish(destination, replacement_evidence, overwrite=True)

    assert json.loads(
        (destination / "comparison-results.json").read_text(encoding="utf-8")
    ) == replacement
    assert not list(tmp_path.glob(".evidence.*"))


def test_failed_initial_write_publishes_nothing_and_cleans_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A staging fault cannot expose a partial package at the destination."""
    evidence = _generated_evidence(tmp_path / "inputs")
    destination = tmp_path / "evidence"
    real_write = reporting._write_atomic_member
    writes = 0

    def fail_second_member(path: Path, content: bytes) -> None:
        nonlocal writes
        writes += 1
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        if writes == 2:
            raise OSError("injected write fault")
        real_write(path, content)

    monkeypatch.setattr(
        "adviso_compare.reporting._write_atomic_member",
        fail_second_member,
    )

    with pytest.raises(OutputError) as raised:
        _publish(destination, evidence)

    assert raised.value.code == "write_failed"
    assert not destination.exists()
    assert not list(tmp_path.glob(".evidence.*"))


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFOs are not available")
def test_special_filesystem_destination_is_never_replaced(tmp_path: Path) -> None:
    """Explicit overwrite cannot replace a non-regular filesystem object."""
    evidence = _generated_evidence(tmp_path / "inputs")
    destination = tmp_path / "evidence"
    os.mkfifo(destination)

    with pytest.raises(OutputError) as raised:
        _publish(destination, evidence, overwrite=True)

    assert raised.value.code == "invalid_destination"
    assert stat.S_ISFIFO(destination.lstat().st_mode)
    assert not list(tmp_path.glob(".evidence.*"))


@pytest.mark.parametrize("inconsistency", ["schema", "source_context"])
def test_invalid_generated_result_is_not_rendered_or_published(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    inconsistency: str,
) -> None:
    """Generated-result self-validation precedes HTML or filesystem output."""
    evidence = _generated_evidence(tmp_path / "inputs")
    invalid: JsonObject = deepcopy(evidence.document)
    if inconsistency == "schema":
        invalid["run"]["id"] = "not-a-uuid"
    else:
        invalid["exclusions"] = [
            {
                "code": "undeclared_field_excluded",
                "side": "query",
                "source_field": "fabricated_field",
                "record_count": 1,
            }
        ]
    rendered = False

    def observe_render(_: JsonObject) -> bytes:
        nonlocal rendered
        rendered = True
        return b""

    monkeypatch.setattr(
        "adviso_compare.reporting.render_html_report",
        observe_render,
    )

    with pytest.raises(ResultValidationError):
        publish_evidence_package(
            tmp_path / "evidence",
            invalid,
            prepared=evidence.prepared,
            contract=evidence.contract,
            records=evidence.records,
            values=evidence.values,
        )

    assert rendered is False
    assert not (tmp_path / "evidence").exists()
    assert not list(tmp_path.glob(".evidence.*"))
