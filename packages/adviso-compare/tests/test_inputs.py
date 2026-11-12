"""Behavioural tests for deterministic dataset input parsing."""

from __future__ import annotations

import json
from contextlib import contextmanager
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Iterator

import pytest

from adviso_compare.inputs import (
    InputError,
    InputFormat,
    InputSide,
    JsonLocation,
    JsonValueError,
    NativeCategory,
    NativeValue,
    TabularLocation,
    decode_json_value,
    load_dataset,
)


def _write_bytes(path: Path, content: bytes) -> Path:
    """Write one controlled input and return its path."""
    path.write_bytes(content)
    return path


@pytest.mark.parametrize(
    ("filename", "content", "expected_format"),
    [
        ("REFERENCE.CSV", b"record_id,value\nS1,alpha\n", InputFormat.CSV),
        ("reference.TsV", b"record_id\tvalue\nS1\talpha\n", InputFormat.TSV),
        ("reference.JsOn", b'[{"record_id":"S1","value":"alpha"}]', InputFormat.JSON),
    ],
)
def test_format_and_exact_byte_provenance_are_discovered_independently(
    tmp_path: Path,
    filename: str,
    content: bytes,
    expected_format: InputFormat,
) -> None:
    """The final case-insensitive suffix selects format and bytes supply provenance."""
    path = _write_bytes(tmp_path / filename, content)

    dataset = load_dataset(path, InputSide.REFERENCE)

    assert dataset.provenance.basename == filename
    assert dataset.provenance.format is expected_format
    assert dataset.provenance.encoding == "utf-8"
    assert dataset.provenance.size_bytes == len(content)
    assert dataset.provenance.sha256 == sha256(content).hexdigest()
    assert len(dataset.records) == 1


@pytest.mark.parametrize(
    ("suffix", "delimiter"),
    [("csv", ","), ("tsv", "\t")],
)
def test_fixed_tabular_dialects_preserve_strings_and_record_locations(
    tmp_path: Path,
    suffix: str,
    delimiter: str,
) -> None:
    """Quoted syntax, multiline cells, and physical locations follow one dialect."""
    content = (
        f'record_id{delimiter}result{delimiter}note\r\n'
        f'S1{delimiter}"a{delimiter}b"{delimiter}"first\r\nsecond"\r\n'
        f'S2{delimiter}"""quoted"""{delimiter}\r\n'
    ).encode()
    path = _write_bytes(tmp_path / f"records.{suffix}", content)

    dataset = load_dataset(path, InputSide.QUERY)

    assert dataset.field_names == ("record_id", "result", "note")
    assert len(dataset.records) == 2
    first, second = dataset.records
    assert first.value("result").category is NativeCategory.STRING
    assert first.value("result").value == f"a{delimiter}b"
    assert first.value("note").value == "first\r\nsecond"
    assert second.value("result").value == '"quoted"'
    assert second.value("note").value == ""
    assert first.location == TabularLocation(record_number=1, line_number=2)
    assert first.location_for("note") == TabularLocation(
        record_number=1,
        line_number=2,
        field_name="note",
    )
    assert second.location == TabularLocation(record_number=2, line_number=4)


def test_lf_and_crlf_inputs_have_equal_records_but_distinct_byte_provenance(
    tmp_path: Path,
) -> None:
    """Accepted line-ending variants preserve parsed content, not byte evidence."""
    lf_path = _write_bytes(tmp_path / "lf.csv", b"record_id,value\nS1,alpha\n")
    crlf_path = _write_bytes(
        tmp_path / "crlf.csv", b"record_id,value\r\nS1,alpha\r\n"
    )

    lf_dataset = load_dataset(lf_path, InputSide.REFERENCE)
    crlf_dataset = load_dataset(crlf_path, InputSide.REFERENCE)

    assert lf_dataset.records == crlf_dataset.records
    assert lf_dataset.provenance.sha256 != crlf_dataset.provenance.sha256
    assert lf_dataset.provenance.size_bytes != crlf_dataset.provenance.size_bytes


def test_json_preserves_native_categories_lexical_numbers_and_pointers(
    tmp_path: Path,
) -> None:
    """JSON values remain lossless and attributable before configured processing."""
    content = (
        b'[{"text":"01","integer":1,"decimal":1.00,"exponent":1e-1,'
        b'"boolean":true,"nothing":null,"array":[1,"x"],'
        b'"object":{"z":2,"a":1},"quoted_nonfinite":"NaN",'
        b'"a/b~c":"located"}]'
    )
    path = _write_bytes(tmp_path / "records.json", content)

    dataset = load_dataset(path, InputSide.REFERENCE)

    assert dataset.field_names == (
        "a/b~c",
        "array",
        "boolean",
        "decimal",
        "exponent",
        "integer",
        "nothing",
        "object",
        "quoted_nonfinite",
        "text",
    )
    record = dataset.records[0]
    assert record.location == JsonLocation(pointer="/0")
    assert record.location_for("a/b~c") == JsonLocation(pointer="/0/a~1b~0c")
    assert record.value("text").category is NativeCategory.STRING
    assert record.value("text").value == "01"
    assert record.value("integer").category is NativeCategory.INTEGER
    assert record.value("integer").value == 1
    assert record.value("integer").lexical == "1"
    assert record.value("decimal").category is NativeCategory.DECIMAL
    assert record.value("decimal").value == Decimal("1.00")
    assert record.value("decimal").lexical == "1.00"
    assert record.value("exponent").value == Decimal("1e-1")
    assert record.value("exponent").lexical == "1e-1"
    assert record.value("boolean").category is NativeCategory.BOOLEAN
    assert record.value("nothing").category is NativeCategory.NULL
    assert record.has_field("nothing")
    assert not record.has_field("missing")
    assert record.location_for("missing") == record.location
    assert record.value("quoted_nonfinite") == NativeValue(
        NativeCategory.STRING, "NaN"
    )
    assert record.value("array").category is NativeCategory.ARRAY
    assert record.value("array").value[0].category is NativeCategory.INTEGER
    assert record.value("object").category is NativeCategory.OBJECT
    assert tuple(name for name, _ in record.value("object").value) == ("a", "z")


def test_json_record_field_names_are_nonempty_but_nested_empty_names_are_data(
    tmp_path: Path,
) -> None:
    """Only names that participate in dataset-wide field discovery are nonempty."""
    invalid = _write_bytes(
        tmp_path / "invalid.json",
        b'[{"record_id":"S1","":"value"}]',
    )
    nested = _write_bytes(
        tmp_path / "nested.json",
        b'[{"record_id":"S1","value":{"":"retained"}}]',
    )

    with pytest.raises(InputError) as raised:
        load_dataset(invalid, InputSide.REFERENCE)

    assert raised.value.code == "invalid_structure"
    assert "empty field name" in raised.value.message
    dataset = load_dataset(nested, InputSide.QUERY)
    nested_members = dataset.records[0].value("value").value
    assert nested_members == (("", NativeValue(NativeCategory.STRING, "retained")),)


def test_parser_native_equality_is_recursive_and_category_preserving(
    tmp_path: Path,
) -> None:
    """Objects ignore member order while arrays and native categories remain exact."""
    first = load_dataset(
        _write_bytes(
            tmp_path / "first.json",
            b'[{"value":{"b":1.00,"a":[1,2]},"other":1}]',
        ),
        InputSide.REFERENCE,
    ).records[0]
    second = load_dataset(
        _write_bytes(
            tmp_path / "second.json",
            b'[{"other":1.0,"value":{"a":[1,2],"b":1.0}}]',
        ),
        InputSide.QUERY,
    ).records[0]
    reversed_array = load_dataset(
        _write_bytes(
            tmp_path / "third.json",
            b'[{"value":{"a":[2,1],"b":1.0}}]',
        ),
        InputSide.QUERY,
    ).records[0]

    assert first.value("value") == second.value("value")
    assert first.value("other") != second.value("other")
    assert first.value("value") != reversed_array.value("value")


@pytest.mark.parametrize(
    ("filename", "content", "expected_fields"),
    [
        ("empty.json", b"[]", ()),
        ("empty.csv", b"record_id,value\n", ("record_id", "value")),
        ("empty.tsv", b"record_id\tvalue\n", ("record_id", "value")),
    ],
)
def test_structurally_valid_empty_datasets_remain_valid(
    tmp_path: Path,
    filename: str,
    content: bytes,
    expected_fields: tuple[str, ...],
) -> None:
    """An empty record collection is distinct from an empty input file."""
    dataset = load_dataset(
        _write_bytes(tmp_path / filename, content), InputSide.REFERENCE
    )

    assert dataset.records == ()
    assert dataset.field_names == expected_fields


@pytest.mark.parametrize(("suffix", "delimiter"), [("csv", ","), ("tsv", "\t")])
@pytest.mark.parametrize(
    ("body", "line_number"),
    [
        ('"unterminated', 2),
        ('unquoted"quote', 2),
        ('"closed"trailing', 2),
        ('"backslash\\"escape"', 2),
        ("bare\rcarriage-return", 2),
    ],
)
def test_malformed_tabular_quote_and_line_syntax_is_rejected_for_each_dialect(
    tmp_path: Path,
    suffix: str,
    delimiter: str,
    body: str,
    line_number: int,
) -> None:
    """Both fixed dialects reject non-standard quoting and record endings."""
    content = f"record_id{delimiter}value\nS1{delimiter}{body}\n".encode()
    path = _write_bytes(tmp_path / f"records.{suffix}", content)

    with pytest.raises(InputError) as raised:
        load_dataset(path, InputSide.QUERY)

    assert raised.value.code == "invalid_syntax"
    assert f"physical line {line_number}" in raised.value.message


@pytest.mark.parametrize(("suffix", "delimiter"), [("csv", ","), ("tsv", "\t")])
@pytest.mark.parametrize(
    ("document_template", "message_fragment"),
    [
        ("field{d}field\n", "duplicate column names"),
        ("field{d}\n", "empty column name"),
        ("field{d}other\none\n", "has 1 fields; expected 2"),
        ("field{d}other\none{d}two{d}three\n", "has 3 fields; expected 2"),
        ("field{d}other\n\n", "has 0 fields; expected 2"),
    ],
)
def test_invalid_tabular_structure_is_rejected_for_each_dialect(
    tmp_path: Path,
    suffix: str,
    delimiter: str,
    document_template: str,
    message_fragment: str,
) -> None:
    """Headers, row widths, and blank physical records are checked symmetrically."""
    content = document_template.format(d=delimiter)
    path = _write_bytes(tmp_path / f"records.{suffix}", content.encode())

    with pytest.raises(InputError) as raised:
        load_dataset(path, InputSide.REFERENCE)

    assert raised.value.code == "invalid_structure"
    assert message_fragment in raised.value.message


@pytest.mark.parametrize("suffix", ["csv", "tsv", "json"])
def test_invalid_utf8_is_rejected_before_format_parsing(
    tmp_path: Path,
    suffix: str,
) -> None:
    """The UTF-8 requirement is identical for every supported format."""
    path = _write_bytes(tmp_path / f"records.{suffix}", b"\xff")

    with pytest.raises(InputError) as raised:
        load_dataset(path, InputSide.REFERENCE)

    assert raised.value.code == "invalid_encoding"


@pytest.mark.parametrize(
    "document",
    [
        b"NaN",
        b'[{"value":Infinity}]',
        b'[{"value":{"nested":-Infinity}}]',
        b'[{"value":[NaN]}]',
    ],
    ids=["root", "field", "nested-object", "nested-array"],
)
def test_non_finite_json_tokens_are_rejected_in_every_structural_context(
    tmp_path: Path,
    document: bytes,
) -> None:
    """No parser location enables non-standard JSON numerical constants."""
    path = _write_bytes(tmp_path / "records.json", document)

    with pytest.raises(InputError) as raised:
        load_dataset(path, InputSide.QUERY)

    assert raised.value.code == "invalid_syntax"
    assert raised.value.message == "query JSON input contains a non-finite number"


@pytest.mark.parametrize(
    ("content", "message_fragment"),
    [
        (b"{}", "JSON root is object"),
        (b"1", "JSON root is integer"),
        (b'"record"', "JSON root is string"),
        (b"[1]", "array item 0 is integer"),
        (b'[{"record_id":"S1"},[]]', "array item 1 is array"),
    ],
)
def test_invalid_json_roots_identify_the_value_and_required_structure(
    tmp_path: Path,
    content: bytes,
    message_fragment: str,
) -> None:
    """Root errors identify the safe structural category and offending index."""
    path = _write_bytes(tmp_path / "records.json", content)

    with pytest.raises(InputError) as raised:
        load_dataset(path, InputSide.REFERENCE)

    assert raised.value.code == "invalid_structure"
    assert message_fragment in raised.value.message
    assert "record object" in raised.value.message


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b'[\n {"a": 1},\n]', id="array-trailing-comma"),
        pytest.param(b'[\n {"a": 1,}\n]', id="object-trailing-comma"),
        pytest.param(b'[\n {"a": }\n]', id="missing-value"),
    ],
)
def test_malformed_json_reports_its_parser_location(
    tmp_path: Path, content: bytes
) -> None:
    """Syntax diagnostics preserve the running JSON parser's location."""
    # Python versions can attribute trailing commas to different positions.
    with pytest.raises(json.JSONDecodeError) as parser_error:
        json.loads(content)
    location = parser_error.value
    path = _write_bytes(tmp_path / "records.json", content)

    with pytest.raises(InputError) as raised:
        load_dataset(path, InputSide.QUERY)

    assert raised.value.code == "invalid_syntax"
    assert raised.value.message == (
        f"query JSON input has invalid syntax at line {location.lineno}, "
        f"column {location.colno}"
    )


@pytest.mark.parametrize(
    ("text", "kind"),
    [("[\n", "invalid_syntax"), ('{"x":1,"x":2}', "duplicate_member"),
     ("NaN", "non_finite")],
)
def test_json_errors_survive_cleanup_with_their_original_context(
    text: str, kind: str
) -> None:
    """Cleanup preserves the parser error, its cause, and location metadata."""
    originals: list[JsonValueError] = []
    causes: list[BaseException | None] = []
    cleanup_finished = False

    @contextmanager
    def cleanup() -> Iterator[None]:
        nonlocal cleanup_finished
        try:
            yield
        finally:
            cleanup_finished = True

    with pytest.raises(JsonValueError) as raised:
        with cleanup():
            try:
                decode_json_value(text)
            except JsonValueError as error:
                originals.append(error)
                causes.append(error.__cause__)
                raise

    assert cleanup_finished
    assert raised.value is originals[0]
    assert raised.value.__cause__ is causes[0]
    assert raised.value.kind == kind
    if kind == "invalid_syntax":
        assert (raised.value.line, raised.value.column) == (2, 1)
    else:
        assert (raised.value.line, raised.value.column) == (None, None)


@pytest.mark.parametrize(
    ("filename", "content", "expected_code"),
    [
        ("records", b"record_id\n", "unsupported_format"),
        ("records.txt", b"record_id\n", "unsupported_format"),
        ("records.json", b"[", "invalid_syntax"),
        ("records.json", b"", "invalid_syntax"),
        ("records.csv", b"", "invalid_structure"),
        ("records.tsv", b"", "invalid_structure"),
        ("records.json", b'[{"a":1,"a":2}]', "invalid_structure"),
        ("records.json", b'[{"a":{"b":1,"b":2}}]', "invalid_structure"),
    ],
)
def test_invalid_inputs_are_rejected_with_the_specific_input_error(
    tmp_path: Path,
    filename: str,
    content: bytes,
    expected_code: str,
) -> None:
    """Malformed bytes, syntax, and structures are not repaired or inferred."""
    path = _write_bytes(tmp_path / filename, content)

    with pytest.raises(InputError) as raised:
        load_dataset(path, InputSide.QUERY)

    assert raised.value.category == "input"
    assert raised.value.code == expected_code
    assert raised.value.side is InputSide.QUERY
    assert raised.value.diagnostic.startswith(f"ERROR [input.{expected_code}]: ")
    assert str(tmp_path) not in raised.value.diagnostic
    assert "\n" not in raised.value.diagnostic


def test_unreadable_input_is_classified_without_exposing_its_path(
    tmp_path: Path,
) -> None:
    """Filesystem failures use a stable error without leaking an absolute path."""
    path = tmp_path / "missing.json"

    with pytest.raises(InputError) as raised:
        load_dataset(path, InputSide.REFERENCE)

    assert raised.value.code == "unreadable"
    assert raised.value.diagnostic == (
        "ERROR [input.unreadable]: reference input could not be read"
    )
    assert str(path) not in raised.value.diagnostic
