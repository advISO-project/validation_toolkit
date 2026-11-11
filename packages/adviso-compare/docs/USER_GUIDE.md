# AdvISO Compare user guide

This guide applies to AdvISO Compare version 1 and to version `1.0` of both the
comparison-configuration schema and the comparison-results schema.

AdvISO Compare compares a reference dataset with a query dataset. The two
datasets may use different field names and ways of writing values. A comparison
configuration can describe how to translate both datasets into a shared form.
The tool then reports differences that remain after translation.

The output is comparison evidence. It is not a pass/fail decision, a pipeline
validation report, or a claim of ISO 15189 compliance. A laboratory must decide
how the evidence contributes to its own validation and quality processes.

## 1. Install and check the tool

AdvISO Compare requires Python 3.10 or later. Install a released wheel and its
dependencies with `pip`. For example:

```console
python -m venv .venv
. .venv/bin/activate
python -m pip install /path/to/adviso_compare-1.0.0-py3-none-any.whl
adviso-compare --version
adviso-compare --help
```

On Windows, activate the environment with `.venv\Scripts\activate`.
Installation may use a package index to obtain dependencies. Once installed,
the comparison itself needs no network service.

The full guide is installed with the software under
`share/doc/adviso-compare/USER_GUIDE.md` in the Python environment. The two
JSON schemas are installed as resources in the `adviso_compare.schemas` Python
package.

## 2. The command

The command has no subcommands:

```text
adviso-compare \
  --reference REFERENCE \
  --query QUERY \
  --output OUTPUT \
  [--configuration CONFIGURATION] \
  [--overwrite]
```

| Option | Meaning |
| --- | --- |
| `--reference REFERENCE` | Reference dataset. Required. |
| `--query QUERY` | Query dataset produced by the pipeline. Required. |
| `--output OUTPUT` | New directory in which to place the evidence package. Required. |
| `--configuration CONFIGURATION` | Custom YAML comparison configuration. If omitted, automatic strict-exact mode is used. |
| `--overwrite` | Replace an existing complete evidence package. See below. |
| `--version` | Print the installed version and exit. |
| `--help` | Print concise help and exit. |

The output directory normally must not exist. `--overwrite` can replace only a
directory that is recognisably a complete evidence package containing
exactly `comparison-results.json` and `comparison-report.html`. It will not
replace a file, symbolic link, empty or partial directory, or a directory with
other contents. A failed replacement leaves the old complete package in place.

The command prints a short completion summary to standard output. An execution
error is printed to standard error. The exit codes are:

| Code | Meaning |
| ---: | --- |
| `0` | The run is complete. This includes complete runs that found differences. |
| `1` | The run is incomplete because at least one intended value comparison was not assessable. An evidence package is still written. |
| `2` | Expected operational error, such as an invalid option, configuration, input, key, resource condition, or output destination. No evidence package is written. |
| `3` | Unexpected internal error. No evidence package is written. |

Do not treat exit code `0` as a statement that the query passed validation. It
means only that the configured comparison was completed.

## 3. Input datasets

The reference and query can independently be CSV, TSV, or JSON. The
case-insensitive filename extension selects the format: `.csv`, `.tsv`, or
`.json`. There is no format override. Both files must be UTF-8.

### 3.1 CSV and TSV

CSV uses commas; TSV uses tabs. Both use a double quote as the quote character.
A double quote inside a quoted cell is written twice. Quoted cells may contain
the delimiter or a line break. LF and CRLF line endings are accepted.

A header is required. Header names must be non-empty and unique. Every data row
must contain the same number of cells as the header. All cells initially count
as strings, including empty cells and text that looks like a number or boolean.

### 3.2 JSON

JSON must contain one array of record objects at its root, even when there is
only one record:

```json
[
  {"sample_id": "S1", "result": "detected"},
  {"sample_id": "S2", "result": "not_detected"}
]
```

A single root object is not accepted. Every array item must be an object.
Top-level record field names must be non-empty and unique. Duplicate member
names anywhere in the JSON are rejected.

JSON strings, integers, decimals, booleans, nulls, arrays, and objects retain
their natural JSON type. Decimal numbers are read exactly without first being
converted to binary floating point, and their original spelling is retained as
evidence. `NaN` and infinities are not valid JSON numbers.

### 3.3 Empty datasets

`[]` is a valid zero-record JSON dataset. A header with no data rows is a valid
zero-record CSV or TSV dataset. A zero-byte file is not a valid dataset.

A custom configuration can compare empty datasets when it supplies the needed
field and key information. Automatic mode cannot select a key from two empty
JSON arrays because they expose no fields.

## 4. Automatic strict-exact mode

Omit `--configuration` to use automatic mode. It is suitable when the two
datasets already use the same field names and the same representations.

The tool first finds field names shared by both datasets. It selects the record
key as follows:

1. If both sides contain `record_id`, that field is used. It must contain a
   unique, non-null string in every record on both sides.
2. Otherwise, a candidate must be a shared field containing a unique,
   non-null string in every record on both sides, with at least one value shared
   between the datasets.
3. Exactly one candidate must remain. No candidate or more than one candidate
   is an `input.invalid_record_key` error.

The selected key is compared as a typed string. All other shared fields are
compared using strict parser-native equality: value types must match as well as
content. For example, JSON integer `1` does not equal JSON string `"1"`.
Fields found on only one side are reported as exclusions, not differences.

The tool creates an effective configuration internally and includes it in the
result.

### 4.1 Runnable automatic example

Change to the `examples` directory installed next to this guide, then run:

```console
adviso-compare \
  --reference automatic/reference.csv \
  --query automatic/query.csv \
  --output automatic-evidence
```

The example has no `record_id`. `sample_id` is the only valid key candidate, so
it is discovered automatically. The run is complete and reports one changed
`lineage`. The query-only `pipeline_version` field appears in the exclusions.

Automatic mode is deliberately conservative. Use a custom configuration when
source field names differ, values require translation, a composite key is
needed, or automatic key selection is ambiguous.

## 5. Custom comparison configurations

A custom configuration is one UTF-8 YAML document with suffix `.yaml` or
`.yaml`.

The file is checked before either dataset is read. YAML aliases, anchors,
merge keys, explicit tags, duplicate keys, and unsafe
object constructors are rejected. Identifiers, versions, field and
operation names, dates, datetimes, and decimal parameters need to be quoted.
Unknown properties are rejected.

The JSON Schema file
`comparison-configuration-v1.0.schema.json` is the machine-readable definition
of the expected YAML structure, and input custom configurations that are not
compliant with the schema are rejected.

The tool also checks relationships that are awkward to express in JSON Schema:
all named key and in-scope fields must be defined; source field names must be
unique on each dataset side; mapping sources must not be repeated, conflicting,
or unreachable; operations and comparators must suit their field; and custom
configurations must not use the reserved automatic-mode ID
`org.adviso.automatic-strict-exact`.

### 5.1 Top-level properties

| Property | Required | Meaning |
| --- | --- | --- |
| `schema_version` | Yes | Must be a supported schema version (e.g. `"1.0"`). |
| `metadata` | Yes | Identity and description of the configuration. It does not alter the comparison. |
| `fields` | Yes | Key, scope, field correspondence, and comparison rules. |

`metadata` has these properties:

| Property | Required | Meaning |
| --- | --- | --- |
| `id` | Yes | Stable, non-empty identifier chosen by the configuration owner. |
| `revision` | Yes | Non-empty revision string managed by the configuration owner. |
| `title` | No | Human-readable title; may be empty. |
| `description` | No | Human-readable description; may be empty. |

`fields` has these properties:

| Property | Required | Meaning |
| --- | --- | --- |
| `record_key` | Yes | Non-empty ordered list of canonical field names forming one key. Order matters for a composite key. |
| `in_scope` | Yes | Non-empty list of canonical fields to assess. Key fields must be included. List order does not affect results. |
| `definitions` | Yes | Non-empty mapping from user-chosen canonical field names to field definitions. |

A definition not listed in `in_scope` is deliberately excluded and appears once
as `configured_field_excluded`. A source field not named by any definition on
its side (reference or query) appears as `undeclared_field_excluded`. Neither kind
is compared or makes a run incomplete.

### 5.2 Field definitions

Every entry in `fields.definitions` is object with a canonical field name as
key, and has the following properties:

| Property | Required | Meaning |
| --- | --- | --- |
| `source_fields` | Yes | `reference` and `query` give the source field name on each side. Both are required non-empty strings. |
| `required` | Yes | `reference` and `query` booleans say whether every applicable record on that side must contain the field. |
| `logical_type` | Usually | Scalar type or collection declaration. Omit only for `preserved_exact`. |
| `null_policy` | Yes | Defines whether null is allowed and how two nulls compare. |
| `source_normalisation` | No | Side-specific ordered text operations before mapping and type parsing. |
| `collection_representation` | Collections only, optional | Describes how either side writes a collection. |
| `value_mapping` | Scalar typed fields only, optional | Side-specific closed translation tables. |
| `typed_normalisation` | Scalar typed fields only, optional | Ordered operations applied to parsed values on both sides. |
| `comparator` | Yes | Comparison rule and, where needed, its parameters. |
| `review_priority` | No | `low`, `normal`, or `high`; defaults to `normal`. It helps organise review and does not change findings, status, exit code, or clinical significance. |

Every field part of the record key must be in `definitions` and `in_scope`, required
and non-nullable on both sides, scalar, and compared with `typed_exact`. Key fields
may use explicit source normalisation or value mapping.

### 5.3 Logical types

A scalar `logical_type` is `string`, `integer`, `decimal`, `boolean`, `date`, or
`datetime`. Parsing is strict. In particular, CSV and TSV cells start as
strings and are parsed only because a logical type was declared. Dates use
`YYYY-MM-DD`. Datetimes use RFC 3339 with an explicit timezone.

The accepted source values are deliberately narrow:

| Logical type | Accepted parser-native input |
| --- | --- |
| `string` | String only. |
| `integer` | JSON integer, or text containing an optional sign and ASCII digits. Decimal points and exponents are not accepted. |
| `decimal` | JSON integer or decimal, or signed decimal text in plain or scientific notation. Text such as `.5` or `1.` is not accepted. |
| `boolean` | JSON boolean, or exactly the lowercase text `true` or `false`. |
| `date` | String containing a valid Gregorian `YYYY-MM-DD` date. |
| `datetime` | String containing a full RFC 3339 date and time with `Z` or a numeric offset. A local time without an offset is not accepted. |

JSON objects cannot be converted to any of the logical types. They may be compared
as complete, untyped JSON values using `preserved_exact`. More generally, the tool
does not guess how one source representation should be converted into another: any
conversion not directly supported by the declared logical type must be stated explicitly
in value_mapping.

A collection uses an object:

```yaml
logical_type:
  collection_type: "set"
  element_type: "string"
  element_comparator:
    name: "typed_exact"
```

`collection_type` is `list`, `set`, or `multiset`. `element_type` is one of the
scalar types. Nested collections are not supported. Lists keep order, sets
ignore order and reject duplicates, and multisets ignore order but retain how
many times each value occurs. Sets and multisets require `typed_exact` elements.
Lists allow `typed_exact`, or `numeric_tolerance` for integer or decimal
elements.

### 5.4 Null policy and typed value descriptions

`null_policy.allowed` and `null_policy.nulls_equal` are required booleans. If
null is not allowed, `nulls_equal` must be false. JSON null is always recognised
as null. A missing field is different from a present field containing null.

Optional `missing_tokens` may contain a non-empty `reference` list, a non-empty
`query` list, or both. Each item describes a parser-native value to treat as
null. For example:

```yaml
missing_tokens:
  reference:
    - category: "string"
      value: "NA"
  query:
    - category: "string"
      value: "."
```

Each missing token describes a non-null source value using a category and a value.
The permitted categories are `string`, `integer`, `decimal`, and `boolean`. Strings,
integers, and decimals use a textual `value`; booleans use `true` or `false`. An
actual JSON `null` does not need to be listed because the tool recognises it
automatically.

### 5.5 Source normalisation

`source_normalisation` may have `reference`, `query`, or both. Each present
side is a non-empty ordered list. Operations affect only parser-native strings
from that side. Non-strings pass through unchanged.

| Operation | Parameters | Effect |
| --- | --- | --- |
| `unicode_normalise` | `form`: `NFC`, `NFD`, `NFKC`, or `NFKD` | Applies the named Unicode normalisation form. |
| `trim` | `side`: `leading`, `trailing`, or `both` | Removes Unicode White_Space characters from the chosen end or ends. |
| `case_fold` | None; omit `parameters` | Applies locale-independent full Unicode case folding. |

Operations run in list order. Case folding does not silently perform Unicode
normalisation; list both operations when both are needed.

### 5.6 Value mapping

`value_mapping` may have `reference`, `query`, or both. Each present side is a
non-empty list of `from` and `to` value descriptions:

```yaml
value_mapping:
  query:
    - from: {category: "string", value: "pos"}
      to: {category: "string", value: "detected"}
```

The mapping is closed: when a side has a mapping, every non-null value on that
side must match an entry. An unmapped value produces a `mapping_failure`; it is
not passed through. Many source values may map to the same destination. A
destination may be null, after which the null policy applies.

A mapping destination may use category: "null" without a value. This converts
the mapped source value to null, after which the field’s `null_policy` is applied.
Mapping from null is not supported because an actual JSON null is recognised and
handled before value mapping.

Mapping happens after source normalisation and missing-token recognition, and
before parsing to the logical type.

### 5.7 Collections written as text

`collection_representation` may have `reference`, `query`, or both. An omitted
side defaults to `json_array` with no element processing.

Each side requires `format`:

- `json_array` means a JSON array value, or a CSV/TSV string containing valid
  JSON-array text. It must not have a `delimiter`.
- `delimited_text` means a parser-native string split on the required,
  non-empty `delimiter` string.

Optional `element_normalisation` is a non-empty ordered list of the text
operations in Section 5.5. Optional `element_mapping` is a non-empty closed
mapping whose `from` and `to` values must both be non-null. These act on each
element, not the collection as a whole. Collection fields cannot also use the
field-level `source_normalisation`, `value_mapping`, or `typed_normalisation`.

### 5.8 Typed normalisation

`typed_normalisation` is an optional, non-empty ordered list of operations
applied to parsed values from both the reference and query. Operations run
before the comparator is applied.

#### Decimal quantisation

`decimal_quantise` fixes the number of digits retained after the decimal point:

```yaml
typed_normalisation:
  - operation: "decimal_quantise"
    parameters:
      places: 2
      rounding: "half_even"
```

Here, `places: 2` means that values are quantised to two digits after the
decimal point. A value is not first converted to binary floating point; exact
decimal arithmetic is used.

The available rounding methods are:

| Method | Meaning |
| --- | --- |
| `half_even` | Round to the nearest value. If the discarded part is exactly halfway between two possible results, choose the result whose last retained digit is even. For example, at two decimal places, `1.235` becomes `1.24`, while `1.245` becomes `1.24`. |
| `half_up` | Round to the nearest value. If the discarded part is exactly halfway between two possible results, round away from zero. At two decimal places, `1.235` becomes `1.24` and `-1.235` becomes `-1.24`. |
| `down` | Discard digits beyond the requested number of decimal places, moving towards zero rather than rounding to the nearest value. At two decimal places, `1.239` becomes `1.23` and `-1.239` becomes `-1.23`. |

`places: 0` quantises to a whole-number value, although the field remains
logically a decimal. Quantisation is applied independently to both reference
and query values before they are compared.

#### Datetime truncation

`datetime_truncate` limits fractional-second precision after the datetime has
been converted to UTC:

```yaml
typed_normalisation:
  - operation: "datetime_truncate"
    parameters:
      precision: "millisecond"
```

The permitted values are:

- `second`: remove the entire fractional-second part;
- `millisecond`: retain at most three fractional digits; and
- `microsecond`: retain at most six fractional digits.

Discarded digits are removed without rounding. For example, millisecond
truncation changes `.1238` seconds to `.123`, not `.124`.

### 5.9 Comparators

Every comparator is an object with `name`. The following take no parameters:

| Name | Use |
| --- | --- |
| `preserved_exact` | Parser-native equality without a declared logical type. Array order matters; object member order does not. |
| `typed_exact` | Exact equality after typed parsing and configured processing. |
| `normalised_string` | Exact comparison of processed strings. |
| `numeric_exact` | Exact comparison of integer or decimal values. |
| `date_exact` | Exact canonical calendar date. |
| `datetime_exact` | Same instant after conversion to UTC. |
| `list_exact` | Ordered collection comparison. |
| `set_exact` | Order-independent unique collection comparison. |
| `multiset_exact` | Order-independent comparison retaining duplicate counts. |

String comparators require `logical_type: "string"`; numeric comparators require
`integer` or `decimal`; date and datetime comparators require their matching
temporal type; and each collection comparator requires the collection type with
the same name. `normalised_string` also requires at least one applicable
normalisation operation. `preserved_exact` is the only comparator with no
`logical_type`, and it cannot be combined with normalisation, mapping,
collection representation, typed normalisation, or configured missing tokens.

`numeric_tolerance` requires exactly one parameter. With
`absolute_tolerance`, values match when their absolute difference is no greater
than the tolerance. With `relative_tolerance`, values match when:

```text
absolute difference <= relative tolerance × absolute reference value
```

The tolerance is a quoted, non-negative finite decimal. The boundary is
included. A relative tolerance around a zero reference allows only exact zero;
use an absolute tolerance when a non-zero difference around zero is intended.

The schema restricts the possible shape of comparators. The tool's further
checks ensure that a comparator suits the declared logical type and collection
kind.

### 5.10 Processing order

For a scalar field, the order is:

1. distinguish absence from a present parser-native value;
2. apply side-specific source normalisation to strings;
3. recognise configured missing tokens;
4. apply the side-specific closed value mapping;
5. apply the null policy;
6. parse the declared logical type;
7. apply typed normalisation to both sides; and
8. compare the canonical values.

For a collection, whole-field missing-token and null handling happens before
the representation is decoded. Element normalisation, mapping, and typed
parsing then happen for each element before collection comparison.

### 5.11 Runnable custom example

Run the supplied example with:

```console
adviso-compare \
  --reference custom/reference.json \
  --query custom/query.csv \
  --configuration custom/configuration.yaml \
  --output custom-evidence
```

The configuration maps different source field names to shared canonical names.
It shows decimal quantisation and absolute tolerance, string trimming and case
folding, value mapping, and translation of slash-delimited text to a set. It
also declares `curator_note` but leaves it out of `fields.in_scope`, while the
query's undeclared `pipeline_version` is also excluded. The run is complete and
reports one `measurement` difference.

Custom configurations should be treated as controlled documents in a
accreditable environment. Give each one a stable ID and revision, review changes,
retain the exact configuration used for a comparison, and test it with representative data.
The result embeds the effective configuration, but local quality arrangements remain
the authority for approval and retention.

## 6. How the comparison works

The result describes several different aspects of a comparison. Understanding
their relationship makes the report easier to interpret.

### 6.1 The reporting model

| Concept | What it describes | Examples |
| --- | --- | --- |
| Run status | Whether the comparison as a whole could be completed | `complete`, `incomplete`, `error` |
| Phase status | Whether one of the three comparison phases completed its applicable work | `complete`, `incomplete` |
| Finding | One reported difference or problem that requires attention | A missing record or an invalid field value |
| Finding classification | The broad meaning of a finding | `comparison_difference`, `assessment_issue` |
| Finding code | The specific type of finding | `value_mismatch`, `mapping_failure` |
| Value-opportunity outcome | What happened when one in-scope field was considered for one aligned record | `matched`, `mismatched`, `not_assessable` |
| Exclusion | A field that was deliberately or implicitly outside the comparison | A configured or undeclared field exclusion |
| Review priority | Optional presentation priority for a finding about a configured field | `low`, `normal`, `high` |

A finding is an individual entry in the report. Every finding has one
classification and one more-specific finding code. The classification explains
the general nature of the finding; the code explains exactly what happened.

### 6.2 Comparison phases

Every comparison performs three phases in order:

1. **Contract:** checks that configured fields can be found and translated as
   declared, including requiredness, null, type, validity, and mapping rules.
2. **Records:** constructs canonical keys, aligns records, and identifies
   missing and extra records.
3. **Values:** compares each assessable, in-scope, non-key field in aligned
   records.

A problem in an earlier phase does not automatically stop all later work. The
tool continues wherever the required information remains valid and
unambiguous. The phase attached to a finding records where the finding arose;
it is separate from the finding's classification.

### 6.3 Findings, classifications, and codes

There are two finding classifications.

`comparison_difference` means that the relevant translation and comparison
prerequisites succeeded, and a difference remained. It includes a reference
record missing from the query, an extra query record, or two valid translated
values that do not match.

`assessment_issue` means that the declared translation or assessment could not
be applied cleanly to some input content. For example, a required field may be
absent or a source value may not have an entry in a configured mapping. Such an
issue can be important, but the tool cannot call it a post-translation
difference because the intended translation did not succeed.

The eight finding codes are:

| Code | Classification | Meaning |
| --- | --- | --- |
| `missing_record` | `comparison_difference` | A reference record has no aligned query record. |
| `extra_record` | `comparison_difference` | A query record has no aligned reference record. |
| `value_mismatch` | `comparison_difference` | Two valid translated values differ under the comparator. |
| `missing_required_field` | `assessment_issue` | A required source field is absent. |
| `type_mismatch` | `assessment_issue` | The source value type cannot be used for the declared logical type. |
| `invalid_field_value` | `assessment_issue` | The source value type is acceptable, but the value itself is invalid. |
| `null_policy_violation` | `assessment_issue` | A null is present where null is not allowed. |
| `mapping_failure` | `assessment_issue` | A closed mapping has no entry for the source value. |

Successful record and value matches are included in summary counts rather than
reported as individual findings.

### 6.4 Value-opportunity outcomes

A value opportunity is one in-scope, non-key field considered for one pair of
aligned records. Every such opportunity is counted as exactly one of:

- `matched`: both sides were assessable and matched under the configured
  comparator;
- `mismatched`: both sides were assessable but did not match, producing a
  `value_mismatch` finding; or
- `not_assessable`: the intended comparison could not be performed because a
  prerequisite failed, producing the applicable `assessment_issue` finding.

`not_assessable` is a summary outcome, not a finding code. The associated
finding explains why the comparison could not be performed. At least one
not-assessable opportunity makes the values phase, and therefore the run,
`incomplete`.

### 6.5 Run and phase status

The possible run statuses are:

- `complete`: every applicable comparison was performed;
- `incomplete`: the record model remains trustworthy, but at least one intended
  value comparison was not assessable; and
- `error`: no trustworthy comparison result could be produced, for example
  because an input was malformed or a record key was invalid.

The contract, records, and values phases each have a status of `complete` or
`incomplete`. Overall run status is `complete` only when all three phases are
complete. An errored run has no evidence package and therefore no reported
phase statuses.

### 6.6 Exclusions and review priority

An exclusion records a field that was outside the comparison:

- `configured_field_excluded` means that the field has a definition but is not
  listed in `fields.in_scope`;
- `undeclared_field_excluded` means that a source field was observed but is not
  represented by a field definition on that side.

Excluded fields are not assessed. They do not produce findings or value
opportunities, and they do not make a run incomplete. This is different from
`not_assessable`, which describes an intended comparison that could not be
performed.

`review_priority` may be `low`, `normal`, or `high`. It helps organise findings
about configured fields for human review. It does not change the comparison,
the finding classification, run status, or exit code, and it is not a statement
of clinical significance. Record findings do not carry a review priority; they
are counted as `unassigned` in the priority summary.

### 6.7 No acceptance verdict

The tool reports what it compared, what differed, and what it could not assess.
It does not decide whether the results are acceptable, whether a pipeline has
passed validation, or whether an ISO 15189 requirement has been met. Those
decisions belong to the laboratory's separately governed validation process.

## 7. The evidence package

A complete or incomplete run creates exactly:

```text
OUTPUT/
├── comparison-results.json
└── comparison-report.html
```

`comparison-results.json` is the canonical result for software use and detailed
review. `comparison-report.html` is a self-contained, offline view made only
from the validated JSON. The HTML gives no additional comparison facts. It can
be opened in an ordinary browser with scripting disabled.

The report separates run completeness, comparison differences, and assessment
issues. It does not apply acceptance thresholds or give a pass/fail verdict.

## 8. Canonical JSON reference

Before consuming a result, check `results_schema_version`. Version `1.0` uses
`comparison-results-v1.0.schema.json`. Software should validate the document and
use its structured properties, classifications, and finding codes. Do not
extract facts by parsing the English `message` text.

Every top-level property below is required, even when `exclusions` or
`findings` is empty. Unknown properties are not allowed.

### 8.1 Run and provenance

| Property | Meaning |
| --- | --- |
| `results_schema_version` | Must be `"1.0"`. |
| `run.id` | Random lowercase UUID version 4 for this run. |
| `run.status` | `complete` or `incomplete`. Error runs do not produce this JSON. |
| `run.completed_at` | Completion time in UTC, as `YYYY-MM-DDTHH:MM:SSZ`. |
| `phases.contract` | `complete` or `incomplete` contract-phase status. |
| `phases.records` | `complete` or `incomplete` records-phase status. |
| `phases.values` | `complete` or `incomplete` values-phase status. |
| `software.name` | Always `adviso-compare`. |
| `software.version` | Installed software version. |
| `software.build` | Optional non-empty build identifier when one is available. |
| `runtime.python` | Python implementation and full version, such as `cpython-3.12.7`. |
| `runtime.platform` | General operating-system family and architecture, such as `linux-x86_64`; no host identity. |
| `runtime.unicode_version` | Unicode database version used by text operations. |

`inputs.reference` and `inputs.query` each contain:

| Property | Meaning |
| --- | --- |
| `basename` | Input filename without its directory. Treat this as potentially sensitive. |
| `format` | `csv`, `tsv`, or `json`. |
| `encoding` | Always `utf-8`. |
| `size_bytes` | Exact input size in bytes. |
| `digest.algorithm` | Always `sha256`. |
| `digest.value` | Lowercase 64-character SHA-256 digest of the exact bytes. |

Absolute paths, usernames, hostnames, environment variables, working
directories, raw command lines, and dependency inventories are not included.

### 8.2 Key and configuration

`record_key_fields.reference`, `.query`, and `.canonical` are ordered,
non-empty arrays of unique field names. Their common order is the component
order of a composite key.

`comparison_configuration.document` is the complete effective configuration.
It validates against comparison-configuration schema version `1.0`. In
automatic mode it is the generated configuration, not a path or a digest.

### 8.3 Summary and exclusions

`summary.records` contains non-negative counts: `reference`, `query`, `matched`,
`missing`, and `extra`. The reference count equals matched plus missing; the
query count equals matched plus extra.

`summary.values` contains `matched`, `mismatched`, and `not_assessable` counts
for all in-scope non-key value opportunities. Each opportunity appears in
exactly one count.

`summary.findings.total` is the total number of findings.
`by_classification` always contains `comparison_difference` and
`assessment_issue`. `by_code` always contains all eight finding codes.
`by_review_priority` always contains `low`, `normal`, `high`, and `unassigned`.
Zero-valued entries remain present. Each grouping sums to `total`.

Each item in `exclusions` has one of two exact forms:

- `configured_field_excluded`: `code` and `canonical_field`;
- `undeclared_field_excluded`: `code`, `side` (`reference` or `query`),
  `source_field`, and non-negative `record_count`.

Exclusions are not findings and do not affect run status.

### 8.4 Finding properties

Every finding has `id`, `classification`, `code`, `phase`, `message`, and
`affected_side`.

- `id` is a report-local sequence such as `F000001`.
- `classification` is `comparison_difference` or `assessment_issue`.
- `code` is one of the eight codes in Section 6.
- `phase` is `contract`, `records`, or `values`.
- `message` is deterministic English presentation text. It adds no fact that is
  absent from the structured fields.
- `affected_side` is `reference`, `query`, or `both`, as allowed for the code.

Properties are included only when their finding form needs them:

| Property | Meaning |
| --- | --- |
| `record_identity` | Ordered `reference`, `query`, and `canonical` value arrays. A missing record's absent side is JSON null. A one-field key still uses a one-item array. |
| `source_locations` | Independent `reference` and `query` locations; a side is null if its record does not exist. |
| `field` | Canonical field name for a field finding. |
| `review_priority` | Resolved `low`, `normal`, or `high` priority for that field. |
| `values` | Side-specific presence and permitted value evidence. |

CSV and TSV locations use one-based `record_number` and starting physical
`line_number`, with optional source `field`. JSON locations use an RFC 6901
`json_pointer`. An absent field points to its containing record because the
missing member has no location.

`values.reference` and `values.query` each have `state`: `present` or `absent`.
An absent side has no `source` or `canonical` value. A present side may include:

- `source.category`: `string`, `integer`, `decimal`, `boolean`, `null`, `array`,
  or `object`; `value` is present except for null and recursively contains typed
  values for arrays and objects;
- `canonical.logical_type`: `string`, `integer`, `decimal`, `boolean`, `date`,
  `datetime`, `list`, `set`, or `multiset`; scalar and collection forms contain
  their uniquely rendered `value`, and collections also contain `element_type`.

Source numbers retain their original lexical text. Canonical integers use
ordinary base-10 text. Canonical decimals use one normal scientific rendering.
Canonical datetimes are UTC. Lists retain order; sets and multisets use
deterministic order, with multiset duplicates retained.

The schema defines exact finding forms. In summary:

- missing and extra records have record identity and locations, but no field,
  priority, or value evidence;
- record-specific missing-required-field findings have identity, locations,
  field, priority, and presence states; the zero-record dataset-level form has
  only field and priority in addition to the common properties;
- type, invalid-value, null-policy, and mapping findings have identity,
  locations, field, priority, and only the value evidence needed to explain the
  problem;
- value mismatches have identity, locations, field, priority, and evidence for
  both sides.

### 8.5 Structural and semantic validation

JSON Schema validation checks document shape, required properties, permitted
values, patterns, cross-references, and recognised formats. Format checking
must be enabled so that invalid UUIDs, dates, and datetimes are rejected. For
example, using Python and the installed schema resources:

```python
import json
from importlib.resources import files

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

schema_root = files("adviso_compare.schemas")
config_schema = json.loads(
    schema_root.joinpath("comparison-configuration-v1.0.schema.json")
    .read_text(encoding="utf-8")
)
results_schema = json.loads(
    schema_root.joinpath("comparison-results-v1.0.schema.json")
    .read_text(encoding="utf-8")
)
registry = Registry().with_resource(
    config_schema["$id"], Resource.from_contents(config_schema)
)
validator = Draft202012Validator(
    results_schema,
    registry=registry,
    format_checker=FormatChecker(),
)
result = json.loads(open("comparison-results.json", encoding="utf-8").read())
validator.validate(result)
```

Schema validation cannot prove that the counts and linked facts agree. Before
publication, AdvISO Compare also checks semantic consistency, including:

- overall status agrees with all phase statuses;
- record equations and all finding totals reconcile;
- key field-name and identity arrays have matching lengths and order;
- findings and exclusions have the required order and no duplicates;
- IDs are sequential after sorting;
- each finding's code agrees with its classification, side, phase, evidence,
  field, locations, and embedded configuration; and
- configuration-derived fields, priorities, and exclusions agree with the
  embedded configuration and observed source fields.

A consumer can use JSON Schema to reject a structurally invalid document, but
independent reproduction or trusted production by AdvISO Compare is needed for
full semantic assurance.

## 9. Errors and corrective action

The first error line has the form:

```text
ERROR [category.code]: message
```

| Code or category | What to check |
| --- | --- |
| `invocation.invalid_arguments` | Run `adviso-compare --help`; supply all required options and no subcommand. |
| `configuration.unreadable` | Check the path and read permission. |
| `configuration.invalid_syntax` | Check UTF-8 YAML; remove aliases, anchors, tags, merges, and duplicate keys. |
| `configuration.schema_violation` | Use the reported YAML path to fix a missing, unknown, or invalid property. |
| `configuration.semantic_violation` | Check named fields, key rules, logical types, operations, mappings, and comparator compatibility. |
| `configuration.unsupported_version` | Use a configuration schema version supported by the installed tool. |
| `input.unreadable` | Check the input path and read permission. |
| `input.unsupported_format` | Give the input a single recognised `.csv`, `.tsv`, or `.json` extension. |
| `input.invalid_encoding` | Convert the input to valid UTF-8 without silent replacement. |
| `input.invalid_syntax` | Fix malformed CSV, TSV, or JSON syntax. |
| `input.invalid_structure` | Check headers, row widths, JSON root shape, record objects, and field names. |
| `input.invalid_record_key` | Ensure the chosen key is present, non-null, valid, and unique; in automatic mode remove ambiguity or use a custom configuration. |
| `resource.limit_exceeded` or `resource.exhausted` | Reduce input size or provide more resources, then rerun. No partial result is valid. |
| `output.invalid_destination` | Choose a new destination or use `--overwrite` only for a complete two-file package. |
| `output.write_failed` | Check parent-directory permissions and available storage. |
| `internal.unexpected` | Rerun once; if it persists, report the software version and safe reproduction details. Do not disclose clinical data. |

An assessment issue inside an otherwise readable and alignable dataset is a
finding, not an execution error. Review the evidence package for those issues.

## 10. Security, governance, and limitations

The tool operates locally and does not transmit inputs, configurations, or
results. The evidence package can contain sensitive laboratory or patient
information, including record identifiers, values needed to explain findings,
and input basenames. Store it with permissions, retention, backup, and disposal
controls suitable for the source data. The laboratory remains responsible for
appropriate pseudonymisation.

Routine terminal output and error diagnostics do not reproduce record
identifiers or source values. The tool does not provide de-identification,
identifier hashing, access control, encryption, or sensitivity policies.

Version 1 compares one complete reference dataset with one complete query
dataset. It does not download data, run a bioinformatics pipeline, subset a
validation dataset, apply acceptance thresholds, decide fitness for purpose,
or produce a complete ISO 15189 validation dossier. It supports the evidence
review that forms part of a wider, governed validation process.

This release sets no fixed input-size or record-count limit. Available memory,
storage, and operating-system resources still impose practical limits. Resource
exhaustion produces an error and no partial evidence package.

## 11. Reproducing the examples

The example inputs and YAML are hand-maintained, synthetic, non-sensitive text
fixtures under `docs/examples/`. No generation script is needed. Their expected
stable outcomes are:

| Example | Status | Comparison differences | Assessment issues |
| --- | --- | ---: | ---: |
| automatic | `complete` | 1 | 0 |
| custom | `complete` | 1 | 0 |

Delete or choose new output directories, run the commands in Sections 4.1 and
5.11, and validate each generated `comparison-results.json` as shown in Section
8.5. Run IDs and completion times change on every run. Software and runtime
provenance can change between environments. Input digests change if the fixture
bytes are edited. The comparison outcome above remains the controlled check.
