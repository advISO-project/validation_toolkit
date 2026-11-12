"""Resolve unambiguous record identity for custom and automatic comparisons."""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from adviso_compare.configuration import (
    AUTOMATIC_CONFIGURATION_ID,
    EffectiveConfiguration,
    FieldDefinition,
    JsonObject,
    resolve_automatic_configuration,
)
from adviso_compare.inputs import (
    InputSide,
    JsonLocation,
    NativeCategory,
    NativeValue,
    ParsedDataset,
    ParsedRecord,
    SourceLocation,
    TabularLocation,
)
from adviso_compare.translation import (
    ValueDisposition,
    render_canonical_scalar,
    translate_field_value,
)


@dataclass(frozen=True, slots=True)
class CanonicalKeyComponent:
    """One typed, uniquely rendered component of a canonical record key."""

    logical_type: str
    text: str


RecordKey = tuple[CanonicalKeyComponent, ...]


@dataclass(frozen=True, slots=True)
class KeyedRecord:
    """A source record accompanied by its source and canonical identities."""

    record: ParsedRecord
    key: RecordKey
    source_identity: tuple[str, ...]
    canonical_identity: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecordModel:
    """All records from one dataset indexed without silent replacement."""

    side: InputSide
    records: tuple[KeyedRecord, ...]
    by_key: Mapping[RecordKey, KeyedRecord]


@dataclass(slots=True)
class RecordKeyError(Exception):
    """An expected input failure that prevents unambiguous record identity."""

    message: str
    side: InputSide | None = None
    key_fields: tuple[str, ...] = ()
    candidate_fields: tuple[str, ...] = ()
    locations: tuple[SourceLocation, ...] = ()
    code: str = "invalid_record_key"

    @property
    def category(self) -> str:
        """Return the stable execution-error category."""
        return "input"

    @property
    def diagnostic(self) -> str:
        """Render a value-free, single-line execution diagnostic."""
        return f"ERROR [input.{self.code}]: {self.message}"

    def __str__(self) -> str:
        """Return the actionable value-free message."""
        return self.message


def generate_automatic_configuration(
    reference: ParsedDataset,
    query: ParsedDataset,
) -> EffectiveConfiguration:
    """Select one conservative key and build strict preserved-exact rules."""
    key_name = _select_automatic_key(reference, query)
    common_fields = sorted(set(reference.field_names) & set(query.field_names))
    ordered_fields = [key_name]
    ordered_fields.extend(name for name in common_fields if name != key_name)

    definitions: JsonObject = {
        key_name: {
            "source_fields": {
                "reference": key_name,
                "query": key_name,
            },
            "required": {"reference": True, "query": True},
            "logical_type": "string",
            "null_policy": {"allowed": False, "nulls_equal": False},
            "comparator": {"name": "typed_exact"},
        }
    }
    for field_name in ordered_fields[1:]:
        definitions[field_name] = {
            "source_fields": {
                "reference": field_name,
                "query": field_name,
            },
            "required": {"reference": False, "query": False},
            "null_policy": {"allowed": True, "nulls_equal": True},
            "comparator": {"name": "preserved_exact"},
        }

    document: JsonObject = {
        "schema_version": "1.0",
        "metadata": {
            "id": AUTOMATIC_CONFIGURATION_ID,
            "revision": "1.0",
        },
        "fields": {
            "record_key": [key_name],
            "in_scope": ordered_fields,
            "definitions": definitions,
        },
    }
    return resolve_automatic_configuration(document)


def build_record_model(
    dataset: ParsedDataset,
    configuration: EffectiveConfiguration,
    side: InputSide,
) -> RecordModel:
    """Translate configured key fields and reject every ambiguous identity."""
    keyed_records: list[KeyedRecord] = []
    index: dict[RecordKey, KeyedRecord] = {}
    source_key_fields = tuple(
        _source_field(configuration.field(name), side)
        for name in configuration.record_key
    )

    for record in dataset.records:
        components: list[CanonicalKeyComponent] = []
        source_identity: list[str] = []
        for canonical_name, source_name in zip(
            configuration.record_key,
            source_key_fields,
        ):
            field = configuration.field(canonical_name)
            if not record.has_field(source_name):
                raise _key_value_error(
                    side,
                    source_name,
                    "is missing",
                    record.location,
                    source_key_fields,
                )
            source = record.value(source_name)
            translated = translate_field_value(source, field, side)
            if translated.is_null or source.category is NativeCategory.NULL:
                raise _key_value_error(
                    side,
                    source_name,
                    "is null",
                    record.location_for(source_name),
                    source_key_fields,
                )
            if (
                translated.disposition is not ValueDisposition.VALID
                or translated.canonical is None
            ):
                raise _key_value_error(
                    side,
                    source_name,
                    "is invalid",
                    record.location_for(source_name),
                    source_key_fields,
                )
            logical_type = field.logical_type
            if not isinstance(logical_type, str):
                raise AssertionError("validated key field is not scalar")
            canonical_text = render_canonical_scalar(
                translated.canonical.value,
                logical_type,
            )
            components.append(CanonicalKeyComponent(logical_type, canonical_text))
            source_identity.append(_source_identity_text(source))

        key = tuple(components)
        keyed = KeyedRecord(
            record=record,
            key=key,
            source_identity=tuple(source_identity),
            canonical_identity=tuple(component.text for component in key),
        )
        previous = index.get(key)
        if previous is not None:
            locations = (previous.record.location, record.location)
            fields_text = ", ".join(repr(name) for name in source_key_fields)
            raise RecordKeyError(
                message=(
                    f"{side.value} duplicate record key using {fields_text} at "
                    f"{_format_location(locations[0])} and "
                    f"{_format_location(locations[1])}"
                ),
                side=side,
                key_fields=source_key_fields,
                locations=locations,
            )
        index[key] = keyed
        keyed_records.append(keyed)

    return RecordModel(
        side=side,
        records=tuple(keyed_records),
        by_key=MappingProxyType(index),
    )


def _select_automatic_key(
    reference: ParsedDataset,
    query: ParsedDataset,
) -> str:
    """Apply the fixed record_id preference and candidate criteria."""
    shared_fields = sorted(set(reference.field_names) & set(query.field_names))
    if "record_id" in shared_fields:
        _validate_automatic_record_id(reference, InputSide.REFERENCE)
        _validate_automatic_record_id(query, InputSide.QUERY)
        return "record_id"

    candidates = tuple(
        field_name
        for field_name in shared_fields
        if _is_automatic_candidate(field_name, reference, query)
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise RecordKeyError(
            message=(
                "no field satisfied the automatic record-key criteria after "
                "considering both inputs"
            )
        )
    names = ", ".join(repr(name) for name in candidates)
    raise RecordKeyError(
        message=(
            "automatic record-key selection is ambiguous after considering both "
            f"inputs; candidate fields are {names}"
        ),
        candidate_fields=candidates,
    )


def _validate_automatic_record_id(
    dataset: ParsedDataset,
    side: InputSide,
) -> None:
    """Require the preferred automatic key to be complete, string, and unique."""
    seen: dict[str, ParsedRecord] = {}
    for record in dataset.records:
        if not record.has_field("record_id"):
            raise _key_value_error(
                side,
                "record_id",
                "is missing",
                record.location,
                ("record_id",),
            )
        value = record.value("record_id")
        if value.category is not NativeCategory.STRING:
            reason = (
                "is null"
                if value.category is NativeCategory.NULL
                else "is not a parser-native string"
            )
            raise _key_value_error(
                side,
                "record_id",
                reason,
                record.location_for("record_id"),
                ("record_id",),
            )
        text = value.value
        if not isinstance(text, str):
            raise AssertionError("parser-native string does not contain text")
        previous = seen.get(text)
        if previous is not None:
            locations = (previous.location, record.location)
            raise RecordKeyError(
                message=(
                    f"{side.value} duplicate record key using 'record_id' at "
                    f"{_format_location(locations[0])} and "
                    f"{_format_location(locations[1])}"
                ),
                side=side,
                key_fields=("record_id",),
                locations=locations,
            )
        seen[text] = record


def _is_automatic_candidate(
    field_name: str,
    reference: ParsedDataset,
    query: ParsedDataset,
) -> bool:
    """Return whether one shared field satisfies every automatic-key criterion."""
    reference_values = _complete_unique_strings(reference, field_name)
    if reference_values is None:
        return False
    query_values = _complete_unique_strings(query, field_name)
    if query_values is None:
        return False
    return not reference_values.isdisjoint(query_values)


def _complete_unique_strings(
    dataset: ParsedDataset,
    field_name: str,
) -> set[str] | None:
    """Return unique source strings, or None when the candidate is invalid."""
    values: set[str] = set()
    for record in dataset.records:
        if not record.has_field(field_name):
            return None
        value = record.value(field_name)
        if value.category is not NativeCategory.STRING:
            return None
        text = value.value
        if not isinstance(text, str):
            raise AssertionError("parser-native string does not contain text")
        if text in values:
            return None
        values.add(text)
    return values


def _key_value_error(
    side: InputSide,
    source_name: str,
    reason: str,
    location: SourceLocation,
    key_fields: tuple[str, ...],
) -> RecordKeyError:
    """Construct one attributable, value-free key error."""
    return RecordKeyError(
        message=(
            f"{side.value} key field {source_name!r} {reason} at "
            f"{_format_location(location)}"
        ),
        side=side,
        key_fields=key_fields,
        locations=(location,),
    )


def _source_field(field: FieldDefinition, side: InputSide) -> str:
    """Select a field's source name for one dataset side."""
    if side is InputSide.REFERENCE:
        return field.source_fields.reference
    return field.source_fields.query


def _source_identity_text(value: NativeValue) -> str:
    """Render a scalar source key using its retained lexical representation."""
    if value.category is NativeCategory.STRING:
        if not isinstance(value.value, str):
            raise AssertionError("parser-native string does not contain text")
        return value.value
    if value.category in {NativeCategory.INTEGER, NativeCategory.DECIMAL}:
        if value.lexical is not None:
            return value.lexical
        return str(value.value)
    if value.category is NativeCategory.BOOLEAN:
        return "true" if value.value else "false"
    raise AssertionError("validated key source is not a non-null scalar")


def _format_location(location: SourceLocation) -> str:
    """Render a non-sensitive source location for an execution diagnostic."""
    if isinstance(location, TabularLocation):
        return (
            f"record {location.record_number}, physical line "
            f"{location.line_number}"
        )
    if isinstance(location, JsonLocation):
        pointer = json.dumps(location.pointer, ensure_ascii=False)
        return f"JSON pointer {pointer}"
    raise AssertionError("unknown source-location type")
