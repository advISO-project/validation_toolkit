"""Safe loading and validation of custom comparison configurations."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field as dataclass_field
from decimal import Decimal
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import Any, Generic, Mapping, TypeVar

import yaml
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, ScalarNode
from yaml.tokens import AliasToken, AnchorToken, TagToken

from adviso_compare.processing import (
    apply_source_text_operation,
    field_comparator_is_compatible,
    typed_normalisation_is_compatible,
)


CONFIGURATION_SCHEMA_FILE = "comparison-configuration-v1.0.schema.json"
CONFIGURATION_SCHEMA_PACKAGE = "adviso_compare.schemas"
SUPPORTED_SCHEMA_VERSION = "1.0"
AUTOMATIC_CONFIGURATION_ID = "org.adviso.automatic-strict-exact"

JsonObject = dict[str, Any]
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class DatasetSides(Generic[T]):
    """Resolved reference-side and query-side values of one declaration."""

    reference: T
    query: T


@dataclass(frozen=True, slots=True)
class Operation:
    """One registered processing operation and its immutable parameters."""

    name: str
    parameters: Mapping[str, object] = dataclass_field(
        default_factory=lambda: MappingProxyType({})
    )


@dataclass(frozen=True, slots=True)
class SourceValueDescriptor:
    """One explicitly typed value used by null or mapping rules."""

    category: str
    value: object = None


@dataclass(frozen=True, slots=True)
class ValueMappingEntry:
    """One closed source-to-destination value mapping."""

    source: SourceValueDescriptor
    destination: SourceValueDescriptor


@dataclass(frozen=True, slots=True)
class Comparator:
    """A comparator declaration and its immutable parameters."""

    name: str
    parameters: Mapping[str, object] = dataclass_field(
        default_factory=lambda: MappingProxyType({})
    )


@dataclass(frozen=True, slots=True)
class CollectionLogicalType:
    """The resolved logical type of a collection-valued field."""

    collection_type: str
    element_type: str
    element_comparator: Comparator


@dataclass(frozen=True, slots=True)
class NullPolicy:
    """Resolved null acceptance and side-specific missing tokens."""

    allowed: bool
    nulls_equal: bool
    missing_tokens: DatasetSides[tuple[SourceValueDescriptor, ...]]


@dataclass(frozen=True, slots=True)
class CollectionRepresentation:
    """Resolved representation and element processing for one dataset side."""

    format: str
    delimiter: str | None
    element_normalisation: tuple[Operation, ...]
    element_mapping: tuple[ValueMappingEntry, ...]


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    """An immutable effective declaration for one canonical field."""

    name: str
    source_fields: DatasetSides[str]
    required: DatasetSides[bool]
    logical_type: str | CollectionLogicalType | None
    null_policy: NullPolicy
    source_normalisation: DatasetSides[tuple[Operation, ...]]
    collection_representation: DatasetSides[CollectionRepresentation] | None
    value_mapping: DatasetSides[tuple[ValueMappingEntry, ...]]
    typed_normalisation: tuple[Operation, ...]
    comparator: Comparator
    review_priority: str


@dataclass(frozen=True, slots=True)
class ConfigurationMetadata:
    """Identity and optional human-readable metadata for one configuration."""

    id: str
    revision: str
    title: str | None
    description: str | None


@dataclass(frozen=True, slots=True)
class EffectiveConfiguration:
    """A validated custom configuration with immutable resolved application state."""

    schema_version: str
    metadata: ConfigurationMetadata
    record_key: tuple[str, ...]
    in_scope: tuple[str, ...]
    fields: Mapping[str, FieldDefinition]
    _document: JsonObject = dataclass_field(repr=False, compare=False)

    @property
    def document(self) -> JsonObject:
        """Return a fresh JSON-compatible copy of the validated source document."""
        return copy.deepcopy(self._document)

    def field(self, name: str) -> FieldDefinition:
        """Return one resolved canonical field definition."""
        try:
            return self.fields[name]
        except KeyError as error:
            raise KeyError(f"unknown canonical field: {name}") from error


@dataclass(frozen=True, slots=True)
class ConfigurationError(Exception):
    """A classified expected failure while loading a custom configuration."""

    code: str
    path: str
    message: str

    @property
    def category(self) -> str:
        """Return the stable execution-error category."""
        return "configuration"

    @property
    def diagnostic(self) -> str:
        """Render the stable single-line diagnostic."""
        return f"ERROR [configuration.{self.code}]: {self.path}: {self.message}"

    def __str__(self) -> str:
        """Return the actionable path and message."""
        return f"{self.path}: {self.message}"


class _Yaml12SafeLoader(yaml.SafeLoader):
    """Safe loader with YAML 1.2 core scalar resolution and strict mappings."""

    yaml_implicit_resolvers = copy.deepcopy(yaml.SafeLoader.yaml_implicit_resolvers)

    def construct_mapping(
        self,
        node: MappingNode,
        deep: bool = False,
    ) -> dict[str, object]:
        """Construct a string-keyed mapping while rejecting merges and duplicates."""
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None, "expected a mapping", node.start_mark)
        mapping: dict[str, object] = {}
        for key_node, value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "merge keys are not permitted",
                    key_node.start_mark,
                )
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "mapping keys must be strings",
                    key_node.start_mark,
                )
            if key in mapping:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "duplicate mapping key",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


for first_character, resolvers in tuple(
    _Yaml12SafeLoader.yaml_implicit_resolvers.items()
):
    _Yaml12SafeLoader.yaml_implicit_resolvers[first_character] = [
        (tag, expression)
        for tag, expression in resolvers
        if tag
        not in {
            "tag:yaml.org,2002:bool",
            "tag:yaml.org,2002:float",
            "tag:yaml.org,2002:int",
            "tag:yaml.org,2002:null",
            "tag:yaml.org,2002:timestamp",
        }
    ]

_Yaml12SafeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:null",
    re.compile(r"^(?:~|null|Null|NULL)$"),
    ["~", "n", "N"],
)
_Yaml12SafeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    ["t", "T", "f", "F"],
)
_Yaml12SafeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:int",
    re.compile(r"^[-+]?(?:[0-9][0-9_]*|0o[0-7_]+|0x[0-9a-fA-F_]+)$"),
    list("-+0123456789"),
)
_Yaml12SafeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(
        r"^[-+]?(?:(?:[0-9][0-9_]*)?\.[0-9_]+"
        r"|[0-9][0-9_]*\.(?:[0-9_]*)"
        r"|[0-9][0-9_]*(?:[eE][-+]?[0-9]+))$"
    ),
    list("-+0123456789."),
)


def _construct_yaml12_integer(loader: _Yaml12SafeLoader, node: ScalarNode) -> int:
    """Construct YAML 1.2 decimal, octal, or hexadecimal integer syntax."""
    value = loader.construct_scalar(node).replace("_", "")
    sign = 1
    if value.startswith("-"):
        sign = -1
        value = value[1:]
    elif value.startswith("+"):
        value = value[1:]
    if value.startswith("0o"):
        return sign * int(value[2:], 8)
    if value.startswith("0x"):
        return sign * int(value[2:], 16)
    return sign * int(value, 10)


_Yaml12SafeLoader.add_constructor(
    "tag:yaml.org,2002:int",
    _construct_yaml12_integer,
)


def load_comparison_configuration(path: Path) -> EffectiveConfiguration:
    """Load, structurally validate, and semantically resolve one custom YAML file."""
    try:
        content = path.read_bytes()
    except OSError as error:
        raise ConfigurationError(
            code="unreadable",
            path="$",
            message="comparison configuration could not be read",
        ) from error
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ConfigurationError(
            code="invalid_syntax",
            path="$",
            message="comparison configuration is not valid UTF-8",
        ) from error

    document = _load_yaml_document(text)
    if (
        isinstance(document, dict)
        and isinstance(document.get("schema_version"), str)
        and document["schema_version"] != SUPPORTED_SCHEMA_VERSION
    ):
        raise ConfigurationError(
            code="unsupported_version",
            path="$.schema_version",
            message="comparison-configuration schema version is not supported",
        )
    _validate_schema(document)
    if not isinstance(document, dict):
        raise AssertionError("schema accepted a non-object configuration")
    _validate_semantics(document)
    return _build_effective_configuration(document)


def _load_yaml_document(text: str) -> object:
    """Load exactly one safe YAML 1.2 document with forbidden features disabled."""
    try:
        for token in yaml.scan(text, Loader=_Yaml12SafeLoader):
            if isinstance(token, (AliasToken, AnchorToken, TagToken)):
                raise ConfigurationError(
                    code="invalid_syntax",
                    path="$",
                    message=(
                        "YAML aliases, anchors, and explicit tags are not permitted"
                    ),
                )
        return yaml.load(text, Loader=_Yaml12SafeLoader)
    except ConfigurationError:
        raise
    except yaml.YAMLError as error:
        raise ConfigurationError(
            code="invalid_syntax",
            path="$",
            message="comparison configuration is not permitted YAML syntax",
        ) from error


def _configuration_validator() -> Draft202012Validator:
    """Load the authoritative packaged schema through the resource API."""
    resource = files(CONFIGURATION_SCHEMA_PACKAGE).joinpath(CONFIGURATION_SCHEMA_FILE)
    schema = json.loads(resource.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_schema(document: object) -> None:
    """Raise the most deterministic actionable structural validation error."""
    errors = list(_configuration_validator().iter_errors(document))
    if not errors:
        return
    error = min(errors, key=_schema_error_sort_key)
    path_components = list(error.absolute_path)
    if error.validator == "required" and isinstance(error.instance, dict):
        missing = sorted(set(error.validator_value) - set(error.instance))
        if missing:
            path_components.append(missing[0])
    elif error.validator == "additionalProperties" and isinstance(
        error.instance, dict
    ):
        permitted = set(error.schema.get("properties", {}))
        extras = sorted(set(error.instance) - permitted)
        if extras:
            path_components.append(extras[0])
    path = _configuration_path(path_components)
    raise ConfigurationError(
        code="schema_violation",
        path=path,
        message=_schema_error_message(error),
    )


def _schema_error_sort_key(error: ValidationError) -> tuple[str, str]:
    """Return a stable ordering key for competing schema failures."""
    return (
        _configuration_path(list(error.absolute_path)),
        "/".join(str(component) for component in error.absolute_schema_path),
    )


def _schema_error_message(error: ValidationError) -> str:
    """Describe a schema rule without reproducing configuration values."""
    messages = {
        "required": "required property is missing",
        "additionalProperties": "unknown property is not permitted",
        "const": "value does not identify the required schema version or form",
        "enum": "value is not one of the permitted choices",
        "minItems": "list must contain at least one item",
        "minLength": "string must not be empty",
        "minProperties": "mapping must contain at least one property",
        "uniqueItems": "list items must be unique",
        "type": "value has the wrong type",
    }
    return messages.get(
        str(error.validator),
        f"value violates schema rule {error.validator}",
    )


def _configuration_path(components: list[object]) -> str:
    """Render one unambiguous JSONPath-like configuration location."""
    path = "$"
    for component in components:
        if isinstance(component, int):
            path += f"[{component}]"
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(component)):
            path += f".{component}"
        else:
            path += f"[{json.dumps(str(component), ensure_ascii=False)}]"
    return path


def _semantic_error(path: str, message: str) -> None:
    """Raise one semantic configuration failure."""
    raise ConfigurationError(
        code="semantic_violation",
        path=path,
        message=message,
    )


def _validate_semantics(document: JsonObject) -> None:
    """Apply cross-property rules not reliably expressible in JSON Schema."""
    fields = document["fields"]
    definitions = fields["definitions"]
    in_scope = fields["in_scope"]

    for index, field_name in enumerate(fields["record_key"]):
        path = f"$.fields.record_key[{index}]"
        if field_name not in definitions:
            _semantic_error(path, "record-key field has no field definition")
        if field_name not in in_scope:
            _semantic_error(path, "record-key field is not included in fields.in_scope")
        _validate_key_field(field_name, definitions[field_name])

    for index, field_name in enumerate(in_scope):
        if field_name not in definitions:
            _semantic_error(
                f"$.fields.in_scope[{index}]",
                "in-scope field has no field definition",
            )

    source_names: dict[str, dict[str, str]] = {"reference": {}, "query": {}}
    for field_name, field in definitions.items():
        field_path = _field_path(field_name)
        _validate_field_semantics(field_path, field)
        for side in ("reference", "query"):
            source_name = field["source_fields"][side]
            previous = source_names[side].get(source_name)
            if previous is not None:
                _semantic_error(
                    f"{field_path}.source_fields.{side}",
                    f"source field is already used by canonical field {previous!r}",
                )
            source_names[side][source_name] = field_name

    if document["metadata"]["id"] == AUTOMATIC_CONFIGURATION_ID:
        _semantic_error(
            "$.metadata.id",
            "identifier is reserved for automatically generated configurations",
        )


def _validate_key_field(field_name: str, field: JsonObject) -> None:
    """Validate the mandatory contract for one record-key field."""
    path = _field_path(field_name)
    for side in ("reference", "query"):
        if not field["required"][side]:
            _semantic_error(
                f"{path}.required.{side}",
                "record-key field must be required on both sides",
            )
    if field["null_policy"]["allowed"]:
        _semantic_error(
            f"{path}.null_policy.allowed",
            "record-key field must not allow null",
        )
    if not isinstance(field.get("logical_type"), str):
        _semantic_error(
            f"{path}.logical_type",
            "record-key field must have a scalar logical type",
        )
    if field["comparator"]["name"] != "typed_exact":
        _semantic_error(
            f"{path}.comparator.name",
            "record-key field must use typed_exact",
        )


def _validate_field_semantics(path: str, field: JsonObject) -> None:
    """Validate comparator, operation, and mapping relationships for one field."""
    logical_type = field.get("logical_type")
    comparator_name = field["comparator"]["name"]
    if logical_type is None:
        if comparator_name != "preserved_exact":
            _semantic_error(
                f"{path}.comparator.name",
                "field without logical_type must use preserved_exact",
            )
    elif comparator_name == "preserved_exact":
        _semantic_error(
            f"{path}.comparator.name",
            "preserved_exact field must omit logical_type",
        )

    _validate_comparator_compatibility(path, logical_type, field)
    _validate_typed_normalisation(path, logical_type, field)
    _validate_side_mappings(path, field)
    _validate_collection_mappings(path, field)


def _validate_comparator_compatibility(
    path: str,
    logical_type: object,
    field: JsonObject,
) -> None:
    """Require the field comparator to match its resolved logical type."""
    comparator = field["comparator"]["name"]
    if isinstance(logical_type, dict):
        compatible = field_comparator_is_compatible(
            comparator,
            collection_type=logical_type["collection_type"],
        )
    else:
        compatible = field_comparator_is_compatible(
            comparator,
            scalar_type=logical_type,
        )
    if not compatible:
        _semantic_error(
            f"{path}.comparator.name",
            "comparator is incompatible with the field logical type",
        )
    if comparator == "normalised_string":
        source_operations = field.get("source_normalisation", {})
        if not source_operations.get("reference") and not source_operations.get(
            "query"
        ):
            _semantic_error(
                f"{path}.comparator.name",
                "normalised_string requires a configured string normalisation",
            )


def _validate_typed_normalisation(
    path: str,
    logical_type: object,
    field: JsonObject,
) -> None:
    """Require each typed operation to match the scalar destination type."""
    for index, operation in enumerate(field.get("typed_normalisation", [])):
        if not typed_normalisation_is_compatible(
            operation["operation"],
            logical_type if isinstance(logical_type, str) else None,
        ):
            _semantic_error(
                f"{path}.typed_normalisation[{index}].operation",
                "typed normalisation is incompatible with the field logical type",
            )


def _validate_side_mappings(path: str, field: JsonObject) -> None:
    """Reject duplicate, colliding, and missing-token-unreachable field mappings."""
    mappings = field.get("value_mapping", {})
    source_operations = field.get("source_normalisation", {})
    missing_tokens = field["null_policy"].get("missing_tokens", {})
    for side in ("reference", "query"):
        operations = source_operations.get(side, [])
        missing = {
            _descriptor_key(descriptor, operations)
            for descriptor in missing_tokens.get(side, [])
        }
        seen: set[tuple[str, object]] = set()
        for index, entry in enumerate(mappings.get(side, [])):
            entry_path = f"{path}.value_mapping.{side}[{index}].from"
            key = _descriptor_key(entry["from"], operations)
            if key in seen:
                _semantic_error(
                    entry_path,
                    "mapping source duplicates another source after normalisation",
                )
            if key in missing:
                _semantic_error(
                    entry_path,
                    "mapping source is unreachable because it is a missing token",
                )
            seen.add(key)


def _validate_collection_mappings(path: str, field: JsonObject) -> None:
    """Reject element mapping sources that collide after element normalisation."""
    for side, representation in field.get("collection_representation", {}).items():
        operations = representation.get("element_normalisation", [])
        seen: set[tuple[str, object]] = set()
        for index, entry in enumerate(representation.get("element_mapping", [])):
            entry_path = (
                f"{path}.collection_representation.{side}.element_mapping"
                f"[{index}].from"
            )
            key = _descriptor_key(entry["from"], operations)
            if key in seen:
                _semantic_error(
                    entry_path,
                    "element mapping source duplicates another source after "
                    "normalisation",
                )
            seen.add(key)


def _descriptor_key(
    descriptor: JsonObject,
    operations: list[JsonObject],
) -> tuple[str, object]:
    """Return parser-native descriptor equality after configured text operations."""
    category = descriptor["category"]
    value = descriptor.get("value")
    if category == "integer":
        value = int(value)
    elif category == "decimal":
        value = Decimal(value)
    elif category == "string":
        for operation in operations:
            value = apply_source_text_operation(
                value,
                operation["operation"],
                operation.get("parameters", {}),
            )
    return category, value


def _field_path(field_name: str) -> str:
    """Return the unambiguous configuration path for a canonical field."""
    return _configuration_path(["fields", "definitions", field_name])


def _build_effective_configuration(document: JsonObject) -> EffectiveConfiguration:
    """Resolve optional declarations into immutable application values."""
    metadata = document["metadata"]
    fields = {
        name: _build_field(name, field)
        for name, field in document["fields"]["definitions"].items()
    }
    return EffectiveConfiguration(
        schema_version=document["schema_version"],
        metadata=ConfigurationMetadata(
            id=metadata["id"],
            revision=metadata["revision"],
            title=metadata.get("title"),
            description=metadata.get("description"),
        ),
        record_key=tuple(document["fields"]["record_key"]),
        in_scope=tuple(document["fields"]["in_scope"]),
        fields=MappingProxyType(fields),
        _document=copy.deepcopy(document),
    )


def _build_field(name: str, field: JsonObject) -> FieldDefinition:
    """Build one immutable field definition with resolved omissions."""
    logical_document = field.get("logical_type")
    if isinstance(logical_document, dict):
        logical_type: str | CollectionLogicalType | None = CollectionLogicalType(
            collection_type=logical_document["collection_type"],
            element_type=logical_document["element_type"],
            element_comparator=_build_comparator(
                logical_document["element_comparator"]
            ),
        )
    else:
        logical_type = logical_document

    null_policy = field["null_policy"]
    missing_tokens = null_policy.get("missing_tokens", {})
    source_normalisation = field.get("source_normalisation", {})
    value_mapping = field.get("value_mapping", {})
    collection_document = field.get("collection_representation", {})
    if isinstance(logical_type, CollectionLogicalType):
        collection_representation: DatasetSides[CollectionRepresentation] | None
        collection_representation = DatasetSides(
            reference=_build_collection_representation(
                collection_document.get("reference")
            ),
            query=_build_collection_representation(collection_document.get("query")),
        )
    else:
        collection_representation = None

    return FieldDefinition(
        name=name,
        source_fields=DatasetSides(**field["source_fields"]),
        required=DatasetSides(**field["required"]),
        logical_type=logical_type,
        null_policy=NullPolicy(
            allowed=null_policy["allowed"],
            nulls_equal=null_policy["nulls_equal"],
            missing_tokens=DatasetSides(
                reference=tuple(
                    _build_descriptor(item)
                    for item in missing_tokens.get("reference", [])
                ),
                query=tuple(
                    _build_descriptor(item) for item in missing_tokens.get("query", [])
                ),
            ),
        ),
        source_normalisation=DatasetSides(
            reference=tuple(
                _build_operation(item)
                for item in source_normalisation.get("reference", [])
            ),
            query=tuple(
                _build_operation(item)
                for item in source_normalisation.get("query", [])
            ),
        ),
        collection_representation=collection_representation,
        value_mapping=DatasetSides(
            reference=tuple(
                _build_mapping(item) for item in value_mapping.get("reference", [])
            ),
            query=tuple(
                _build_mapping(item) for item in value_mapping.get("query", [])
            ),
        ),
        typed_normalisation=tuple(
            _build_operation(item) for item in field.get("typed_normalisation", [])
        ),
        comparator=_build_comparator(field["comparator"]),
        review_priority=field.get("review_priority", "normal"),
    )


def _build_operation(document: JsonObject) -> Operation:
    """Build one immutable processing operation."""
    return Operation(
        name=document["operation"],
        parameters=MappingProxyType(dict(document.get("parameters", {}))),
    )


def _build_comparator(document: JsonObject) -> Comparator:
    """Build one immutable comparator declaration."""
    return Comparator(
        name=document["name"],
        parameters=MappingProxyType(dict(document.get("parameters", {}))),
    )


def _build_descriptor(document: JsonObject) -> SourceValueDescriptor:
    """Build one immutable source-value descriptor."""
    return SourceValueDescriptor(
        category=document["category"],
        value=document.get("value"),
    )


def _build_mapping(document: JsonObject) -> ValueMappingEntry:
    """Build one immutable value-mapping entry."""
    return ValueMappingEntry(
        source=_build_descriptor(document["from"]),
        destination=_build_descriptor(document["to"]),
    )


def _build_collection_representation(
    document: JsonObject | None,
) -> CollectionRepresentation:
    """Build one side's collection representation, applying omission defaults."""
    if document is None:
        return CollectionRepresentation(
            format="json_array",
            delimiter=None,
            element_normalisation=(),
            element_mapping=(),
        )
    return CollectionRepresentation(
        format=document["format"],
        delimiter=document.get("delimiter"),
        element_normalisation=tuple(
            _build_operation(item)
            for item in document.get("element_normalisation", [])
        ),
        element_mapping=tuple(
            _build_mapping(item) for item in document.get("element_mapping", [])
        ),
    )
