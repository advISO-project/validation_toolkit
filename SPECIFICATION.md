# AdvISO Validation Toolkit: `compare` Behaviour Specification

**Document status:** Draft for review  
**Specification version:** 0.1.0-draft  
**Applies to:** The `compare` command and its supporting comparison engine  
**Normative language:** The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** indicate requirement strength.

## 1. Purpose

This document defines a specification for version 1.0 of the AdvISO Validation Toolkit: a command-line namespace for cohesive capabilities that support bioinformatics validation and verification activities associated with ISO 15189 accreditation.

The initial sole user-facing subcommand within the toolkit is `compare`. This subcommand compares a reference dataset with a query dataset according to an explicit comparison configuration and produces deterministic, machine-readable findings and a human-readable summary suitable for review and retention as one component of a bioinformatics pipeline validation or verification record. It is intended to answer this question:

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
└── validation_toolkit repository
    └── adviso-validation distribution and executable
        └── adviso_validation Python import package
            ├── internal comparison, configuration, provenance, findings, and reporting components
            └── compare subcommand
```

The **AdvISO Validation Toolkit** is the user-facing product and a minimal command namespace. Its installable distribution package and command-line executable MUST both be named **`adviso-validation`**. **`compare`** is currently the sole specified subcommand. The other components, including the **comparison engine**, are internal reusable software components and are not separate products.

The command-line form MUST be:

```text
adviso-validation compare ...
```

The Python import package MUST be named `adviso_validation`. The repository name MAY differ from the distribution and import-package names, but it MUST be documented clearly. Once released, changes to the distribution, executable, or import-package name MUST follow the documented compatibility policy.

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

### 2.3 Out of scope

The `compare` command does not:

- establish analytical sensitivity, analytical specificity, precision, limit of detection, reportable range, clinical validity, or clinical utility;
- generate or adjudicate truth data;
- determine whether a reference dataset is representative or fit for purpose;
- replace laboratory review or approval;
- compare unstructured prose, images, binary files, or specialist bioinformatics formats (e.g. SAM, VCF, FASTQ);
- infer biological equivalence of variants, transcripts, genomic intervals, taxonomic calls, or other domain objects;
- provide automated redaction, identifier pseudonymisation, keyed hashing, or field-level sensitivity policies;
- provide an electronic-signature or laboratory document-management system.

## 3. Design principles

The following principles govern all requirements:

1. **Explicit over inferred:** Comparison behaviour MUST be declared, not guessed from observed data.
2. **No silent data loss:** Input records, duplicate keys, unmapped values, and unsupported structures MUST NOT be silently discarded or overwritten.
3. **Symmetry:** Missing and extra content MUST be assessed in both directions.
4. **Separation of concerns:** Run status, comparison evidence, and the laboratory's acceptance decision are distinct concepts.
5. **Complete evidence:** A normal comparison mismatch MUST still produce a complete report.
6. **Determinism:** Identical inputs, configuration, and tool version MUST produce semantically identical results.
7. **Traceability:** Findings MUST identify the rule, record, and field that produced them.
8. **Data minimisation:** Reports MUST include only the source identifiers and values necessary to explain and review the comparison; routine logs and diagnostics MUST not reproduce them by default.
9. **Fail clearly:** Invalid or ambiguous input MUST produce an explicit error rather than an assumed interpretation.
10. **Testability:** Each normative requirement SHOULD be traceable to one or more automated tests.

## 4. Terminology

- **Reference dataset:** The dataset containing the approved expected or comparator records. “Reference” does not imply intrinsic truth.
- **Query dataset:** The dataset being evaluated against the reference.
- **Comparison configuration:** The versioned YAML configuration declaring the data contract, normalisation, and comparison behaviour. Its permitted structure and semantics are defined by the comparison-configuration schema and this behaviour specification.
- **Not assessed:** Deliberately excluded by an explicit field policy.
- **Not assessable:** Included in the configured comparison, but unable to be compared safely because a prerequisite was not satisfied.
- **Contract comparison:** Assessment of whether inputs satisfy the declared data contract, including fields, logical types, key definitions, nullability, mappings, and configured constraints.
- **Records comparison:** Alignment and assessment of valid record identities, including matching, missing, and extra records. Invalid, missing, null, or duplicate record keys are execution errors rather than record-comparison findings.
- **Value comparison:** Application of declared comparators to values in records that can be aligned meaningfully.
- **Record:** One logical unit of comparison.
- **Record key:** One field or an ordered combination of fields that uniquely identifies a record within a dataset.
- **Field:** A named value within a record.
- **Finding:** A structured observation generated by applying one comparison rule to a record, field, dataset, or run.
- **Run status:** Whether the requested comparison is `complete`, `incomplete`, or ended in `error`.
- **Laboratory decision:** The externally reviewed conclusion about validation or verification. The toolkit does not make this decision.
- **Missing:** Expected in the reference but absent from the query.
- **Extra:** Present in the query but absent from the reference.
- **Null:** A present field with an explicitly empty/no-value representation defined by the input format or comparison configuration.
- **Absent:** A field or record that is not present at all.
- **Normalisation:** A declared, non-lossy or intentionally controlled transformation performed before comparison.
- **Mapping:** A declared translation of field names or values from one representation to another.

## 5. Inputs

### 5.1 Required inputs

A comparison run MUST receive:

- one reference dataset;
- one query dataset;
- an output destination.

A custom comparison configuration MAY be supplied. If it is omitted, the bundled strict-exact configuration defined in Section 6.9 MUST be used.

### 5.2 Supported formats

The initial implementation MUST support:

- CSV conforming to the configured dialect;
- TSV conforming to the configured dialect;
- JSON using a documented record-oriented structure.

The reference and query formats MAY be selected independently through explicit command-line options. If a format is not supplied, it MAY be detected only from a recognised, unambiguous extension: `.csv`, `.tsv` or `.json`. In either case:

- detected format MUST be recorded;
- ambiguous or unsupported content MUST fail execution;
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
- duplicate or empty column names MUST cause an input error;
- delimiters, quoting, escaping, and embedded newlines MUST be handled by a standards-compliant parser;
- rows with too many or too few columns MUST be input errors;
- all physical input rows MUST be accounted for;
- source row numbers SHOULD be retained for traceability;
- input values MUST initially remain strings unless a custom configuration declares a null representation or type conversion; in the bundled strict-exact configuration, an empty cell is an empty string.

### 5.5 JSON parsing

- JSON inputs MUST use a schema-validated list of record objects:

```json
[
  {"sample_id": "S1", "gene": "BRAF", "result": "detected"},
  {"sample_id": "S2", "gene": "KRAS", "result": "not_detected"}
]
```

- Values such as `yes`, `no`, `on`, `off`, uppercase boolean-like values, and timestamp-like strings MUST remain strings unless a custom configuration explicitly maps or parses them.
- JSON decimal numbers - i.e. numbers containing a fractional or exponent component - MUST be parsed using exact decimal arithmetic, without first converting them to binary floating-point values. The tool MUST also retain the original text of each number — for example, distinguishing the representations `0.100`, `0.1`, and `1e-1` — for inclusion in evidence and diagnostic output when required.
- A JSON input MUST contain either one object representing a single record or an array of objects representing multiple records. A root-level scalar, or a root-level array containing any item that is not an object, MUST be an input error. The error MUST identify the invalid root value or array item and explain the required structure.

### 5.6 Parser-native value model

- When an input file is read, and before any configured type conversion, mapping, or normalisation is applied, each input value MUST be represented internally using one of the following parser-native value categories: `string`, `integer`, `decimal`, `boolean`, `null`, `array`, and `object`.
- CSV and TSV cells MUST be strings, including empty strings, unless a custom configuration declares further processing.
- JSON numbers without a fractional or exponent component MUST be integers, while other finite JSON numbers MUST be exact decimals.
- JSON arrays used as field values MUST be represented internally as `array` values, and JSON objects used as field values MUST be represented internally as `object` values.
- Parser-native values are equal only when they have the same category and recursively equal content. For array-valued fields, element order is significant; for object-valued fields, member names and values must match but member order is not significant. Top-level records are aligned by their declared record keys, and their input order does not affect comparison.
- Numerical values MUST be retained exactly as they appeared in the input for reporting and traceability. However, two values in the same numerical category compare as equal when they represent the same number; for example, decimal `1.0` and decimal `1.00` are equal.
- `NaN`, positive infinity, and negative infinity are not valid numerical values. In an attributable non-key field, they MUST produce a contract finding and make that value `not_assessable`; other assessable content MUST still be compared. If such a value occurs in a record key or prevents construction of an unambiguous record model, it MUST produce an execution error.

### 5.7 Empty inputs

- Empty files and datasets with zero records MUST be recognised explicitly.
- If both datasets are syntactically valid and contain no records, the records phase MUST report no missing or extra records, and the values phase MUST perform no comparisons. Contract requirements that can be evaluated without records MUST still be checked. The tool MUST NOT infer that an empty dataset is unsuitable merely because it is empty; any minimum-size acceptance criterion belongs to the external laboratory decision process.
- A non-empty reference and empty query MUST report every expected record as missing.
- An empty reference and non-empty query MUST report every observed record as extra.

## 6. Comparison configurations

### 6.1 General requirements

Every comparison uses an effective comparison configuration. A custom configuration MUST:

- use a published, independently versioned comparison-configuration schema supported by the installed toolkit release;
- declare its schema version and a stable configuration identifier and revision;
- be validated fully before either dataset is compared;
- reject unknown configuration keys by default;
- provide actionable validation errors with configuration locations;
- be identified in provenance by a cryptographic digest;
- be retained or embedded in the evidence package, subject to policy.

A valid comparison configuration MUST declare at least:

- record key fields;
- field definitions and an explicit policy for undeclared fields;
- comparison rules.

### 6.2 Custom comparison-configuration YAML format

Custom comparison configurations MUST be YAML documents conforming to the format defined in this section. YAML is used only for the comparison configuration; it is not a supported dataset format. A configuration file SHOULD use the `.yaml` or `.yml` extension.

#### 6.2.1 YAML parsing and validation

- The document MUST be UTF-8 encoded and contain exactly one YAML mapping at its root.
- The configuration MUST be parsed according to the YAML 1.2 rules for interpreting unquoted scalar values.
- The parser MUST use a safe loading mode that cannot construct arbitrary application objects or execute code.
- Duplicate mapping keys, merge keys, aliases, anchors, explicit tags, and executable or implementation-specific object constructors MUST be rejected as configuration errors.
- Unknown keys MUST be rejected as configuration errors.
- Required keys MUST NOT be supplied as YAML null values.
- `schema_version`, `id`, `revision`, field names, operation names, comparator names, enumerated values, decimal lexical values, dates, and datetimes SHOULD be quoted to prevent unintended YAML scalar conversion.
- The complete document MUST be validated against the published schema identified by `schema_version` before either dataset is read.
- Validation errors MUST identify the YAML path and the violated requirement.

#### 6.2.2 Complete structural template

The following template defines the complete first-release structure. Keys marked “optional” in comments MAY be omitted; other displayed keys are required when their parent construct is used, except where a conditional omission is explicitly permitted below. Optional processing properties are omitted rather than represented by empty lists.

```yaml
schema_version: "1.0"

metadata:
  id: "org.example.pipeline-output-comparison"
  revision: "1.0.0"
  title: "Example pipeline-output comparison"       # optional
  description: "Approved comparison rules"          # optional

fields:
  record_key:
    - "record_id"
  undeclared: "fail"
  definitions:
    record_id:
      source:
        reference: "sample_id"
        query: "specimen_id"
      required:
        reference: true
        query: true
      logical_type: "string"
      nulls:
        allowed: false
        nulls_equal: false
      comparator:
        name: "typed_exact"
    field_example_1:
      source:
        reference: "expected_result"
        query: "reported_result"
      required:
        reference: true
        query: true
      logical_type: "decimal"
      nulls:
        allowed: false
        nulls_equal: false
      typed_normalisation:
        - operation: "decimal_quantise"
          parameters:
            places: 3
            rounding: "half_even"
      comparator:
        name: "numeric_tolerance"
        parameters:
          absolute_tolerance: "0.01"
          relative_tolerance: "0.05"
      review_priority: "high"                       # optional; default: normal
    field_example_2:
      source:
        reference: "expected_interpretation"
        query: "reported_interpretation"
      required:
        reference: true
        query: true
      logical_type: "string"
      nulls:
        allowed: true
        nulls_equal: true
        missing_tokens:
          reference:
            - category: "string"
              value: "na"
          query:
            - category: "string"
              value: "."
      source_normalisation:
        reference:
          - operation: "trim"
            parameters:
              side: "both"
          - operation: "case_fold"
        query:
          - operation: "trim"
            parameters:
              side: "both"
      value_mapping:
        reference:
          - from:
              category: "string"
              value: "detected"
            to:
              category: "string"
              value: "detected"
          - from:
              category: "string"
              value: "not detected"
            to:
              category: "string"
              value: "not_detected"
        query:
          - from:
              category: "string"
              value: "pos"
            to:
              category: "string"
              value: "detected"
          - from:
              category: "string"
              value: "neg"
            to:
              category: "string"
              value: "not_detected"
      comparator:
        name: "typed_exact"
      review_priority: "low"                        # optional; default: normal

```

The template is illustrative rather than an instruction to use these particular rules. In particular, laboratories MUST choose identifiers, field definitions, and policies appropriate to the intended comparison. The published machine-readable schema MUST encode the same structure and constraints as this section; where the schema and this document disagree, the normative behaviour specification MUST be corrected before release rather than silently choosing one interpretation.

The three field definitions illustrate different configuration roles: `record_id` is a renamed exact key; `field_example_1` is parsed as an exact decimal and quantised before tolerance comparison; and `field_example_2` demonstrates source-text normalisation, side-specific missing tokens, and mapping different source vocabularies to common canonical string values. The deliberately generic names make clear that these are user-defined canonical field names rather than reserved configuration keywords. These example rules are not domain recommendations.

#### 6.2.3 Top-level keys and identity

The only permitted top-level keys are `schema_version`, `metadata`, and `fields`.

- `schema_version` MUST be a quoted string identifying a supported comparison-configuration schema version.
- `metadata.id` MUST be a stable, non-empty identifier for the comparison configuration. It SHOULD use a collision-resistant organisational namespace.
- `metadata.revision` MUST be a non-empty revision string controlled by the configuration owner. Any behaviourally material change elsewhere in the configuration MUST produce a new revision.
- `metadata.title` and `metadata.description` are optional human-readable strings.
- The `metadata` properties MUST NOT directly alter comparison behaviour. Any change to them nevertheless changes the configuration document and therefore its provenance digest.

#### 6.2.4 Record-key selection

- `fields.record_key` MUST be a non-empty ordered list of canonical field names present in `fields.definitions`. The list defines one logical record key, and list order defines the component order of a composite key.
- Every key field MUST be required on both sides, non-nullable, and declared with a scalar logical type. A key field MAY use explicitly declared source normalisation or value mapping, but MUST use `typed_exact` after transformation.

#### 6.2.5 Field selection, declaration, and source names

- Every field in `fields.definitions` is in scope. Field definitions are the sole mechanism for selecting explicitly configured fields in version 1.
- `fields.undeclared` is required and MUST be one of `compare`, `exclude`, or `fail`.
  - `compare` compares shared undeclared fields with `preserved_exact`; an undeclared field present on only one side creates a contract finding because no corresponding value can be compared.
  - `exclude` does not compare undeclared fields and records them in the exclusion summary as `not_assessed`.
  - `fail` creates a contract finding for every undeclared field.
- Undeclared reference and query fields MUST be aligned only when their input field names are identical. No name inference or source-name mapping is applied to undeclared fields. Fields with different names MUST be declared explicitly under a common canonical field definition if they are intended to correspond.
- `fields.definitions` MUST be a mapping keyed by unique canonical field name and MUST contain a definition for every field referenced by `fields.record_key`.
- `source.reference` and `source.query` MUST each contain a non-empty source field name. A declared field always defines correspondence between one reference field and one query field, regardless of whether either field is required to be present in every record.
- `required.reference` and `required.query` MUST be booleans. Absence of a field required on a particular side MUST create a contract finding. Absence of an optional field MUST NOT create a missing-field finding.
- A field observed in an input but absent from `fields.definitions` is an undeclared field and MUST be handled only according to `fields.undeclared`.
- `review_priority`, when present, MUST be `low`, `normal`, or `high`. When omitted, it defaults to `normal` in the effective configuration.
- A declared field's resolved `review_priority` MUST be attached to every finding attributable to that canonical field, including missing-field, null-policy, type, parsing, mapping, and value-mismatch findings. It MUST NOT be inherited by findings that cannot be attributed to that field, such as missing or extra records, truncation, invalid-configuration findings, or internal failures.
- Review priority is presentation and review-workflow metadata only. It MUST NOT change comparison behaviour, determine whether a finding is emitted, alter counts, affect run or phase status, affect exit codes, or constitute a laboratory acceptance decision.
- Human-readable reports MAY use review priority for grouping, ordering, filtering, icons, or colour coding. Colour MUST NOT be the only means of communicating priority. Reports and documentation MUST NOT describe review priority as clinical significance or as an execution-error classification.

#### 6.2.6 Logical types and null policy

For a scalar field, `logical_type` MUST be one of `string`, `integer`, `decimal`, `boolean`, `date`, or `datetime`. It MAY be omitted only when the comparator is `preserved_exact` and no typed parsing, mapping, or typed normalisation is configured.

For a collection field, `logical_type` MUST use this form:

```yaml
logical_type:
  name: "list"                 # list, set, or multiset
  element_type: "string"       # scalar logical type
  element_comparator:
    name: "typed_exact"
```

Nested collection types MUST be rejected. The comparator named for the field itself MUST correspond to the collection kind: `list_exact`, `set_exact`, or `multiset_exact`.

Every declared field MUST contain a `nulls` mapping:

- `allowed` and `nulls_equal` MUST be booleans.
- `nulls_equal` MUST be `false` when `allowed` is `false`.
- `missing_tokens` MAY be omitted; omission means that no additional source values are interpreted as null. Parser-native JSON null remains null independently of this property.
- When `missing_tokens` is present, it MUST contain `reference`, `query`, or both. Each present side MUST be a non-empty list of source-value descriptors. An omitted side has no configured textual missing tokens. A matched token is converted to null at processing step 3 in Section 6.8.

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

`source_normalisation` MAY be omitted; omission means that no source-text normalisation is applied. When present, it MUST contain `reference`, `query`, or both. Each present side MUST be a non-empty ordered list of operations applied only to values from that dataset; an omitted side has no source-text operations.

`typed_normalisation` MAY be omitted; omission means that no typed-value normalisation is applied. When present, it MUST be a non-empty ordered list applied to the canonical typed values on both sides. Each operation entry has this form:

```yaml
- operation: "trim"
  parameters:
    side: "both"
```

`parameters` MAY be omitted only when the registered operation has no parameters. `operation` MUST name an operation defined by the applicable schema version, and its parameters MUST validate against that operation’s published parameter schema. An unknown operation or parameter MUST invalidate the comparison configuration. List order is execution order. The permitted processing stages and their overall order are fixed by Section 6.8.

The first-release source-text operation identifiers are:

- `unicode_normalise`, requiring `form` with one of `NFC`, `NFD`, `NFKC`, or `NFKD`;
- `trim`, requiring `side` with one of `leading`, `trailing`, or `both`; here `side` identifies which end or ends of the text are trimmed, not the reference or query dataset; and
- `case_fold`, which takes no parameters.

The first-release typed-value operation identifiers are:

- `decimal_quantise`, requiring a non-negative integer `places` and `rounding` with one of `half_even`, `half_up`, or `down`; and
- `datetime_truncate`, requiring `precision` with one of `second`, `millisecond`, or `microsecond`.

A source-text operation MUST appear only in `source_normalisation.reference` or `source_normalisation.query` and applies only to that dataset. A typed-value operation MUST appear only in `typed_normalisation` and applies identically to both datasets. Operation semantics, including the Unicode-data version used by Unicode operations, MUST be published with the schema and recorded sufficiently for reproducibility.

`value_mapping` MAY be omitted; omission means that no value mapping is applied. When present, it MUST contain `reference`, `query`, or both. Each present side MUST be a non-empty ordered list of entries with this form; an omitted side has no value mapping:

```yaml
- from:
    category: "string"
    value: "resistant"
  to:
    category: "string"
    value: "R"
```

- `from` and `to` MUST be source-value descriptors as defined in Section 6.2.6.
- A `from` descriptor is matched against the source value after the applicable `source_normalisation` operations and missing-token recognition have been performed, in accordance with the processing order in Section 6.8.
- A `to` descriptor with `category: "null"` explicitly maps to null and is distinct from absence of a mapping entry.
- Each `from` value MUST occur at most once within one side’s mapping. Conflicting or unreachable entries MUST invalidate the comparison configuration.
- A value mapping requires a scalar `logical_type`; value mapping of collection fields is not supported in the first release. Its `to` values are parsed as the destination type after mapping.
- When a side has a value mapping, a source value with no mapping entry creates a contract finding. Pass-through of unmapped values is not supported in the first release.

Before comparison, the tool MUST expand omitted optional processing properties and omitted dataset sides into explicit empty internal structures in the effective configuration. The user-authored configuration and the expanded effective configuration MUST remain distinguishable in provenance. Omission changes no behaviour beyond declaring that the corresponding processing step is absent.

#### 6.2.8 Comparator declarations

Every field definition MUST contain `comparator.name`. `name` MUST be one of the comparator identifiers in Section 7.4. A `parameters` mapping MUST be present only when the selected comparator requires parameters and MUST contain only parameters valid for that comparator.

- `preserved_exact`, `typed_exact`, `normalised_string`, `numeric_exact`, `date_exact`, `datetime_exact`, `list_exact`, `set_exact`, and `multiset_exact` take no field-level parameters in the first release; `parameters` MUST be omitted for these comparators.
- `numeric_tolerance` MUST contain a `parameters` mapping that permits only `absolute_tolerance` and `relative_tolerance`. At least one tolerance MUST be present. Each MUST be a quoted, non-negative finite decimal string; omission of one means it is treated as zero as specified in Section 7.4.5.
- The comparator MUST be compatible with `logical_type`: string comparators with `string`, numeric comparators with `integer` or `decimal`, date comparators with their corresponding temporal type, and collection comparators with their corresponding collection type.
- `normalised_string` requires at least one operation in `source_normalisation.reference`, `source_normalisation.query`, or `typed_normalisation` that is applicable to strings.

#### 6.2.9 Normative machine-readable schema and semantic validation

The normative JSON Schema Draft 2020-12 definition of comparison-configuration schema version `1.0` is [`src/adviso_validation/schemas/comparison-configuration-v1.0.schema.json`](src/adviso_validation/schemas/comparison-configuration-v1.0.schema.json). A YAML configuration MUST first be loaded using Section 6.2.1. The resulting JSON-compatible data structure MUST then validate against that schema before either input dataset is read.

The standalone schema file is the authoritative machine-readable definition. It MUST be version controlled in the source repository, included as package data in the installed `adviso_validation.schemas` package, and loaded at runtime through the package-resource API rather than through a path relative to the working directory. CI MUST verify its presence in built distributions and validate every documented example and controlled configuration fixture against it. Any inconsistency between the human-readable requirements in this document and the machine-readable schema is a specification defect that MUST be resolved before release.

JSON Schema cannot reliably express every relationship involving user-defined mapping keys, uniqueness across separate arrays, or references between distant parts of a document. After schema validation, the implementation MUST therefore apply the following semantic checks before reading either dataset:

- every name in `fields.record_key` exists in `fields.definitions`;
- every key field is required on both sides, non-nullable, scalar, and uses `typed_exact`;
- a field without `logical_type` uses `preserved_exact` and has no typed normalisation or value mapping;
- each comparator and normalisation operation is compatible with the field’s logical type and processing stage;
- source-value descriptors contain lexically valid values for their declared categories, and each side’s value mapping has unique `from` values;

A failure of any semantic check MUST be reported as an invalid comparison configuration with the relevant configuration path and violated rule.

### 6.3 Record keys

- A record key MUST contain one or more named fields.
- Composite-key field order MUST be stable and recorded.
- Key fields MUST be present, valid under their declared field definitions, and non-null.
- Key values MUST NOT undergo implicit numeric or boolean conversion.
- Normalisation of key values MUST be explicitly configured.
- Alternative key names and composite keys MUST be declared in a custom configuration.
- Key names MUST NOT be inferred, and command-line key overrides MUST NOT be supported in the first release.
- The normalised key MUST uniquely identify one record within its dataset.
- A missing, null, invalid, or duplicate record key prevents construction of an unambiguous record model and MUST be an input error in every comparison. The resulting execution error MUST identify the affected dataset and the key or key field involved and, where available, the relevant source-record locations.
- Duplicate records MUST never overwrite one another silently.
- Findings and reports MUST retain enough information to distinguish every source record.

### 6.4 Field declarations and preserved values

The comparison engine MUST support both preserved, untyped values and explicitly declared logical types. A type declaration is required for a field that uses typed parsing, normalisation, mapping, or a type-specific comparator. Every custom configuration MUST explicitly declare how undeclared fields are treated: `compare`, `exclude`, or `fail`. There MUST be no implicit policy. An `exclude` policy MUST be represented as an assessment exclusion in accordance with Section 7.5.

Every declared field MUST define its canonical name, reference and query source names, required status on each side, null policy, and comparator. It MUST declare a logical type except where Section 6.2.6 permits omission for `preserved_exact`. Normalisation, value mapping, and review priority are optional. An omitted review priority resolves to `normal` in the effective configuration. The authoritative YAML representation and validation rules are defined in Section 6.2.

### 6.5 Logical types and typed parsing

The comparison engine MUST support custom configurations declaring scalar logical types `string`, `integer`, `decimal`, `boolean`, `date`, and `datetime`, and typed `list`, `set`, and `multiset` collections. Collection fields MUST declare their element type. Null is a distinct value state governed by field policy, not a logical type.

Type parsing MUST be field-specific and declared. The tool MUST NOT infer a logical type from observed text. Values of different logical types MUST NOT be implicitly equal. Intended equivalence between differing source representations requires both sides to be parsed as the same declared destination logical type, with an explicit value mapping where the source representation cannot be parsed directly. The original source value or lexical representation MUST remain available to the comparison engine and MAY be included in evidence when required to explain a finding.

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

The comparison configuration MUST distinguish absent fields, explicit nulls, empty strings, whitespace-only strings, and configured missing tokens such as `NA`, `.`, or `null`. No two states are equivalent unless a field-specific policy declares them equivalent. Applied equivalence rules MUST be recorded.

- Two explicit nulls MUST match only when the field permits null and its policy declares them equivalent.
- Null MUST NOT implicitly equal empty string, absent field, zero, boolean false, or a missing token.
- A missing token MUST become null only through an explicit field policy.
- Two absent required fields MUST produce contract findings and MUST NOT constitute a value match.
- A null and non-null pair MUST be a value mismatch when both states are valid and comparable.
- A prohibited null MUST be a contract finding and MUST make the affected value `not_assessable` unless another treatment is explicitly configured.

The bundled strict-exact configuration permits parser-native nulls. Under that configuration, null matches only null and remains distinct from an absent field, an empty string, and every non-null value.

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
- Values used in mappings MUST be represented using the typed source-value descriptor. The parser MUST NOT infer their intended category from YAML scalar syntax.
- Applied mappings MUST be identifiable in the evidence.

### 6.8 Normalisation and processing order

Normalisation MUST be opt-in, field-specific, ordered deterministically, and recorded. Source-text normalisation is distinct from typed-value normalisation.

Source-text normalisation MAY include Unicode normalisation, leading or trailing whitespace trimming, and case folding. Typed-value normalisation MAY include datetime offset normalisation, declared precision reduction, and stable ordering of collections declared to be unordered.

Typed processing MUST occur in this order:

1. preserve the source value and representation;
2. apply the source-text normalisation declared for the applicable dataset side;
3. recognise configured null or missing tokens;
4. apply a declared source-value mapping;
5. parse the declared logical type;
6. apply declared typed-value normalisation;
7. compare canonical values.

Column-name mapping MUST occur before field-value processing. A failure at any stage MUST identify the stage and attributable record and field. The source value MUST be included in the evidence report only when required to explain the failure and MUST NOT be reproduced in routine logs or terminal diagnostics by default.

### 6.9 Bundled strict-exact configuration

If `--configuration` is omitted, the tool MUST select the bundled strict-exact configuration. It MUST be distributed as a documented template from which laboratories can develop controlled custom configurations, and the selected effective configuration MUST be recorded in provenance. Supplying `--configuration` MUST select the named custom configuration.

The bundled default configuration MUST:

- declare one key whose canonical, reference, and query field names are all `record_id`;
- include every shared non-key field without requiring field-specific declarations;
- preserve parser-native types and use `preserved_exact` comparison;
- perform no type inference, implicit coercion, mapping, normalisation, or tolerance;
- permit parser-native null values and compare them according to Section 6.6;
- treat two syntactically valid zero-record datasets as having zero missing records, zero extra records, and zero value mismatches, while evaluating contract findings as required by Sections 5.7 and 7.2;
- treat reference-only and query-only fields as contract findings.

Because parser-native types differ between formats, strict-exact comparison across different input formats MAY report type mismatches for lexically similar values. A custom typed configuration is required when cross-format logical equivalence is intended.

## 7. Comparison behaviour

### 7.1 Comparison phases

Every comparison MUST perform all three phases in this order:

1. **Contract:** assess fields, logical types, key definitions, nullability, mappings, and declared data-contract constraints.
2. **Records:** align valid record identities and assess matching, missing, and extra records.
3. **Values:** compare corresponding values using declared comparators.

A finding or `not_assessable` item in an earlier phase MUST NOT automatically prevent later assessment. Later comparison MUST continue wherever its prerequisites remain satisfied. Configured content that cannot be compared safely MUST be `not_assessable`; content deliberately excluded by field policy MUST be `not_assessed`.

A run MUST conceptually:

1. validate the effective comparison configuration;
2. identify and hash inputs;
3. parse inputs without silent loss;
4. perform the contract phase;
5. align and compare records;
6. compare values for safely aligned records;
7. determine whether every configured assessment was completed;
8. write results and provenance atomically.

### 7.2 Contract comparison

The contract phase MUST assess declared and observed fields from both directions for every record. It MUST distinguish:

- field present and valid;
- required field missing from the reference or query;
- observed undeclared field and the treatment required by `fields.undeclared`;
- invalid logical type, null state, mapping, or controlled value;
- field deliberately `not_assessed`;
- field `not_assessable` because a prerequisite failed.

One record’s observed field set MUST NOT be assumed to represent every other record. Key presence, validity, and uniqueness MUST always be assessed because later interpretation depends on an unambiguous record model.

For a zero-record dataset, contract requirements that can be evaluated from available structural information, such as CSV or TSV headers, MUST still be assessed. A requirement that depends on examining a record and cannot be evaluated because no records exist MUST be reported as `not_assessable`; it MUST NOT be treated as satisfied merely because no contradictory record was observed.

### 7.3 Records comparison

For the union of normalised valid record keys, the records phase MUST classify each key as matching, missing from the query, or extra in the query. Duplicate or otherwise invalid keys are execution errors under Section 8.3, not ordinary record findings.

Missing and extra records MUST be reported individually. Query-only records MUST NOT be ignored. Missing or extra records MUST NOT prevent value comparison of the safely aligned intersection.

### 7.4 Values comparison and comparators

The values phase MUST compare every configured, valid field in safely aligned records. A value whose contract or alignment prerequisite failed MUST be `not_assessable`; other values MUST continue to be compared.

The first release MUST support the following deterministic comparators with stable identifiers.

#### 7.4.1 `preserved_exact`

Used by the bundled strict-exact configuration. Values match according to the parser-native value model and equality rules in Section 5.6. No inference, coercion, mapping, normalisation, or tolerance is applied. Textual `"1"`, integer `1`, decimal `1.0`, and boolean `true` are distinct.

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
- A documented implementation safeguard MAY stop assessment to protect resources, but it MUST NOT be configurable through the comparison configuration. Reaching such a safeguard MUST be reported prominently as truncation and MUST make the run `incomplete`. A truncated run MUST NOT make claims about unexamined content.
- A malformed record that prevents a complete and unambiguous record model MUST be an input error and MUST NOT disappear silently.
- Key fields MUST always be processed.
- Under `fields.undeclared: "exclude"`, undeclared fields MUST be represented by a summary rather than by an individual finding for every excluded occurrence. The canonical report MUST record a stable exclusion code, the policy, the affected input field names, and the number of excluded records or values where calculable.
- Record order MUST NOT affect results unless explicitly declared significant.
- Output ordering MUST be deterministic and independent of hash-map ordering and locale.

## 8. Findings and run status

### 8.1 Finding structure

Every finding MUST be structured and SHOULD contain:

- stable finding code;
- category;
- review priority, when the finding is attributable to a declared field;
- record key;
- reference and query source locations where available;
- canonical field name;
- expected and observed presence state;
- expected and observed logical type;
- expected and observed value when required to explain the finding;
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
- undeclared field;
- type mismatch;
- value mismatch;
- mapping failure;
- parse or data-contract error;
- invalid comparison configuration;
- not assessed;
- not assessable;
- comparison truncated;
- internal execution error.

### 8.3 Run status

Run status MUST be one of:

- `complete`: every configured assessment was performed wherever the configuration and inputs made it applicable;
- `incomplete`: the inputs and record model remain sufficiently trustworthy for a useful comparison, but one or more configured assessments could not be completed safely or assessment was truncated;
- `error`: no trustworthy comparison result could be produced because of an invalid invocation or comparison configuration, malformed or unreadable input syntax or structure, a missing, null, invalid, or duplicate record key, an incomplete or ambiguous record model, an input/output failure, or an unexpected internal failure.

Differences between valid, assessable reference and query content—including contract findings, missing or extra records, and value mismatches—MUST NOT by themselves change a run from `complete` to `incomplete` or `error`. The run status describes completeness and operational validity, not acceptability.

Any configured content classified as `not_assessable`, or any content left unexamined because assessment was truncated, MUST make the run `incomplete`. Deliberately `not_assessed` content MUST NOT do so. An incomplete report MUST identify the affected or unexamined content and MUST not make claims about it.

Content that is parseable and attributable to an unambiguous record but violates the declared data contract MUST be recorded as a comparison finding rather than an error. Comparisons that remain assessable MUST continue. An error report SHOULD be written where possible and MUST be identified as such.

Each phase MUST record whether it was `complete` or `incomplete`. Overall status is `complete` only when all three phases are complete. The tool MUST report raw findings and metrics without applying acceptance thresholds or producing a pass/fail verdict.

### 8.4 Laboratory decision

The run status and reported differences do not constitute a laboratory validation, approval, or acceptance decision. Any acceptance criteria and their application belong to a separately governed process outside the tool. Reports MUST label these concepts separately and MUST NOT describe the output as “ISO 15189 compliant”, “clinically validated”, or equivalent.

## 9. Output and evidence

A non-error comparison, whether `complete` or `incomplete`, MUST create an evidence-package directory at the destination selected by `--output`. The package MUST contain, at minimum, the canonical JSON result and the HTML report. A CSV findings export MAY also be included. Package member names and layout MUST be stable and documented.

### 9.1 Machine-readable output

JSON MUST be the canonical output format. It MUST have a published, versioned schema containing:

- report schema version;
- run status and per-phase completion status;
- run identifier;
- timestamps;
- tool identity and version;
- comparison-configuration identity, revision, schema version, and digest;
- input identities and digests;
- effective comparison settings;
- summary counts;
- structured findings;
- errors and warnings;
- truncation status;

Consumers MUST be able to distinguish absent and null values.

### 9.2 Human-readable output

The first release MUST produce an HTML human-readable report. The report SHOULD include:

- purpose of the run and the three comparison phases performed;
- prominent run status and per-phase completion status;
- identities of reference, query, and comparison configuration;
- summary counts;
- measured counts and findings, without an acceptance verdict;
- grouped discrepancy details;
- limitations, exclusions, and unassessed content;
- provenance and reproduction information;
- space or linkage for review and approval outside the tool.

CSV MAY be provided as an export of findings, but MUST:

- be produced using a conforming CSV writer;
- preserve record identifiers;
- quote delimiters, quotes, and newlines correctly;
- use a stable documented column schema;
- mitigate spreadsheet formula injection when intended for spreadsheet use;
- never be the only canonical evidence format.

### 9.3 Summary counts

Summary counts MUST reconcile with emitted findings and MUST include at least:

- input record counts;
- valid unique key counts;
- matched, missing, and extra record counts;
- fields assessed and not assessed;
- findings by code and, where applicable, review priority;
- complete/incomplete status for each of the three phases.

### 9.4 Provenance

Provenance MUST include:

- SHA-256 or stronger digest of each input and the comparison configuration;
- tool version and build/release identity;
- report schema version;
- invocation parameters with secrets omitted;
- start and end timestamps with time-zone offset;
- runtime environment sufficient for reproduction;
- selected input formats and encodings;
- all non-default policies in effect.

Absolute paths and the raw command line MUST NOT be included. Safe display names MAY be supplied separately.

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
  [--configuration CONFIGURATION] \
  [--reference-format {csv,tsv,json}] \
  [--query-format {csv,tsv,json}] \
  [--overwrite]
```

`--configuration` MUST be optional. Its omission MUST select the bundled strict-exact configuration; when present, its value MUST be treated as the path to a custom comparison-configuration file. `--reference-format` and `--query-format` MUST follow Section 5.2. `--output` MUST name the evidence-package directory described in Section 9, and `--overwrite` MUST provide the explicit overwrite authorisation required by Section 9.5.

Convenience flags MAY override non-critical settings only when the effective configuration is captured in provenance. Clinically material overrides SHOULD require an explicit opt-in and be prominent in the report.

### 10.3 Exit codes

Exit codes MUST distinguish at least:

| Code | Meaning |
| ---: | --- |
| 0 | Run status is `complete`, whether or not differences were found |
| 1 | Run status is `incomplete` |
| 2 | Invocation, comparison-configuration, input, or I/O error |
| 3 | Unexpected internal error |

These exit-code meanings MUST be stable and documented. A complete comparison that finds differences MUST still exit with code 0 and write the evidence package. Error classes represented by exit codes 2 and 3 have run status `error`; the distinct codes allow automation to distinguish expected operational errors from unexpected implementation failures.

### 10.4 Additional commands

No additional command is specified for the initial release. In particular, the prototype’s format-conversion operation is excluded because it does not presently justify a place in the validation-evidence workflow. Any future command requires its own approved behaviour specification and MUST satisfy the product-boundary criteria in Section 2.1.

## 11. Security and data governance

- The tool MUST assume that datasets and evidence packages may contain confidential patient or laboratory information.
- It MUST operate locally and MUST NOT transmit input data, comparison configurations, logs, or results over a network.
- Routine logs, progress output, and terminal diagnostics MUST NOT contain record identifiers or source values by default. A user MAY explicitly request diagnostic detail, and that choice MUST be prominent.
- Evidence reports MAY contain record identifiers and source values only where required to identify or explain findings. Reports MUST state prominently that the evidence package may contain sensitive information.
- Absolute paths, raw command lines, environment variables, and secrets MUST NOT be included in reports or routine logs. Safe display names and a structured record of non-secret invocation parameters MAY be included.
- Temporary files MUST be created securely and removed according to documented policy.
- Comparison-configuration YAML MUST be parsed using the safe-loader rules in Section 6.2.1.
- Spreadsheet-oriented exports MUST mitigate formula injection.
- Resource limits SHOULD protect against unexpectedly large or malicious inputs without silently truncating results.
- The tool SHOULD document filesystem permission expectations. The laboratory is responsible for supplying appropriately pseudonymised input data where required and for controlling access to, retention of, and disposal of inputs and evidence packages.
- Automated redaction, identifier pseudonymisation, keyed hashing, and field-level sensitivity policies are outside the scope of version 1.0.

## 12. Deployment, accessibility, and reliability

- all core comparison functionality MUST operate fully offline;
- the toolkit MUST NOT require a hosted service, account, licence server, or telemetry connection;
- an offline-installable artefact with integrity information SHOULD be provided;
- reports MUST use open formats and MUST NOT require proprietary software;
- errors and documentation SHOULD be usable without specialist Python knowledge;
- documentation and examples SHOULD be available offline;
- localisation SHOULD remain possible without changing result semantics.

Releases SHOULD state any enforced resource or input-size limits.

Large inputs MUST either be processed within documented limits or stopped without presenting an incomplete assessment as complete. Resource exhaustion before construction of a complete and unambiguous record model MUST produce an error. Resource exhaustion after that model has been constructed MAY produce an `incomplete` run only when the evidence package identifies the unexamined content and otherwise satisfies Section 8.3. Interrupted runs MUST NOT leave apparently complete reports. Results MUST remain deterministic across supported Python versions and operating systems. Internal exceptions MUST be captured in an error report where safe, with concise diagnostics presented to the user.

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
- schema validation tests for comparison configurations and reports;
- installation tests from wheel and source distribution;
- regression tests for every corrected material defect;
- tests across all supported Python versions;
- deterministic-output tests;
- representative malformed and adversarial inputs;
- tests for duplicate/composite keys and missing/extra content in both directions;
- boundary tests for comparator tolerances.

Property-based testing SHOULD be used for parsing and comparison invariants. Mutation testing SHOULD be used to assess whether the suite detects deliberately introduced comparison defects.

### 13.3 Test data

Controlled test cases SHOULD record:

- stable scenario identifier;
- requirement(s) tested;
- purpose and rationale;
- input data and comparison configuration;
- expected findings, counts, run status, per-phase statuses, and exit code;
- fixture provenance or generation method;
- fixture version and digest;
- independent review status where used as formal validation evidence.

Generated fixtures MUST be reproducible. Clinically derived fixtures MUST be appropriately de-identified and governed. Controlled test fixtures, including test comparison configurations, MUST be maintained by the development team under version control and its documented review process. In operational use, each laboratory is responsible for creating, approving, maintaining, and retaining its own comparison configurations under its local quality-management arrangements; the AdvISO project does not centrally approve or manage laboratory configurations.

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
- compatibility statements for comparison-configuration and report schemas;
- documented change-impact assessment;
- signed or otherwise attestable source and build artefacts where practical;
- a reproducible lockfile or equivalent dependency record;
- evidence that required verification tests passed.

Comparison-configuration schema versions and toolkit versions MUST be independent. Each toolkit release MUST document the comparison-configuration-schema and report-schema versions it supports. An unsupported schema version MUST be rejected clearly rather than interpreted approximately. The project MUST publish migration and compatibility rules before changing either schema and MUST provide a migration path or documented transition period for any incompatible change.

## 14. Acceptance-test catalogue

This catalogue summarises minimum executable scenarios for the first release. It verifies, but does not independently define, the normative behaviour above. When normative requirement identifiers are assigned, every scenario MUST reference the requirements it verifies.

### 14.1 Input and contract scenarios

- **AT-CON-001:** Identical typed datasets satisfy their contract.
- **AT-CON-002:** Required missing fields produce contract findings in both directions and across heterogeneous records; optional missing fields do not. Observed undeclared fields are handled according to each `fields.undeclared` mode and aligned only by identical input names under `compare`.
- **AT-CON-003:** Leading-zero identifiers remain strings unless explicitly transformed.
- **AT-CON-004:** Null, empty string, whitespace-only string, absent field, and configured missing tokens remain distinct according to policy.
- **AT-CON-005:** Unknown, conflicting, and incomplete mappings fail clearly; mapping to null differs from a missing map entry.
- **AT-CON-006:** Malformed syntax or structure, empty or duplicate column names, and irregular tabular rows receive their specified error classification without silent data loss.
- **AT-CON-007:** For two syntactically valid zero-record datasets, the records phase reports no missing or extra records and the values phase performs no comparisons under every configuration. Independently assessable contract requirements are still evaluated, and requirements that depend on examining a record are `not_assessable`. One-sided empty datasets produce all applicable missing or extra record findings.
- **AT-CON-008:** Comparison-configuration YAML scalar resolution and cross-format typed dataset parsing are deterministic across supported environments.
- **AT-CON-009:** The bundled strict-exact configuration treats parser-native null as equal only to null and distinguishes null, absent fields, and empty strings.
- **AT-CON-010:** `fields.undeclared` is required and accepts only `compare`, `exclude`, or `fail`; omission and unknown policies are rejected.
- **AT-CON-011:** A complete custom YAML configuration conforming to Section 6.2 validates; omitted optional processing properties and dataset sides expand to empty internal structures in the effective configuration, while explicitly empty placeholder lists or mappings are rejected.
- **AT-CON-012:** Duplicate or unknown YAML keys, unsafe YAML features, unsupported schema versions, invalid enumerations, and incompatible type/comparator combinations are rejected with precise configuration paths.
- **AT-CON-013:** Source-value descriptors distinguish strings, numbers, booleans, and null; mapping to null remains distinct from an absent mapping entry.
- **AT-CON-014:** The authoritative schema is present in the source tree and built distribution, can be loaded through the installed package-resource API, and validates every complete configuration example and controlled configuration fixture.
- **AT-CON-015:** Configurations that are structurally schema-valid but violate a semantic rule in Section 6.2.9 are rejected with the relevant configuration path and rule.
- **AT-CON-016:** `review_priority` accepts only `low`, `normal`, or `high`; omission resolves to `normal` in the effective configuration.
- **AT-CON-017:** `fields.record_key` is required, non-empty, ordered, and free of duplicate component fields; every entry names a field in `fields.definitions` that satisfies all key-field constraints.
- **AT-CON-018:** `metadata.id` and `metadata.revision` are required non-empty strings; title and description are optional, metadata does not alter comparison behaviour, and every metadata change alters the configuration digest.
- **AT-CON-019:** Every declared field supplies non-empty `source.reference` and `source.query` names, including when the field is optional on either side; the `required` flags govern record-level presence rather than whether a correspondence is declared.

### 14.2 Record scenarios

- **AT-REC-001:** Every reference-only record is reported as missing and every query-only record as extra, including when both occur together.
- **AT-REC-002:** Duplicate single and composite keys produce execution errors without overwriting data; each error identifies the affected dataset, duplicate normalised key, and available source-record locations.
- **AT-REC-003:** Composite keys preserve multiple legitimate records belonging to one sample.
- **AT-REC-004:** Record order does not alter findings, metrics, or run and phase statuses.

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
- **AT-VAL-011:** Every defined field is included in comparison; under `fields.undeclared: "exclude"`, undeclared fields are `not_assessed` and represented by the required exclusion summary.
- **AT-VAL-012:** `preserved_exact` follows the parser-native category table, including deterministic same-format and cross-format comparisons.

### 14.4 Phase and run-status scenarios

- **AT-OUT-001:** Every comparison performs the contract, records, and values phases in order and records a completion status for each.
- **AT-OUT-002:** A finding or `not_assessable` item in an earlier phase does not prevent later assessment where prerequisites remain satisfied.
- **AT-OUT-003:** Content excluded deliberately is `not_assessed`; configured content blocked by a failed prerequisite is `not_assessable`.
- **AT-OUT-004:** A fully performed comparison is `complete` whether it finds no differences or any combination of contract findings, missing records, extra records, and value mismatches.
- **AT-OUT-005:** Complete, incomplete, invocation or input error, and unexpected internal error produce their documented exit behaviour.
- **AT-OUT-006:** Truncation produces `incomplete`, identifies unexamined content, and makes no claims about it.
- **AT-OUT-007:** Configured `not_assessable` content produces `incomplete`; deliberately `not_assessed` content does not.
- **AT-OUT-008:** Invalid configuration, malformed or unreadable input, and an incomplete or ambiguous record model produce `error`, never `incomplete`.

### 14.5 Evidence, CLI, and packaging scenarios

- **AT-EVD-001:** Identical runs produce semantically identical canonical results except for explicitly variable run metadata.
- **AT-EVD-002:** Reports contain input and comparison-configuration digests without exposing absolute paths, raw command lines, environment variables, or secrets.
- **AT-EVD-003:** If the optional CSV findings export is provided, findings containing commas, quotes, newlines, or formula prefixes are exported safely.
- **AT-EVD-004:** An output failure or interrupted write cannot leave an evidence package that appears complete.
- **AT-EVD-005:** Every complete comparison exits with code 0 and produces its evidence package, including when differences are reported.
- **AT-EVD-006:** Omitting `--configuration` selects and records the bundled strict-exact configuration; a supplied value is treated only as a custom comparison-configuration path.
- **AT-EVD-007:** Explicit reference and query formats override extension detection; recognised extensions are detected and recorded; unknown or ambiguous extensions require explicit formats.
- **AT-EVD-008:** A complete or incomplete run creates the documented JSON and HTML evidence package, refuses an existing destination by default, and replaces it only with `--overwrite`.
- **AT-EVD-009:** When an output location can be established and an error report can be written, invocation, configuration, input, and output errors produce a clearly identified error report.
- **AT-EVD-010:** Routine logs, progress output, and terminal diagnostics omit record identifiers and source values.
- **AT-EVD-011:** Evidence packages warn that they may contain sensitive information, and findings contain record identifiers or source values only where needed to identify or explain the finding.
- **AT-EVD-012:** Core comparison completes without network access and makes no attempt to transmit inputs, comparison configurations, logs, or results.
- **AT-EVD-013:** Findings attributable to declared fields inherit their resolved review priority; other findings do not. HTML presentation may distinguish priorities but does not rely on colour alone, and priority never changes findings, counts, status, or exit code.
- **AT-PKG-001:** The built distribution is named `adviso-validation`, contains an importable `adviso_validation` package and every required subpackage, installs the `adviso-validation` executable, and completes an end-to-end comparison through that executable.

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

1. Which provenance fields are mandatory in local interactive use, CI, and formal retained evidence?
2. What compatibility period, if any, is required for the prototype CLI and outputs?

## 17. Suggested approval criteria for this specification

Before implementation begins, reviewers SHOULD confirm that:

- the intended use and non-claims are accurate;
- terminology matches laboratory practice;
- the record model covers representative pipeline outputs;
- missing- and extra-content policies, and the handling of duplicate, null, and malformed data, are unambiguous;
- comparison evidence, run status, and the laboratory decision are clearly separated;
- data-handling and provenance requirements fit local governance;
- every first-milestone scenario has an agreed expected result;
- unresolved decisions have named owners and target dates;
- approved requirements have stable identifiers for test traceability.
