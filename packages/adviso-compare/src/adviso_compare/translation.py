"""Translate configured source field values into canonical typed values."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
from enum import Enum
from typing import TypeVar

from adviso_compare.configuration import (
    CollectionLogicalType,
    CollectionRepresentation,
    DatasetSides,
    FieldDefinition,
    Operation,
    SourceValueDescriptor,
    ValueMappingEntry,
)
from adviso_compare.inputs import (
    InputSide,
    JsonValueError,
    NativeCategory,
    NativeValue,
    decode_json_value,
)
from adviso_compare.processing import apply_source_text_operation


_INTEGER_PATTERN = re.compile(r"^[+-]?[0-9]+$")
_DECIMAL_PATTERN = re.compile(
    r"^[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$"
)
_DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_DATETIME_PATTERN = re.compile(
    r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]"
    r"(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    r"(?:\.(?P<fraction>[0-9]+))?"
    r"(?P<offset>[Zz]|[+-][0-9]{2}:[0-9]{2})$"
)
T = TypeVar("T")


class ValueDisposition(str, Enum):
    """The assessment state of one configured field value."""

    VALID = "valid"
    ABSENT = "absent"
    NOT_ASSESSABLE = "not_assessable"
    NOT_ASSESSED = "not_assessed"


class TranslationIssueCode(str, Enum):
    """The causal finding code for an unsuccessful field translation."""

    MISSING_REQUIRED_FIELD = "missing_required_field"
    TYPE_MISMATCH = "type_mismatch"
    INVALID_FIELD_VALUE = "invalid_field_value"
    NULL_POLICY_VIOLATION = "null_policy_violation"
    MAPPING_FAILURE = "mapping_failure"


class TranslationStage(str, Enum):
    """The processing stage at which an attributable value became unusable."""

    PRESENCE = "presence"
    NULL_POLICY = "null_policy"
    VALUE_MAPPING = "value_mapping"
    TYPE_PARSING = "type_parsing"
    TYPED_NORMALISATION = "typed_normalisation"
    COLLECTION_DECODING = "collection_decoding"
    ELEMENT_MAPPING = "element_mapping"
    ELEMENT_PARSING = "element_parsing"
    COLLECTION_VALIDATION = "collection_validation"


@dataclass(frozen=True, slots=True)
class TranslationIssue:
    """A structured cause for one not-assessable translated value."""

    code: TranslationIssueCode
    stage: TranslationStage
    element_index: int | None = None


@dataclass(frozen=True, slots=True)
class CanonicalValue:
    """One scalar, null, or collection value in its declared logical type."""

    logical_type: str
    value: object
    element_type: str | None = None


@dataclass(frozen=True, slots=True)
class TranslatedValue:
    """The complete source-to-canonical outcome for one field on one side."""

    disposition: ValueDisposition
    source: NativeValue | None
    canonical: CanonicalValue | None = None
    preserved: NativeValue | None = None
    is_null: bool = False
    issue: TranslationIssue | None = None


@dataclass(frozen=True, slots=True)
class _ExactDateTime:
    """A UTC whole second plus an exact non-negative fractional second."""

    utc_second: datetime
    fraction: Decimal


class _TypeMismatch(ValueError):
    """The parser-native category is incompatible with a logical type."""


class _InvalidValue(ValueError):
    """The parser-native category is accepted but its content is invalid."""


def translate_field_value(
    source: NativeValue | None,
    field: FieldDefinition,
    side: InputSide,
    *,
    in_scope: bool = True,
) -> TranslatedValue:
    """Apply the configured translation pipeline to one attributable field value."""
    if not in_scope:
        return TranslatedValue(ValueDisposition.NOT_ASSESSED, source)
    if source is None:
        if _for_side(field.required, side):
            return _failure(
                source,
                TranslationIssueCode.MISSING_REQUIRED_FIELD,
                TranslationStage.PRESENCE,
            )
        return TranslatedValue(ValueDisposition.ABSENT, source)

    if field.logical_type is None:
        if source.category is NativeCategory.NULL:
            return _apply_null_policy(source, source, field)
        return TranslatedValue(
            ValueDisposition.VALID,
            source,
            preserved=source,
        )

    source_operations = _for_side(field.source_normalisation, side)
    working = _apply_source_operations(source, source_operations)
    if working.category is NativeCategory.NULL or _matches_any_descriptor(
        working,
        _for_side(field.null_policy.missing_tokens, side),
        source_operations,
    ):
        return _apply_null_policy(source, working, field)

    mappings = _for_side(field.value_mapping, side)
    if mappings:
        mapped = _mapped_value(working, mappings, source_operations)
        if mapped is None:
            return _failure(
                source,
                TranslationIssueCode.MAPPING_FAILURE,
                TranslationStage.VALUE_MAPPING,
            )
        working = mapped
        if working.category is NativeCategory.NULL:
            return _apply_null_policy(source, working, field)

    if isinstance(field.logical_type, CollectionLogicalType):
        return _translate_collection(source, working, field, side)

    try:
        value = _parse_scalar(working, field.logical_type)
        for operation in field.typed_normalisation:
            value = _apply_typed_operation(value, operation)
        value = _finalize_scalar(value, field.logical_type)
    except _TypeMismatch:
        return _failure(
            source,
            TranslationIssueCode.TYPE_MISMATCH,
            TranslationStage.TYPE_PARSING,
        )
    except _InvalidValue:
        return _failure(
            source,
            TranslationIssueCode.INVALID_FIELD_VALUE,
            TranslationStage.TYPE_PARSING,
        )
    return TranslatedValue(
        ValueDisposition.VALID,
        source,
        canonical=CanonicalValue(field.logical_type, value),
    )


def _apply_null_policy(
    source: NativeValue,
    _working: NativeValue,
    field: FieldDefinition,
) -> TranslatedValue:
    """Return the configured outcome for a recognised or mapped null value."""
    if not field.null_policy.allowed:
        return _failure(
            source,
            TranslationIssueCode.NULL_POLICY_VIOLATION,
            TranslationStage.NULL_POLICY,
        )
    if field.logical_type is None:
        return TranslatedValue(
            ValueDisposition.VALID,
            source,
            preserved=source,
            is_null=True,
        )
    if isinstance(field.logical_type, CollectionLogicalType):
        canonical = CanonicalValue(
            field.logical_type.collection_type,
            None,
            element_type=field.logical_type.element_type,
        )
    else:
        canonical = CanonicalValue(field.logical_type, None)
    return TranslatedValue(
        ValueDisposition.VALID,
        source,
        canonical=canonical,
        is_null=True,
    )


def _translate_collection(
    source: NativeValue,
    working: NativeValue,
    field: FieldDefinition,
    side: InputSide,
) -> TranslatedValue:
    """Decode and translate every element of one declared collection value."""
    logical_type = field.logical_type
    if not isinstance(logical_type, CollectionLogicalType):
        raise AssertionError("collection translation received a scalar field")
    representations = field.collection_representation
    if representations is None:
        raise AssertionError("resolved collection field has no representations")
    representation = _for_side(representations, side)
    try:
        elements = _decode_collection(working, representation)
    except _TypeMismatch:
        return _failure(
            source,
            TranslationIssueCode.TYPE_MISMATCH,
            TranslationStage.COLLECTION_DECODING,
        )
    except _InvalidValue:
        return _failure(
            source,
            TranslationIssueCode.INVALID_FIELD_VALUE,
            TranslationStage.COLLECTION_DECODING,
        )

    canonical_elements: list[object] = []
    for index, element in enumerate(elements):
        if element.category is NativeCategory.NULL:
            return _failure(
                source,
                TranslationIssueCode.INVALID_FIELD_VALUE,
                TranslationStage.ELEMENT_PARSING,
                element_index=index,
            )
        element = _apply_source_operations(
            element,
            representation.element_normalisation,
        )
        if representation.element_mapping:
            mapped = _mapped_value(
                element,
                representation.element_mapping,
                representation.element_normalisation,
            )
            if mapped is None:
                return _failure(
                    source,
                    TranslationIssueCode.MAPPING_FAILURE,
                    TranslationStage.ELEMENT_MAPPING,
                    element_index=index,
                )
            element = mapped
        try:
            parsed = _parse_scalar(element, logical_type.element_type)
            canonical_elements.append(
                _finalize_scalar(parsed, logical_type.element_type)
            )
        except _TypeMismatch:
            return _failure(
                source,
                TranslationIssueCode.TYPE_MISMATCH,
                TranslationStage.ELEMENT_PARSING,
                element_index=index,
            )
        except _InvalidValue:
            return _failure(
                source,
                TranslationIssueCode.INVALID_FIELD_VALUE,
                TranslationStage.ELEMENT_PARSING,
                element_index=index,
            )

    if logical_type.collection_type == "set":
        if len(set(canonical_elements)) != len(canonical_elements):
            return _failure(
                source,
                TranslationIssueCode.INVALID_FIELD_VALUE,
                TranslationStage.COLLECTION_VALIDATION,
            )
        canonical_elements.sort(
            key=lambda value: render_canonical_scalar(
                value, logical_type.element_type
            )
        )
    elif logical_type.collection_type == "multiset":
        canonical_elements.sort(
            key=lambda value: render_canonical_scalar(
                value, logical_type.element_type
            )
        )

    return TranslatedValue(
        ValueDisposition.VALID,
        source,
        canonical=CanonicalValue(
            logical_type.collection_type,
            tuple(canonical_elements),
            element_type=logical_type.element_type,
        ),
    )


def _decode_collection(
    value: NativeValue,
    representation: CollectionRepresentation,
) -> tuple[NativeValue, ...]:
    """Decode one side's declared source representation into native elements."""
    if representation.format == "delimited_text":
        if value.category is not NativeCategory.STRING:
            raise _TypeMismatch
        if not isinstance(value.value, str):
            raise AssertionError("parser-native string does not contain text")
        if value.value == "":
            return ()
        return tuple(
            NativeValue(NativeCategory.STRING, element)
            for element in value.value.split(representation.delimiter)
        )

    if value.category is NativeCategory.STRING:
        if not isinstance(value.value, str):
            raise AssertionError("parser-native string does not contain text")
        try:
            decoded = decode_json_value(value.value)
        except JsonValueError as error:
            raise _InvalidValue from error
    elif value.category is NativeCategory.ARRAY:
        decoded = value
    else:
        raise _TypeMismatch
    if decoded.category is not NativeCategory.ARRAY:
        raise _InvalidValue
    if not isinstance(decoded.value, tuple):
        raise AssertionError("parser-native array does not contain a tuple")
    return decoded.value


def _apply_source_operations(
    value: NativeValue,
    operations: tuple[Operation, ...],
) -> NativeValue:
    """Apply ordered source-text operations only to parser-native strings."""
    if value.category is not NativeCategory.STRING:
        return value
    text = value.value
    if not isinstance(text, str):
        raise AssertionError("parser-native string does not contain text")
    for operation in operations:
        text = apply_source_text_operation(
            text,
            operation.name,
            operation.parameters,
        )
    return NativeValue(NativeCategory.STRING, text)


def _mapped_value(
    value: NativeValue,
    mappings: tuple[ValueMappingEntry, ...],
    source_operations: tuple[Operation, ...],
) -> NativeValue | None:
    """Return the destination of one closed mapping or signal no match."""
    for mapping in mappings:
        if _matches_descriptor(value, mapping.source, source_operations):
            return _descriptor_value(mapping.destination)
    return None


def _matches_any_descriptor(
    value: NativeValue,
    descriptors: tuple[SourceValueDescriptor, ...],
    source_operations: tuple[Operation, ...],
) -> bool:
    """Return whether a value equals any configured source descriptor."""
    return any(
        _matches_descriptor(value, descriptor, source_operations)
        for descriptor in descriptors
    )


def _matches_descriptor(
    value: NativeValue,
    descriptor: SourceValueDescriptor,
    source_operations: tuple[Operation, ...],
) -> bool:
    """Compare a native value with a typed descriptor by category and content."""
    expected = _apply_source_operations(
        _descriptor_value(descriptor),
        source_operations,
    )
    return value.category is expected.category and value.value == expected.value


def _descriptor_value(descriptor: SourceValueDescriptor) -> NativeValue:
    """Convert a validated descriptor into its parser-native representation."""
    category = NativeCategory(descriptor.category)
    if category is NativeCategory.NULL:
        return NativeValue(category)
    if category is NativeCategory.INTEGER:
        lexical = str(descriptor.value)
        return NativeValue(category, int(lexical), lexical)
    if category is NativeCategory.DECIMAL:
        lexical = str(descriptor.value)
        return NativeValue(category, Decimal(lexical), lexical)
    return NativeValue(category, descriptor.value)


def _parse_scalar(value: NativeValue, logical_type: str) -> object:
    """Parse one non-null native scalar into its declared logical type."""
    if logical_type == "string":
        if value.category is not NativeCategory.STRING:
            raise _TypeMismatch
        return value.value
    if logical_type == "integer":
        if value.category is NativeCategory.INTEGER:
            return value.value
        if value.category is not NativeCategory.STRING:
            raise _TypeMismatch
        if not isinstance(value.value, str) or not _INTEGER_PATTERN.fullmatch(
            value.value
        ):
            raise _InvalidValue
        return int(value.value)
    if logical_type == "decimal":
        if value.category is NativeCategory.INTEGER:
            return Decimal(value.value)
        if value.category is NativeCategory.DECIMAL:
            return value.value
        if value.category is not NativeCategory.STRING:
            raise _TypeMismatch
        if not isinstance(value.value, str) or not _DECIMAL_PATTERN.fullmatch(
            value.value
        ):
            raise _InvalidValue
        parsed = Decimal(value.value)
        if not parsed.is_finite():
            raise _InvalidValue
        return parsed
    if logical_type == "boolean":
        if value.category is NativeCategory.BOOLEAN:
            return value.value
        if value.category is not NativeCategory.STRING:
            raise _TypeMismatch
        if value.value == "true":
            return True
        if value.value == "false":
            return False
        raise _InvalidValue
    if logical_type == "date":
        if value.category is not NativeCategory.STRING:
            raise _TypeMismatch
        if not isinstance(value.value, str) or not _DATE_PATTERN.fullmatch(value.value):
            raise _InvalidValue
        try:
            return date.fromisoformat(value.value).isoformat()
        except ValueError as error:
            raise _InvalidValue from error
    if logical_type == "datetime":
        if value.category is not NativeCategory.STRING:
            raise _TypeMismatch
        if not isinstance(value.value, str):
            raise _InvalidValue
        return _parse_datetime(value.value)
    raise AssertionError(f"validated logical type is not registered: {logical_type}")


def _parse_datetime(value: str) -> _ExactDateTime:
    """Parse one offset-bearing datetime without losing fractional precision."""
    match = _DATETIME_PATTERN.fullmatch(value)
    if match is None:
        raise _InvalidValue
    second = int(match["second"])
    if second > 59:
        raise _InvalidValue
    offset_text = match["offset"]
    if offset_text in {"Z", "z"}:
        offset = timezone.utc
    else:
        if offset_text == "-00:00":
            raise _InvalidValue
        offset_hour = int(offset_text[1:3])
        offset_minute = int(offset_text[4:6])
        if offset_hour > 23 or offset_minute > 59:
            raise _InvalidValue
        delta = timedelta(hours=offset_hour, minutes=offset_minute)
        if offset_text.startswith("-"):
            delta = -delta
        try:
            offset = timezone(delta)
        except ValueError as error:
            raise _InvalidValue from error
    try:
        local = datetime(
            *map(int, match["date"].split("-")),
            int(match["hour"]),
            int(match["minute"]),
            second,
            tzinfo=offset,
        )
    except ValueError as error:
        raise _InvalidValue from error
    fraction_text = match["fraction"]
    fraction = Decimal(f"0.{fraction_text}") if fraction_text else Decimal(0)
    try:
        utc_second = local.astimezone(timezone.utc)
    except (OverflowError, ValueError) as error:
        raise _InvalidValue from error
    return _ExactDateTime(utc_second, fraction)


def _apply_typed_operation(value: object, operation: Operation) -> object:
    """Apply one validated typed-value operation."""
    if operation.name == "decimal_quantise":
        if not isinstance(value, Decimal):
            raise AssertionError("decimal operation received a non-decimal value")
        places = operation.parameters["places"]
        rounding_name = operation.parameters["rounding"]
        if not isinstance(places, int) or not isinstance(rounding_name, str):
            raise AssertionError("validated decimal operation parameters are invalid")
        rounding = {
            "half_even": ROUND_HALF_EVEN,
            "half_up": ROUND_HALF_UP,
            "down": ROUND_DOWN,
        }[rounding_name]
        quantum = Decimal(1).scaleb(-places)
        integer_digits = max(value.adjusted() + 1, 1) if value else 1
        with localcontext() as context:
            context.prec = (
                max(len(value.as_tuple().digits), integer_digits + places) + 2
            )
            return value.quantize(quantum, rounding=rounding)
    if operation.name == "datetime_truncate":
        if not isinstance(value, _ExactDateTime):
            raise AssertionError("datetime operation received a non-datetime value")
        precision = operation.parameters["precision"]
        places = {"second": 0, "millisecond": 3, "microsecond": 6}[precision]
        if places == 0:
            fraction = Decimal(0)
        else:
            fraction = value.fraction.quantize(
                Decimal(1).scaleb(-places),
                rounding=ROUND_DOWN,
            )
        return _ExactDateTime(value.utc_second, fraction)
    raise AssertionError(
        f"validated typed operation is not registered: {operation.name}"
    )


def _finalize_scalar(value: object, logical_type: str) -> object:
    """Convert internal exact temporal state to its unique canonical value."""
    if logical_type == "datetime":
        if not isinstance(value, _ExactDateTime):
            raise AssertionError("parsed datetime has unexpected internal type")
        return _render_datetime(value)
    return value


def _render_datetime(value: _ExactDateTime) -> str:
    """Render an exact UTC datetime using the canonical results representation."""
    instant = value.utc_second
    text = (
        f"{instant.year:04d}-{instant.month:02d}-{instant.day:02d}T"
        f"{instant.hour:02d}:{instant.minute:02d}:{instant.second:02d}"
    )
    if value.fraction:
        fraction = format(value.fraction, "f").partition(".")[2].rstrip("0")
        text += f".{fraction}"
    return f"{text}Z"


def render_canonical_scalar(value: object, logical_type: str) -> str:
    """Render a canonical scalar for deterministic collection ordering."""
    if logical_type == "boolean":
        return "true" if value else "false"
    if logical_type == "decimal":
        if not isinstance(value, Decimal):
            raise AssertionError("canonical decimal has unexpected internal type")
        return _render_decimal(value)
    return str(value)


def _render_decimal(value: Decimal) -> str:
    """Render one finite decimal in the canonical normalized scientific form."""
    if value.is_zero():
        return "0"
    normalized = value.normalize()
    sign = "-" if normalized.is_signed() else ""
    digits = "".join(str(digit) for digit in normalized.as_tuple().digits)
    exponent = normalized.adjusted()
    coefficient = digits[0]
    if len(digits) > 1:
        coefficient += f".{digits[1:]}"
    if exponent:
        coefficient += f"e{exponent}"
    return f"{sign}{coefficient}"


def _failure(
    source: NativeValue | None,
    code: TranslationIssueCode,
    stage: TranslationStage,
    *,
    element_index: int | None = None,
) -> TranslatedValue:
    """Construct one attributable not-assessable translation outcome."""
    return TranslatedValue(
        ValueDisposition.NOT_ASSESSABLE,
        source,
        issue=TranslationIssue(code, stage, element_index),
    )


def _for_side(sides: DatasetSides[T], side: InputSide) -> T:
    """Select one resolved side-specific configuration value."""
    return sides.reference if side is InputSide.REFERENCE else sides.query
