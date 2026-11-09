"""Assemble, validate, and serialize canonical comparison results."""

from __future__ import annotations

import json
import platform as runtime_platform
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from importlib.resources import files
from typing import TYPE_CHECKING, Any, Mapping
from uuid import UUID, uuid4

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource

from adviso_compare._version import __version__
from adviso_compare.alignment import RecordAlignment, RecordFinding, RecordsResult
from adviso_compare.configuration import EffectiveConfiguration, FieldDefinition
from adviso_compare.contract import (
    ConfiguredFieldExclusion,
    ContractFinding,
    ContractResult,
    FieldAssessment,
    UndeclaredFieldExclusion,
)
from adviso_compare.inputs import (
    InputSide,
    JsonLocation,
    NativeCategory,
    NativeValue,
    ParsedDataset,
    SourceLocation,
    TabularLocation,
)
from adviso_compare.translation import (
    CanonicalValue,
    TranslatedValue,
    ValueDisposition,
    render_canonical_scalar,
)
from adviso_compare.values import ValueFinding, ValuesResult

if TYPE_CHECKING:
    from adviso_compare.application import PreparedComparison


JsonObject = dict[str, Any]
RESULTS_SCHEMA_FILE = "comparison-results-v1.0.schema.json"
CONFIGURATION_SCHEMA_FILE = "comparison-configuration-v1.0.schema.json"
SCHEMA_PACKAGE = "adviso_compare.schemas"
FINDING_CODES = (
    "missing_record",
    "extra_record",
    "missing_required_field",
    "type_mismatch",
    "invalid_field_value",
    "null_policy_violation",
    "mapping_failure",
    "value_mismatch",
)
CLASSIFICATIONS = ("comparison_difference", "assessment_issue")
REVIEW_PRIORITIES = ("low", "normal", "high", "unassigned")


@dataclass(frozen=True, slots=True)
class RuntimeIdentity:
    """Non-identifying software-runtime provenance."""

    python: str
    platform: str
    unicode_version: str


@dataclass(frozen=True, slots=True)
class ResultValidationError(ValueError):
    """An internally generated result violates a structural or semantic rule."""

    message: str

    def __str__(self) -> str:
        """Return the concise invariant failure."""
        return self.message


def current_runtime_identity() -> RuntimeIdentity:
    """Return normalized, non-identifying runtime provenance."""
    implementation = runtime_platform.python_implementation().casefold()
    version = runtime_platform.python_version()
    operating_system = runtime_platform.system().casefold()
    operating_system = {"darwin": "macos"}.get(
        operating_system,
        operating_system,
    )
    architecture = runtime_platform.machine().casefold()
    architecture = {
        "amd64": "x86_64",
        "arm64": "aarch64",
    }.get(architecture, architecture)
    return RuntimeIdentity(
        python=f"{implementation}-{version}",
        platform=f"{operating_system}-{architecture}",
        unicode_version=unicodedata.unidata_version,
    )


def assemble_result(
    prepared: PreparedComparison,
    contract: ContractResult,
    records: RecordsResult,
    values: ValuesResult,
    *,
    run_id: UUID | None = None,
    completed_at: datetime | None = None,
    software_version: str = __version__,
    runtime: RuntimeIdentity | None = None,
) -> JsonObject:
    """Build and self-validate one complete canonical result document."""
    identifier = run_id or uuid4()
    completion = completed_at or datetime.now(timezone.utc)
    if identifier.version != 4:
        raise ValueError("run_id must be a UUID version 4")
    if completion.tzinfo is None or completion.utcoffset() is None:
        raise ValueError("completed_at must be timezone-aware")
    completion_text = completion.astimezone(timezone.utc).replace(
        microsecond=0
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    runtime_identity = runtime or current_runtime_identity()

    findings = _assemble_findings(prepared.configuration, contract, records, values)
    phase_statuses = {
        "contract": contract.status.value,
        "records": records.status.value,
        "values": values.status.value,
    }
    run_status = (
        "complete"
        if all(status == "complete" for status in phase_statuses.values())
        else "incomplete"
    )
    document: JsonObject = {
        "results_schema_version": "1.0",
        "run": {
            "id": str(identifier),
            "status": run_status,
            "completed_at": completion_text,
        },
        "phases": phase_statuses,
        "software": {"name": "adviso-compare", "version": software_version},
        "runtime": {
            "python": runtime_identity.python,
            "platform": runtime_identity.platform,
            "unicode_version": runtime_identity.unicode_version,
        },
        "inputs": {
            "reference": _input_document(prepared.reference),
            "query": _input_document(prepared.query),
        },
        "record_key_fields": _record_key_fields(prepared.configuration),
        "comparison_configuration": {
            "document": _ordered_configuration(prepared.configuration.document)
        },
        "summary": _summary_document(records, values, findings),
        "exclusions": [_exclusion_document(item) for item in contract.exclusions],
        "findings": findings,
    }
    validate_result(
        document,
        prepared=prepared,
        contract=contract,
        records=records,
        values=values,
    )
    return document


def serialize_result(document: Mapping[str, object]) -> bytes:
    """Serialize a validated result as canonical UTF-8 JSON."""
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def validate_result(
    document: JsonObject,
    *,
    prepared: PreparedComparison | None = None,
    contract: ContractResult | None = None,
    records: RecordsResult | None = None,
    values: ValuesResult | None = None,
) -> None:
    """Apply schema and semantic validation to a generated result."""
    try:
        _results_validator().validate(document)
    except ValidationError as error:
        raise ResultValidationError(
            "canonical result failed schema validation"
        ) from error
    _validate_semantics(document, prepared, contract, records, values)


@lru_cache(maxsize=1)
def _results_validator() -> Draft202012Validator:
    """Load the packaged schemas with format assertion and local resolution."""
    package = files(SCHEMA_PACKAGE)
    results = json.loads(
        package.joinpath(RESULTS_SCHEMA_FILE).read_text(encoding="utf-8")
    )
    configuration = json.loads(
        package.joinpath(CONFIGURATION_SCHEMA_FILE).read_text(encoding="utf-8")
    )
    registry = Registry().with_resources(
        (
            (results["$id"], Resource.from_contents(results)),
            (configuration["$id"], Resource.from_contents(configuration)),
        )
    )
    return Draft202012Validator(
        results,
        registry=registry,
        format_checker=FormatChecker(),
    )


def _input_document(dataset: ParsedDataset) -> JsonObject:
    """Render exact-byte input provenance without exposing a path."""
    provenance = dataset.provenance
    return {
        "basename": provenance.basename,
        "format": provenance.format.value,
        "encoding": provenance.encoding,
        "size_bytes": provenance.size_bytes,
        "digest": {"algorithm": "sha256", "value": provenance.sha256},
    }


def _record_key_fields(configuration: EffectiveConfiguration) -> JsonObject:
    """Render ordered source and canonical key-field declarations."""
    return {
        "reference": [
            configuration.field(name).source_fields.reference
            for name in configuration.record_key
        ],
        "query": [
            configuration.field(name).source_fields.query
            for name in configuration.record_key
        ],
        "canonical": list(configuration.record_key),
    }


def _ordered_configuration(document: JsonObject) -> JsonObject:
    """Return the configuration in fixed-schema and dynamic-name order."""
    metadata = document["metadata"]
    fields = document["fields"]
    definitions = fields["definitions"]
    return {
        "schema_version": document["schema_version"],
        "metadata": _ordered_selected(
            metadata,
            ("id", "revision", "title", "description"),
        ),
        "fields": {
            "record_key": fields["record_key"],
            "in_scope": fields["in_scope"],
            "definitions": {
                name: _ordered_field_definition(definitions[name])
                for name in sorted(definitions)
            },
        },
    }


def _ordered_field_definition(document: JsonObject) -> JsonObject:
    """Order one embedded field declaration without applying defaults."""
    ordered: JsonObject = {}
    for name in (
        "source_fields",
        "required",
        "logical_type",
        "null_policy",
        "source_normalisation",
        "collection_representation",
        "value_mapping",
        "typed_normalisation",
        "comparator",
        "review_priority",
    ):
        if name not in document:
            continue
        value = document[name]
        if name in {"source_fields", "required", "source_normalisation"}:
            ordered[name] = _ordered_sides(value)
        elif name == "logical_type" and isinstance(value, dict):
            logical = _ordered_selected(
                value,
                ("collection_type", "element_type", "element_comparator"),
            )
            if "element_comparator" in logical:
                logical["element_comparator"] = _ordered_named_parameters(
                    logical["element_comparator"]
                )
            ordered[name] = logical
        elif name == "null_policy":
            null_policy = _ordered_selected(
                value,
                ("allowed", "nulls_equal", "missing_tokens"),
            )
            if "missing_tokens" in null_policy:
                null_policy["missing_tokens"] = _ordered_sides(
                    null_policy["missing_tokens"]
                )
            ordered[name] = null_policy
        elif name in {"collection_representation", "value_mapping"}:
            ordered[name] = _ordered_sides(value)
        elif name == "comparator":
            ordered[name] = _ordered_named_parameters(value)
        else:
            ordered[name] = _ordered_nested(value)
    return ordered


def _ordered_sides(document: object) -> object:
    """Order a reference/query mapping and recursively order its content."""
    if not isinstance(document, dict):
        return _ordered_nested(document)
    return {
        name: _ordered_nested(document[name])
        for name in ("reference", "query")
        if name in document
    }


def _ordered_named_parameters(document: JsonObject) -> JsonObject:
    """Order an operation or comparator declaration."""
    return _ordered_selected(document, ("name", "operation", "parameters"))


def _ordered_selected(
    document: Mapping[str, object],
    names: tuple[str, ...],
) -> JsonObject:
    """Copy selected fixed properties in documented schema order."""
    return {
        name: _ordered_nested(document[name])
        for name in names
        if name in document
    }


def _ordered_nested(value: object) -> object:
    """Order known fixed objects and otherwise use Unicode member order."""
    if isinstance(value, list):
        return [_ordered_nested(item) for item in value]
    if not isinstance(value, dict):
        return value
    keys = set(value)
    if keys <= {"reference", "query"}:
        return _ordered_sides(value)
    if "operation" in value:
        return _ordered_selected(value, ("operation", "parameters"))
    if keys <= {"category", "value"} and "category" in value:
        return _ordered_selected(value, ("category", "value"))
    if keys <= {"from", "to"}:
        return _ordered_selected(value, ("from", "to"))
    if "format" in value:
        return _ordered_selected(
            value,
            ("format", "delimiter", "element_normalisation", "element_mapping"),
        )
    if keys <= {"name", "parameters"} and "name" in value:
        return _ordered_named_parameters(value)
    return {name: _ordered_nested(value[name]) for name in sorted(value)}


def _summary_document(
    records: RecordsResult,
    values: ValuesResult,
    findings: list[JsonObject],
) -> JsonObject:
    """Build fixed-shape, zero-inclusive reconciled summary counts."""
    code_counts = Counter(item["code"] for item in findings)
    classification_counts = Counter(item["classification"] for item in findings)
    priority_counts = Counter(
        item.get("review_priority", "unassigned") for item in findings
    )
    return {
        "records": {
            "reference": records.counts.reference,
            "query": records.counts.query,
            "matched": records.counts.matched,
            "missing": records.counts.missing,
            "extra": records.counts.extra,
        },
        "values": {
            "matched": values.counts.matched,
            "mismatched": values.counts.mismatched,
            "not_assessable": values.counts.not_assessable,
        },
        "findings": {
            "total": len(findings),
            "by_classification": {
                name: classification_counts[name] for name in CLASSIFICATIONS
            },
            "by_code": {name: code_counts[name] for name in FINDING_CODES},
            "by_review_priority": {
                name: priority_counts[name] for name in REVIEW_PRIORITIES
            },
        },
    }


def _exclusion_document(
    exclusion: ConfiguredFieldExclusion | UndeclaredFieldExclusion,
) -> JsonObject:
    """Render one of the two closed exclusion forms."""
    if isinstance(exclusion, ConfiguredFieldExclusion):
        return {
            "code": exclusion.code,
            "canonical_field": exclusion.canonical_field,
        }
    return {
        "code": exclusion.code,
        "side": exclusion.side.value,
        "source_field": exclusion.source_field,
        "record_count": exclusion.record_count,
    }


def _assemble_findings(
    configuration: EffectiveConfiguration,
    contract: ContractResult,
    records: RecordsResult,
    values: ValuesResult,
) -> list[JsonObject]:
    """Convert, coalesce, sort, and identify every finding candidate."""
    candidates = [
        *(
            _record_finding_document(finding)
            for finding in records.findings
        ),
        *(
            _contract_finding_document(configuration, records, contract, finding)
            for finding in contract.findings
        ),
        *(
            _value_finding_document(configuration, finding)
            for finding in values.findings
        ),
    ]
    unique: dict[tuple[object, ...], JsonObject] = {}
    for candidate in candidates:
        key = _finding_sort_key(candidate)
        unique.setdefault(key, candidate)
    ordered = [unique[key] for key in sorted(unique)]
    return [
        _identified_finding(index, candidate)
        for index, candidate in enumerate(ordered, start=1)
    ]


def _record_finding_document(finding: RecordFinding) -> JsonObject:
    """Build structured evidence for one missing or extra record."""
    return {
        "classification": finding.classification,
        "code": finding.code,
        "phase": finding.phase,
        "affected_side": finding.affected_side.value,
        "record_identity": _record_identity(finding.alignment),
        "source_locations": {
            "reference": _location_document(finding.reference_location),
            "query": _location_document(finding.query_location),
        },
    }


def _contract_finding_document(
    configuration: EffectiveConfiguration,
    records: RecordsResult,
    contract: ContractResult,
    finding: ContractFinding,
) -> JsonObject:
    """Build code-specific evidence for one failed contract prerequisite."""
    base: JsonObject = {
        "classification": finding.classification,
        "code": finding.code,
        "phase": finding.phase,
        "affected_side": finding.side.value,
    }
    if finding.record is None:
        base["field"] = finding.canonical_field
        base["review_priority"] = finding.review_priority
        return base

    alignment = records.alignment(finding.record.key)
    field = configuration.field(finding.canonical_field)
    assessments = {
        side: _assessment_for_alignment(
            contract,
            alignment,
            side,
            finding.canonical_field,
        )
        for side in (InputSide.REFERENCE, InputSide.QUERY)
    }
    base["record_identity"] = _record_identity(alignment)
    base["source_locations"] = _field_locations(field, alignment)
    base["field"] = finding.canonical_field
    base["review_priority"] = finding.review_priority
    base["values"] = _contract_values(finding, field, assessments)
    return base


def _value_finding_document(
    configuration: EffectiveConfiguration,
    finding: ValueFinding,
) -> JsonObject:
    """Build complete two-sided evidence for one post-translation difference."""
    opportunity = finding.opportunity
    field = configuration.field(finding.canonical_field)
    return {
        "classification": finding.classification,
        "code": finding.code,
        "phase": finding.phase,
        "affected_side": finding.affected_side,
        "record_identity": _record_identity(opportunity.alignment),
        "source_locations": {
            "reference": _location_document(finding.reference_location),
            "query": _location_document(finding.query_location),
        },
        "field": finding.canonical_field,
        "review_priority": finding.review_priority,
        "values": {
            "reference": _field_evidence(
                opportunity.reference.translated,
                include_source=True,
                include_canonical=field.logical_type is not None,
            ),
            "query": _field_evidence(
                opportunity.query.translated,
                include_source=True,
                include_canonical=field.logical_type is not None,
            ),
        },
    }


def _assessment_for_alignment(
    contract: ContractResult,
    alignment: RecordAlignment,
    side: InputSide,
    canonical_field: str,
) -> FieldAssessment | None:
    """Return the field assessment when the aligned side contains a record."""
    record = alignment.reference if side is InputSide.REFERENCE else alignment.query
    if record is None:
        return None
    return contract.assessment(side, record.key, canonical_field)


def _contract_values(
    finding: ContractFinding,
    field: FieldDefinition,
    assessments: Mapping[InputSide, FieldAssessment | None],
) -> JsonObject:
    """Apply the finding-code-specific source-value minimisation rules."""
    values: JsonObject = {}
    for side in (InputSide.REFERENCE, InputSide.QUERY):
        assessment = assessments[side]
        if assessment is None:
            values[side.value] = {"state": "absent"}
            continue
        translated = assessment.translated
        if finding.code == "missing_required_field":
            values[side.value] = {
                "state": (
                    "absent"
                    if translated.disposition is ValueDisposition.NOT_ASSESSABLE
                    and translated.source is None
                    else "present"
                )
            }
            continue
        affected = side is finding.side
        evidence = _field_evidence(
            translated,
            include_source=affected,
            include_canonical=False,
        )
        if (
            affected
            and finding.code == "null_policy_violation"
            and field.logical_type is not None
        ):
            evidence["canonical"] = _null_canonical_document(field)
        values[side.value] = evidence
    return values


def _field_evidence(
    translated: TranslatedValue,
    *,
    include_source: bool,
    include_canonical: bool,
) -> JsonObject:
    """Render one side's presence and permitted source/canonical evidence."""
    if translated.disposition is ValueDisposition.ABSENT or translated.source is None:
        return {"state": "absent"}
    evidence: JsonObject = {"state": "present"}
    if include_source:
        evidence["source"] = _source_value_document(translated.source)
    if include_canonical and translated.canonical is not None:
        evidence["canonical"] = _canonical_value_document(translated.canonical)
    return evidence


def _null_canonical_document(field: FieldDefinition) -> JsonObject:
    """Render the declared typed-null representation for a null violation."""
    logical_type = field.logical_type
    if logical_type is None:
        raise AssertionError("untyped null violation has no canonical null")
    if isinstance(logical_type, str):
        return {"logical_type": logical_type, "value": None}
    return {
        "logical_type": logical_type.collection_type,
        "element_type": logical_type.element_type,
        "value": None,
    }


def _source_value_document(value: NativeValue) -> JsonObject:
    """Render a recursively typed parser-native source value."""
    document: JsonObject = {"category": value.category.value}
    if value.category is NativeCategory.NULL:
        return document
    if value.category is NativeCategory.STRING:
        document["value"] = value.value
    elif value.category in {NativeCategory.INTEGER, NativeCategory.DECIMAL}:
        document["value"] = (
            value.lexical if value.lexical is not None else str(value.value)
        )
    elif value.category is NativeCategory.BOOLEAN:
        document["value"] = value.value
    elif value.category is NativeCategory.ARRAY:
        if not isinstance(value.value, tuple):
            raise AssertionError("parser-native array does not contain a tuple")
        document["value"] = [_source_value_document(item) for item in value.value]
    elif value.category is NativeCategory.OBJECT:
        if not isinstance(value.value, tuple):
            raise AssertionError("parser-native object does not contain members")
        document["value"] = {
            name: _source_value_document(member)
            for name, member in sorted(value.value, key=lambda item: item[0])
        }
    else:
        raise AssertionError("unregistered parser-native category")
    return document


def _canonical_value_document(value: CanonicalValue) -> JsonObject:
    """Render one typed canonical value in its unique evidence form."""
    if value.element_type is not None:
        rendered = None
        if value.value is not None:
            if not isinstance(value.value, tuple):
                raise AssertionError("canonical collection does not contain a tuple")
            rendered = [
                _compact_canonical_scalar(item, value.element_type)
                for item in value.value
            ]
        return {
            "logical_type": value.logical_type,
            "element_type": value.element_type,
            "value": rendered,
        }
    rendered_value: object = value.value
    if value.value is not None:
        rendered_value = _compact_canonical_scalar(value.value, value.logical_type)
    return {"logical_type": value.logical_type, "value": rendered_value}


def _compact_canonical_scalar(value: object, logical_type: str) -> object:
    """Render a canonical scalar using the schema's compact scalar form."""
    if logical_type == "boolean":
        return value
    return render_canonical_scalar(value, logical_type)


def _record_identity(alignment: RecordAlignment) -> JsonObject:
    """Render source-side and canonical ordered record identities."""
    return {
        "reference": (
            list(alignment.reference.source_identity)
            if alignment.reference is not None
            else None
        ),
        "query": (
            list(alignment.query.source_identity)
            if alignment.query is not None
            else None
        ),
        "canonical": list(alignment.canonical_identity),
    }


def _field_locations(
    field: FieldDefinition,
    alignment: RecordAlignment,
) -> JsonObject:
    """Render each side's present-field or containing-record location."""
    return {
        "reference": _location_document(
            alignment.reference.record.location_for(field.source_fields.reference)
            if alignment.reference is not None
            else None
        ),
        "query": _location_document(
            alignment.query.record.location_for(field.source_fields.query)
            if alignment.query is not None
            else None
        ),
    }


def _location_document(location: SourceLocation | None) -> JsonObject | None:
    """Render one tabular or JSON source location."""
    if location is None:
        return None
    if isinstance(location, TabularLocation):
        document: JsonObject = {
            "record_number": location.record_number,
            "line_number": location.line_number,
        }
        if location.field_name is not None:
            document["field"] = location.field_name
        return document
    if isinstance(location, JsonLocation):
        return {"json_pointer": location.pointer}
    raise AssertionError("unknown source-location type")


def _identified_finding(index: int, candidate: JsonObject) -> JsonObject:
    """Assign a sequential ID and deterministic presentation message."""
    document: JsonObject = {
        "id": f"F{index:06d}",
        "classification": candidate["classification"],
        "code": candidate["code"],
        "phase": candidate["phase"],
        "message": _finding_message(candidate),
        "affected_side": candidate["affected_side"],
    }
    for name in (
        "record_identity",
        "source_locations",
        "field",
        "review_priority",
        "values",
    ):
        if name in candidate:
            document[name] = candidate[name]
    return document


def _finding_message(finding: Mapping[str, object]) -> str:
    """Derive concise English presentation text from structured properties."""
    code = finding["code"]
    side = str(finding["affected_side"])
    field = finding.get("field")
    if code == "missing_record":
        return "The query record is missing."
    if code == "extra_record":
        return "The query contains an extra record."
    if code == "missing_required_field":
        return f"Required {side} field {field!r} is absent."
    if code == "type_mismatch":
        return f"The {side} value for field {field!r} has an incompatible type."
    if code == "invalid_field_value":
        return f"The {side} value for field {field!r} is invalid."
    if code == "null_policy_violation":
        return f"The {side} value for field {field!r} violates its null policy."
    if code == "mapping_failure":
        return f"The {side} value for field {field!r} has no configured mapping."
    if code == "value_mismatch":
        return f"Reference and query values for field {field!r} differ."
    raise AssertionError("unregistered finding code")


def _finding_sort_key(finding: Mapping[str, object]) -> tuple[object, ...]:
    """Return the complete canonical total-order and coalescence key."""
    classification_order = {name: index for index, name in enumerate(CLASSIFICATIONS)}
    phase_order = {"contract": 0, "records": 1, "values": 2}
    code_order = {name: index for index, name in enumerate(FINDING_CODES)}
    side_order = {"reference": 0, "query": 1, "both": 2}
    identity = finding.get("record_identity")
    canonical_identity: tuple[str, ...] = ()
    if isinstance(identity, dict):
        canonical_identity = tuple(identity["canonical"])
    remaining = {
        key: value
        for key, value in finding.items()
        if key not in {"id", "message"}
    }
    return (
        classification_order[str(finding["classification"])],
        phase_order[str(finding["phase"])],
        identity is not None,
        canonical_identity,
        str(finding.get("field", "")),
        code_order[str(finding["code"])],
        side_order[str(finding["affected_side"])],
        _locations_sort_key(finding.get("source_locations")),
        json.dumps(
            remaining,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


def _locations_sort_key(locations: object) -> tuple[object, ...]:
    """Return the specified two-sided source-location ordering key."""
    if not isinstance(locations, dict):
        return ((0,), (0,))
    return (
        _location_sort_key(locations.get("reference")),
        _location_sort_key(locations.get("query")),
    )


def _location_sort_key(location: object) -> tuple[object, ...]:
    """Return the specified order for one serialized location."""
    if location is None:
        return (0,)
    if not isinstance(location, dict):
        raise ResultValidationError("source location is not an object or null")
    if "record_number" in location:
        return (
            1,
            location["record_number"],
            location["line_number"],
            location.get("field", ""),
        )
    return (1, location["json_pointer"])


def _validate_semantics(
    document: JsonObject,
    prepared: PreparedComparison | None,
    contract: ContractResult | None,
    domain_records: RecordsResult | None,
    domain_values: ValuesResult | None,
) -> None:
    """Verify invariants that JSON Schema cannot express."""
    phases = document["phases"]
    expected_status = (
        "complete"
        if all(value == "complete" for value in phases.values())
        else "incomplete"
    )
    _require(
        document["run"]["status"] == expected_status,
        "run status disagrees with phases",
    )

    records = document["summary"]["records"]
    _require(
        records["reference"] == records["matched"] + records["missing"],
        "reference record counts do not reconcile",
    )
    _require(
        records["query"] == records["matched"] + records["extra"],
        "query record counts do not reconcile",
    )
    configuration_fields = document["comparison_configuration"]["document"][
        "fields"
    ]
    compared_field_count = len(
        set(configuration_fields["in_scope"])
        - set(configuration_fields["record_key"])
    )
    value_summary = document["summary"]["values"]
    classified_opportunities = sum(value_summary.values())
    expected_opportunities = records["matched"] * compared_field_count
    _require(
        classified_opportunities == expected_opportunities,
        "value opportunity counts do not reconcile",
    )
    expected_values_status = (
        "incomplete" if value_summary["not_assessable"] else "complete"
    )
    _require(
        phases["values"] == expected_values_status,
        "values phase status disagrees with not-assessable opportunities",
    )
    if domain_records is not None:
        _require(
            records
            == {
                "reference": domain_records.counts.reference,
                "query": domain_records.counts.query,
                "matched": domain_records.counts.matched,
                "missing": domain_records.counts.missing,
                "extra": domain_records.counts.extra,
            },
            "record summary disagrees with the records phase",
        )
    if domain_values is not None:
        _require(
            document["summary"]["values"]
            == {
                "matched": domain_values.counts.matched,
                "mismatched": domain_values.counts.mismatched,
                "not_assessable": domain_values.counts.not_assessable,
            },
            "value summary disagrees with the values phase",
        )
    if (
        contract is not None
        and domain_records is not None
        and domain_values is not None
    ):
        expected_phases = {
            "contract": contract.status.value,
            "records": domain_records.status.value,
            "values": domain_values.status.value,
        }
        _require(phases == expected_phases, "phase status disagrees with phase results")
        if prepared is None:
            raise ResultValidationError(
                "phase-result validation requires prepared comparison context"
            )
        expected_findings = _assemble_findings(
            prepared.configuration,
            contract,
            domain_records,
            domain_values,
        )
        _require(
            document["findings"] == expected_findings,
            "findings disagree with the comparison phase results",
        )

    findings = document["findings"]
    summary = document["summary"]["findings"]
    _require(summary["total"] == len(findings), "finding total does not reconcile")
    expected_classifications = Counter(item["classification"] for item in findings)
    expected_codes = Counter(item["code"] for item in findings)
    expected_priorities = Counter(
        item.get("review_priority", "unassigned") for item in findings
    )
    _require(
        summary["by_classification"]
        == {name: expected_classifications[name] for name in CLASSIFICATIONS},
        "finding classification counts do not reconcile",
    )
    _require(
        summary["by_code"] == {name: expected_codes[name] for name in FINDING_CODES},
        "finding code counts do not reconcile",
    )
    _require(
        summary["by_review_priority"]
        == {name: expected_priorities[name] for name in REVIEW_PRIORITIES},
        "finding review-priority counts do not reconcile",
    )

    expected_ids = [f"F{index:06d}" for index in range(1, len(findings) + 1)]
    _require(
        [item["id"] for item in findings] == expected_ids,
        "finding IDs are not sequential",
    )
    finding_keys = [_finding_sort_key(item) for item in findings]
    _require(
        finding_keys == sorted(finding_keys),
        "findings are not canonically ordered",
    )
    _require(
        len(finding_keys) == len(set(finding_keys)),
        "duplicate findings are present",
    )

    key_fields = document["record_key_fields"]
    key_length = len(key_fields["canonical"])
    _require(
        len(key_fields["reference"]) == key_length
        and len(key_fields["query"]) == key_length,
        "record-key field arrays have inconsistent lengths",
    )
    for finding in findings:
        identity = finding.get("record_identity")
        if identity is None:
            continue
        _require(
            len(identity["canonical"]) == key_length
            and (
                identity["reference"] is None
                or len(identity["reference"]) == key_length
            )
            and (identity["query"] is None or len(identity["query"]) == key_length),
            "record identity has an inconsistent component count",
        )

    exclusion_keys = [_exclusion_sort_key(item) for item in document["exclusions"]]
    _require(
        exclusion_keys == sorted(exclusion_keys),
        "exclusions are not canonically ordered",
    )
    _require(
        len(exclusion_keys) == len(set(exclusion_keys)),
        "duplicate exclusions are present",
    )
    _validate_configuration_derivations(document, prepared)


def _validate_configuration_derivations(
    document: JsonObject,
    prepared: PreparedComparison | None,
) -> None:
    """Cross-check configuration-derived evidence and available source context."""
    configuration = document["comparison_configuration"]["document"]
    if prepared is not None:
        _require(
            configuration == prepared.configuration.document,
            "embedded configuration disagrees with the effective configuration",
        )
        _require(
            document["inputs"]
            == {
                "reference": _input_document(prepared.reference),
                "query": _input_document(prepared.query),
            },
            "input provenance disagrees with the parsed inputs",
        )
    fields = configuration["fields"]
    definitions = fields["definitions"]
    record_key = fields["record_key"]
    expected_key_fields = {
        "reference": [
            definitions[name]["source_fields"]["reference"] for name in record_key
        ],
        "query": [
            definitions[name]["source_fields"]["query"] for name in record_key
        ],
        "canonical": record_key,
    }
    _require(
        document["record_key_fields"] == expected_key_fields,
        "record-key metadata disagrees with the embedded configuration",
    )
    for finding in document["findings"]:
        field = finding.get("field")
        if field is None:
            continue
        _require(field in definitions, "finding names an undeclared canonical field")
        expected_priority = definitions[field].get("review_priority", "normal")
        _require(
            finding["review_priority"] == expected_priority,
            "finding review priority disagrees with the embedded configuration",
        )

    expected_configured = [
        {"code": "configured_field_excluded", "canonical_field": name}
        for name in sorted(set(definitions) - set(fields["in_scope"]))
    ]
    actual_configured = [
        item
        for item in document["exclusions"]
        if item["code"] == "configured_field_excluded"
    ]
    _require(
        actual_configured == expected_configured,
        "configured-field exclusions disagree with the embedded configuration",
    )
    if prepared is None:
        return
    expected_undeclared = _expected_undeclared_exclusions(
        prepared,
        definitions,
    )
    actual_undeclared = [
        item
        for item in document["exclusions"]
        if item["code"] == "undeclared_field_excluded"
    ]
    _require(
        actual_undeclared == expected_undeclared,
        "undeclared-field exclusions disagree with observed source fields",
    )


def _expected_undeclared_exclusions(
    prepared: PreparedComparison,
    definitions: Mapping[str, JsonObject],
) -> list[JsonObject]:
    """Derive expected source-field exclusions from parsed datasets."""
    expected: list[JsonObject] = []
    for side, dataset in (
        ("reference", prepared.reference),
        ("query", prepared.query),
    ):
        represented = {
            definition["source_fields"][side]
            for definition in definitions.values()
        }
        for source_field in sorted(set(dataset.field_names) - represented):
            expected.append(
                {
                    "code": "undeclared_field_excluded",
                    "side": side,
                    "source_field": source_field,
                    "record_count": sum(
                        record.has_field(source_field) for record in dataset.records
                    ),
                }
            )
    return expected


def _exclusion_sort_key(exclusion: Mapping[str, object]) -> tuple[object, ...]:
    """Return the complete specified exclusion order and identity."""
    if exclusion["code"] == "configured_field_excluded":
        return (0, exclusion["canonical_field"])
    side_order = {"reference": 0, "query": 1}
    return (
        1,
        side_order[str(exclusion["side"])],
        exclusion["source_field"],
        exclusion["record_count"],
    )


def _require(condition: bool, message: str) -> None:
    """Raise the internal validation exception for a failed invariant."""
    if not condition:
        raise ResultValidationError(message)
