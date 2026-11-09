"""Deterministic comparison of successfully translated field values."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from types import MappingProxyType
from typing import Callable, Mapping

from adviso_compare.configuration import (
    CollectionLogicalType,
    Comparator,
    FieldDefinition,
)
from adviso_compare.inputs import NativeCategory, NativeValue
from adviso_compare.translation import (
    CanonicalValue,
    TranslatedValue,
    ValueDisposition,
)


ComparatorFunction = Callable[
    [FieldDefinition, TranslatedValue, TranslatedValue], bool
]


def compare_translated_values(
    field: FieldDefinition,
    reference: TranslatedValue,
    query: TranslatedValue,
) -> bool:
    """Apply one field's registered comparator to two valid translations."""
    if (
        reference.disposition is not ValueDisposition.VALID
        or query.disposition is not ValueDisposition.VALID
    ):
        raise ValueError("comparators require two valid translated values")
    if reference.is_null or query.is_null:
        return (
            reference.is_null
            and query.is_null
            and field.null_policy.nulls_equal
        )
    try:
        comparator = _COMPARATORS[field.comparator.name]
    except KeyError as error:
        raise AssertionError("validated comparator is not registered") from error
    return comparator(field, reference, query)


def _preserved_exact(
    _field: FieldDefinition,
    reference: TranslatedValue,
    query: TranslatedValue,
) -> bool:
    """Compare parser-native values recursively without lexical coercion."""
    if reference.preserved is None or query.preserved is None:
        raise AssertionError("preserved comparator received no preserved value")
    return _native_equal(reference.preserved, query.preserved)


def _native_equal(reference: NativeValue, query: NativeValue) -> bool:
    """Apply parser-native category and recursive content equality."""
    if reference.category is not query.category:
        return False
    if reference.category is NativeCategory.ARRAY:
        reference_values = _native_array(reference)
        query_values = _native_array(query)
        return len(reference_values) == len(query_values) and all(
            _native_equal(reference_item, query_item)
            for reference_item, query_item in zip(reference_values, query_values)
        )
    if reference.category is NativeCategory.OBJECT:
        reference_members = _native_object(reference)
        query_members = _native_object(query)
        if set(reference_members) != set(query_members):
            return False
        return all(
            _native_equal(reference_members[name], query_members[name])
            for name in reference_members
        )
    return reference.value == query.value


def _native_array(value: NativeValue) -> tuple[NativeValue, ...]:
    """Return a validated parser-native array's elements."""
    if not isinstance(value.value, tuple) or not all(
        isinstance(item, NativeValue) for item in value.value
    ):
        raise AssertionError("parser-native array has unexpected content")
    return value.value


def _native_object(value: NativeValue) -> dict[str, NativeValue]:
    """Return a validated parser-native object's members by name."""
    if not isinstance(value.value, tuple):
        raise AssertionError("parser-native object has unexpected content")
    members: dict[str, NativeValue] = {}
    for member in value.value:
        if (
            not isinstance(member, tuple)
            or len(member) != 2
            or not isinstance(member[0], str)
            or not isinstance(member[1], NativeValue)
        ):
            raise AssertionError("parser-native object has unexpected member")
        if member[0] in members:
            raise AssertionError("parser-native object has a duplicate member")
        members[member[0]] = member[1]
    return members


def _canonical_exact(
    _field: FieldDefinition,
    reference: TranslatedValue,
    query: TranslatedValue,
) -> bool:
    """Compare two canonical scalar values exactly."""
    return _canonical(reference) == _canonical(query)


def _numeric_tolerance(
    field: FieldDefinition,
    reference: TranslatedValue,
    query: TranslatedValue,
) -> bool:
    """Compare two canonical numbers with exact configured tolerance arithmetic."""
    reference_value = _canonical(reference).value
    query_value = _canonical(query).value
    return _numbers_within_tolerance(
        reference_value,
        query_value,
        field.comparator,
    )


def _collection_exact(
    field: FieldDefinition,
    reference: TranslatedValue,
    query: TranslatedValue,
) -> bool:
    """Apply the declared ordered or unordered collection equality."""
    logical_type = field.logical_type
    if not isinstance(logical_type, CollectionLogicalType):
        raise AssertionError("collection comparator received a scalar field")
    reference_value = _canonical(reference)
    query_value = _canonical(query)
    if reference_value.logical_type != logical_type.collection_type:
        raise AssertionError("reference collection has unexpected logical type")
    if query_value.logical_type != logical_type.collection_type:
        raise AssertionError("query collection has unexpected logical type")
    if not isinstance(reference_value.value, tuple) or not isinstance(
        query_value.value, tuple
    ):
        raise AssertionError("non-null collection has unexpected canonical value")

    if logical_type.collection_type in {"set", "multiset"}:
        return reference_value.value == query_value.value
    if len(reference_value.value) != len(query_value.value):
        return False
    return all(
        _compare_collection_element(
            reference_element,
            query_element,
            logical_type.element_comparator,
        )
        for reference_element, query_element in zip(
            reference_value.value,
            query_value.value,
        )
    )


def _compare_collection_element(
    reference: object,
    query: object,
    comparator: Comparator,
) -> bool:
    """Compare one positional list element under its declared comparator."""
    if comparator.name == "typed_exact":
        return reference == query
    if comparator.name == "numeric_tolerance":
        return _numbers_within_tolerance(reference, query, comparator)
    raise AssertionError("validated collection element comparator is not registered")


def _numbers_within_tolerance(
    reference: object,
    query: object,
    comparator: Comparator,
) -> bool:
    """Evaluate absolute or reference-directed relative tolerance exactly."""
    reference_fraction = _number_fraction(reference)
    query_fraction = _number_fraction(query)
    difference = abs(reference_fraction - query_fraction)
    if "absolute_tolerance" in comparator.parameters:
        allowed = _tolerance_fraction(
            comparator.parameters["absolute_tolerance"]
        )
    elif "relative_tolerance" in comparator.parameters:
        allowed = _tolerance_fraction(
            comparator.parameters["relative_tolerance"]
        ) * abs(reference_fraction)
    else:
        raise AssertionError("numeric tolerance has no validated parameter")
    return difference <= allowed


def _number_fraction(value: object) -> Fraction:
    """Convert a canonical integer or decimal to an exact rational value."""
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise AssertionError("numeric comparator received a non-numeric value")
    return Fraction(value)


def _tolerance_fraction(value: object) -> Fraction:
    """Convert a validated decimal-string tolerance without binary floating point."""
    if not isinstance(value, str):
        raise AssertionError("numeric tolerance parameter is not a string")
    return Fraction(Decimal(value))


def _canonical(value: TranslatedValue) -> CanonicalValue:
    """Return a successfully translated canonical value."""
    if value.canonical is None:
        raise AssertionError("typed comparator received no canonical value")
    return value.canonical


_COMPARATORS: Mapping[str, ComparatorFunction] = MappingProxyType(
    {
        "preserved_exact": _preserved_exact,
        "typed_exact": _canonical_exact,
        "normalised_string": _canonical_exact,
        "numeric_exact": _canonical_exact,
        "numeric_tolerance": _numeric_tolerance,
        "date_exact": _canonical_exact,
        "datetime_exact": _canonical_exact,
        "list_exact": _collection_exact,
        "set_exact": _collection_exact,
        "multiset_exact": _collection_exact,
    }
)
