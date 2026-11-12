# `adviso-compare` user guide

## Contents

- [1. Introduction](#1-introduction)
  - [1.1 Records, fields, and comparison rules](#11-records-fields-and-comparison-rules)
  - [1.2 Findings and run status](#12-findings-and-run-status)
- [2. Installation](#2-installation)
  - [2.1 Install with pip](#21-install-with-pip)
  - [2.2 Install with pipx](#22-install-with-pipx)
  - [2.3 Check the installation](#23-check-the-installation)
- [3. Quick start](#3-quick-start)
  - [3.1 Run your first comparison](#31-run-your-first-comparison)
  - [3.2 Read and interpret the results](#32-read-and-interpret-the-results)
- [4. Command and input reference](#4-command-and-input-reference)
  - [4.1 Command options and exit codes](#41-command-options-and-exit-codes)
  - [4.2 Input datasets](#42-input-datasets)
- [5. Custom comparison configurations](#5-custom-comparison-configurations)
  - [5.1 A small custom comparison](#51-a-small-custom-comparison)
  - [5.2 Runnable custom example with transformations](#52-runnable-custom-example-with-transformations)
  - [5.3 Configuration checks and conventions](#53-configuration-checks-and-conventions)
  - [5.4 Top-level properties](#54-top-level-properties)
  - [5.5 Field definitions](#55-field-definitions)
  - [5.6 Logical types](#56-logical-types)
  - [5.7 Null policy and typed value descriptions](#57-null-policy-and-typed-value-descriptions)
  - [5.8 Source normalisation](#58-source-normalisation)
  - [5.9 Value mapping](#59-value-mapping)
  - [5.10 Collections written as text](#510-collections-written-as-text)
  - [5.11 Typed normalisation](#511-typed-normalisation)
  - [5.12 Comparators](#512-comparators)
  - [5.13 Processing order](#513-processing-order)
- [6. The evidence package](#6-the-evidence-package)
- [7. JSON output reference](#7-json-output-reference)
  - [7.1 `comparison-configuration.json`](#71-comparison-configurationjson)
  - [7.2 `comparison-results.json`](#72-comparison-resultsjson)
  - [7.3 Structural and semantic validation](#73-structural-and-semantic-validation)
- [8. Errors and corrective action](#8-errors-and-corrective-action)
- [9. Security, governance, and limitations](#9-security-governance-and-limitations)
- [10. Reproducing the examples](#10-reproducing-the-examples)

## 1. Introduction

`adviso-compare` compares a reference dataset with a query dataset, such as the
output of a bioinformatics pipeline. A comparison configuration describes how
to pair records, associate fields, and translate values into a shared form.
The tool reports differences that remain after translation and problems that
prevented parts of the comparison.

The output is comparison evidence. Your laboratory decides how that evidence
contributes to its validation and quality processes; the tool does not make an
acceptance decision or establish ISO 15189 compliance.

### 1.1 Records, fields, and comparison rules

A dataset contains **records**, such as rows in a CSV file. Each record has
**fields**, such as a sample identifier or a measurement. The **reference**
is the dataset you compare against; the **query** is the dataset being checked.

A **record key** identifies corresponding records on the two sides. For
example, a sample identifier can pair a reference row with the query row for
the same sample. A key uses one field, or several fields together as a
**composite key**. Keys are unique within each dataset; record order does not
establish correspondence.

A configuration can associate differently named source fields with one
**canonical field**: a shared name used within the comparison. For example,
reference field `expected` and query field `observed` could both represent the
canonical field `measurement`. A **logical type**, such as decimal or date,
describes how to interpret a value. A **comparator** is the rule used to decide
whether two values match. The resulting shared representations are called
**canonical values**.

A **parser-native value** is the value and type read from the input before
configured transformations. CSV cells start as text; JSON can distinguish
text, numbers, booleans, and other value types. A scalar is a single value,
such as a string or number, rather than a collection of values.

A present field can contain **null**, an explicit no-value marker. An absent
field is missing entirely; an empty string is present text with no characters.

The **effective configuration** is the configuration used for a run. You can
supply a custom configuration, or let automatic mode generate one. Its
**scope** selects the fields to assess. Fields outside that scope are reported
as **exclusions** and are not compared.

### 1.2 Findings and run status

The report contains **findings**: individual differences or problems that
prevented assessment. Findings have two broad meanings:

- A **comparison difference** remains after the applicable translation and
  comparison rules have been applied.
- An **assessment issue** explains a problem applying those rules, such as a
  required field being absent or a value that cannot be interpreted as declared.

A run is **complete** when every applicable comparison was performed. It can
be complete and still report differences. A run is **incomplete** when some
intended value comparisons could not be performed. Both produce an **evidence
package**: a directory containing the results, configuration, and HTML report.
An execution error prevents a trustworthy result and produces no new package.

## 2. Installation

`adviso-compare` requires Python 3.10 or later. You can install it into an
existing virtual environment with `pip`, or use `pipx` to manage a dedicated
environment for the tool. Creating a new environment yourself is optional.

In the commands below, replace the example wheel path with the actual file
supplied to you, including its versioned filename.

### 2.1 Install with pip

Activate the virtual environment you want to use, then install the wheel and
its dependencies:

```console
python -m pip install /path/to/adviso_compare-VERSION-py3-none-any.whl
```

If you prefer a new environment, create and activate one before running that
installation command:

```console
python -m venv .venv
. .venv/bin/activate
```

On Windows Command Prompt, activate it with `.venv\Scripts\activate`; in
PowerShell, use `.venv\Scripts\Activate.ps1`.

### 2.2 Install with pipx

If you use [pipx](https://pipx.pypa.io/stable/), install the wheel with:

```console
pipx install /path/to/adviso_compare-VERSION-py3-none-any.whl
```

`pipx` creates and manages a separate virtual environment for `adviso-compare`
and makes the command available on your PATH. There is no need to activate
that environment to run the command.

### 2.3 Check the installation

Installation may use a package index to obtain dependencies. Once installed,
the comparison itself needs no network service. After either installation,
check that the command is available:

```console
adviso-compare --version
adviso-compare --help
```

The full guide is installed with the software under
`share/doc/adviso-compare/USER_GUIDE.md` in the Python environment.
For a `pipx` installation, this is the environment managed by `pipx`; `pipx list`
shows where it keeps application environments.

## 3. Quick start

The installed examples provide a first comparison without creating a
configuration yourself. Run the automatic example, then use its report to
explore the results. Section 5 shows how to supply your own configuration.

### 3.1 Run your first comparison

**Automatic strict-exact mode** is suitable when both datasets already use the
same field names and representations. It generates the comparison configuration
for you. To try it, omit `--configuration`.

#### 3.1.1 Runnable automatic example

Copy the `examples` directory installed next to this guide into a writable
working directory outside the Python environment. Keep its `automatic` and
`custom` subdirectories together, then change into the copied `examples`
directory. The commands below create evidence beside your copies of the inputs,
leaving the installed files unchanged.

From that copied directory, run:

```console
adviso-compare \
  --reference automatic/reference.csv \
  --query automatic/query.csv \
  --output automatic-evidence
```

The example has no `record_id`. `sample_id` is the only valid key candidate, so
it is discovered automatically. The run is complete and reports one changed
`lineage`. The query-only `pipeline_version` field appears in the exclusions.

The completion summary has this form, with a different run-directory name on
each invocation:

```text
Run status: complete
Comparison differences: 1
Assessment issues: 0
Evidence package: automatic-evidence/20261111T143205Z-123e4567-e89b-42d3-a456-426614174000
```

Run the same command again with `--output automatic-evidence` to add another
run directory while preserving the first. Section 6 shows the resulting layout.

Automatic mode is deliberately conservative. Use a custom configuration when
source field names differ, values require translation, a composite key is
needed, or automatic key selection is ambiguous.

#### 3.1.2 How automatic mode selects fields and keys

`adviso-compare` first finds field names shared by both datasets. It selects
the record key as follows:

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

The tool creates an effective configuration internally and saves it as
`comparison-configuration.json` alongside the results and report.

### 3.2 Read and interpret the results

Open `comparison-report.html` in the directory named by the completion
summary. Beside it are `comparison-results.json`, for software use and detailed
review, and `comparison-configuration.json`, the effective configuration.

Begin with run completeness, then review comparison differences, assessment
issues, and exclusions. The automatic example reports a complete run with one
comparison difference and no assessment issues. Its query-only
`pipeline_version` field was excluded, so it did not create a finding.

The report describes several aspects of the comparison:

#### 3.2.1 The reporting model

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

#### 3.2.2 Comparison phases

Every comparison performs three phases in order:

1. **Contract:** checks that configured fields can be found and translated as
   declared, including requiredness, null, type, validity, and mapping rules.
2. **Records:** pairs records using their keys and identifies
   missing and extra records.
3. **Values:** compares each assessable, in-scope, non-key field in aligned
   records.

A problem in an earlier phase does not automatically stop all later work. The
tool continues wherever the required information remains valid and
unambiguous. The phase attached to a finding records where the finding arose;
it is separate from the finding's classification.

#### 3.2.3 Findings, classifications, and codes

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

#### 3.2.4 Value-opportunity outcomes

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

#### 3.2.5 Run and phase status

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

#### 3.2.6 Exclusions and review priority

An exclusion records a field that was outside the comparison:

- `configured_field_excluded` means that the configuration describes the field
  but leaves it outside the selected scope;
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

#### 3.2.7 No acceptance verdict

The tool reports what it compared, what differed, and what it could not assess.
It does not decide whether the results are acceptable, whether a pipeline has
passed validation, or whether an ISO 15189 requirement has been met. Those
decisions belong to the laboratory's separately governed validation process.

## 4. Command and input reference

### 4.1 Command options and exit codes

The command has no subcommands:

```text
adviso-compare \
  --reference REFERENCE \
  --query QUERY \
  --output OUTPUT \
  [--configuration CONFIGURATION]
```

| Option | Meaning |
| --- | --- |
| `--reference REFERENCE` | Reference dataset. Required. |
| `--query QUERY` | Query dataset produced by the pipeline. Required. |
| `--output OUTPUT` | Parent directory under which to create a new run directory. Required. |
| `--configuration CONFIGURATION` | Custom YAML comparison configuration. If omitted, automatic strict-exact mode is used. |
| `--version` | Print the installed version and exit. |
| `--help` | Print concise help and exit. |

`--output` selects a parent directory. Each complete or incomplete run
creates its own directory there and preserves existing content. Section 6
explains directory names, permissions, and publication errors.

The command prints a short completion summary to standard output. An execution
error is printed to standard error. The exit codes are:

| Code | Meaning |
| ---: | --- |
| `0` | The run is complete. This includes complete runs that found differences. |
| `1` | The run is incomplete because at least one intended value comparison was not assessable. An evidence package is still written. |
| `2` | Expected operational error, such as an invalid option, configuration, input, key, resource condition, or output destination. No evidence package is written. |
| `3` | Unexpected internal error. No evidence package is written. |

Exit code `0` means the configured comparison completed. It does not indicate
acceptance of the query or its pipeline.

### 4.2 Input datasets

The reference and query can independently be CSV, TSV, or JSON. The
case-insensitive filename extension selects the format: `.csv`, `.tsv`, or
`.json`. There is no format override. Both files must be UTF-8.

#### 4.2.1 CSV and TSV

CSV uses commas; TSV uses tabs. Both use a double quote as the quote character.
A double quote inside a quoted cell is written twice. Quoted cells may contain
the delimiter or a line break. LF and CRLF line endings are accepted.

A header is required. Header names must be non-empty and unique. Every data row
must contain the same number of cells as the header. All cells initially count
as strings, including empty cells and text that looks like a number or boolean.

#### 4.2.2 JSON

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

#### 4.2.3 Empty datasets

`[]` is a valid zero-record JSON dataset. A header with no data rows is a valid
zero-record CSV or TSV dataset. A zero-byte file is not a valid dataset.

A custom configuration can compare empty datasets when it supplies the needed
field and key information. Automatic mode cannot select a key from two empty
JSON arrays because they expose no fields.

## 5. Custom comparison configurations

A custom configuration lets you choose the record key, associate different
source field names, and declare how values are interpreted and compared. It
is one UTF-8 YAML document. The `.yaml` or `.yml` suffix is recommended so that
its format is easy to recognise.

### 5.1 A small custom comparison

This example pairs samples whose identifier fields have different names and
compares their measurements as decimals. In a working directory of your
choice, save the following as `reference.csv`:

```csv
record_id,measurement
S1,1.00
S2,2.00
```

Save the query as `query.csv` in the same directory:

```csv
sample_id,result
S1,1
S2,2.10
```

Save this complete configuration as `configuration.yaml`:

```yaml
schema_version: "1.0"
metadata:
  id: "org.example.simple-comparison"
  revision: "1"
fields:
  record_key: ["sample"]
  in_scope: ["sample", "measurement"]
  definitions:
    sample:
      source_fields: {reference: "record_id", query: "sample_id"}
      required: {reference: true, query: true}
      logical_type: "string"
      null_policy: {allowed: false, nulls_equal: false}
      comparator: {name: "typed_exact"}
    measurement:
      source_fields: {reference: "measurement", query: "result"}
      required: {reference: true, query: true}
      logical_type: "decimal"
      null_policy: {allowed: false, nulls_equal: false}
      comparator: {name: "numeric_exact"}
```

`schema_version` identifies the configuration format. `metadata` gives this
configuration a stable ID and revision; it does not change comparison rules.
`fields` describes record identity, scope, and the values to compare.

The canonical field `sample` associates the two identifier names and provides
the record key. `measurement` associates the values to compare. Both fields
are required on both sides, and neither permits null: an explicit missing
value. An absent field is different from a present field containing null.
`typed_exact` compares the interpreted key strings; `numeric_exact` compares
exact decimal values. No tolerance or rounding is applied.

From that directory, run:

```console
adviso-compare \
  --reference reference.csv \
  --query query.csv \
  --configuration configuration.yaml \
  --output evidence
```

The run completes with one comparison difference and no assessment issues.
For `S1`, `1.00` and `1` represent the same decimal value. For `S2`, `2.00` and
`2.10` differ, producing one `value_mismatch` finding. The key identifies the
sample; it is not counted again as a measurement comparison.

### 5.2 Runnable custom example with transformations

For a richer example, use the writable copy of the `examples` directory from
Section 3.1.1. If you are starting here, copy the installed `examples` directory
to a working directory outside the Python environment first, then change into
that copy and run:

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

A stable ID and revision, review of changes, and testing with representative
data help your laboratory manage each configuration as a controlled document.
The evidence package retains the complete effective configuration as
`comparison-configuration.json`. Local quality arrangements remain the
authority for approval and retention.

### 5.3 Configuration checks and conventions

The file is checked before either dataset is read. YAML aliases, anchors,
merge keys, explicit tags, duplicate keys, and unsafe
object constructors are rejected, as are unknown properties. Quoting textual
values helps prevent YAML from interpreting them as numbers, dates, or
booleans. In particular, `schema_version` is a quoted string, and decimal
parameters use strings such as `"0.1"`. The examples use quotes to make
intended string values clear.

A JSON schema describes a document's permitted structure and values.
`comparison-configuration-v1.0.schema.json` defines the expected configuration
structure. After parsing the YAML, the tool checks it against this schema and
rejects configurations that do not conform.

The tool also checks relationships between settings: key and in-scope fields
have definitions; source field names are unique on each dataset side; mapping
sources are not repeated, conflicting, or unreachable; and operations and
comparators suit their field. It rejects custom configurations using the
reserved automatic-mode ID
`org.adviso.automatic-strict-exact`.

### 5.4 Top-level properties

| Property | Required | Meaning |
| --- | --- | --- |
| `schema_version` | Yes | Configuration format version; the supported version is `"1.0"`. |
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

### 5.5 Field definitions

Every entry in `fields.definitions` is an object with a canonical field name as
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

For each record-key field, the tool requires an entry in `definitions` and
`in_scope`, a scalar logical type, and `typed_exact` comparison. The field is
required and non-nullable on both sides. Key fields may use explicit source
normalisation or value mapping.

### 5.6 Logical types

For a scalar field, `logical_type` is `string`, `integer`, `decimal`, `boolean`,
`date`, or `datetime`. Parsing is strict. In particular, CSV and TSV cells
start as strings and are parsed only because a logical type was declared. Dates use
`YYYY-MM-DD`. Datetimes use RFC 3339 with an explicit timezone.

The tool accepts these source values for each declared type:

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
uses the declared logical type for parsing. Use `value_mapping` to describe
translations that type parsing does not provide.

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

### 5.7 Null policy and typed value descriptions

`null_policy.allowed` and `null_policy.nulls_equal` are required booleans. If
null is not allowed, `nulls_equal` must be false. JSON null is always recognised
as null. A missing field is different from a present field containing null.

Within a field's `null_policy`, optional `missing_tokens` may contain a
non-empty `reference` list, a non-empty `query` list, or both. Each item
describes a parser-native value to treat as null. For example, this fragment
belongs inside a field definition:

```yaml
null_policy:
  allowed: true
  nulls_equal: true
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

### 5.8 Source normalisation

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

### 5.9 Value mapping

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

A mapping destination may use `category: "null"` without a `value`. This converts
the mapped source value to null, after which the field’s `null_policy` is applied.
Mapping from null is not supported because an actual JSON null is recognised and
handled before value mapping.

Mapping happens after source normalisation and missing-token recognition, and
before parsing to the logical type.

### 5.10 Collections written as text

`collection_representation` may have `reference`, `query`, or both. An omitted
side defaults to `json_array` with no element processing.

Each side requires `format`:

- `json_array` means a JSON array value, or a CSV/TSV string containing valid
  JSON-array text. It must not have a `delimiter`.
- `delimited_text` means a parser-native string split on the required,
  non-empty `delimiter` string.

Optional `element_normalisation` is a non-empty ordered list of the text
operations in Section 5.8. Optional `element_mapping` is a non-empty closed
mapping whose `from` and `to` values must both be non-null. These act on each
element, not the collection as a whole. Collection fields cannot also use the
field-level `source_normalisation`, `value_mapping`, or `typed_normalisation`.

### 5.11 Typed normalisation

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

### 5.12 Comparators

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

`numeric_tolerance` requires exactly one entry inside `parameters`. For
example, this field-level comparator allows an absolute difference of up to
`0.1`:

```yaml
comparator:
  name: "numeric_tolerance"
  parameters:
    absolute_tolerance: "0.1"
```

With `absolute_tolerance`, values match when their absolute difference is no
greater than the tolerance. Use `relative_tolerance` in its place to match when:

```text
absolute difference <= relative tolerance × absolute reference value
```

The tolerance is a quoted, non-negative finite decimal. The boundary is
included. A relative tolerance around a zero reference allows only exact zero;
use an absolute tolerance when a non-zero difference around zero is intended.

The schema restricts the possible shape of comparators. The tool's further
checks ensure that a comparator suits the declared logical type and collection
kind.

### 5.13 Processing order

For a scalar field, processing follows this order:

1. distinguish absence from a present parser-native value;
2. apply side-specific source normalisation to strings;
3. recognise explicit null or configured missing tokens; for null, apply the
   null policy and skip mapping and type parsing;
4. for non-null values, apply the side-specific closed value mapping;
5. if mapping produces null, apply the null policy and skip type parsing;
6. otherwise parse the declared logical type;
7. apply typed normalisation where applicable; and
8. compare the canonical values under the configured null and comparison rules.

For a collection, whole-field missing-token and null handling happens before
the representation is decoded. Element normalisation, mapping, and typed
parsing then happen for each element before collection comparison.

## 6. The evidence package

Each complete or incomplete run publishes one new directory under `OUTPUT`.
For example, two successive runs can produce:

```text
OUTPUT/
├── 20261111T143205Z-123e4567-e89b-42d3-a456-426614174000/
│   ├── comparison-results.json
│   ├── comparison-configuration.json
│   └── comparison-report.html
└── 20261111T145810Z-123e4567-e89b-42d3-a456-426614174001/
    ├── comparison-results.json
    ├── comparison-configuration.json
    └── comparison-report.html
```

Each run directory contains exactly these three regular evidence files.
Packages are validated and generated in private staging on the destination
filesystem before publication. The destination must support exclusive
directory rename;
if safe publication is unavailable, the run returns `output.write_failed`
and preserves existing content.

The output parent may already exist and contain any files or directories.
Existing contents and permissions are preserved. If the parent does not exist,
the tool creates it privately; its enclosing directory must already exist.
The selected parent cannot be a symbolic link, regular file, or special
filesystem object. Symbolic links in ancestor directories are permitted.

Each complete or incomplete run publishes a new immediate child named
`YYYYMMDDTHHMMSSZ-<run-id>`. The timestamp and full UUID come directly from that
result's UTC `run.completed_at` and `run.id`. Two runs can share a timestamp
without sharing a directory. An occupied run-directory path is an error;
the tool never replaces it or chooses a different name for that run.

On error, no new evidence package is published and existing parent contents
remain intact. A parent created during publication preparation may remain
empty. Input and configuration errors do not create it. Private temporary
staging is cleaned up after success and, where safe, after an error.

The completion summary's `Evidence package:` line identifies the published
child. With a relative `--output`, it shows the relative parent and child.
With an absolute `--output`, it shows only the parent basename and child; for
a filesystem-root parent it shows only the child name. Absolute paths are not
printed. For automation, retain the selected parent path and use the reported
child name to locate that run. The reported directory identifies this run
reliably; concurrent runs may finish in a different order from when they started.

Retention and disposal of accumulated evidence remain the laboratory's
responsibility; the tool does not remove earlier runs or maintain a `latest`
pointer.

`comparison-results.json` is the canonical result for software use and detailed
review. `comparison-configuration.json` retains the complete effective
configuration: the selected custom document or the generated automatic
document, including metadata and explicit declarations. Omitted optional
properties remain absent; internal defaults are not added. List order is
preserved. The saved file is JSON, rather than a copy of the source YAML bytes;
`--configuration` continues to accept only custom YAML.

Both JSON files use UTF-8 without a byte-order mark, two-space indentation, LF
line endings, and exactly one final newline. Non-ASCII text is emitted directly
unless JSON escaping is needed. Fixed properties follow their schema order;
dynamic names use Unicode code-point order. Identical effective configurations
produce identical saved bytes, without run identifiers or timestamps.

Keep the three files together. The results link to the saved configuration by
its exact-byte SHA-256 digest, as explained in Section 7.2.2.
`comparison-report.html` is a self-contained, offline view made solely from the
validated results and saved configuration, with verified linkage. It adds fixed
explanatory text and external review space, but no comparison facts. Rendering
does not reread the original YAML. The report opens in an ordinary browser,
works offline, and does not require scripting.

The report separates run completeness, comparison differences, and assessment
issues. It does not apply acceptance thresholds or give a pass/fail verdict.

## 7. JSON output reference

The evidence package contains two JSON documents with different purposes:

| File | Contents |
| --- | --- |
| `comparison-configuration.json` | The effective configuration: its identity, field definitions, scope, and comparison rules. |
| `comparison-results.json` | The run's findings, counts, statuses, input provenance, and digest link to the configuration. |

The subsections below describe the fields in each document. Section 7.3
explains how to validate them together.

### 7.1 `comparison-configuration.json`

This is the complete effective configuration selected or generated for the
run, saved as JSON. Its schema is
`comparison-configuration-v1.0.schema.json`, identified by its own root
`schema_version` value `"1.0"`.

The three root properties are `schema_version`, `metadata`, and `fields`.
All are required. Their fields are:

| Property | Meaning |
| --- | --- |
| `schema_version` | Configuration document format, currently `"1.0"`. |
| `metadata.id` | Stable identifier of the configuration. |
| `metadata.revision` | Revision assigned by its owner, or by the tool for automatic mode. |
| `metadata.title` | Optional human-readable title. |
| `metadata.description` | Optional human-readable description. |
| `fields.record_key` | Ordered canonical field names identifying records. |
| `fields.in_scope` | Canonical fields selected for assessment, including the key fields. |
| `fields.definitions` | Definitions indexed by canonical field name. Each definition associates source names and supplies the field's requiredness, null policy, comparison rule, and any declared type or transformations. |

Sections 5.4–5.13 describe the permitted configuration properties, values,
constraints, and interactions; the [field-definition reference](#55-field-definitions)
lists the settings within each `fields.definitions` entry. The same structure
applies to a parsed custom YAML configuration and to this saved JSON document. Metadata does not change
the comparison rules.

The saved configuration preserves explicit declarations and list order.
Optional properties that were omitted remain absent; internal defaults are
not added. In automatic mode, `metadata.id` is
`org.adviso.automatic-strict-exact` and `metadata.revision` is `"1.0"`. This
revision identifies the generated configuration, separately from its schema
version.

The saved document contains no run ID or completion timestamp. Its identity
and revision are read here rather than duplicated in the results. Results link
to its exact saved bytes through `comparison_configuration_digest`.

### 7.2 `comparison-results.json`

This document describes the comparison outcome. Its schema is
`comparison-results-v1.0.schema.json`, identified by its root `schema_version`
value `"1.0"`. For automation, use structured properties, classifications,
and finding codes; the English `message` text is intended for human readers.

The required root properties are:

| Property | Meaning |
| --- | --- |
| `schema_version` | Results document format. |
| `run` | Run identity, status, and completion time. |
| `phases` | Completion status of each comparison phase. |
| `software` | Software identity and version used for the run. |
| `runtime` | Python, platform, and Unicode-data provenance. |
| `inputs` | Basenames, formats, sizes, and exact-byte input digests. |
| `record_key_fields` | Ordered reference, query, and canonical key-field names. |
| `comparison_configuration_digest` | SHA-256 link to the saved configuration bytes. |
| `summary` | Record, value-opportunity, and finding counts. |
| `exclusions` | Fields outside the comparison scope. |
| `findings` | Individual comparison differences and assessment issues. |

Empty `exclusions` and `findings` arrays remain present. Unknown properties
are rejected at the defined object levels.

#### 7.2.1 Run and provenance

| Property | Meaning |
| --- | --- |
| `schema_version` | Must be `"1.0"`, identifying the results format. |
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

#### 7.2.2 Record keys and configuration digest

`record_key_fields.reference`, `.query`, and `.canonical` are ordered,
non-empty arrays of unique field names. Their common order is the component
order of a composite key.

The required top-level `comparison_configuration_digest` has exactly two
properties:

| Property | Meaning |
| --- | --- |
| `algorithm` | Always `sha256`. |
| `value` | Lowercase 64-character SHA-256 digest of the exact saved `comparison-configuration.json` bytes, including the final newline. |

Verify this digest against the file bytes before parsing or reserializing the
configuration. It is not a digest of the custom source YAML. Even a whitespace
edit to the saved JSON changes its digest. The digest establishes content
linkage; it does not prove authenticity or laboratory approval.

The configuration's schema version, ID, and revision are held in the saved
document's `schema_version`, `metadata.id`, and `metadata.revision`. They are
not duplicated in the results. The sibling filename is fixed; no configuration
path, URI, or alternative filename is selected by the results document.

#### 7.2.3 Summary and exclusions

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

#### 7.2.4 Finding properties

Every finding has `id`, `classification`, `code`, `phase`, `message`, and
`affected_side`.

- `id` is a report-local sequence such as `F000001`.
- `classification` is `comparison_difference` or `assessment_issue`.
- `code` is one of the eight codes in Section 3.2.3.
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

### 7.3 Structural and semantic validation

The supported combination is results schema `1.0` with configuration schema
`1.0`. These formats are independently versioned.

A JSON schema describes a document's permitted structure and values. The two
schemas are installed as resources in the `adviso_compare.schemas` Python
package.

Select a schema using the document family and its root `schema_version`.
The fixed filenames distinguish the document families; the bare version string
does not identify a schema globally. Their canonical `$id` values identify
distinct schemas. Select supported schemas from trusted installed resources,
without downloading schemas or constructing arbitrary paths from document values.

The software version and the two schema versions have separate lifecycles.
Supporting a compatible configuration format need not change the results
schema; features that change results structure or meaning can require a results
schema revision. Software must support the selected combination, rather than
assuming that the two version strings must match.

Validation has three layers:

| Layer | What it establishes |
| --- | --- |
| Independent structural validation | Each JSON document conforms to its own supported schema, including required properties, permitted values, finding forms, and recognised formats. The results schema neither loads the configuration schema nor constrains its version. |
| Exact-byte linkage | The required configuration sibling exists and its saved bytes match `comparison_configuration_digest`. |
| Semantic validation | The configuration rules, result counts, statuses, findings, and configuration-derived facts agree, using source comparison context where available. |

A results-schema check alone is not full package validation. A valid digest
also does not establish that the configuration or comparison is semantically
valid. To inspect a saved package, use the Python interpreter from the
environment where `adviso-compare` is installed:

- For installation with `pip`, activate the environment used in Section 2.1.
  Its `python` command can import the installed package.
- For the `pipx` installation in Section 2.2, run `pipx list` and find the
  directory shown after `venvs are in`. The tool's environment is the
  `adviso-compare` directory within it. The interpreter paths are:

  | Platform | Python interpreter |
  | --- | --- |
  | macOS or Linux | `<venvs directory>/adviso-compare/bin/python` |
  | Windows | `<venvs directory>\adviso-compare\Scripts\python.exe` |

  Replace `<venvs directory>` with the reported path. When starting an
  interpreter whose path contains spaces, quote its full path; in PowerShell,
  precede a quoted executable path with `&`.

Change into the published run directory, start that Python interpreter, and
paste the following code at its prompt. `Path(".")` selects the current run
directory:

```python
from pathlib import Path

from adviso_compare.reporting import validate_evidence_package

validate_evidence_package(Path("."))
print("Package checks passed for the saved evidence.")
```

The function returns normally on success and raises `ResultValidationError`
if the JSON evidence cannot be read or validated, or the package members are
invalid. It requires exactly the three fixed regular files. Its JSON
validation procedure is:

1. Parse results as strict UTF-8 JSON, rejecting duplicate object members,
   non-standard number constants, and non-finite numbers. Select the supported
   results schema by document family and root `schema_version`, and validate
   with format assertion enabled.
2. Require the fixed sibling `comparison-configuration.json` to be a readable
   regular file, rejecting missing files, symbolic links, and other filesystem
   objects. Read its exact bytes without following an alternative filename.
3. Compare SHA-256 of those bytes, including the final newline, with the
   result's `comparison_configuration_digest` before using the contents.
4. Parse the configuration with the same strict JSON rules and independently
   select and validate its schema using its own `schema_version`.
5. Check that the software supports the two schema versions together, then
   validate configuration semantics. Saved automatic configurations are valid
   evidence; the reserved-ID restriction still applies to custom YAML inputs.
6. Apply result and cross-document semantic checks using the saved
   configuration and any available comparison context.

Both structural validators use JSON Schema Draft 2020-12 format assertion.
If you implement these checks independently, enable equivalent format checking
(for example, `Draft202012Validator(schema, format_checker=FormatChecker())`
with Python's `jsonschema` package). With format checking enabled, the
validator rejects invalid recognised UUID, date, and date-time formats. Schemas are loaded from trusted local
package resources; no network access or schema registry linking the two
formats is needed.

Semantic checks available from the saved documents include:

- overall status agrees with phase statuses;
- record equations, value-opportunity counts, and finding totals reconcile;
- key field-name and identity arrays have the required lengths and order;
- findings and exclusions have the required order and no duplicates;
- finding IDs are sequential after sorting; and
- key declarations, finding field identities, review priorities, and
  configured-field exclusions agree with the saved configuration.

Before publication, `adviso-compare` additionally has the parsed input datasets
and comparison-phase results. It checks that the saved configuration agrees
with the selected effective configuration, input provenance matches the parsed
inputs, findings and summaries match the phase results, and undeclared-field
exclusions match observed source fields. Inspection of a saved package alone
cannot repeat those source-dependent checks or prove that the comparison was
performed correctly. Independent reproduction requires the original input
bytes and suitable comparison context. The snippet checks the saved JSON
pair and package membership; it does not regenerate or authenticate the HTML
report.

The normative details are in [Specification Section 9.1.4](SPECIFICATION.md#914-structural-and-semantic-package-validation).

## 8. Errors and corrective action

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
| `output.invalid_destination` | Select a regular parent with an existing enclosing directory. Check whether the run-directory path is occupied; existing content is never replaced. |
| `output.write_failed` | Check parent-directory permissions, available storage, and filesystem support for exclusive directory rename. |
| `internal.unexpected` | Rerun once; if it persists, report the software version and safe reproduction details. Use synthetic examples when sharing reproduction details. |

An assessment issue inside an otherwise readable and alignable dataset is a
finding, not an execution error. Review the evidence package for those issues.

## 9. Security, governance, and limitations

The tool operates locally and does not transmit inputs, configurations, or
results. The evidence package can contain sensitive laboratory or patient
information, including record identifiers, values needed to explain findings,
and input basenames. Store it with permissions, retention, backup, and disposal
controls suitable for the source data. The laboratory remains responsible for
appropriate pseudonymisation.

On POSIX systems, newly created output parents and run directories have
owner-only permissions (`0700`), and evidence files use `0600`. Existing
parent permissions are retained. On other systems, apply the corresponding
filesystem access controls under laboratory policy.

Routine terminal output and error diagnostics do not reproduce record
identifiers or source values. The tool does not provide de-identification,
identifier hashing, access control, encryption, or sensitivity policies.

`adviso-compare` compares one complete reference dataset with one complete query
dataset. It does not download data, run a bioinformatics pipeline, subset a
validation dataset, apply acceptance thresholds, decide fitness for purpose,
or produce a complete ISO 15189 validation dossier. It supports the evidence
review that forms part of a wider, governed validation process.

There is no fixed input-size or record-count limit. Available memory,
storage, and operating-system resources still impose practical limits. Resource
exhaustion produces an error and no partial evidence package.

## 10. Reproducing the examples

The examples use synthetic, non-sensitive data. Section 5.1 provides complete
file contents to save yourself. The other example inputs and YAML are
hand-maintained fixtures under `docs/examples/`, installed next to this guide.
No generation script is needed. Their expected stable outcomes are:

| Example | Status | Comparison differences | Assessment issues |
| --- | --- | ---: | ---: |
| automatic (Section 3.1.1) | `complete` | 1 | 0 |
| small custom (Section 5.1) | `complete` | 1 | 0 |
| custom with transformations (Section 5.2) | `complete` | 1 | 0 |

Run the commands in Sections 3.1.1, 5.1, and 5.2, then open the run directory
identified by each completion summary and validate the complete package
as shown in Section 7.3. The same output parents can be reused: each invocation
adds a new run directory. Run IDs and completion times change on every run.
Software and runtime provenance can change between environments. Input digests
change if the fixture bytes are edited. The comparison outcome above remains
the controlled check.
