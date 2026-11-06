"""Deterministic, lossless parsing of supported comparison inputs."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import TypeAlias


class InputFormat(str, Enum):
    """A supported dataset serialization format."""

    CSV = "csv"
    TSV = "tsv"
    JSON = "json"


class InputSide(str, Enum):
    """The role an input dataset has in a comparison."""

    REFERENCE = "reference"
    QUERY = "query"


class NativeCategory(str, Enum):
    """A value category assigned by the source-format parser."""

    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    NULL = "null"
    ARRAY = "array"
    OBJECT = "object"


@dataclass(frozen=True, slots=True)
class NativeValue:
    """A parser-native value with optional numerical lexical evidence.

    Lexical evidence is deliberately excluded from equality: numerical values
    in the same category compare by their exact numerical content.
    """

    category: NativeCategory
    value: object = None
    lexical: str | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class TabularLocation:
    """A one-based tabular record and starting physical-line location."""

    record_number: int
    line_number: int
    field_name: str | None = None


@dataclass(frozen=True, slots=True)
class JsonLocation:
    """An RFC 6901 JSON Pointer location."""

    pointer: str


SourceLocation: TypeAlias = TabularLocation | JsonLocation


@dataclass(frozen=True, slots=True)
class ParsedRecord:
    """One immutable source record and its attributable location."""

    members: tuple[tuple[str, NativeValue], ...]
    location: SourceLocation

    @property
    def field_names(self) -> tuple[str, ...]:
        """Return source field names in deterministic parser order."""
        return tuple(name for name, _ in self.members)

    def value(self, field_name: str) -> NativeValue:
        """Return the present source value for ``field_name``."""
        for name, value in self.members:
            if name == field_name:
                return value
        raise KeyError(field_name)

    def has_field(self, field_name: str) -> bool:
        """Return whether the source record contains ``field_name``."""
        return any(name == field_name for name, _ in self.members)

    def location_for(self, field_name: str) -> SourceLocation:
        """Return a present field's location, or the record location if absent."""
        if not self.has_field(field_name):
            return self.location
        if isinstance(self.location, TabularLocation):
            return TabularLocation(
                record_number=self.location.record_number,
                line_number=self.location.line_number,
                field_name=field_name,
            )
        return JsonLocation(
            pointer=f"{self.location.pointer}/{_escape_json_pointer(field_name)}"
        )


@dataclass(frozen=True, slots=True)
class InputProvenance:
    """Automatically captured evidence about exact input bytes."""

    basename: str
    format: InputFormat
    encoding: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ParsedDataset:
    """A losslessly parsed dataset before configured interpretation."""

    provenance: InputProvenance
    field_names: tuple[str, ...]
    records: tuple[ParsedRecord, ...]


@dataclass(frozen=True, slots=True)
class InputError(Exception):
    """A classified expected failure while discovering or parsing an input."""

    code: str
    side: InputSide
    message: str

    @property
    def category(self) -> str:
        """Return the stable execution-error category."""
        return "input"

    @property
    def diagnostic(self) -> str:
        """Render the stable, single-line non-sensitive diagnostic."""
        return f"ERROR [input.{self.code}]: {self.message}"

    def __str__(self) -> str:
        """Return the actionable message without exposing input content."""
        return self.message


class _DuplicateMember(ValueError):
    """Signal a duplicate JSON object member before mapping construction."""


class _NonFiniteNumber(ValueError):
    """Signal a non-standard non-finite JSON numerical token."""


def load_dataset(path: Path, side: InputSide) -> ParsedDataset:
    """Discover and parse one supported dataset from its exact bytes."""
    input_format = _discover_format(path, side)
    try:
        content = path.read_bytes()
    except OSError as error:
        raise InputError(
            code="unreadable",
            side=side,
            message=f"{side.value} input could not be read",
        ) from error

    provenance = InputProvenance(
        basename=path.name,
        format=input_format,
        encoding="utf-8",
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
    )
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise InputError(
            code="invalid_encoding",
            side=side,
            message=f"{side.value} input is not valid UTF-8",
        ) from error

    if input_format is InputFormat.JSON:
        field_names, records = _parse_json(text, side)
    else:
        delimiter = "," if input_format is InputFormat.CSV else "\t"
        field_names, records = _parse_table(text, delimiter, side)
    return ParsedDataset(
        provenance=provenance,
        field_names=field_names,
        records=records,
    )


def _discover_format(path: Path, side: InputSide) -> InputFormat:
    """Select a format solely from the final case-insensitive suffix."""
    suffix = path.suffix.casefold()
    formats = {
        ".csv": InputFormat.CSV,
        ".tsv": InputFormat.TSV,
        ".json": InputFormat.JSON,
    }
    try:
        return formats[suffix]
    except KeyError as error:
        raise InputError(
            code="unsupported_format",
            side=side,
            message=(
                f"{side.value} input must have a .csv, .tsv, or .json "
                "filename extension"
            ),
        ) from error


def _parse_table(
    text: str,
    delimiter: str,
    side: InputSide,
) -> tuple[tuple[str, ...], tuple[ParsedRecord, ...]]:
    """Parse one CSV or TSV document using the fixed version 1 dialect."""
    _validate_tabular_lexical_syntax(text, delimiter, side)
    reader = csv.reader(
        io.StringIO(text, newline=""),
        delimiter=delimiter,
        quotechar='"',
        doublequote=True,
        escapechar=None,
        strict=True,
    )
    try:
        header = next(reader)
    except StopIteration as error:
        raise InputError(
            code="invalid_structure",
            side=side,
            message=f"{side.value} tabular input must contain a header row",
        ) from error
    except csv.Error as error:
        raise _tabular_syntax_error(side, reader.line_num) from error

    if not header or any(name == "" for name in header):
        raise InputError(
            code="invalid_structure",
            side=side,
            message=f"{side.value} tabular header contains an empty column name",
        )
    if len(set(header)) != len(header):
        raise InputError(
            code="invalid_structure",
            side=side,
            message=f"{side.value} tabular header contains duplicate column names",
        )

    records: list[ParsedRecord] = []
    previous_ending_line = reader.line_num
    while True:
        starting_line = previous_ending_line + 1
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error as error:
            raise _tabular_syntax_error(side, reader.line_num) from error
        ending_line = reader.line_num
        record_number = len(records) + 1
        if len(row) != len(header):
            raise InputError(
                code="invalid_structure",
                side=side,
                message=(
                    f"{side.value} tabular data record {record_number} starting "
                    f"on physical line {starting_line} has {len(row)} fields; "
                    f"expected {len(header)}"
                ),
            )
        members = tuple(
            (name, NativeValue(NativeCategory.STRING, value))
            for name, value in zip(header, row)
        )
        records.append(
            ParsedRecord(
                members=members,
                location=TabularLocation(
                    record_number=record_number,
                    line_number=starting_line,
                ),
            )
        )
        previous_ending_line = ending_line
    return tuple(header), tuple(records)


def _validate_tabular_lexical_syntax(
    text: str,
    delimiter: str,
    side: InputSide,
) -> None:
    """Reject quote and line-ending forms accepted by permissive CSV readers."""
    start_field = "start_field"
    unquoted = "unquoted"
    quoted = "quoted"
    after_quote = "after_quote"
    state = start_field
    line_number = 1
    quoted_start_line: int | None = None
    index = 0

    while index < len(text):
        character = text[index]
        if character == "\r":
            if index + 1 >= len(text) or text[index + 1] != "\n":
                raise _tabular_syntax_error(side, line_number)
            if state != quoted:
                state = start_field
            line_number += 1
            index += 2
            continue
        if character == "\n":
            if state != quoted:
                state = start_field
            line_number += 1
            index += 1
            continue
        if character == delimiter:
            if state != quoted:
                state = start_field
            index += 1
            continue
        if character == '"':
            if state == start_field:
                state = quoted
                quoted_start_line = line_number
            elif state == unquoted:
                raise _tabular_syntax_error(side, line_number)
            elif state == quoted:
                state = after_quote
            else:
                state = quoted
            index += 1
            continue
        if state == start_field:
            state = unquoted
        elif state == after_quote:
            raise _tabular_syntax_error(side, line_number)
        index += 1

    if state == quoted:
        raise _tabular_syntax_error(side, quoted_start_line or line_number)


def _tabular_syntax_error(side: InputSide, line_number: int) -> InputError:
    """Construct a stable syntax error without reproducing parser input."""
    line_context = f" near physical line {line_number}" if line_number else ""
    return InputError(
        code="invalid_syntax",
        side=side,
        message=f"{side.value} tabular input has invalid quoted syntax{line_context}",
    )


def _parse_json(
    text: str,
    side: InputSide,
) -> tuple[tuple[str, ...], tuple[ParsedRecord, ...]]:
    """Parse a record-oriented JSON array without lossy numerical conversion."""

    def parse_integer(lexical: str) -> NativeValue:
        return NativeValue(NativeCategory.INTEGER, int(lexical), lexical)

    def parse_decimal(lexical: str) -> NativeValue:
        return NativeValue(NativeCategory.DECIMAL, Decimal(lexical), lexical)

    def reject_constant(_lexical: str) -> object:
        raise _NonFiniteNumber

    def parse_object(pairs: list[tuple[str, object]]) -> NativeValue:
        names = [name for name, _ in pairs]
        if len(set(names)) != len(names):
            raise _DuplicateMember
        members = tuple(
            sorted(
                ((name, _to_native(value)) for name, value in pairs),
                key=lambda item: item[0],
            )
        )
        return NativeValue(NativeCategory.OBJECT, members)

    try:
        root = json.loads(
            text,
            parse_int=parse_integer,
            parse_float=parse_decimal,
            parse_constant=reject_constant,
            object_pairs_hook=parse_object,
        )
    except _NonFiniteNumber as error:
        raise InputError(
            code="invalid_syntax",
            side=side,
            message=f"{side.value} JSON input contains a non-finite number",
        ) from error
    except json.JSONDecodeError as error:
        raise InputError(
            code="invalid_syntax",
            side=side,
            message=(
                f"{side.value} JSON input has invalid syntax at line "
                f"{error.lineno}, column {error.colno}"
            ),
        ) from error
    except _DuplicateMember as error:
        raise InputError(
            code="invalid_structure",
            side=side,
            message=f"{side.value} JSON input contains a duplicate object member",
        ) from error

    if not isinstance(root, list):
        raise InputError(
            code="invalid_structure",
            side=side,
            message=(
                f"{side.value} JSON root is {_json_category(root)}; it must be "
                "one array of record objects"
            ),
        )

    records: list[ParsedRecord] = []
    all_field_names: set[str] = set()
    for index, item in enumerate(root):
        if (
            not isinstance(item, NativeValue)
            or item.category is not NativeCategory.OBJECT
        ):
            raise InputError(
                code="invalid_structure",
                side=side,
                message=(
                    f"{side.value} JSON array item {index} is "
                    f"{_json_category(item)}; every item must be a record object"
                ),
            )
        members = item.value
        if not isinstance(members, tuple):
            raise AssertionError("JSON object members were not normalized")
        all_field_names.update(name for name, _ in members)
        records.append(
            ParsedRecord(
                members=members,
                location=JsonLocation(pointer=f"/{index}"),
            )
        )
    return tuple(sorted(all_field_names)), tuple(records)


def _to_native(value: object) -> NativeValue:
    """Recursively assign parser-native categories to JSON library values."""
    if isinstance(value, NativeValue):
        return value
    if value is None:
        return NativeValue(NativeCategory.NULL)
    if isinstance(value, bool):
        return NativeValue(NativeCategory.BOOLEAN, value)
    if isinstance(value, str):
        return NativeValue(NativeCategory.STRING, value)
    if isinstance(value, list):
        return NativeValue(
            NativeCategory.ARRAY,
            tuple(_to_native(element) for element in value),
        )
    raise TypeError(f"unsupported JSON parser value: {type(value).__name__}")


def _escape_json_pointer(member_name: str) -> str:
    """Escape one JSON object member for use in an RFC 6901 pointer."""
    return member_name.replace("~", "~0").replace("/", "~1")


def _json_category(value: object) -> str:
    """Describe a parsed JSON value without reproducing its content."""
    if isinstance(value, NativeValue):
        return value.category.value
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    return type(value).__name__
