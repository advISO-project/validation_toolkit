# AdvISO Validation Toolkit: `compare` Behaviour Specification

**Document status:** Draft for review  
**Specification version:** 0.1.0-draft  
**Applies to:** The `compare` command and its supporting comparison engine  
**Normative language:** The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** indicate requirement strength.

## 1. Purpose

This document defines a specification for the AdvISO Validation Toolkit: a command-line namespace for cohesive capabilities that support bioinformatics validation and verification activities associated with ISO 15189 accreditation.

The initial sole user-facing subcommand within the toolkit is `compare`. This subcommand compares a reference dataset with a query dataset according to an explicit comparison specification and produces deterministic, machine-readable findings and a human-readable summary suitable for review and retention as one component of a bioinformatics pipeline validation or verification record. It is intended to answer this question:

> Given these identified inputs and these declared comparison rules, which expected and observed records and values are equivalent, different, missing, extra, or not assessable?

Given this narrow and precisely defined scope, the toolkit cannot be used _alone_ to assert that:

- a pipeline is clinically or analytically valid
- a pipeline conforms with ISO 15189 or any other standard
- a pipeline is fit for an unspecified intended use
- a reference or query dataset is intrinsically correct

Responsibility for the provenance and suitability of reference material, the comparison rules, acceptance criteria, review, approval, and resulting validation decision remains with the laboratory.

## 2. Product structure and scope

### 2.1 Product structure

The organisation of the toolkit within the AdvISO GitHub organisation is:

```text
adviso-project
└── validation_toolkit
    ├── compare subcommand
    └── internal comparison, specification, provenance, findings, and reporting components
```

The **AdvISO Validation Toolkit** is the user-facing product and a minimal command namespace. **`compare`** is currently the sole specified subcommand. The other components, including the **comparison engine**, are internal reusable software components and are not separate products.

The initial command-line form SHOULD be:

```text
adviso-validation compare ...
```

The distribution, import-package, executable, and repository names MAY differ where required by their respective naming conventions, but each MUST identify its relationship to AdvISO clearly. Final distribution and executable names MUST be settled before the first stable release and thereafter follow a documented compatibility policy.

Additional commands are not a development objective for the first release and MUST NOT be added speculatively. A future command MAY be introduced only for a demonstrated, materially distinct operation in the same validation-evidence workflow. The top-level dispatcher MUST remain thin and MUST NOT create speculative shared abstractions. The initial implementation SHOULD use ordinary modules and a small comparator registry, not a general plugin framework. Capabilities with materially different purposes, dependencies, governance, or release lifecycles SHOULD be separate AdvISO packages.

### 2.2 Scope of the `compare` subcommand

The first-release scope of `compare` is:

- comparison of structured records represented in CSV, TSV or JSON;
- explicit single-field or composite record keys;
- detection of matching, differing, missing, and extra records and fields;
- field-specific comparison rules;
- controlled column-name and value mappings;
- explicit treatment of types, nulls, and missing values;
- complete discrepancy collection rather than stopping at the first difference;
- structured JSON results, human-readable reports, and automation-friendly exit codes;
- provenance sufficient to reproduce and review a comparison;
- safe handling of data that may contain sensitive clinical information.

### 2.3 Initially out of scope

Unless introduced by a separately specified extension, the `compare` command does not:

- establish analytical sensitivity, analytical specificity, precision, limit of detection, reportable range, clinical validity, or clinical utility;
- generate or adjudicate truth data;
- determine whether a reference dataset is representative or fit for purpose;
- replace laboratory review or approval;
- compare unstructured prose, images, binary files, or specialist bioinformatics formats (e.g. SAM, VCF, FASTQ);
- infer biological equivalence of variants, transcripts, genomic intervals, taxonomic calls, or other domain objects;
- provide an electronic-signature or laboratory document-management system.

No bioinformatics-specific or domain-aware comparator is required for the first release. Such comparators MAY be added later under explicit, independently versioned specifications.

## 3. Design principles

The following principles govern all requirements:

1. **Explicit over inferred:** Comparison behaviour MUST be declared, not guessed from observed data.
2. **No silent data loss:** Input records, duplicate keys, unmapped values, and unsupported structures MUST NOT be silently discarded or overwritten.
3. **Symmetry:** Missing and extra content MUST be assessed in both directions.
4. **Separation of concerns:** Execution success and comparison outcome are distinct concepts.
5. **Complete evidence:** A normal comparison mismatch MUST still produce a complete report.
6. **Determinism:** Identical inputs, configuration, and tool version MUST produce semantically identical results.
7. **Traceability:** Findings MUST identify the rule, record, and field that produced them.
8. **Privacy by design:** Reports MUST include only the sensitive data necessary for their intended purpose.
9. **Fail clearly:** Invalid or ambiguous input MUST produce an explicit error rather than an assumed interpretation.
10. **Testability:** Each normative requirement SHOULD be traceable to one or more automated tests.

## 4. Terminology

- **Reference dataset:** The dataset containing the approved expected or comparator records. “Reference” does not imply intrinsic truth.
- **Query dataset:** The dataset being evaluated against the reference.
- **Comparison specification:** The versioned configuration declaring the data contract, normalisation, comparison, and acceptance rules.
- **Comparison scope:** The final cumulative comparison phase requested: `contract`, `records`, or `full`.
- **Not assessed:** Deliberately outside the selected scope or excluded by an explicit field policy.
- **Not assessable:** Inside the selected scope, but unable to be compared safely because a prerequisite was not satisfied.
- **Contract comparison:** Assessment of whether inputs satisfy the declared data contract, including fields, logical types, key definitions, nullability, mappings, and configured constraints.
- **Records comparison:** Alignment and assessment of valid record identities, including matching, missing, and extra records. Invalid, missing, null, or duplicate record keys are execution errors rather than record-comparison findings.
- **Value comparison:** Application of declared comparators to values in records that can be aligned meaningfully.
- **Record:** One logical unit of comparison.
- **Record key:** One field or an ordered combination of fields that uniquely identifies a record within a dataset.
- **Field:** A named value within a record.
- **Finding:** A structured observation generated by applying one comparison rule to a record, field, dataset, or run.
- **Execution status:** Whether the requested toolkit command completed correctly.
- **Comparison outcome:** The result of applying configured acceptance criteria: `pass`, `fail`, or `inconclusive`.
- **Laboratory decision:** The externally reviewed conclusion about validation or verification. The toolkit does not make this decision.
- **Missing:** Expected in the reference but absent from the query.
- **Extra:** Present in the query but absent from the reference.
- **Null:** A present field with an explicitly empty/no-value representation defined by the input format or specification.
- **Absent:** A field or record that is not present at all.
- **Normalisation:** A declared, non-lossy or intentionally controlled transformation performed before comparison.
- **Mapping:** A declared translation of field names or values from one representation to another.

## 5. Inputs

### 5.1 Required inputs

A comparison run MUST receive:

- one reference dataset;
- one query dataset;
- an output destination.

A custom comparison specification MAY be supplied. If it is omitted, the bundled strict-exact specification defined in Section 6.9 MUST be used.

### 5.2 Supported formats

The initial implementation MUST support:

- CSV conforming to the configured dialect;
- TSV conforming to the configured dialect;
- JSON using a documented record-oriented structure.

The reference and query formats MAY be selected independently through explicit command-line options. If a format is not supplied, it MAY be detected only from a recognised, unambiguous extension: `.csv`, `.tsv` or `.json`. In either case:

- detected format MUST be recorded;
- ambiguous or unsupported content MUST fail validation;
- an unknown or ambiguous extension, including `.txt`, MUST require an explicit format;
- content MUST be validated against the selected format.

### 5.3 Character encoding and text handling

- UTF-8 MUST be the default and documented encoding.
- Alternative encodings MAY be configured explicitly.
- Invalid byte sequences MUST cause an input error unless an explicit replacement policy is configured and recorded.
- Field names and string values MUST be preserved exactly before declared normalisation.
- Line endings MUST NOT affect comparison results.

### 5.4 Tabular parsing

For CSV and TSV:

- a header row MUST be required;
- duplicate or empty column names MUST be rejected;
- delimiters, quoting, escaping, and embedded newlines MUST be handled by a standards-compliant parser;
- rows with too many or too few columns MUST be input errors;
- all physical input rows MUST be accounted for;
- source row numbers SHOULD be retained for traceability;
- input values MUST initially remain strings unless a custom specification declares a null representation or type conversion; in the bundled strict-exact specification, an empty cell is an empty string.

### 5.5 JSON parsing

- JSON inputs MUST use a schema-validated list of record objects:

```json
[
  {"sample_id": "S1", "gene": "BRAF", "result": "detected"},
  {"sample_id": "S2", "gene": "KRAS", "result": "not_detected"}
]
```

- Values such as `yes`, `no`, `on`, `off`, uppercase boolean-like values, and timestamp-like strings MUST remain strings unless a custom specification explicitly maps or parses them.
- JSON numerical tokens that may be used as decimals MUST be loaded without an intermediate binary floating-point conversion, and their source lexical representations MUST remain available.
- Root scalars, heterogeneous root structures, and records that are not objects MUST be rejected with actionable errors.

### 5.6 Preserved parser-native values

- For `preserved_exact` comparison, parsers MUST expose a common, deterministic set of parser-native value categories: `string`, `integer`, `decimal`, `boolean`, `null`, `array`, and `object`;
- CSV and TSV cells MUST be strings, including empty strings, unless a custom specification declares further processing;
- JSON numbers without a fractional or exponent component MUST be integers, while other finite JSON numbers MUST be exact decimals;
- JSON arrays MUST be arrays, and JSON mappings used as field values MUST be objects; and
- Values are equal only when they have the same parser-native category and recursively equal content. For array-valued fields, element order is significant under `preserved_exact`; for object-valued fields, member names and values must match but member order is not significant. Top-level records are aligned by their declared record keys, and their input order does not affect comparison.
- Numerical values MUST be retained exactly as they appeared in the input for reporting and traceability. However, two values in the same numerical category compare as equal when they represent the same number; for example, decimal `1.0` and decimal `1.00` are equal.
- `NaN`, positive infinity, and negative infinity are not valid numerical values. In an attributable non-key field, they MUST produce a contract finding and make that value `not_assessable`; other assessable content MUST still be compared. If such a value occurs in a record key or prevents construction of an unambiguous record model, it MUST produce an execution error.

### 5.7 Empty inputs

- Empty files and datasets with zero records MUST be recognised explicitly.
- A custom comparison specification MUST state whether a comparison in which both datasets contain no records is acceptable. It MAY accept two empty datasets as having no missing or extra records, or require a minimum number of records.
- A non-empty reference and empty query MUST report every expected record as missing.
- An empty reference and non-empty query MUST report every observed record as extra.

## 6. Comparison specifications

### 6.1 General requirements

Every comparison uses an effective comparison specification. A custom specification MUST:

- use a published, independently versioned specification schema supported by the installed toolkit release;
- declare its schema version and a stable specification identifier and revision;
- be validated fully before either dataset is compared;
- reject unknown configuration keys by default;
- provide actionable validation errors with configuration locations;
- be identified in provenance by a cryptographic digest;
- be retained or embedded in the evidence package, subject to policy.

A valid specification MUST declare at least:

- record key fields;
- field definitions or an explicit policy for undeclared fields;
- comparison rules;
- missing and extra record policy;
- missing and extra field policy;
- duplicate-key policy;
- phase-specific acceptance criteria.

### 6.2 Custom comparison-specification YAML format

Custom comparison specifications MUST be YAML documents conforming to the format defined in this section. YAML is used only for the comparison specification; it is not a supported dataset format. A specification file SHOULD use the `.yaml` extension; `.yml` MAY also be accepted.

#### 6.2.1 YAML parsing and validation

- The document MUST be UTF-8 encoded and contain exactly one YAML mapping at its root.
- YAML 1.2 scalar resolution MUST be used with a safe loader.
- Duplicate mapping keys, merge keys, aliases, anchors, explicit tags, and executable or implementation-specific object constructors MUST be rejected.
- Unknown keys MUST be rejected unless a future schema version explicitly defines an extension mechanism.
- Required keys MUST NOT be supplied as YAML null values.
- `schema_version`, `id`, `revision`, criterion identifiers, exception identifiers, field names, operation names, comparator names, enumerated values, decimal lexical values, dates, and datetimes SHOULD be quoted to prevent unintended YAML scalar conversion.
- The complete document MUST be validated against the published schema identified by `schema_version` before either dataset is read.
- Validation errors MUST identify the YAML path and the violated requirement.

#### 6.2.2 Complete structural template

The following template defines the complete first-release structure. Keys marked “optional” in comments MAY be omitted; other displayed keys are required when their parent construct is used, except where a conditional omission is explicitly permitted below. Empty lists are valid only where stated below.

```yaml
schema_version: "1.0"

specification:
  id: "org.example.pipeline-output-comparison"
  revision: "1.0.0"
  title: "Example pipeline-output comparison"       # optional
  description: "Approved comparison rules"          # optional

records:
  keys:
    - "record_id"
  policies:
    duplicate_keys: "error"
    missing_records: "finding"
    extra_records: "finding"
    empty_datasets: "accept"

fields:
  include: "all"
  undeclared: "fail"
  policies:
    missing_fields: "finding"
    extra_fields: "finding"
  definitions:
    record_id:
      source:
        reference: "sample_id"
        query: "specimen_id"
      required:
        reference: true
        query: true
      logical_type: "string"
      null:
        allowed: false
        nulls_equal: false
        missing_tokens:
          reference: []
          query: []
      source_normalisation: []
      value_mapping:
        reference: []
        query: []
      typed_normalisation: []
      comparator:
        name: "typed_exact"
        parameters: {}
      unit: "laboratory-defined-unit"                # optional
      sensitivity: "identifier"                     # optional label
      finding_severity: "error"                     # optional

acceptance:
  contract:
    - id: "no-contract-findings"
      metric: "contract_finding_count"
      operator: "equal"
      threshold: 0
  records:
    - id: "no-missing-records"
      metric: "missing_record_count"
      operator: "equal"
      threshold: 0
    - id: "no-extra-records"
      metric: "extra_record_count"
      operator: "equal"
      threshold: 0
  values:
    - id: "no-value-mismatches"
      metric: "value_mismatch_count"
      operator: "equal"
      threshold: 0

exceptions: []

reporting:
  finding_limit: 10000                              # optional
  excluded_field_detail: "summary"
```

The template is illustrative rather than an instruction to use these particular rules. In particular, laboratories MUST choose identifiers, field definitions, policies, criteria, thresholds, exceptions, and reporting limits appropriate to the intended comparison. The published machine-readable schema MUST encode the same structure and constraints as this section; where the schema and this document disagree, the normative behaviour specification MUST be corrected before release rather than silently choosing one interpretation.

#### 6.2.3 Top-level keys and identity

The only permitted top-level keys are `schema_version`, `specification`, `records`, `fields`, `acceptance`, `exceptions`, and `reporting`.

- `schema_version` MUST be a quoted string identifying a supported comparison-specification schema version.
- `specification.id` MUST be a stable, non-empty identifier. It SHOULD use a collision-resistant organisational namespace.
- `specification.revision` MUST be a non-empty revision string controlled by the specification owner. Any behaviourally material change MUST produce a new revision.
- `specification.title` and `specification.description` are optional human-readable strings and MUST NOT alter comparison behaviour.

#### 6.2.4 Record configuration

- `records.keys` MUST be a non-empty ordered list of canonical field names present in `fields.definitions`. List order defines composite-key order.
- Every key field MUST be required on both sides, non-nullable, and declared with a scalar logical type. A key field MAY use explicitly declared source normalisation or value mapping, but MUST use `typed_exact` after transformation.
- `records.policies.duplicate_keys` MUST be `error`; `missing_records` and `extra_records` MUST be `finding`. These values are explicit even though no alternative is supported in the first release.
- `records.policies.empty_datasets` MUST be `accept` or `reject`. `accept` means that two syntactically valid zero-record datasets satisfy the records-phase empty-dataset rule; it does not waive independently assessable contract requirements. `reject` creates a records-phase finding and is itself a conclusive records-phase acceptance failure when both datasets contain zero records. This generated criterion and its result MUST be included in the report.

#### 6.2.5 Field selection, declaration, and source names

- `fields.include` MUST be either the string `all` or a non-empty list of canonical field names. Key fields are always included whether or not they appear in the list.
- `fields.undeclared` MUST be one of `compare`, `ignore`, `warn`, or `fail`.
  - `compare` compares shared undeclared fields with `preserved_exact`; an undeclared field present on only one side follows the missing/extra-field policy.
  - `ignore` excludes undeclared fields and records the exclusion as `not_assessed`.
  - `warn` behaves as `ignore` and additionally emits a structured warning.
  - `fail` creates a contract finding for every undeclared field.
- `fields.policies.missing_fields` and `extra_fields` MUST be `finding`. Required missing fields and unexpected extra fields are therefore reported; acceptance criteria determine their effect on the outcome.
- `fields.definitions` MUST be a mapping keyed by unique canonical field name and MUST contain a definition for every field referenced by `records.keys`. Definitions for non-key fields MAY be omitted only to the extent permitted by `fields.undeclared`.
- `source.reference` and `source.query` MUST each contain the source field name used on that side. Omitting either source name is permitted only for a field that is not required on that side.
- `required.reference` and `required.query` MUST be booleans. Absence of a required field creates a contract finding; absence of an optional field does not.
- `sensitivity`, when present, is a stable non-empty classification label interpreted by the selected reporting/privacy policy. It does not itself define redaction behaviour.
- `finding_severity`, when present, MUST be `info`, `warning`, or `error`. Severity is report metadata and MUST NOT determine the comparison outcome unless referenced by an explicit acceptance criterion.
- `unit`, when present, MUST be a non-empty string. It records the declared unit but does not request automatic unit conversion.

#### 6.2.6 Logical types and null policy

For a scalar field, `logical_type` MUST be one of `string`, `integer`, `decimal`, `boolean`, `date`, or `datetime`. It MAY be omitted only when the comparator is `preserved_exact` and no typed parsing, mapping, or typed normalisation is configured.

For a collection field, `logical_type` MUST use this form:

```yaml
logical_type:
  name: "list"                 # list, set, or multiset
  element_type: "string"       # scalar logical type
  element_comparator:
    name: "typed_exact"
    parameters: {}
```

Nested collection types MUST be rejected. The comparator named for the field itself MUST correspond to the collection kind: `list_exact`, `set_exact`, or `multiset_exact`.

Every declared field MUST contain a `null` mapping:

- `allowed` and `nulls_equal` MUST be booleans.
- `nulls_equal` MUST be `false` when `allowed` is `false`.
- `missing_tokens.reference` and `missing_tokens.query` MUST each be a list of source-value descriptors. A matched token is converted to null at processing step 3 in Section 6.8.
- An empty list declares that there are no textual missing tokens on that side. Parser-native JSON null remains null independently of this list.

A source-value descriptor has one of these forms:

```yaml
category: "string"
value: "NA"
```

```yaml
category: "decimal"
value: "1.00"
```

```yaml
category: "null"
```

`category` MUST be `string`, `integer`, `decimal`, `boolean`, or `null`. `value` MUST be present for every category except `null`; it MUST be a quoted lexical string for `string`, `integer`, and `decimal`, and `true` or `false` for `boolean`. The lexical value MUST be valid for its stated category. Descriptors are matched using parser-native category and value equality under Section 5.6; the retained lexical form remains evidence but does not create a distinct numerical value. This explicit representation prevents YAML scalar resolution from changing mapping keys or missing tokens.

#### 6.2.7 Normalisation and value mapping

`source_normalisation` and `typed_normalisation` MUST be ordered lists. Each entry MUST have this form:

```yaml
- operation: "trim"
  parameters:
    side: "both"
```

`parameters` MAY be omitted only when the registered operation has no parameters. `operation` MUST name an operation defined by the applicable schema version, and its parameters MUST validate against that operation’s published parameter schema. An unknown operation or parameter MUST invalidate the specification. List order is execution order. The permitted processing stages and their overall order are fixed by Section 6.8.

The first-release source-text operation identifiers are:

- `unicode_normalise`, requiring `form` with one of `NFC`, `NFD`, `NFKC`, or `NFKD`;
- `trim`, requiring `side` with one of `leading`, `trailing`, or `both`; and
- `case_fold`, which takes no parameters.

The first-release typed-value operation identifiers are:

- `decimal_quantise`, requiring a non-negative integer `places` and `rounding` with one of `half_even`, `half_up`, or `down`; and
- `datetime_truncate`, requiring `precision` with one of `second`, `millisecond`, or `microsecond`.

A source-text operation MUST appear only in `source_normalisation`; a typed-value operation MUST appear only in `typed_normalisation`. Operation semantics, including the Unicode-data version used by Unicode operations, MUST be published with the schema and recorded sufficiently for reproducibility.

`value_mapping.reference` and `value_mapping.query` MUST be ordered lists of entries with this form:

```yaml
- from:
    category: "string"
    value: "resistant"
  to:
    category: "string"
    value: "R"
```

- `from` and `to` MUST be source-value descriptors as defined in Section 6.2.6.
- A `to` descriptor with `category: "null"` explicitly maps to null and is distinct from absence of a mapping entry.
- Each `from` value MUST occur at most once within one side’s mapping. Conflicting or unreachable entries MUST invalidate the specification.
- A non-empty value mapping requires a scalar `logical_type`; value mapping of collection fields is not supported in the first release. Its `to` values are parsed as the destination type after mapping.
- When a side’s value-mapping list is non-empty, a source value with no mapping entry creates a contract finding. Pass-through of unmapped values is not supported in the first release.
- Empty lists declare that no value mapping is applied on that side.

#### 6.2.8 Comparator declarations

Every field definition MUST contain `comparator.name` and `comparator.parameters`. `name` MUST be one of the comparator identifiers in Section 7.4, and `parameters` MUST be a mapping containing only parameters valid for that comparator.

- `preserved_exact`, `typed_exact`, `normalised_string`, `numeric_exact`, `date_exact`, `datetime_exact`, `list_exact`, `set_exact`, and `multiset_exact` take no field-level parameters in the first release; their `parameters` mapping MUST be empty.
- `numeric_tolerance` permits only `absolute_tolerance` and `relative_tolerance`. At least one MUST be present. Each MUST be a quoted, non-negative finite decimal string; omission of one means it is treated as zero as specified in Section 7.4.5.
- The comparator MUST be compatible with `logical_type`: string comparators with `string`, numeric comparators with `integer` or `decimal`, date comparators with their corresponding temporal type, and collection comparators with their corresponding collection type.
- `normalised_string` requires at least one `source_normalisation` or `typed_normalisation` operation applicable to strings.

#### 6.2.9 Acceptance criteria

`acceptance` MUST contain `contract`, `records`, and `values`, each an ordered list of criterion mappings. A list MAY be empty only when that phase cannot be reached under the approved intended use; selecting a scope that includes a phase with no criterion MUST invalidate the run as required by Section 8.5.

Every criterion MUST contain:

- a stable `id`, unique within the specification;
- `metric`, naming a metric defined by the applicable schema version;
- `operator`, one of `equal`, `not_equal`, `less_than`, `less_than_or_equal`, `greater_than`, or `greater_than_or_equal`; and
- `threshold`, expressed as a non-negative integer for count metrics or a quoted finite decimal string between `0` and `1`, inclusive, for proportion metrics.

The first-release core metrics are `contract_finding_count`, `missing_record_count`, `extra_record_count`, `value_mismatch_count`, `not_assessable_count`, `reference_record_count`, and `query_record_count`. It also supports the corresponding proportion metrics `contract_finding_proportion` and `value_mismatch_proportion`.

A criterion MAY additionally contain:

```yaml
fields: ["result", "confidence"]
finding_codes: ["VALUE_MISMATCH"]
parameters:
  side: "reference"
denominator:
  population: "in_scope_values"
  not_assessed: "exclude"
exceptions: ["known-difference-001"]
```

- `fields` restricts the metric to the listed canonical fields; omission means all fields applicable to the metric.
- `finding_codes` restricts a finding-based metric to the listed stable codes; omission means all codes applicable to that metric.
- `parameters` MUST contain only parameters published for the chosen metric. `side` is required for a metric whose population is not otherwise unambiguous.
- A filter or parameter that is not meaningful for the chosen metric MUST invalidate the specification rather than be ignored.
- `denominator` is required for proportion metrics and MUST be absent for count metrics. `population` MUST name a population supported by the metric. `not_assessed` MUST be `include` or `exclude`, making its treatment explicit. `not_assessable` content is governed by Section 8.5 and cannot be configured as a match or silently excluded.
- `exceptions` lists exception identifiers applied before the criterion is evaluated; omission is equivalent to an empty list.
- A referenced exception excludes a matching finding from that criterion’s failing metric but MUST NOT remove the finding from the report, summary counts, or provenance.
- Criteria are evaluated in list order for reporting, but order MUST NOT alter any phase or overall outcome.

#### 6.2.10 Permitted exceptions

`exceptions` MUST be a list and MAY be empty. Each exception MUST contain a unique stable `id`, a non-empty `rationale`, and an `applies_to` mapping containing at least one of `finding_codes`, `fields`, or `record_keys`. It MAY contain `revision`, `approved_by`, and `review_date` as provenance strings. These metadata fields do not replace the laboratory’s external approval controls.

```yaml
exceptions:
  - id: "known-difference-001"
    revision: "1"
    rationale: "Approved legacy representation"
    applies_to:
      finding_codes: ["VALUE_MISMATCH"]
      fields: ["result"]
      record_keys:
        - record_id:
            category: "string"
            value: "S001"
    effect: "permitted_difference"
    approved_by: "approval-record-reference"
    review_date: "2027-01-31"
```

- `finding_codes`, `fields`, and `record_keys` are cumulative filters: a finding must satisfy every filter that is present.
- `record_keys` MUST be a list of mappings containing exactly the canonical key fields declared by `records.keys`. Each field value MUST be expressed as a value descriptor in the form defined by Section 6.2.6 and MUST represent the canonical post-transformation key value.
- `effect` MUST be `permitted_difference`; no exception may suppress parsing, contract assessment, reporting, or provenance.
- Every applied exception MUST remain visible in findings and criterion evaluation.
- An exception has no effect unless its `id` is referenced by an acceptance criterion.

#### 6.2.11 Reporting controls

- `reporting.finding_limit`, when present, MUST be a positive integer. Omission means that no comparison-finding limit is configured, although documented resource limits still apply. Reaching a configured limit has the outcome consequences specified in Sections 7.5 and 8.4.
- `reporting.excluded_field_detail` MUST be `summary` or `individual`. `summary` permits omission of individual `not_assessed` findings only when the exclusion summary required by Section 7.5 is emitted; `individual` requires a finding for each excluded field occurrence.
- Privacy and redaction settings are not defined by this schema version. They MUST be supplied by a separately approved reporting policy and recorded in provenance.

### 6.3 Record keys

- A record key MUST contain one or more named fields.
- Composite-key field order MUST be stable and recorded.
- Key fields MUST be present and non-null.
- Key values MUST NOT undergo implicit numeric or boolean conversion.
- Normalisation of key values MUST be explicitly configured.
- Alternative key names and composite keys MUST be declared in a custom specification.
- Key names MUST NOT be inferred, and command-line key overrides MUST NOT be supported in the first release.
- The normalised key MUST uniquely identify one record.
- Duplicate keys MUST be input errors in every profile and scope.
- Duplicate records MUST never overwrite one another silently.
- Findings and reports MUST retain enough information to distinguish every source record.

### 6.4 Field declarations and preserved values

The comparison engine MUST support both preserved, untyped values and explicitly declared logical types. A type declaration is required for a field that uses typed parsing, normalisation, mapping, or a type-specific comparator. Every custom specification MUST explicitly declare how undeclared fields are treated: `compare`, `ignore`, `warn`, or `fail`. There MUST be no implicit policy. An `ignore` policy MUST still be represented as an assessment exclusion in accordance with Section 7.5.

Every declared field MUST define its canonical name, reference and query source names where applicable, required status on each side, null policy, ordered normalisation and mapping lists, and comparator. It MUST declare a logical type except where Section 6.2.6 permits omission for `preserved_exact`. Unit, sensitivity classification, and finding severity are optional. The authoritative YAML representation and validation rules are defined in Section 6.2.

### 6.5 Logical types and typed parsing

The comparison engine MUST support custom specifications declaring scalar logical types `string`, `integer`, `decimal`, `boolean`, `date`, and `datetime`, and typed `list`, `set`, and `multiset` collections. Collection fields MUST declare their element type. Null is a distinct value state governed by field policy, not a logical type.

Type parsing MUST be field-specific and declared. The tool MUST NOT infer a logical type from observed text. Values of different logical types MUST NOT be implicitly equal. Intended equivalence between differing source representations requires both sides to be parsed as the same declared destination logical type, with an explicit value mapping where the source representation cannot be parsed directly. The original source value or lexical representation MUST remain available in evidence, subject to redaction policy.

An invalid typed value in a non-key field that remains attributable to an unambiguous record MUST be a contract finding and MUST make that value `not_assessable`; it MUST NOT be an execution error. Defects that prevent construction of a complete and unambiguous record model are classified under Section 8.3.

#### 6.5.1 String

- A string MUST preserve its Unicode code points exactly by default.
- `typed_exact` equality MUST be code-point-for-code-point equality.
- Empty strings, whitespace-only strings, nulls, and absent fields MUST remain distinct.

#### 6.5.2 Integer

- Textual integers MUST use signed base-10 notation consisting of an optional `+` or `-` followed by one or more ASCII digits.
- Decimal points, exponent notation, booleans, and other characters MUST be invalid after source-text normalisation and mapping.
- Leading zeros MUST be accepted and have no numerical significance. Identifiers for which leading zeros are significant MUST be declared as strings.
- Integer representation MUST support arbitrary precision within documented resource limits.

#### 6.5.3 Decimal

- Decimals MUST be parsed and represented using decimal arithmetic without an intermediate binary floating-point conversion.
- Plain and scientific decimal notation MUST be accepted.
- Numerically equivalent finite representations such as `1.0`, `1.00`, and `1e0` MUST have the same canonical value.
- Parsing MUST preserve all supplied numerical precision.
- `NaN`, positive infinity, and negative infinity MUST be invalid.

#### 6.5.4 Boolean

- Native JSON booleans MUST be accepted.
- Textual boolean parsing MUST accept only lowercase `true` and `false`.
- Integers, uppercase boolean-like values, `yes`, `no`, `on`, `off`, and other representations MUST require an explicit value mapping.
- Booleans MUST NOT be treated as integers.

#### 6.5.5 Date

- Dates MUST use the ISO 8601 full-date form `YYYY-MM-DD`.
- Values MUST represent valid Gregorian calendar dates.
- Partial dates and locale-dependent forms MUST be invalid.
- The canonical value MUST be the represented calendar date.

#### 6.5.6 Datetime

- Datetimes MUST use an RFC 3339-compatible representation containing a full date, time, and `Z` or numeric UTC offset.
- Local datetimes without an offset MUST be invalid.
- Equivalent instants expressed with different offsets MUST have the same canonical value.
- Fractional seconds MUST be preserved unless explicit precision normalisation is configured.
- Leap-second representations MUST be invalid in the first release.

#### 6.5.7 Collections

- Every collection MUST declare its element logical type and element comparator.
- A `list` MUST preserve order and duplicates.
- A `set` MUST be unordered and MUST reject duplicate source elements rather than silently collapse them.
- A `multiset` MUST be unordered and MUST preserve element occurrence counts.
- JSON collections MUST use arrays.
- A CSV or TSV collection cell MUST use valid JSON-array syntax; ordinary delimited text MUST NOT be inferred to be a collection.
- Nested collections are outside the first-release scope.

### 6.6 Null, blank, and absent values

The specification MUST distinguish absent fields, explicit nulls, empty strings, whitespace-only strings, and configured missing tokens such as `NA`, `.`, or `null`. No two states are equivalent unless a field-specific policy declares them equivalent. Applied equivalence rules MUST be recorded.

- Two explicit nulls MUST match only when the field permits null and its policy declares them equivalent.
- Null MUST NOT implicitly equal empty string, absent field, zero, boolean false, or a missing token.
- A missing token MUST become null only through an explicit field policy.
- Two absent required fields MUST produce contract findings and MUST NOT constitute a value match.
- A null and non-null pair MUST be a value mismatch when both states are valid and comparable.
- A prohibited null MUST be a contract finding and MUST make the affected value `not_assessable` unless another treatment is explicitly configured.

The bundled strict-exact specification permits parser-native nulls. Under that specification, null matches only null and remains distinct from an absent field, an empty string, and every non-null value.

### 6.7 Mappings

#### 6.7.1 Column mappings

- Reference and query fields MAY map to a canonical field name.
- Mappings MUST be one-to-one unless an explicitly defined transformation supports another cardinality.
- Conflicting target mappings MUST be rejected.
- Unknown source fields MUST follow the undeclared-field policy.
- Required mapped fields that are absent MUST be reported.
- All applied mappings MUST be identifiable in the evidence.

#### 6.7.2 Value mappings

- A value mapping MUST operate on a preserved source value before typed parsing.
- The mapping output MUST be parsed as the declared destination logical type.
- A map MUST declare its source representation and destination logical type.
- Unknown source values MUST default to a contract finding, not pass through silently.
- Many-to-one mappings MUST be allowed only when intentionally declared.
- Mapping to null MUST be distinguished from a missing map entry.
- Mapping keys MUST be parsed without format-dependent scalar ambiguity.
- Applied mappings MUST be identifiable in the evidence.

### 6.8 Normalisation and processing order

Normalisation MUST be opt-in, field-specific, ordered deterministically, and recorded. Source-text normalisation is distinct from typed-value normalisation.

Source-text normalisation MAY include Unicode normalisation, leading or trailing whitespace trimming, and case folding. Typed-value normalisation MAY include datetime offset normalisation, declared precision reduction, and stable ordering of collections declared to be unordered. Destructive or clinically material transformations SHOULD require an independently specified domain comparator.

Typed processing MUST occur in this order:

1. preserve the source value and representation;
2. apply declared source-text normalisation;
3. recognise configured null or missing tokens;
4. apply a declared source-value mapping;
5. parse the declared logical type;
6. apply declared typed-value normalisation;
7. compare canonical values.

Column-name mapping MUST occur before field-value processing. A failure at any stage MUST identify the stage and attributable source value, subject to redaction policy.

### 6.9 Bundled strict-exact specification

If `--specification` is omitted, the tool MUST select the bundled strict-exact specification. It MUST be distributed as a documented template from which laboratories can develop controlled custom specifications, and the selected effective specification MUST be recorded in provenance. Supplying `--specification` MUST select the named custom specification; sentinel path values such as `DEFAULT` MUST NOT have special meaning.

The bundled default specification MUST:

- declare one key whose canonical, reference, and query field names are all `record_id`;
- include every shared non-key field without requiring field-specific declarations;
- preserve parser-native types and use `preserved_exact` comparison;
- perform no type inference, implicit coercion, mapping, normalisation, or tolerance;
- permit parser-native null values and compare them according to Section 6.6;
- treat two syntactically valid zero-record datasets as satisfying all bundled acceptance criteria;
- treat reference-only and query-only fields as contract findings;
- require zero contract findings, zero missing or extra records, and zero value mismatches.

Because parser-native types differ between formats, strict-exact comparison across different input formats MAY report type mismatches for lexically similar values. A custom typed specification is required when cross-format logical equivalence is intended.

## 7. Comparison behaviour

### 7.1 Cumulative phases and scopes

Comparison phases MUST be cumulative and ordered:

1. **Contract:** assess fields, logical types, key definitions, nullability, mappings, and declared data-contract constraints.
2. **Records:** align valid record identities and assess matching, missing, and extra records.
3. **Values:** compare corresponding values using declared comparators.

Public scope names identify the final requested phase:

| Scope | Contract | Records | Values |
| --- | --- | --- | --- |
| `contract` | Full | Not assessed | Not assessed |
| `records` | Full | Full | Not assessed |
| `full` | Full | Full | Full |

`full` MUST be the default. Failure of an earlier phase MUST NOT automatically prevent later phases. Later comparison MUST continue wherever its prerequisites remain satisfied. Content inside the selected scope that cannot be compared safely MUST be `not_assessable`; content deliberately outside the scope or excluded by policy MUST be `not_assessed`.

A run MUST conceptually:

1. validate the effective specification;
2. identify and hash inputs;
3. parse inputs without silent loss;
4. perform the contract phase;
5. align and compare records when the scope is `records` or `full`;
6. compare values for safely aligned records when the scope is `full`;
7. evaluate applicable phase acceptance criteria;
8. write results and provenance atomically.

### 7.2 Contract comparison

The contract phase MUST assess declared and observed fields from both directions for every record. It MUST distinguish:

- field present and valid;
- required field missing from the reference or query;
- unexpected reference or query field;
- invalid logical type, null state, mapping, or controlled value;
- field deliberately `not_assessed`;
- field `not_assessable` because a prerequisite failed.

One record’s observed field set MUST NOT be assumed to represent every other record. Key presence, validity, and uniqueness MUST be assessed in every scope because later interpretation depends on an unambiguous record model.

### 7.3 Records comparison

For the union of normalised valid record keys, the records phase MUST classify each key as matching, missing from the query, or extra in the query. Duplicate or otherwise invalid keys are execution errors under Section 8.3, not ordinary record findings.

Missing and extra records MUST be reported individually unless the selected privacy mode permits only aggregate reporting. Query-only records MUST NOT be ignored. Missing or extra records MUST NOT prevent value comparison of the safely aligned intersection when the scope is `full`.

### 7.4 Values comparison and comparators

The values phase MUST compare every in-scope, valid field in safely aligned records. A value whose contract or alignment prerequisite failed MUST be `not_assessable`; other values MUST continue to be compared.

The first release MUST support the following deterministic comparators with stable identifiers.

#### 7.4.1 `preserved_exact`

Used by the bundled strict-exact specification. Values match only when their parser-native types and values are identical. No inference, coercion, mapping, normalisation, or tolerance is applied. Textual `"1"`, integer `1`, decimal `1.0`, and boolean `true` are distinct.

#### 7.4.2 `typed_exact`

Values match only when both are present, valid under their field policies, have the same declared logical type, and have equal canonical values. Null handling follows Section 6.6. Cross-type equality is not implicit.

#### 7.4.3 `normalised_string`

Only configured string normalisations are applied in their declared order. Equality is exact code-point equality after transformation. Applied transformations MUST be identifiable in the evidence.

#### 7.4.4 `numeric_exact`

Integer or decimal comparison MUST use canonical arbitrary-precision values. Integer and decimal remain different logical types. Differing source representations are comparable only when both are explicitly parsed as the same declared logical type, using a mapping where required.

#### 7.4.5 `numeric_tolerance`

```text
difference = abs(reference - query)
allowed_difference = max(absolute_tolerance, relative_tolerance * abs(reference))
match if difference <= allowed_difference
```

- At least one of `absolute_tolerance` or `relative_tolerance` MUST be specified. If only one is specified, the other MUST be treated as zero when calculating the allowed difference.
- Tolerances MUST be non-negative finite decimals.
- The boundary MUST be inclusive.
- Relative tolerance MUST be directional and calculated against the absolute reference value.
- Absolute tolerance MUST govern behaviour around a zero reference value.
- A numeric field MAY declare a unit as metadata. If unit semantics affect equivalence or acceptance, the unit MUST be declared explicitly and MUST be compatible on both sides. Automatic unit conversion is outside the first-release scope.
- Rounding or significant-figure normalisation MUST occur explicitly before comparison.

#### 7.4.6 `date_exact` and `datetime_exact`

Dates match when their canonical calendar dates are equal. Datetimes match when they represent the same instant after UTC-offset normalisation. Any precision reduction MUST be explicitly configured before comparison.

#### 7.4.7 `list_exact`, `set_exact`, and `multiset_exact`

- Lists use ordered element-by-element comparison and their lengths MUST match.
- Sets use order-independent comparison of unique elements; duplicate source elements are invalid under Section 6.5.7.
- Multisets use order-independent comparison that preserves occurrence counts.
- Elements use the declared element comparator.

### 7.5 Completeness, subsets, and determinism

- Comparison findings MUST NOT terminate a normal run.
- All assessable differences MUST be collected.
- A configurable finding limit MAY protect resources and reaching it MUST be reported prominently as truncation. If a conclusive criterion failure has already been established, the outcome MUST remain `fail`; otherwise truncation MUST make the outcome `inconclusive`. A truncated run MUST NOT make claims about unexamined content.
- A malformed record that prevents a complete and unambiguous record model MUST be an input error and MUST NOT disappear silently.
- A field subset MUST be declared in the specification or invocation parameters retained in provenance.
- Key fields MUST always be processed.
- Individual findings for fields outside a configured subset MAY be omitted only under a documented report policy. The canonical report MUST still record a stable exclusion code, the exclusion rule, the affected field names or configured subset, and the number of excluded records or values where calculable.
- The report MUST identify that only a subset was assessed.
- An unknown requested field MUST be an error.
- Record order MUST NOT affect results unless explicitly declared significant.
- Output ordering MUST be deterministic and independent of hash-map ordering and locale.

## 8. Findings and outcomes

### 8.1 Finding structure

Every finding MUST be structured and SHOULD contain:

- stable finding code;
- category;
- severity;
- record key, or privacy-preserving surrogate;
- reference and query source locations where available;
- canonical field name;
- expected and observed presence state;
- expected and observed logical type;
- expected and observed value, subject to redaction policy;
- comparator and parameters;
- mappings/normalisations applied;
- concise human-readable explanation;
- related specification requirement or rule identifier.

Human-readable messages MUST NOT be the sole machine-readable representation of a finding. Successful field and record matches MUST be represented in summary counts and MUST NOT produce individual findings.

### 8.2 Minimum finding categories

Stable result codes MUST exist for at least:

- missing record;
- extra record;
- invalid record key;
- missing field;
- extra field;
- type mismatch;
- value mismatch;
- mapping failure;
- parse or data-contract error;
- invalid specification;
- not assessed;
- not assessable;
- comparison truncated;
- internal execution error.

### 8.3 Execution status

Execution status MUST be separate from comparison outcome and MUST include at least:

- `completed`: comparison ran as specified and the result package was written;
- `error`: the tool could not establish a complete and unambiguous record model or could not complete the required output operation.

An execution error includes an invalid invocation or specification, malformed or unreadable input syntax or structure, missing, null, invalid, or duplicate record keys, input/output failure, or an unexpected internal failure. No comparison outcome MUST be produced for an execution error. An error report SHOULD be written where possible and MUST be identified as such.

Content that is parseable and attributable to an unambiguous record but violates the declared data contract MUST be recorded as a comparison finding rather than an execution error. Comparisons that remain assessable MUST continue. A completed comparison MAY have a failing or inconclusive comparison outcome.

### 8.4 Comparison outcome

Comparison outcome MUST be one of:

- `pass`: all configured acceptance criteria were met;
- `fail`: one or more configured acceptance criteria were not met;
- `inconclusive`: criteria could not be fully evaluated, including truncation or configured recoverable data errors.

A completed run is `inconclusive` only when the inputs remain sufficiently trustworthy for comparison, one or more requested assessments cannot be completed, and the available evidence cannot establish a defensible pass or fail. It MUST identify all unassessed content and MUST never produce a pass.

Each executed phase MUST have its own outcome. A conclusive failure of any applicable criterion MUST produce overall `fail`. If no criterion conclusively fails but one or more applicable criteria cannot be evaluated, the overall outcome MUST be `inconclusive`. Overall `pass` requires every applicable criterion to be evaluated and satisfied. The outcome MUST be calculated only from explicit acceptance criteria and MUST NOT be inferred merely from whether warnings occurred.

### 8.5 Acceptance criteria

The specification MUST associate acceptance criteria with the individual `contract`, `records`, and `values` phases. It MUST NOT define a separate `full` acceptance section. The `contract` scope evaluates contract criteria; `records` evaluates contract and records criteria; and `full` evaluates all three phase sections.

The specification MUST define how findings contribute to outcome. Criteria MAY include:

- zero missing or extra records;
- zero mismatches in critical fields;
- a maximum number or proportion of specified differences;
- metric-specific thresholds;
- permitted known differences identified by stable rule and rationale.

Criteria based on counts or proportions MUST define their denominator and the treatment of deliberately `not_assessed` content. `not_assessable` content MUST NOT be counted as a match or silently removed from a denominator. A criterion that depends on `not_assessable` content MUST be unevaluable unless its failure can be established conclusively from the assessable evidence.

Exceptions and permitted differences MUST be explicit, versioned, reviewable, and reported. A custom specification missing acceptance criteria for any phase applicable to the selected scope MUST be invalid.

### 8.6 Laboratory decision

As established in Section 1, the calculated comparison outcome is not a laboratory validation or approval decision. Reports MUST label these concepts separately and MUST NOT describe the output as “ISO 15189 compliant”, “clinically validated”, or equivalent.

## 9. Output and evidence

A completed comparison MUST create an evidence-package directory at the destination selected by `--output`. The package MUST contain, at minimum, the canonical JSON result and the HTML report. A CSV findings export MAY also be included. Package member names and layout MUST be stable and documented.

### 9.1 Machine-readable output

JSON MUST be the canonical output format. It MUST have a published, versioned schema containing:

- report schema version;
- execution status and comparison outcome;
- run identifier;
- timestamps;
- tool identity and version;
- specification identity, version, and digest;
- input identities and digests;
- effective comparison settings;
- summary counts;
- structured findings;
- errors and warnings;
- truncation status;
- privacy/redaction mode.

Consumers MUST be able to distinguish absent, null, and redacted values.

### 9.2 Human-readable output

The first release MUST produce an HTML human-readable report. The report SHOULD include:

- purpose and scope of the run;
- prominent outcome and execution status;
- identities of reference, query, and specification;
- summary counts;
- acceptance criteria and evaluation;
- grouped discrepancy details;
- limitations, exclusions, and unassessed content;
- provenance and reproduction information;
- space or linkage for review and approval outside the tool.

CSV MAY be provided as an export of findings, but MUST:

- be produced using a conforming CSV writer;
- preserve record identifiers or approved surrogates;
- quote delimiters, quotes, and newlines correctly;
- use a stable documented column schema;
- mitigate spreadsheet formula injection when intended for spreadsheet use;
- never be the only canonical evidence format.

### 9.3 Summary counts

Summary counts MUST reconcile with emitted findings and SHOULD include:

- input record counts;
- valid unique key counts;
- matched, missing, and extra record counts;
- fields assessed and not assessed;
- findings by code and severity;
- pass/fail/inconclusive criteria counts.

### 9.4 Provenance

Provenance MUST include:

- SHA-256 or stronger digest of each input and the specification;
- tool version and build/release identity;
- report schema version;
- invocation parameters after redaction;
- start and end timestamps with time-zone offset;
- runtime environment sufficient for reproduction;
- selected input formats and encodings;
- all non-default policies in effect.

Absolute paths and the raw command line MUST NOT be included by default because they may contain sensitive information or credentials. Safe display names MAY be supplied separately.

### 9.5 Atomicity and overwrite protection

- Output files MUST be written atomically where supported.
- The complete evidence-package directory MUST be published atomically where the platform supports it.
- An existing destination MUST NOT be overwritten unless the user supplies `--overwrite`.
- The actual selected output directory MUST be reported clearly.
- File suffixes MUST be handled structurally, not with character stripping.
- Partial evidence packages MUST be identifiable as incomplete.

## 10. Command-line interface

### 10.1 General behaviour

- A subcommand MUST be required.
- Invalid argument combinations MUST be rejected before input processing.
- Modes and formats MUST use enumerated choices.
- `--help` and `--version` MUST work without other arguments.
- Errors MUST be concise on standard error and actionable.
- Normal summaries SHOULD be written to standard output.
- Comparison progress SHOULD be optional and MUST NOT contaminate machine-readable output.

### 10.2 Proposed comparison interface

The conceptual interface is:

```text
adviso-validation compare \
  --reference REFERENCE \
  --query QUERY \
  --output OUTPUT \
  [--scope {contract,records,full}] \
  [--specification SPECIFICATION] \
  [--reference-format {csv,tsv,json}] \
  [--query-format {csv,tsv,json}] \
  [--overwrite]
```

`--scope` MUST accept `contract`, `records`, or `full`, and MUST default to `full`. Scope selection and any content made `not_assessable` by contract incompatibility MUST be prominent in the report.

`--specification` MUST be optional. Its omission MUST select the bundled strict-exact specification; when present, its value MUST be treated as the path to a custom specification. `--reference-format` and `--query-format` MUST follow Section 5.2. `--output` MUST name the evidence-package directory described in Section 9, and `--overwrite` MUST provide the explicit overwrite authorisation required by Section 9.5.

Convenience flags MAY override non-critical settings only when the effective configuration is captured in provenance. Clinically material overrides SHOULD require an explicit opt-in and be prominent in the report.

### 10.3 Exit codes

Exit codes MUST distinguish at least:

| Code | Meaning |
| ---: | --- |
| 0 | Execution completed and comparison outcome is `pass` |
| 1 | Execution completed and comparison outcome is `fail` |
| 2 | Execution completed but comparison outcome is `inconclusive` |
| 3 | Invocation, specification, input, or I/O error |
| 4 | Unexpected internal error |

These exit-code meanings MUST be stable and documented. A comparison failure MUST still write a report when possible.

### 10.4 Additional commands

No additional command is specified for the initial release. In particular, the prototype’s format-conversion operation is excluded because it does not presently justify a place in the validation-evidence workflow. Any future command requires its own approved behaviour specification and MUST satisfy the product-boundary criteria in Section 2.1.

## 11. Privacy, security, and data governance

- The tool MUST assume that datasets may contain confidential patient or laboratory information.
- It MUST operate locally by default and MUST NOT transmit input or result data over a network without explicit functionality and authorisation.
- Reports MUST support configurable redaction or hashing of record identifiers and sensitive values.
- Hashing used as pseudonymisation MUST support a laboratory-controlled keyed method where resistance to dictionary attacks is required.
- Secrets MUST be redacted from recorded invocation details.
- Temporary files MUST be created securely and removed according to documented policy.
- Logs MUST NOT contain more sensitive information than the selected report policy permits.
- Comparison-specification YAML MUST be parsed using the safe-loader rules in Section 6.2.1.
- Spreadsheet-oriented exports MUST mitigate formula injection.
- Resource limits SHOULD protect against unexpectedly large or malicious inputs without silently truncating results.
- The tool SHOULD document filesystem permission expectations and leave access control to an appropriate deployment wrapper where necessary.

## 12. Deployment, accessibility, performance, and reliability

The toolkit is intended to be usable in low-resource and LMIC settings. Therefore:

- all core comparison functionality MUST operate fully offline;
- the toolkit MUST NOT require a hosted service, account, licence server, or telemetry connection;
- the base installation SHOULD minimise runtime dependency number and size;
- specialised dependencies SHOULD be optional and MUST NOT be required for strict structured-data comparison;
- an offline-installable artefact with integrity information SHOULD be provided;
- a container image MAY be supplied but MUST NOT be the only deployment method;
- reports MUST use open formats and MUST NOT require proprietary software;
- errors and documentation SHOULD be usable without specialist Python knowledge;
- documentation and examples SHOULD be available offline;
- localisation SHOULD remain possible without changing result semantics.

Behaviour MUST be correct before optimisation. Releases SHOULD state:

- the modest hardware profiles on which they were tested;
- representative dataset sizes;
- expected time and memory use;
- enforced resource or input-size limits.

Large inputs MUST either be processed within documented limits or rejected without producing a false pass. Resource exhaustion MUST produce an execution error or `inconclusive` outcome according to whether a trustworthy partial record model remains. Interrupted runs MUST NOT leave apparently complete reports. Results MUST remain deterministic across supported Python versions and operating systems. Internal exceptions MUST be captured in an error report where safe, with concise diagnostics presented to the user.

## 13. Software quality and release requirements

### 13.1 Requirements traceability

- Normative requirements intended for implementation MUST receive stable identifiers before the specification is approved.
- Tests MUST reference relevant requirement identifiers.
- A traceability report SHOULD show requirement-to-test and test-to-requirement coverage.

### 13.2 Testing

The project MUST include:

- unit tests for parsing, typing, mapping, normalisation, and comparators;
- behavioural contract tests for result semantics;
- end-to-end CLI tests including exit codes;
- schema validation tests for specifications and reports;
- installation tests from wheel and source distribution;
- regression tests for every corrected material defect;
- tests across all supported Python versions;
- deterministic-output tests;
- representative malformed and adversarial inputs;
- tests for duplicate/composite keys and missing/extra content in both directions;
- boundary tests for tolerances and acceptance criteria.

Property-based testing SHOULD be used for parsing and comparison invariants. Mutation testing SHOULD be used to assess whether the suite detects deliberately introduced comparison defects.

### 13.3 Test data

Controlled test cases SHOULD record:

- stable scenario identifier;
- requirement(s) tested;
- purpose and rationale;
- input data and comparison specification;
- expected findings, counts, status, outcome, and exit code;
- fixture provenance or generation method;
- fixture version and digest;
- independent review status where used as formal validation evidence.

Generated fixtures MUST be reproducible. Clinically derived fixtures MUST be appropriately de-identified and governed. Controlled test fixtures, including test comparison specifications, MUST be maintained by the development team under version control and its documented review process. In operational use, each laboratory is responsible for creating, approving, maintaining, and retaining its own comparison specifications under its local quality-management arrangements; the AdvISO project does not centrally approve or manage laboratory specifications.

### 13.4 Continuous integration

CI MUST:

- run on proposed changes and protected branches;
- install the built package, not rely solely on the source checkout;
- test the console entry point;
- test the supported Python matrix;
- fail on enforced lint, type, test, and build errors;
- validate that generated schemas and examples are current;
- avoid publishing releases when required checks fail.

### 13.5 Releases and change control

Each release SHOULD provide:

- an immutable semantic version;
- release notes and known limitations;
- compatibility statements for specification and report schemas;
- documented change-impact assessment;
- signed or otherwise attestable source and build artefacts where practical;
- a reproducible lockfile or equivalent dependency record;
- evidence that required verification tests passed.

Specification-schema versions and toolkit versions MUST be independent. Each toolkit release MUST document the specification-schema and report-schema versions it supports. An unsupported schema version MUST be rejected clearly rather than interpreted approximately. The project MUST publish migration and compatibility rules before changing either schema and MUST provide a migration path or documented transition period for any incompatible change.

## 14. Acceptance-test catalogue

This catalogue summarises minimum executable scenarios for the first release. It verifies, but does not independently define, the normative behaviour above. When normative requirement identifiers are assigned, every scenario MUST reference the requirements it verifies.

### 14.1 Input and contract scenarios

- **AT-CON-001:** Identical typed datasets satisfy their contract.
- **AT-CON-002:** Required missing and unexpected extra fields are reported in both directions and across heterogeneous records.
- **AT-CON-003:** Leading-zero identifiers remain strings unless explicitly transformed.
- **AT-CON-004:** Null, empty string, whitespace-only string, absent field, and configured missing tokens remain distinct according to policy.
- **AT-CON-005:** Unknown, conflicting, and incomplete mappings fail clearly; mapping to null differs from a missing map entry.
- **AT-CON-006:** Malformed syntax or structure, empty or duplicate column names, and irregular tabular rows receive their specified error classification without silent data loss.
- **AT-CON-007:** Two syntactically valid empty datasets pass under the bundled strict-exact specification; one-sided empty datasets produce all applicable missing or extra record findings.
- **AT-CON-008:** Comparison-specification YAML scalar resolution and cross-format typed dataset parsing are deterministic across supported environments.
- **AT-CON-009:** The bundled strict-exact specification treats parser-native null as equal only to null and distinguishes null, absent fields, and empty strings.
- **AT-CON-010:** Every custom specification explicitly declares an undeclared-field policy; omission is rejected.
- **AT-CON-011:** A complete custom YAML specification conforming to Section 6.2 validates and produces the declared effective configuration.
- **AT-CON-012:** Duplicate or unknown YAML keys, unsafe YAML features, unsupported schema versions, invalid enumerations, and incompatible type/comparator combinations are rejected with precise configuration paths.
- **AT-CON-013:** Source-value descriptors distinguish strings, numbers, booleans, and null; mapping to null remains distinct from an absent mapping entry.
- **AT-CON-014:** Each selected comparison phase requires applicable acceptance criteria, and count and proportion criteria validate their operators, thresholds, filters, and denominators.

### 14.2 Record scenarios

- **AT-REC-001:** Every reference-only record is reported as missing and every query-only record as extra, including when both occur together.
- **AT-REC-002:** Duplicate single and composite keys are rejected without overwriting data.
- **AT-REC-003:** Composite keys preserve multiple legitimate records belonging to one sample.
- **AT-REC-004:** Record order does not alter findings or outcomes unless explicitly declared significant.

### 14.3 Typed value and comparator scenarios

- **AT-VAL-001:** Boolean `true`, integer `1`, decimal `1.0`, and textual `"1"` remain distinct under the applicable exact comparator.
- **AT-VAL-002:** Typed strings remain code-point-exact unless configured normalisations are applied in declared order.
- **AT-VAL-003:** Integer parsing accepts signed ASCII decimal integers and leading zeros but rejects decimal points, exponents, booleans, and invalid text.
- **AT-VAL-004:** Decimal parsing is exact, accepts scientific notation, and rejects `NaN` and infinities.
- **AT-VAL-005:** Boolean parsing accepts native booleans and lowercase textual `true` or `false`; other representations require a mapping.
- **AT-VAL-006:** Dates reject invalid or non-ISO full dates; datetimes require offsets and compare as instants.
- **AT-VAL-007:** Lists preserve order and duplicates, sets reject duplicates and ignore order, and multisets ignore order while preserving occurrence counts.
- **AT-VAL-008:** Typed transformations follow Section 6.8 and retain evidence of the attributable source value.
- **AT-VAL-009:** Numeric tolerance uses exact decimal arithmetic, a reference-relative component, and an inclusive boundary, including below, at, and above boundary cases.
- **AT-VAL-010:** All assessable differences are collected in one run.
- **AT-VAL-011:** Subset comparison identifies its limited coverage, records the required exclusion summary when individual findings are omitted, and rejects unknown requested fields.
- **AT-VAL-012:** `preserved_exact` follows the parser-native category table, including deterministic same-format and cross-format comparisons.

### 14.4 Scope and outcome scenarios

- **AT-OUT-001:** `contract` assesses only the contract phase.
- **AT-OUT-002:** `records` assesses contract and records without comparing values.
- **AT-OUT-003:** `full` is the default and assesses contract, records, and values.
- **AT-OUT-004:** Failure of an earlier phase does not prevent later assessment where prerequisites remain satisfied.
- **AT-OUT-005:** Content excluded deliberately is `not_assessed`; in-scope content blocked by a failed prerequisite is `not_assessable`.
- **AT-OUT-006:** A conclusive criterion failure produces `fail`; otherwise an unevaluable applicable criterion produces `inconclusive`; every applicable criterion must pass for overall `pass`.
- **AT-OUT-007:** Pass, fail, inconclusive, invocation or input error, and internal error produce their documented exit behaviour.
- **AT-OUT-008:** Truncation preserves an already established conclusive failure; otherwise it produces `inconclusive` and identifies unexamined content.
- **AT-OUT-009:** Counts and proportions use declared denominators; `not_assessable` content is never treated as a match or silently excluded.

### 14.5 Evidence, CLI, and packaging scenarios

- **AT-EVD-001:** Identical runs produce semantically identical canonical results except for explicitly variable run metadata.
- **AT-EVD-002:** Reports contain input and specification digests without exposing absolute paths or raw secrets by default.
- **AT-EVD-003:** CSV findings containing commas, quotes, newlines, or formula prefixes are exported safely.
- **AT-EVD-004:** An output failure or interrupted write cannot leave an evidence package that appears complete.
- **AT-EVD-005:** A completed passing comparison exits with code 0; comparison failures still produce reports.
- **AT-EVD-006:** Omitting `--specification` selects and records the bundled strict-exact specification; a supplied value is treated only as a custom-specification path.
- **AT-EVD-007:** Explicit reference and query formats override extension detection; recognised extensions are detected and recorded; unknown or ambiguous extensions require explicit formats.
- **AT-EVD-008:** A successful run creates the documented JSON and HTML evidence package, refuses an existing destination by default, and replaces it only with `--overwrite`.
- **AT-EVD-009:** Invocation, specification, input, and output errors write a clearly identified error report when an output location can be established.
- **AT-PKG-001:** A built wheel contains every required subpackage, and its installed CLI completes an end-to-end comparison.

## 15. Compatibility with the current prototype

The current `File_IO`, `FileCompare`, and `TableValidator` module names and APIs MUST NOT constrain the new core data model or public terminology. In particular, the new model MUST NOT use a single dictionary keyed only by sample ID as its sole record representation.

Compatibility MAY be provided temporarily through an adapter, provided that:

- legacy semantics are labelled clearly;
- unsafe behaviour such as silent duplicate overwrite is not preserved;
- the adapter has a documented removal policy;
- new evidence reports identify use of legacy compatibility mode.

The current free-form result strings MUST NOT become the canonical result API.

## 16. Decisions required before approval

The following non-kernel decisions remain open. They do not prevent implementation of the comparison kernel, but MUST be resolved at the appropriate point before the specification and first release are approved.

1. What default privacy and redaction mode is appropriate for the intended deployment environment?
2. Which provenance fields are mandatory in local interactive use, CI, and formal retained evidence?
3. What maximum input sizes and performance targets are operationally relevant?
4. What compatibility period, if any, is required for the prototype CLI and outputs?
5. What objective hardware profile should define “modest” deployment and performance testing?

## 17. Suggested approval criteria for this specification

Before implementation begins, reviewers SHOULD confirm that:

- the intended use and non-claims are accurate;
- terminology matches laboratory practice;
- the record model covers representative pipeline outputs;
- missing, extra, duplicate, null, and malformed-data policies are unambiguous;
- comparison and acceptance are clearly separated;
- privacy and provenance requirements fit local governance;
- every first-milestone scenario has an agreed expected result;
- unresolved decisions have named owners and target dates;
- approved requirements have stable identifiers for test traceability.
