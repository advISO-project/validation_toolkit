"""Render and atomically publish the version 1 evidence package."""

from __future__ import annotations

import ctypes
import errno
import html
import json
import os
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from adviso_compare.results import (
    ComparisonEvidence,
    ResultValidationError,
    parse_evidence_json,
    validate_result,
)


RESULTS_FILENAME = "comparison-results.json"
CONFIGURATION_FILENAME = "comparison-configuration.json"
REPORT_FILENAME = "comparison-report.html"
AUTOMATIC_CONFIGURATION_ID = "org.adviso.automatic-strict-exact"
_AT_FDCWD = -100
_RENAME_NOREPLACE = 1
_RENAME_EXCL = 4


# Public reporting API


@dataclass(frozen=True, slots=True)
class OutputError(Exception):
    """An expected failure while selecting or publishing output."""

    code: str
    message: str

    @property
    def category(self) -> str:
        """Return the stable execution-error category."""
        return "output"

    @property
    def diagnostic(self) -> str:
        """Render the stable single-line non-sensitive diagnostic."""
        return f"ERROR [output.{self.code}]: {self.message}"

    def __str__(self) -> str:
        """Return the concise actionable message."""
        return self.message


def render_html_report(
    document: Mapping[str, Any], configuration: Mapping[str, Any]
) -> bytes:
    """Render a self-contained view of validated, linked JSON documents."""
    run = document["run"]
    phases = document["phases"]
    inputs = document["inputs"]
    metadata = configuration["metadata"]
    summary = document["summary"]
    finding_summary = summary["findings"]
    exclusions = document["exclusions"]
    findings = document["findings"]

    status = str(run["status"])
    difference_count = finding_summary["by_classification"][
        "comparison_difference"
    ]
    issue_count = finding_summary["by_classification"]["assessment_issue"]
    sections = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>adviso-compare evidence report</title>",
        "<style>",
        _STYLES,
        "</style>",
        "</head>",
        "<body>",
        '<header class="page-header">',
        "<h1>adviso-compare evidence report</h1>",
        '<p class="warning"><strong>Sensitive information:</strong> This evidence '
        "package may contain sensitive patient or laboratory information. Handle "
        "it under your laboratory’s information-governance arrangements.</p>",
        "<p>This run translated two structured datasets according to the "
        "saved comparison configuration, then performed contract, records, "
        "and values comparison phases. The report presents measured evidence; "
        "review and approval occur outside the tool.</p>",
        "</header>",
        '<main id="main-content">',
        '<section aria-labelledby="headline"><h2 id="headline">Run summary</h2>',
        '<div class="headline-grid">',
        _metric("Run completeness", status.title(), status),
        _metric("Comparison differences", str(difference_count), "difference"),
        _metric("Assessment issues", str(issue_count), "issue"),
        "</div>",
        "</section>",
        _phase_section(phases),
        _identity_section(inputs, metadata),
    ]
    if metadata["id"] == AUTOMATIC_CONFIGURATION_ID:
        sections.append(_automatic_mode_notice())
    sections.extend(
        (
            _counts_section(summary),
            _findings_section(findings),
            _limitations_section(exclusions, summary),
            _provenance_section(document, configuration),
            _review_section(),
            "</main>",
            "</body>",
            "</html>",
            "",
        )
    )
    return "\n".join(sections).encode("utf-8")


# Evidence-package publication


def validate_evidence_package(directory: Path) -> None:
    """Validate saved JSON evidence, including fixed members and byte linkage.

    This checks the invariants available from the package; it cannot reproduce
    the comparison without its source inputs and comparison context.
    """
    directory = Path(directory)
    try:
        members = {member.name for member in directory.iterdir()}
    except OSError as error:
        raise ResultValidationError(
            "evidence package is unreadable"
        ) from error
    if members != {RESULTS_FILENAME, CONFIGURATION_FILENAME, REPORT_FILENAME}:
        raise ResultValidationError("evidence package members are invalid")
    document = parse_evidence_json(
        _read_regular_member(directory / RESULTS_FILENAME)
    )
    configuration_bytes = _read_regular_member(
        directory / CONFIGURATION_FILENAME
    )
    _require_regular_member(directory / REPORT_FILENAME)
    validate_result(document, configuration_bytes=configuration_bytes)


def _require_regular_member(path: Path) -> os.stat_result:
    """Inspect a fixed sibling without accepting a symbolic link."""
    try:
        status = path.lstat()
    except OSError as error:
        raise ResultValidationError(
            "evidence member is unavailable"
        ) from error
    if not stat.S_ISREG(status.st_mode):
        raise ResultValidationError("evidence member must be a regular file")
    return status


def _read_regular_member(path: Path) -> bytes:
    """Read a regular sibling, refusing links and replacement during open."""
    expected = _require_regular_member(path)
    flags = os.O_RDONLY
    for option in ("O_NOFOLLOW", "O_NONBLOCK", "O_BINARY"):
        flags |= getattr(os, option, 0)
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            actual = os.fstat(stream.fileno())
            current = _require_regular_member(path)
            if not (
                stat.S_ISREG(actual.st_mode)
                and os.path.samestat(expected, actual)
                and os.path.samestat(current, actual)
            ):
                raise ResultValidationError(
                    "evidence member changed during open"
                )
            return stream.read()
    except OSError as error:
        raise ResultValidationError("evidence member is unreadable") from error


def publish_evidence_package(parent: Path, result: ComparisonEvidence) -> Path:
    """Publish validated evidence in a child named from its run metadata."""
    document = result.document()
    json_content = result.json_bytes
    html_content = render_html_report(
        document, result.configuration_document()
    )
    run = document["run"]
    timestamp = run["completed_at"].replace("-", "").replace(":", "")
    parent = Path(parent)
    destination = parent / f"{timestamp}-{run['id']}"
    staging_root: Path | None = None
    try:
        _prepare_output_parent(parent)
        _require_absent(destination)
        staging_root = Path(
            tempfile.mkdtemp(prefix=".adviso-compare.staging-", dir=parent)
        )
        os.chmod(staging_root, 0o700)
        stage = staging_root / "package"
        stage.mkdir(mode=0o700)
        _write_atomic_member(stage / RESULTS_FILENAME, json_content)
        _write_atomic_member(
            stage / CONFIGURATION_FILENAME, result.configuration_bytes
        )
        _write_atomic_member(stage / REPORT_FILENAME, html_content)
        _fsync_directory(stage)
        _publish_new_package(stage, destination)
        _fsync_directory(parent)
    except OutputError:
        raise
    except OSError as error:
        raise OutputError(
            code="write_failed",
            message=(
                "the output parent or evidence package could not be written"
            ),
        ) from error
    finally:
        if staging_root is not None:
            _remove_temporary_directory(staging_root)
    return destination


def _prepare_output_parent(parent: Path) -> None:
    """Accept or privately create a regular parent without reading contents."""
    try:
        mode = parent.lstat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        if not parent.parent.is_dir():
            raise OutputError(
                code="invalid_destination",
                message="the output parent's enclosing directory must exist",
            ) from None
        try:
            parent.mkdir(mode=0o700)
        except FileExistsError:
            # A concurrent publisher may have created the shared parent.
            pass
        mode = parent.lstat().st_mode
    if not stat.S_ISDIR(mode):
        raise OutputError(
            code="invalid_destination",
            message=(
                "the output parent must be a regular directory, not a link"
            ),
        )


def _publish_new_package(stage: Path, destination: Path) -> None:
    """Publish atomically without replacing an object at the final path."""
    try:
        _rename_exclusively(stage, destination)
    except OSError as error:
        if error.errno in {errno.ENOTSUP, errno.ENOSYS, errno.EINVAL}:
            raise OutputError(
                code="write_failed",
                message=(
                    "the destination does not support safe directory "
                    "publication; select a different filesystem"
                ),
            ) from error
        if error.errno not in {errno.EEXIST, errno.ENOTEMPTY}:
            raise
        raise OutputError(
            code="invalid_destination",
            message="the run-directory path is already occupied",
        ) from error


def _rename_exclusively(source: Path, destination: Path) -> None:
    """Publish with the host's exclusive rename primitive."""
    if sys.platform == "win32":
        # Windows os.rename refuses every existing destination.
        os.rename(source, destination)
        return
    if sys.platform not in {"linux", "darwin"}:
        raise OSError(
            errno.ENOTSUP, "exclusive directory rename is unavailable"
        )

    library = ctypes.CDLL(None, use_errno=True)
    try:
        if sys.platform == "linux":
            rename = library.renameat2
            rename.argtypes = (
                ctypes.c_int, ctypes.c_char_p,
                ctypes.c_int, ctypes.c_char_p, ctypes.c_uint,
            )
            rename.restype = ctypes.c_int
            result = rename(
                _AT_FDCWD, os.fsencode(source),
                _AT_FDCWD, os.fsencode(destination), _RENAME_NOREPLACE,
            )
        else:
            rename = library.renamex_np
            rename.argtypes = (
                ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint,
            )
            rename.restype = ctypes.c_int
            result = rename(
                os.fsencode(source), os.fsencode(destination), _RENAME_EXCL,
            )
    except AttributeError as error:
        raise OSError(
            errno.ENOTSUP, "exclusive directory rename is unavailable"
        ) from error
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))


def _require_absent(destination: Path) -> None:
    """Refuse an occupied run path without following symbolic links."""
    try:
        destination.lstat()
    except FileNotFoundError:
        return
    raise OutputError(
        code="invalid_destination",
        message="the run-directory path is already occupied",
    )


def _write_atomic_member(path: Path, content: bytes) -> None:
    """Write one private member and atomically give it its final staged name."""
    temporary = path.with_name(f".{path.name}.temporary-{uuid4().hex}")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _remove_temporary_directory(path: Path) -> None:
    """Best-effort removal of this invocation's private staging directory."""
    for _ in range(2):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError:
            continue


def _fsync_directory(path: Path) -> None:
    """Request durable directory metadata where the platform supports it."""
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


# HTML rendering helpers


def _metric(label: str, value: str, kind: str) -> str:
    """Render one labelled headline measure."""
    return (
        f'<div class="metric metric-{_escape(kind)}"><span>{_escape(label)}</span>'
        f"<strong>{_escape(value)}</strong></div>"
    )


def _phase_section(phases: Mapping[str, Any]) -> str:
    """Render the ordered comparison-phase traceability table."""
    rows = "".join(
        f"<tr><th scope=\"row\">{_escape(name.title())}</th>"
        f"<td>{_escape(str(phases[name]).title())}</td></tr>"
        for name in ("contract", "records", "values")
    )
    return (
        '<section aria-labelledby="phases"><h2 id="phases">Comparison phases</h2>'
        "<p>The phases were performed in the order shown.</p>"
        f"<table><thead><tr><th>Phase</th><th>Completion status</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></section>"
    )


def _identity_section(inputs: Mapping[str, Any], metadata: Mapping[str, Any]) -> str:
    """Render input and effective-configuration identities."""
    return (
        '<section aria-labelledby="identities"><h2 id="identities">Compared inputs '
        "and configuration</h2><dl>"
        f"<dt>Reference</dt><dd>{_escape(inputs['reference']['basename'])}</dd>"
        f"<dt>Query</dt><dd>{_escape(inputs['query']['basename'])}</dd>"
        f"<dt>Configuration identifier</dt><dd>{_escape(metadata['id'])}</dd>"
        f"<dt>Configuration revision</dt><dd>{_escape(metadata['revision'])}</dd>"
        "</dl></section>"
    )


def _automatic_mode_notice() -> str:
    """Render the required limitations warning for automatic mode."""
    return (
        '<aside class="notice" aria-labelledby="automatic-mode">'
        '<h2 id="automatic-mode">Automatic strict-exact mode</h2>'
        "<p>Only identically named fields observed on both sides were compared, "
        "using strict parser-native equality without domain-specific translation. "
        "Review the exclusions before interpreting findings. Use a custom "
        "configuration when record identity, field correspondence, or value "
        "equivalence requires domain knowledge.</p></aside>"
    )


def _counts_section(summary: Mapping[str, Any]) -> str:
    """Render record, value, and finding metrics without deriving a verdict."""
    records = summary["records"]
    values = summary["values"]
    findings = summary["findings"]
    return (
        '<section aria-labelledby="counts"><h2 id="counts">Measured counts</h2>'
        "<h3>Records</h3>"
        + _definition_list(records)
        + "<h3>Values</h3>"
        + _definition_list(values)
        + "<h3>Findings</h3><p>Total findings: "
        + f"<strong>{findings['total']}</strong></p>"
        + "<h3>Findings by classification</h3>"
        + _definition_list(findings["by_classification"])
        + "<h3>Findings by code</h3>"
        + _definition_list(findings["by_code"])
        + "<h3>Findings by review priority</h3>"
        + _definition_list(findings["by_review_priority"])
        + "</section>"
    )


def _findings_section(findings: list[Mapping[str, Any]]) -> str:
    """Render findings classification-first with phase as traceability."""
    groups = []
    labels = (
        ("comparison_difference", "Comparison differences"),
        ("assessment_issue", "Assessment issues"),
    )
    for classification, label in labels:
        selected = [
            finding
            for finding in findings
            if finding["classification"] == classification
        ]
        items = "".join(_finding_card(finding) for finding in selected)
        if not items:
            items = "<p>None reported.</p>"
        groups.append(f"<h3>{label}</h3>{items}")
    return (
        '<section aria-labelledby="findings"><h2 id="findings">Finding details</h2>'
        + "".join(groups)
        + "</section>"
    )


def _finding_card(finding: Mapping[str, Any]) -> str:
    """Render one finding without adding facts outside its JSON object."""
    priority = finding.get("review_priority", "unassigned")
    structured = {
        name: value
        for name, value in finding.items()
        if name not in {"id", "classification", "message", "phase", "review_priority"}
    }
    evidence = _escape(json.dumps(structured, ensure_ascii=False, indent=2))
    return (
        '<article class="finding">'
        f"<h4>{_escape(finding['id'])}: {_escape(finding['message'])}</h4>"
        f'<p><span class="label">Phase: {_escape(finding["phase"])}</span> '
        f'<span class="label priority-{_escape(priority)}">Priority: '
        f"{_escape(priority)}</span></p>"
        "<details><summary>Structured evidence</summary>"
        f"<pre>{evidence}</pre></details>"
        "</article>"
    )


def _limitations_section(
    exclusions: list[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> str:
    """Render excluded and not-assessable content explicitly."""
    exclusion_items = "".join(
        f"<li><code>{_escape(item['code'])}</code>: "
        f"{_escape(_exclusion_description(item))}</li>"
        for item in exclusions
    )
    if not exclusion_items:
        exclusion_items = "<li>No field exclusions were reported.</li>"
    not_assessable = summary["values"]["not_assessable"]
    return (
        '<section aria-labelledby="limitations"><h2 id="limitations">Limitations, '
        "exclusions, and unassessed content</h2>"
        f"<p>Not-assessable value opportunities: <strong>{not_assessable}</strong>. "
        "Related assessment-issue findings explain failed prerequisites.</p>"
        f"<ul>{exclusion_items}</ul></section>"
    )


def _exclusion_description(item: Mapping[str, Any]) -> str:
    """Describe one fixed exclusion form from its structured properties."""
    if item["code"] == "configured_field_excluded":
        return f"configured canonical field {item['canonical_field']} was out of scope"
    return (
        f"{item['side']} source field {item['source_field']} was undeclared "
        f"({item['record_count']} records)"
    )


def _provenance_section(
    document: Mapping[str, Any], configuration: Mapping[str, Any]
) -> str:
    """Render provenance and saved configuration for reproduction."""
    run = document["run"]
    software = document["software"]
    runtime = document["runtime"]
    inputs = document["inputs"]
    input_rows = "".join(
        "<tr>"
        f"<th scope=\"row\">{_escape(side.title())}</th>"
        f"<td>{_escape(value['basename'])}</td>"
        f"<td>{_escape(value['format'])}</td>"
        f"<td><code>{_escape(value['digest']['value'])}</code></td>"
        "</tr>"
        for side, value in (
            ("reference", inputs["reference"]),
            ("query", inputs["query"]),
        )
    )
    config_json = _escape(json.dumps(configuration, ensure_ascii=False, indent=2))
    return (
        '<section aria-labelledby="provenance"><h2 id="provenance">Provenance and '
        "reproduction</h2><dl>"
        f"<dt>Run identifier</dt><dd>{_escape(run['id'])}</dd>"
        f"<dt>Completed at</dt><dd>{_escape(run['completed_at'])}</dd>"
        f"<dt>Software</dt><dd>{_escape(software['name'])} "
        f"{_escape(software['version'])}</dd>"
        f"<dt>Python</dt><dd>{_escape(runtime['python'])}</dd>"
        f"<dt>Platform</dt><dd>{_escape(runtime['platform'])}</dd>"
        f"<dt>Unicode data</dt><dd>{_escape(runtime['unicode_version'])}</dd>"
        "<dt>Results schema</dt><dd>"
        f"{_escape(document['schema_version'])}</dd>"
        "<dt>Configuration schema</dt><dd>"
        f"{_escape(configuration['schema_version'])}"
        "</dd>"
        "<dt>Configuration SHA-256</dt><dd><code>"
        f"{_escape(document['comparison_configuration_digest']['value'])}"
        "</code></dd>"
        "</dl><h3>Input byte provenance</h3><table><thead><tr><th>Side</th>"
        "<th>Basename</th><th>Format</th><th>SHA-256</th></tr></thead>"
        f"<tbody>{input_rows}"
        "</tbody></table><details><summary>Effective comparison configuration</summary>"
        f"<pre>{config_json}</pre></details></section>"
    )


def _review_section() -> str:
    """Provide generic space for governance outside the comparison tool."""
    return (
        '<section aria-labelledby="review"><h2 id="review">External review and '
        "approval</h2><p>Reviewer: ____________________</p>"
        "<p>Date: ____________________</p><p>Review notes:</p>"
        '<div class="review-space" aria-label="Blank review notes space">'
        "</div></section>"
    )


def _definition_list(values: Mapping[str, Any]) -> str:
    """Render a compact labelled count list."""
    entries = "".join(
        f"<dt>{_escape(name.replace('_', ' ').title())}</dt><dd>{_escape(value)}</dd>"
        for name, value in values.items()
    )
    return f'<dl class="counts">{entries}</dl>'


def _escape(value: object) -> str:
    """Escape one canonical value for HTML text or attribute use."""
    return html.escape(str(value), quote=True)


_STYLES = """
:root { color-scheme: light; font-family: system-ui, sans-serif; line-height: 1.5; }
body { color: #17202a; background: #fff; margin: 0; }
.page-header, main { max-width: 72rem; margin: 0 auto; padding: 1.25rem; }
.page-header { border-bottom: .35rem solid #244b6b; }
.warning, .notice { border: .18rem solid #8a4b08; padding: 1rem; background: #fff4df; }
section, aside { margin-block: 2rem; }
.headline-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  gap: 1rem;
}
.metric { border: .15rem solid #59636e; padding: 1rem; }
.metric span, .metric strong { display: block; }
.metric strong { font-size: 1.6rem; }
table { border-collapse: collapse; width: 100%; }
th, td {
  border: 1px solid #7b8792;
  padding: .5rem;
  text-align: left;
  vertical-align: top;
}
dl { display: grid; grid-template-columns: minmax(12rem, 1fr) 3fr; gap: .3rem 1rem; }
dt { font-weight: 700; }
.counts { grid-template-columns: repeat(2, minmax(8rem, max-content)); }
.finding {
  border-left: .35rem solid #59636e;
  padding: .25rem 1rem 1rem;
  margin-block: 1rem;
  background: #f5f7f8;
}
.label {
  display: inline-block;
  border: 1px solid #59636e;
  border-radius: .25rem;
  padding: .15rem .4rem;
  margin: .15rem;
}
.priority-high::before { content: "▲ "; }
.priority-normal::before { content: "● "; }
.priority-low::before { content: "▼ "; }
.priority-unassigned::before { content: "— "; }
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: #eef1f3;
  padding: 1rem;
}
code { overflow-wrap: anywhere; }
.review-space { min-height: 8rem; border: 1px solid #59636e; }
@media print { .page-header, main { max-width: none; } details { display: block; } }
""".strip()
