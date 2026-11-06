"""Behavioural tests for deterministic dataset input parsing."""

from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pytest

from adviso_compare.inputs import (
    InputError,
    InputFormat,
    InputSide,
    JsonLocation,
    NativeCategory,
    NativeValue,
    TabularLocation,
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


@pytest.mark.parametrize(
    ("filename", "content", "expected_code"),
    [
        ("records", b"record_id\n", "unsupported_format"),
        ("records.txt", b"record_id\n", "unsupported_format"),
        ("records.csv", b"record_id\n\xff", "invalid_encoding"),
        ("records.json", b"[", "invalid_syntax"),
        ("records.json", b"[NaN]", "invalid_syntax"),
        ("records.json", b"", "invalid_syntax"),
        ("records.csv", b"", "invalid_structure"),
        ("records.tsv", b"", "invalid_structure"),
        ("records.csv", b'a,b\n"unterminated,b\n', "invalid_syntax"),
        ("records.csv", b"a,a\n1,2\n", "invalid_structure"),
        ("records.csv", b"a,\n1,2\n", "invalid_structure"),
        ("records.csv", b"a,b\n1\n", "invalid_structure"),
        ("records.tsv", b"a\tb\n1\t2\t3\n", "invalid_structure"),
        ("records.json", b"{}", "invalid_structure"),
        ("records.json", b"1", "invalid_structure"),
        ("records.json", b"[1]", "invalid_structure"),
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
