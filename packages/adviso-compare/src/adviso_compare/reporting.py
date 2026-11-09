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
from typing import TYPE_CHECKING, Any, Mapping
from uuid import uuid4

from adviso_compare.results import JsonObject, serialize_result, validate_result

if TYPE_CHECKING:
    from adviso_compare.alignment import RecordsResult
    from adviso_compare.application import PreparedComparison
    from adviso_compare.contract import ContractResult
    from adviso_compare.values import ValuesResult


RESULTS_FILENAME = "comparison-results.json"
REPORT_FILENAME = "comparison-report.html"
PACKAGE_MEMBERS = frozenset({RESULTS_FILENAME, REPORT_FILENAME})
AUTOMATIC_CONFIGURATION_ID = "org.adviso.automatic-strict-exact"
_AT_FDCWD = -100
_RENAME_NOREPLACE = 1
_RENAME_EXCHANGE = 2
_UNSUPPORTED_RENAME_ERRORS = {
    getattr(errno, name)
    for name in ("EINVAL", "ENOSYS", "ENOTSUP", "EOPNOTSUPP")
    if hasattr(errno, name)
}


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


def render_html_report(document: Mapping[str, Any]) -> bytes:
    """Render a self-contained HTML view using only canonical-result facts."""
    run = document["run"]
    phases = document["phases"]
    inputs = document["inputs"]
    configuration = document["comparison_configuration"]["document"]
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
        "<title>AdvISO Compare evidence report</title>",
        "<style>",
        _STYLES,
        "</style>",
        "</head>",
        "<body>",
        '<header class="page-header">',
        "<h1>AdvISO Compare evidence report</h1>",
        '<p class="warning"><strong>Sensitive information:</strong> This evidence '
        "package may contain sensitive patient or laboratory information. Handle "
        "it under your laboratory’s information-governance arrangements.</p>",
        "<p>This run translated two structured datasets according to the embedded "
        "comparison configuration, then performed contract, records, and values "
        "comparison phases. The report presents measured evidence; review and "
        "approval occur outside the tool.</p>",
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
            _provenance_section(document),
            _review_section(),
            "</main>",
            "</body>",
            "</html>",
            "",
        )
    )
    return "\n".join(sections).encode("utf-8")


def publish_evidence_package(
    destination: Path,
    document: JsonObject,
    *,
    prepared: PreparedComparison,
    contract: ContractResult,
    records: RecordsResult,
    values: ValuesResult,
    overwrite: bool = False,
) -> Path:
    """Validate, stage, and publish one complete two-file evidence package."""
    validate_result(
        document,
        prepared=prepared,
        contract=contract,
        records=records,
        values=values,
    )
    json_content = serialize_result(document)
    published_document = json.loads(json_content.decode("utf-8"))
    html_content = render_html_report(published_document)
    destination = Path(destination)
    existing = _inspect_destination(destination, overwrite=overwrite)
    parent = destination.parent
    if not parent.is_dir():
        raise OutputError(
            code="write_failed",
            message="the output parent directory does not exist or is not a directory",
        )

    staging_root: Path | None = None
    try:
        staging_root = Path(
            tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=parent)
        )
        os.chmod(staging_root, 0o700)
        stage = staging_root / "package"
        stage.mkdir(mode=0o700)
        _write_atomic_member(stage / RESULTS_FILENAME, json_content)
        _write_atomic_member(stage / REPORT_FILENAME, html_content)
        _fsync_directory(stage)

        if existing:
            _inspect_destination(destination, overwrite=True)
            _replace_existing_package(stage, destination)
        else:
            _publish_new_package(stage, destination)
        _fsync_directory(parent)
    except OutputError:
        raise
    except OSError as error:
        raise OutputError(
            code="write_failed",
            message="the evidence package could not be written or published",
        ) from error
    finally:
        if staging_root is not None:
            _remove_temporary_directory(staging_root)
    return destination


def _publish_new_package(stage: Path, destination: Path) -> None:
    """Publish to an absent path without replacement where supported."""
    try:
        supported = _renameat2(stage, destination, _RENAME_NOREPLACE)
    except OSError as error:
        if error.errno not in {errno.EEXIST, errno.ENOTEMPTY}:
            raise
        raise OutputError(
            code="invalid_destination",
            message="the selected output destination already exists",
        ) from error
    if supported:
        return
    _require_absent(destination)
    os.rename(stage, destination)


def _replace_existing_package(
    stage: Path,
    destination: Path,
) -> None:
    """Replace only through an atomic exchange that preserves the original."""
    if not _exchange_directories(stage, destination):
        raise OutputError(
            code="write_failed",
            message=(
                "atomic overwrite is not supported at this destination; "
                "select a new output destination"
            ),
        )
    _remove_temporary_directory(stage)


def _exchange_directories(left: Path, right: Path) -> bool:
    """Atomically exchange two directories when the host filesystem supports it."""
    return _renameat2(left, right, _RENAME_EXCHANGE)


def _renameat2(source: Path, destination: Path, flags: int) -> bool:
    """Invoke Linux renameat2, returning false when the operation is unavailable."""
    if sys.platform != "linux":
        return False
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except AttributeError:
        return False
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        _AT_FDCWD,
        os.fsencode(source),
        _AT_FDCWD,
        os.fsencode(destination),
        flags,
    )
    if result == 0:
        return True
    error_number = ctypes.get_errno()
    if error_number in _UNSUPPORTED_RENAME_ERRORS:
        return False
    raise OSError(error_number, os.strerror(error_number))


def _inspect_destination(destination: Path, *, overwrite: bool) -> bool:
    """Return whether a replaceable complete package occupies the destination."""
    try:
        destination_stat = destination.lstat()
    except FileNotFoundError:
        return False
    except OSError as error:
        raise OutputError(
            code="invalid_destination",
            message="the selected output destination could not be inspected",
        ) from error
    if not overwrite:
        raise OutputError(
            code="invalid_destination",
            message="the selected output destination already exists",
        )
    if not stat.S_ISDIR(destination_stat.st_mode):
        raise OutputError(
            code="invalid_destination",
            message=(
                "overwrite requires an existing complete evidence-package "
                "directory"
            ),
        )
    try:
        entries = {entry.name: entry for entry in os.scandir(destination)}
        if set(entries) != PACKAGE_MEMBERS:
            raise OutputError(
                code="invalid_destination",
                message=(
                    "overwrite requires a directory containing exactly the two "
                    "version 1 evidence-package files"
                ),
            )
        if any(not entry.is_file(follow_symlinks=False) for entry in entries.values()):
            raise OutputError(
                code="invalid_destination",
                message="evidence-package members must be regular files",
            )
        result_bytes = (destination / RESULTS_FILENAME).read_bytes()
        report_text = (destination / REPORT_FILENAME).read_text(encoding="utf-8")
        existing_result = json.loads(result_bytes.decode("utf-8"))
        validate_result(existing_result)
        if not report_text.casefold().startswith("<!doctype html>"):
            raise ValueError("report is not recognizable HTML")
    except OutputError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise OutputError(
            code="invalid_destination",
            message=(
                "the existing directory is not a complete version 1 evidence "
                "package"
            ),
        ) from error
    return True


def _require_absent(destination: Path) -> None:
    """Refuse a destination that appeared while the package was staged."""
    try:
        destination.lstat()
    except FileNotFoundError:
        return
    except OSError as error:
        raise OutputError(
            code="invalid_destination",
            message="the selected output destination could not be inspected",
        ) from error
    raise OutputError(
        code="invalid_destination",
        message="the selected output destination already exists",
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
    """Best-effort removal for private staging or backup directories."""
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


def _provenance_section(document: Mapping[str, Any]) -> str:
    """Render sufficient provenance and embedded reproduction material."""
    run = document["run"]
    software = document["software"]
    runtime = document["runtime"]
    inputs = document["inputs"]
    configuration = document["comparison_configuration"]["document"]
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
        f"<dt>Results schema</dt><dd>{_escape(document['results_schema_version'])}</dd>"
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
