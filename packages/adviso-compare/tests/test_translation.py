"""Behavioural tests for source-to-canonical field translation."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Callable

import pytest
import yaml

from adviso_compare.configuration import FieldDefinition, load_comparison_configuration
from adviso_compare.inputs import InputSide, NativeCategory, NativeValue
from adviso_compare.translation import (
    TranslationIssueCode,
    TranslationStage,
    ValueDisposition,
    translate_field_value,
)
from tests.support.documents import JsonObject, minimal_configuration


FieldMutation = Callable[[JsonObject], None]


def _field_definition(
    tmp_path: Path,
    mutation: FieldMutation | None = None,
) -> FieldDefinition:
    """Load a measured-value definition through the configuration boundary."""
    document = minimal_configuration()
    field = document["fields"]["definitions"]["measured_value"]
    if mutation is not None:
        mutation(field)
    path = tmp_path / "configuration.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return load_comparison_configuration(path).field("measured_value")


def _scalar_field(logical_type: str) -> FieldMutation:
    def mutate(field: JsonObject) -> None:
        field["logical_type"] = logical_type
        field["comparator"] = {"name": "typed_exact"}

    return mutate


@pytest.mark.parametrize(
    ("logical_type", "source", "expected"),
    [
        ("string", NativeValue(NativeCategory.STRING, "01"), "01"),
        ("integer", NativeValue(NativeCategory.INTEGER, 7, "7"), 7),
        ("integer", NativeValue(NativeCategory.STRING, "+001"), 1),
        ("decimal", NativeValue(NativeCategory.INTEGER, 2, "2"), Decimal("2")),
        (
            "decimal",
            NativeValue(NativeCategory.DECIMAL, Decimal("1.00"), "1.00"),
            Decimal("1.00"),
        ),
        ("decimal", NativeValue(NativeCategory.STRING, "+1.2"), Decimal("1.2")),
        ("decimal", NativeValue(NativeCategory.STRING, "01.2"), Decimal("1.2")),
        ("decimal", NativeValue(NativeCategory.STRING, "1"), Decimal("1")),
        ("decimal", NativeValue(NativeCategory.STRING, "1E+2"), Decimal("1E+2")),
        ("boolean", NativeValue(NativeCategory.BOOLEAN, True), True),
        ("boolean", NativeValue(NativeCategory.STRING, "false"), False),
        ("date", NativeValue(NativeCategory.STRING, "2024-02-29"), "2024-02-29"),
        (
            "datetime",
            NativeValue(NativeCategory.STRING, "2024-01-02T03:04:05.1200+01:00"),
            "2024-01-02T02:04:05.12Z",
        ),
        (
            "datetime",
            NativeValue(NativeCategory.STRING, "2024-01-02t03:04:05z"),
            "2024-01-02T03:04:05Z",
        ),
        (
            "datetime",
            NativeValue(NativeCategory.STRING, "2024-01-02T03:04:05+23:59"),
            "2024-01-01T03:05:05Z",
        ),
        (
            "datetime",
            NativeValue(NativeCategory.STRING, "2024-01-02T03:04:05-23:59"),
            "2024-01-03T03:03:05Z",
        ),
    ],
)
def test_declared_scalar_types_parse_without_implicit_cross_type_conversion(
    tmp_path: Path,
    logical_type: str,
    source: NativeValue,
    expected: object,
) -> None:
    """Each accepted parser-native representation produces its exact typed value."""
    field = _field_definition(tmp_path, _scalar_field(logical_type))

    result = translate_field_value(source, field, InputSide.REFERENCE)

    assert result.disposition is ValueDisposition.VALID
    assert result.source is source
    assert result.canonical is not None
    assert result.canonical.logical_type == logical_type
    assert result.canonical.value == expected
    assert result.issue is None


@pytest.mark.parametrize(
    ("logical_type", "source", "issue_code"),
    [
        ("string", NativeValue(NativeCategory.INTEGER, 1, "1"), "type_mismatch"),
        (
            "integer",
            NativeValue(NativeCategory.DECIMAL, Decimal("1"), "1.0"),
            "type_mismatch",
        ),
        ("integer", NativeValue(NativeCategory.STRING, "1.0"), "invalid_field_value"),
        ("integer", NativeValue(NativeCategory.STRING, "1e2"), "invalid_field_value"),
        ("integer", NativeValue(NativeCategory.BOOLEAN, True), "type_mismatch"),
        ("decimal", NativeValue(NativeCategory.BOOLEAN, True), "type_mismatch"),
        ("decimal", NativeValue(NativeCategory.STRING, ".5"), "invalid_field_value"),
        ("decimal", NativeValue(NativeCategory.STRING, "1."), "invalid_field_value"),
        ("decimal", NativeValue(NativeCategory.STRING, "NaN"), "invalid_field_value"),
        (
            "decimal",
            NativeValue(NativeCategory.STRING, "Infinity"),
            "invalid_field_value",
        ),
        (
            "decimal",
            NativeValue(NativeCategory.STRING, "-Infinity"),
            "invalid_field_value",
        ),
        ("boolean", NativeValue(NativeCategory.INTEGER, 1, "1"), "type_mismatch"),
        ("boolean", NativeValue(NativeCategory.STRING, "True"), "invalid_field_value"),
        (
            "date",
            NativeValue(NativeCategory.STRING, "2023-02-29"),
            "invalid_field_value",
        ),
        (
            "date",
            NativeValue(NativeCategory.STRING, "2024-1-2"),
            "invalid_field_value",
        ),
        (
            "date",
            NativeValue(NativeCategory.STRING, "2024-01"),
            "invalid_field_value",
        ),
        (
            "datetime",
            NativeValue(NativeCategory.STRING, "2024-01-02T03:04:05"),
            "invalid_field_value",
        ),
        (
            "datetime",
            NativeValue(NativeCategory.STRING, "2024-01-02T03:04:60Z"),
            "invalid_field_value",
        ),
        (
            "datetime",
            NativeValue(NativeCategory.STRING, "2024-01-02 03:04:05Z"),
            "invalid_field_value",
        ),
        (
            "datetime",
            NativeValue(NativeCategory.STRING, "2024-01-02T03:04:05-00:00"),
            "invalid_field_value",
        ),
        (
            "datetime",
            NativeValue(NativeCategory.STRING, "2024-01-02T03:04:05+24:00"),
            "invalid_field_value",
        ),
        (
            "datetime",
            NativeValue(NativeCategory.STRING, "2024-01-02T03:04:05-24:00"),
            "invalid_field_value",
        ),
        ("integer", NativeValue(NativeCategory.OBJECT, ()), "type_mismatch"),
    ],
)
def test_scalar_failures_distinguish_category_mismatch_from_invalid_content(
    tmp_path: Path,
    logical_type: str,
    source: NativeValue,
    issue_code: str,
) -> None:
    """Failed typed values remain attributable without acquiring a canonical value."""
    field = _field_definition(tmp_path, _scalar_field(logical_type))

    result = translate_field_value(source, field, InputSide.QUERY)

    assert result.disposition is ValueDisposition.NOT_ASSESSABLE
    assert result.source is source
    assert result.canonical is None
    assert result.issue is not None
    assert result.issue.code.value == issue_code
    assert result.issue.stage is TranslationStage.TYPE_PARSING


def test_presence_scope_and_null_states_remain_distinct(tmp_path: Path) -> None:
    """Absence, exclusion, valid null, and prohibited null have distinct outcomes."""
    required = _field_definition(tmp_path, _scalar_field("decimal"))
    missing = translate_field_value(None, required, InputSide.REFERENCE)
    excluded = translate_field_value(
        NativeValue(NativeCategory.STRING, "ignored"),
        required,
        InputSide.REFERENCE,
        in_scope=False,
    )

    def optional_nullable(field: JsonObject) -> None:
        _scalar_field("decimal")(field)
        field["required"] = {"reference": False, "query": False}
        field["null_policy"] = {"allowed": True, "nulls_equal": True}

    nullable = _field_definition(tmp_path, optional_nullable)
    absent = translate_field_value(None, nullable, InputSide.REFERENCE)
    null = translate_field_value(
        NativeValue(NativeCategory.NULL), nullable, InputSide.REFERENCE
    )
    prohibited = translate_field_value(
        NativeValue(NativeCategory.NULL), required, InputSide.REFERENCE
    )

    assert missing.disposition is ValueDisposition.NOT_ASSESSABLE
    assert missing.issue.code is TranslationIssueCode.MISSING_REQUIRED_FIELD
    assert excluded.disposition is ValueDisposition.NOT_ASSESSED
    assert absent.disposition is ValueDisposition.ABSENT
    assert null.disposition is ValueDisposition.VALID
    assert null.is_null
    assert null.canonical.value is None
    assert prohibited.disposition is ValueDisposition.NOT_ASSESSABLE
    assert prohibited.issue.code is TranslationIssueCode.NULL_POLICY_VIOLATION


def test_source_processing_missing_tokens_and_closed_mapping_follow_fixed_order(
    tmp_path: Path,
) -> None:
    """Normalisation precedes missing-token recognition and closed value mapping."""

    def mapped(field: JsonObject) -> None:
        field["logical_type"] = "string"
        field["comparator"] = {"name": "typed_exact"}
        field["null_policy"] = {
            "allowed": True,
            "nulls_equal": True,
            "missing_tokens": {
                "reference": [{"category": "string", "value": " NA "}]
            },
        }
        field["source_normalisation"] = {
            "reference": [
                {"operation": "trim", "parameters": {"side": "both"}},
                {"operation": "case_fold"},
            ]
        }
        field["value_mapping"] = {
            "reference": [
                {
                    "from": {"category": "string", "value": " RESISTANT "},
                    "to": {"category": "string", "value": "R"},
                },
                {
                    "from": {"category": "string", "value": " UNKNOWN "},
                    "to": {"category": "null"},
                },
            ]
        }

    field = _field_definition(tmp_path, mapped)

    missing = translate_field_value(
        NativeValue(NativeCategory.STRING, " NA "), field, InputSide.REFERENCE
    )
    mapped_value = translate_field_value(
        NativeValue(NativeCategory.STRING, " RESISTANT "),
        field,
        InputSide.REFERENCE,
    )
    mapped_null = translate_field_value(
        NativeValue(NativeCategory.STRING, " UNKNOWN "), field, InputSide.REFERENCE
    )
    unmapped = translate_field_value(
        NativeValue(NativeCategory.STRING, "susceptible"),
        field,
        InputSide.REFERENCE,
    )

    assert missing.disposition is ValueDisposition.VALID
    assert missing.is_null
    assert mapped_value.canonical.value == "R"
    assert mapped_null.disposition is ValueDisposition.VALID
    assert mapped_null.is_null
    assert unmapped.disposition is ValueDisposition.NOT_ASSESSABLE
    assert unmapped.issue.code is TranslationIssueCode.MAPPING_FAILURE
    assert unmapped.issue.stage is TranslationStage.VALUE_MAPPING


def test_source_text_operations_leave_non_string_native_values_unchanged(
    tmp_path: Path,
) -> None:
    """Configured text operations neither stringify nor reject native numbers."""

    def configured(field: JsonObject) -> None:
        _scalar_field("decimal")(field)
        field["source_normalisation"] = {
            "reference": [
                {"operation": "unicode_normalise", "parameters": {"form": "NFC"}},
                {"operation": "trim", "parameters": {"side": "both"}},
                {"operation": "case_fold"},
            ]
        }

    field = _field_definition(tmp_path, configured)
    source = NativeValue(NativeCategory.INTEGER, 7, "7")

    result = translate_field_value(source, field, InputSide.REFERENCE)

    assert result.disposition is ValueDisposition.VALID
    assert result.canonical.value == Decimal(7)
    assert result.source is source


@pytest.mark.parametrize(
    ("trim_side", "source_text", "expected"),
    [
        ("both", " \u00a0Ｋ\u00a0 ", "k"),
        ("both", "\u001cＫ\u001c", "\u001ck\u001c"),
        ("leading", " Ｋ ", "k "),
        ("trailing", " Ｋ ", " k"),
    ],
)
def test_source_text_operations_apply_to_strings_in_declared_order(
    tmp_path: Path,
    trim_side: str,
    source_text: str,
    expected: str,
) -> None:
    """Unicode normalisation, trimming, and case folding compose predictably."""

    def configured(field: JsonObject) -> None:
        _scalar_field("string")(field)
        field["source_normalisation"] = {
            "query": [
                {"operation": "unicode_normalise", "parameters": {"form": "NFKC"}},
                {"operation": "trim", "parameters": {"side": trim_side}},
                {"operation": "case_fold"},
            ]
        }

    field = _field_definition(tmp_path, configured)

    result = translate_field_value(
        NativeValue(NativeCategory.STRING, source_text),
        field,
        InputSide.QUERY,
    )

    assert result.disposition is ValueDisposition.VALID
    assert result.canonical.value == expected


def test_case_folding_is_full_locale_independent_and_does_not_normalise(
    tmp_path: Path,
) -> None:
    """Case folding expands sharp s while retaining decomposed Unicode form."""

    def configured(field: JsonObject) -> None:
        _scalar_field("string")(field)
        field["source_normalisation"] = {
            "reference": [{"operation": "case_fold"}]
        }

    field = _field_definition(tmp_path, configured)
    result = translate_field_value(
        NativeValue(NativeCategory.STRING, "Straße A\u030A"),
        field,
        InputSide.REFERENCE,
    )

    assert result.disposition is ValueDisposition.VALID
    assert result.canonical.value == "strasse a\u030a"


@pytest.mark.parametrize(
    ("operation", "source", "expected"),
    [
        (
            {
                "operation": "decimal_quantise",
                "parameters": {"places": 2, "rounding": "half_even"},
            },
            NativeValue(NativeCategory.STRING, "1.225"),
            Decimal("1.22"),
        ),
        (
            {
                "operation": "decimal_quantise",
                "parameters": {"places": 2, "rounding": "half_up"},
            },
            NativeValue(NativeCategory.STRING, "1.225"),
            Decimal("1.23"),
        ),
        (
            {
                "operation": "decimal_quantise",
                "parameters": {"places": 2, "rounding": "down"},
            },
            NativeValue(NativeCategory.STRING, "-1.239"),
            Decimal("-1.23"),
        ),
        (
            {"operation": "datetime_truncate", "parameters": {"precision": "second"}},
            NativeValue(
                NativeCategory.STRING,
                "2024-01-02T03:04:05.999999+01:00",
            ),
            "2024-01-02T02:04:05Z",
        ),
        (
            {
                "operation": "datetime_truncate",
                "parameters": {"precision": "millisecond"},
            },
            NativeValue(NativeCategory.STRING, "2024-01-02T03:04:05.123956Z"),
            "2024-01-02T03:04:05.123Z",
        ),
        (
            {
                "operation": "datetime_truncate",
                "parameters": {"precision": "microsecond"},
            },
            NativeValue(NativeCategory.STRING, "2024-01-02T03:04:05.1234569Z"),
            "2024-01-02T03:04:05.123456Z",
        ),
    ],
)
def test_typed_normalisation_operations_are_explicit_and_deterministic(
    tmp_path: Path,
    operation: JsonObject,
    source: NativeValue,
    expected: object,
) -> None:
    """Every registered typed operation transforms an already parsed value."""
    logical_type = "datetime" if "datetime" in operation["operation"] else "decimal"

    def configured(field: JsonObject) -> None:
        _scalar_field(logical_type)(field)
        field["typed_normalisation"] = [operation]

    field = _field_definition(tmp_path, configured)
    result = translate_field_value(source, field, InputSide.QUERY)

    assert result.disposition is ValueDisposition.VALID
    assert result.canonical.value == expected


def _collection_field(
    collection_type: str,
    element_type: str,
    *,
    query_representation: JsonObject | None = None,
) -> FieldMutation:
    def mutate(field: JsonObject) -> None:
        field["logical_type"] = {
            "collection_type": collection_type,
            "element_type": element_type,
            "element_comparator": {"name": "typed_exact"},
        }
        field["comparator"] = {"name": f"{collection_type}_exact"}
        if query_representation is not None:
            field["collection_representation"] = {
                "query": query_representation
            }

    return mutate


@pytest.mark.parametrize(
    ("collection_type", "element_type", "source", "representation", "expected"),
    [
        (
            "list",
            "integer",
            NativeValue(
                NativeCategory.ARRAY,
                (
                    NativeValue(NativeCategory.STRING, "02"),
                    NativeValue(NativeCategory.STRING, "1"),
                    NativeValue(NativeCategory.STRING, "1"),
                ),
            ),
            None,
            (2, 1, 1),
        ),
        (
            "set",
            "integer",
            NativeValue(NativeCategory.STRING, '["10", "2"]'),
            {"format": "json_array"},
            (10, 2),
        ),
        (
            "multiset",
            "string",
            NativeValue(NativeCategory.STRING, "b||a||b"),
            {"format": "delimited_text", "delimiter": "||"},
            ("a", "b", "b"),
        ),
        (
            "list",
            "string",
            NativeValue(NativeCategory.STRING, ""),
            {"format": "delimited_text", "delimiter": ","},
            (),
        ),
        (
            "list",
            "string",
            NativeValue(NativeCategory.STRING, ",a,"),
            {"format": "delimited_text", "delimiter": ","},
            ("", "a", ""),
        ),
    ],
)
def test_collection_representations_preserve_declared_collection_semantics(
    tmp_path: Path,
    collection_type: str,
    element_type: str,
    source: NativeValue,
    representation: JsonObject | None,
    expected: tuple[object, ...],
) -> None:
    """Lists preserve order while sets and multisets use canonical output order."""
    field = _field_definition(
        tmp_path,
        _collection_field(
            collection_type,
            element_type,
            query_representation=representation,
        ),
    )

    result = translate_field_value(source, field, InputSide.QUERY)

    assert result.disposition is ValueDisposition.VALID
    assert result.canonical.logical_type == collection_type
    assert result.canonical.element_type == element_type
    assert result.canonical.value == expected


def test_collection_element_processing_runs_before_element_type_parsing(
    tmp_path: Path,
) -> None:
    """Element normalisation and closed mapping adapt a delimited source dialect."""
    representation = {
        "format": "delimited_text",
        "delimiter": ";",
        "element_normalisation": [
            {"operation": "trim", "parameters": {"side": "both"}},
            {"operation": "case_fold"},
        ],
        "element_mapping": [
            {
                "from": {"category": "string", "value": "r"},
                "to": {"category": "string", "value": "resistant"},
            },
            {
                "from": {"category": "string", "value": "s"},
                "to": {"category": "string", "value": "susceptible"},
            },
        ],
    }
    field = _field_definition(
        tmp_path,
        _collection_field("list", "string", query_representation=representation),
    )

    result = translate_field_value(
        NativeValue(NativeCategory.STRING, " R ; s "), field, InputSide.QUERY
    )

    assert result.disposition is ValueDisposition.VALID
    assert result.canonical.value == ("resistant", "susceptible")


def _collection_with_unmatched_element_mapping(field: JsonObject) -> None:
    """Configure a closed element mapping with no entry for the test value."""
    _collection_field(
        "list",
        "string",
        query_representation={
            "format": "json_array",
            "element_mapping": [
                {
                    "from": {"category": "string", "value": "known"},
                    "to": {"category": "string", "value": "canonical"},
                }
            ],
        },
    )(field)


@pytest.mark.parametrize(
    ("source", "mutation", "issue_code", "stage"),
    [
        (
            NativeValue(NativeCategory.INTEGER, 1, "1"),
            _collection_field("list", "integer"),
            TranslationIssueCode.TYPE_MISMATCH,
            TranslationStage.COLLECTION_DECODING,
        ),
        (
            NativeValue(NativeCategory.STRING, "not-json"),
            _collection_field(
                "list", "integer", query_representation={"format": "json_array"}
            ),
            TranslationIssueCode.INVALID_FIELD_VALUE,
            TranslationStage.COLLECTION_DECODING,
        ),
        (
            NativeValue(
                NativeCategory.ARRAY,
                (NativeValue(NativeCategory.NULL),),
            ),
            _collection_field("list", "integer"),
            TranslationIssueCode.INVALID_FIELD_VALUE,
            TranslationStage.ELEMENT_PARSING,
        ),
        (
            NativeValue(
                NativeCategory.ARRAY,
                (
                    NativeValue(NativeCategory.STRING, "01"),
                    NativeValue(NativeCategory.STRING, "1"),
                ),
            ),
            _collection_field("set", "integer"),
            TranslationIssueCode.INVALID_FIELD_VALUE,
            TranslationStage.COLLECTION_VALIDATION,
        ),
        (
            NativeValue(
                NativeCategory.ARRAY,
                (NativeValue(NativeCategory.STRING, "unknown"),),
            ),
            _collection_with_unmatched_element_mapping,
            TranslationIssueCode.MAPPING_FAILURE,
            TranslationStage.ELEMENT_MAPPING,
        ),
    ],
)
def test_collection_failures_identify_the_failed_processing_stage(
    tmp_path: Path,
    source: NativeValue,
    mutation: FieldMutation,
    issue_code: TranslationIssueCode,
    stage: TranslationStage,
) -> None:
    """A failed collection never exposes a partial canonical collection value."""
    field = _field_definition(tmp_path, mutation)

    result = translate_field_value(source, field, InputSide.QUERY)

    assert result.disposition is ValueDisposition.NOT_ASSESSABLE
    assert result.canonical is None
    assert result.issue.code is issue_code
    assert result.issue.stage is stage


def test_preserved_exact_retains_recursive_parser_native_content(
    tmp_path: Path,
) -> None:
    """An untyped field bypasses transformation and typed canonical construction."""

    def preserved(field: JsonObject) -> None:
        field.pop("logical_type")
        field["comparator"] = {"name": "preserved_exact"}

    field = _field_definition(tmp_path, preserved)
    source = NativeValue(
        NativeCategory.OBJECT,
        (
            (
                "nested",
                NativeValue(
                    NativeCategory.ARRAY,
                    (NativeValue(NativeCategory.INTEGER, 1, "1"),),
                ),
            ),
        ),
    )

    result = translate_field_value(source, field, InputSide.REFERENCE)

    assert result.disposition is ValueDisposition.VALID
    assert result.source is source
    assert result.preserved is source
    assert result.canonical is None
