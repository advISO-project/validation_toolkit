"""Shared runtime semantics for configured value processing."""

from __future__ import annotations

import unicodedata
from types import MappingProxyType
from typing import Mapping


_UNICODE_WHITE_SPACE_CHARACTERS = "".join(
    chr(code_point)
    for code_point in (
        *range(0x0009, 0x000E),
        0x0020,
        0x0085,
        0x00A0,
        0x1680,
        *range(0x2000, 0x200B),
        0x2028,
        0x2029,
        0x202F,
        0x205F,
        0x3000,
    )
)


_SCALAR_COMPARATORS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "string": frozenset({"typed_exact", "normalised_string"}),
        "integer": frozenset(
            {"typed_exact", "numeric_exact", "numeric_tolerance"}
        ),
        "decimal": frozenset(
            {"typed_exact", "numeric_exact", "numeric_tolerance"}
        ),
        "boolean": frozenset({"typed_exact"}),
        "date": frozenset({"typed_exact", "date_exact"}),
        "datetime": frozenset({"typed_exact", "datetime_exact"}),
    }
)

_TYPED_NORMALISATION_TYPES: Mapping[str, str] = MappingProxyType(
    {
        "decimal_quantise": "decimal",
        "datetime_truncate": "datetime",
    }
)


def field_comparator_is_compatible(
    comparator: str,
    *,
    scalar_type: str | None = None,
    collection_type: str | None = None,
) -> bool:
    """Return whether a comparator can assess the identified field type."""
    if collection_type is not None:
        return comparator == f"{collection_type}_exact"
    if scalar_type is None:
        return comparator == "preserved_exact"
    return comparator in _SCALAR_COMPARATORS[scalar_type]


def typed_normalisation_is_compatible(
    operation: str,
    logical_type: str | None,
) -> bool:
    """Return whether a typed operation accepts the identified scalar type."""
    return _TYPED_NORMALISATION_TYPES[operation] == logical_type


def apply_source_text_operation(
    value: str,
    operation: str,
    parameters: Mapping[str, object],
) -> str:
    """Apply one registered source-text operation to a string value."""
    if operation == "unicode_normalise":
        form = parameters["form"]
        if not isinstance(form, str):
            raise AssertionError("validated Unicode form is not a string")
        return unicodedata.normalize(form, value)
    if operation == "trim":
        side = parameters["side"]
        if side == "leading":
            return value.lstrip(_UNICODE_WHITE_SPACE_CHARACTERS)
        if side == "trailing":
            return value.rstrip(_UNICODE_WHITE_SPACE_CHARACTERS)
        if side == "both":
            return value.strip(_UNICODE_WHITE_SPACE_CHARACTERS)
        raise AssertionError("validated trim side is not registered")
    if operation == "case_fold":
        return value.casefold()
    raise AssertionError(f"validated source operation is not registered: {operation}")
