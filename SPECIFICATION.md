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

**REQ-PRD-001.** The **AdvISO Validation Toolkit** is the user-facing product and a minimal command namespace. The installable distribution package MUST be named **`adviso-validation`**. The command-line executable MUST be named **`adviso-validation`**. **`compare`** is currently the sole specified subcommand. The other components, including the **comparison engine**, are internal reusable software components and are not separate products.

**REQ-PRD-002.** The command-line form MUST be:

```text
adviso-validation compare ...
```

**REQ-PRD-003.** The Python import package MUST be named `adviso_validation`.

**REQ-PRD-004.** The repository name MAY differ from the distribution and import-package names. Any difference between these names MUST be documented clearly.

**REQ-PRD-005.** Once released, changes to the distribution name MUST follow the documented compatibility policy. Changes to the executable name MUST follow that policy. Changes to the import-package name MUST follow that policy.

**REQ-PRD-006.** Additional commands are not a development objective for the first release. They MUST NOT be added speculatively.

**REQ-PRD-007.** A future command MAY be introduced only for a demonstrated, materially distinct operation in the same validation-evidence workflow.

**REQ-PRD-008.** The top-level dispatcher MUST remain thin. It MUST NOT create speculative shared abstractions.

**REQ-PRD-009.** The initial implementation SHOULD use ordinary modules and a small comparator registry rather than a general plugin framework.

**REQ-PRD-010.** Capabilities with materially different purposes, dependencies, governance, or release lifecycles SHOULD be separate AdvISO packages.

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

1. **REQ-PRN-001.** **Explicit over inferred:** Comparison behaviour MUST be declared, not guessed from observed data.
2. **REQ-PRN-002.** **No silent data loss:** Input records, duplicate keys, unmapped values, and unsupported structures MUST NOT be silently discarded or overwritten.
3. **REQ-PRN-003.** **Symmetry:** Missing and extra content MUST be assessed in both directions.
4. **Separation of concerns:** Run status, comparison evidence, and the laboratory's acceptance decision are distinct concepts.
5. **REQ-PRN-004.** **Complete evidence:** A normal comparison mismatch MUST still produce a complete report.
6. **REQ-PRN-005.** **Determinism:** Identical inputs, configuration, and tool version MUST produce semantically identical results.
7. **REQ-PRN-006.** **Traceability:** Findings MUST identify the rule, record, and field that produced them.
8. **REQ-PRN-007.** **Data minimisation:** Reports MUST include only the source identifiers and values necessary to explain and review the comparison. Routine logs, progress output, terminal diagnostics, and execution-error diagnostics MUST NOT reproduce them.
9. **REQ-PRN-008.** **Fail clearly:** Invalid or ambiguous input MUST produce an explicit error rather than an assumed interpretation.

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

**REQ-INP-001.** A comparison run MUST receive:

- **REQ-INP-060.** one reference dataset;
- **REQ-INP-061.** one query dataset;
- **REQ-INP-062.** an output destination.

**REQ-INP-002.** A custom comparison configuration MAY be supplied.

**REQ-INP-003.** If a custom comparison configuration is omitted, the bundled strict-exact configuration defined in Section 6.9 MUST be used.

### 5.2 Supported formats

**REQ-INP-004.** The initial implementation MUST support:

- **REQ-INP-063.** CSV using the fixed version 1 parsing rules in Section 5.4;
- **REQ-INP-064.** TSV using the fixed version 1 parsing rules in Section 5.4;
- **REQ-INP-065.** JSON using a documented record-oriented structure.

For each input:

- **REQ-INP-005.** its format MUST be determined from its case-insensitive filename extension: `.csv`, `.tsv` or `.json`;
- **REQ-INP-006.** the detected format MUST be recorded;
- **REQ-INP-007.** a missing, unknown, or ambiguous extension, including `.txt`, MUST cause an input error;
- **REQ-INP-008.** its content MUST be validated against the format indicated by the extension;
- **REQ-INP-009.** content that does not conform to the indicated format MUST cause an input error.

### 5.3 Character encoding and text handling

- **REQ-INP-010.** UTF-8 MUST be the only supported input encoding in version 1.
- **REQ-INP-011.** Invalid UTF-8 byte sequences MUST cause an input error.
- **REQ-INP-012.** Invalid UTF-8 byte sequences MUST NOT be replaced silently.
- **REQ-INP-013.** Field names and string values MUST be preserved exactly before declared normalisation.
- **REQ-INP-014.** Line endings MUST NOT affect comparison results.

### 5.4 Tabular parsing

For CSV and TSV:

- **REQ-INP-015.** CSV MUST use comma as its delimiter.
- **REQ-INP-016.** TSV MUST use tab as its delimiter.
- **REQ-INP-017.** CSV and TSV MUST use double quote as the quote character.
- **REQ-INP-018.** A double quote within a quoted field MUST be escaped by doubling it.
- **REQ-INP-019.** CRLF and LF record endings MUST be accepted.
- **REQ-INP-020.** Embedded delimiters and line breaks MUST be accepted only within quoted fields.
- No separate backslash or alternative escape mechanism is supported in version 1.
- **REQ-INP-021.** a header row MUST be required;
- **REQ-INP-022.** duplicate or empty column names MUST cause an input error;
- **REQ-INP-023.** delimiters, quoting, escaping, and embedded newlines MUST be handled by a standards-compliant parser;
- **REQ-INP-024.** rows with too many or too few columns MUST be input errors;
- **REQ-INP-025.** all physical input rows MUST be accounted for;
- **REQ-INP-026.** source row numbers SHOULD be retained for traceability;
- **REQ-INP-027.** Input values MUST initially remain strings unless a custom configuration declares a null representation or type conversion.
- **REQ-INP-028.** In the bundled strict-exact configuration, an empty cell MUST be an empty string.

### 5.5 JSON parsing

- **REQ-INP-029.** JSON inputs MUST use a schema-validated list of record objects:

```json
[
  {"sample_id": "S1", "gene": "BRAF", "result": "detected"},
  {"sample_id": "S2", "gene": "KRAS", "result": "not_detected"}
]
```

- **REQ-INP-030.** Values such as `yes`, `no`, `on`, `off`, uppercase boolean-like values, and timestamp-like strings MUST remain strings unless a custom configuration explicitly maps or parses them.
- **REQ-INP-031.** JSON decimal numbers - i.e. numbers containing a fractional or exponent component - MUST be parsed using exact decimal arithmetic.
- **REQ-INP-032.** JSON decimal numbers MUST NOT first be converted to binary floating-point values.
- **REQ-INP-033.** The tool MUST retain the original text of each JSON number — for example, distinguishing the representations `0.100`, `0.1`, and `1e-1` — for inclusion in evidence when required.
- **REQ-INP-034.** A JSON input MUST contain either one object representing a single record or an array of objects representing multiple records.
- **REQ-INP-035.** A root-level scalar MUST cause an input error.
- **REQ-INP-036.** A root-level array containing any item that is not an object MUST cause an input error.
- **REQ-INP-037.** An invalid-root error MUST identify the invalid root value or array item.
- **REQ-INP-038.** An invalid-root error MUST explain the required structure.

### 5.6 Parser-native value model

- **REQ-INP-039.** When an input file is read, and before any configured type conversion, mapping, or normalisation is applied, each input value MUST be represented internally using one of the following parser-native value categories: `string`, `integer`, `decimal`, `boolean`, `null`, `array`, and `object`.
- **REQ-INP-040.** CSV and TSV cells MUST be strings, including empty strings, unless a custom configuration declares further processing.
- **REQ-INP-041.** JSON numbers without a fractional or exponent component MUST be integers.
- **REQ-INP-042.** Other finite JSON numbers MUST be exact decimals.
- **REQ-INP-043.** JSON arrays used as field values MUST be represented internally as `array` values.
- **REQ-INP-044.** JSON objects used as field values MUST be represented internally as `object` values.
- Parser-native values are equal only when they have the same category and recursively equal content. For array-valued fields, element order is significant; for object-valued fields, member names and values must match but member order is not significant. Top-level records are aligned by their declared record keys, and their input order does not affect comparison.
- **REQ-INP-045.** Numerical values MUST be retained exactly as they appeared in the input for reporting and traceability.
- **REQ-INP-046.** Two values in the same numerical category MUST compare as equal when they represent the same number; for example, decimal `1.0` and decimal `1.00` are equal.
- `NaN`, positive infinity, and negative infinity are not valid numerical values.
- **REQ-INP-047.** A non-finite value in an attributable non-key field MUST produce a contract finding.
- **REQ-INP-048.** A non-finite value in an attributable non-key field MUST make that value `not_assessable`.
- **REQ-INP-049.** Other assessable content MUST still be compared when a non-finite value occurs in an attributable non-key field.
- **REQ-INP-050.** A non-finite value in a record key MUST produce an execution error.
- **REQ-INP-051.** A non-finite value that prevents construction of an unambiguous record model MUST produce an execution error.

### 5.7 Empty inputs

- **REQ-INP-052.** Empty files and datasets with zero records MUST be recognised explicitly.
- **REQ-INP-053.** If both datasets are syntactically valid and contain no records, the records phase MUST report no missing records.
- **REQ-INP-054.** If both datasets are syntactically valid and contain no records, the records phase MUST report no extra records.
- **REQ-INP-055.** If both datasets are syntactically valid and contain no records, the values phase MUST perform no comparisons.
- **REQ-INP-056.** Contract requirements that can be evaluated without records MUST still be checked.
- **REQ-INP-057.** The tool MUST NOT infer that an empty dataset is unsuitable merely because it is empty.
- Any minimum-size acceptance criterion belongs to the external laboratory decision process.
- **REQ-INP-058.** A non-empty reference and empty query MUST report every expected record as missing.
- **REQ-INP-059.** An empty reference and non-empty query MUST report every observed record as extra.

## 6. Comparison configurations

### 6.1 General requirements

**REQ-CFG-001.** Every comparison uses an effective comparison configuration. A custom configuration MUST:

- **REQ-CFG-095.** use a published, independently versioned comparison-configuration schema supported by the installed toolkit release;
- **REQ-CFG-096.** declare its schema version and a stable configuration identifier and revision;
- **REQ-CFG-097.** be validated fully before either dataset is compared;
- **REQ-CFG-098.** reject unknown configuration keys by default;
- **REQ-CFG-099.** provide actionable validation errors with configuration locations;
- **REQ-CFG-100.** be embedded in the canonical comparison result.

**REQ-CFG-002.** A valid comparison configuration MUST declare at least:

- **REQ-CFG-101.** record key fields;
- **REQ-CFG-102.** field definitions and an explicit policy for undeclared fields;
- **REQ-CFG-103.** comparison rules.

### 6.2 Custom comparison-configuration YAML format

**REQ-CFG-003.** Custom comparison configurations MUST be YAML documents conforming to the format defined in this section. YAML is used only for the comparison configuration; it is not a supported dataset format.

**REQ-CFG-004.** A configuration file SHOULD use the `.yaml` or `.yml` extension.

#### 6.2.1 YAML parsing and validation

- **REQ-CFG-005.** The document MUST be UTF-8 encoded and contain exactly one YAML mapping at its root.
- **REQ-CFG-006.** The configuration MUST be parsed according to the YAML 1.2 rules for interpreting unquoted scalar values.
- **REQ-CFG-007.** The parser MUST use a safe loading mode that cannot construct arbitrary application objects or execute code.
- **REQ-CFG-008.** Duplicate mapping keys, merge keys, aliases, anchors, explicit tags, and executable or implementation-specific object constructors MUST be rejected as configuration errors.
- **REQ-CFG-009.** Unknown keys MUST be rejected as configuration errors.
- **REQ-CFG-010.** Required keys MUST NOT be supplied as YAML null values.
- **REQ-CFG-011.** `schema_version`, `id`, `revision`, field names, operation names, comparator names, enumerated values, decimal lexical values, dates, and datetimes SHOULD be quoted to prevent unintended YAML scalar conversion.
- **REQ-CFG-012.** The complete document MUST be validated against the published schema identified by `schema_version` before either dataset is read.
- **REQ-CFG-013.** Validation errors MUST identify the YAML path and the violated requirement.

#### 6.2.2 Complete structural template

**REQ-CFG-014.** The following template defines the complete first-release structure. Keys marked “optional” in comments MAY be omitted; other displayed keys are required when their parent construct is used, except where a conditional omission is explicitly permitted below. Optional processing properties are omitted rather than represented by empty lists.

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

**REQ-CFG-015.** The template is illustrative rather than an instruction to use these particular rules. Laboratories MUST choose identifiers, field definitions, and policies appropriate to the intended comparison.

**REQ-CFG-016.** The published machine-readable schema MUST encode the complete version 1 comparison-configuration structure and constraints.

The three field definitions illustrate different configuration roles: `record_id` is a renamed exact key; `field_example_1` is parsed as an exact decimal and quantised before tolerance comparison; and `field_example_2` demonstrates source-text normalisation, side-specific missing tokens, and mapping different source vocabularies to common canonical string values. The deliberately generic names make clear that these are user-defined canonical field names rather than reserved configuration keywords. These example rules are not domain recommendations.

#### 6.2.3 Top-level keys and identity

The only permitted top-level keys are `schema_version`, `metadata`, and `fields`.

- **REQ-CFG-017.** `schema_version` MUST be a quoted string identifying a supported comparison-configuration schema version.
- **REQ-CFG-018.** `metadata.id` MUST be a stable, non-empty identifier for the comparison configuration.
- **REQ-CFG-019.** `metadata.id` SHOULD use a collision-resistant organisational namespace.
- **REQ-CFG-020.** `metadata.revision` MUST be a non-empty revision string controlled by the configuration owner.
- **REQ-CFG-021.** Any behaviourally material change elsewhere in the configuration MUST produce a new revision.
- `metadata.title` and `metadata.description` are optional human-readable strings.
- **REQ-CFG-022.** The `metadata` properties MUST NOT directly alter comparison behaviour.
- **REQ-CFG-023.** The `metadata` properties MUST be preserved in the configuration embedded in the canonical result.

#### 6.2.4 Record-key selection

- **REQ-CFG-024.** `fields.record_key` MUST be a non-empty ordered list of canonical field names present in `fields.definitions`. The list defines one logical record key, and list order defines the component order of a composite key.
- **REQ-CFG-025.** Every key field MUST be required on both sides.
- **REQ-CFG-026.** Every key field MUST be non-nullable.
- **REQ-CFG-027.** Every key field MUST be declared with a scalar logical type.
- **REQ-CFG-028.** A key field MAY use explicitly declared source normalisation or value mapping.
- **REQ-CFG-029.** Every key field MUST use `typed_exact` after transformation.

#### 6.2.5 Field selection, declaration, and source names

- Every field in `fields.definitions` is in scope. Field definitions are the sole mechanism for selecting explicitly configured fields in version 1.
- **REQ-CFG-030.** `fields.undeclared` is required and MUST be one of `compare`, `exclude`, or `fail`.
  - `compare` compares shared undeclared fields with `preserved_exact`; an undeclared field present on only one side creates a contract finding because no corresponding value can be compared.
  - `exclude` does not compare undeclared fields and records them in the exclusion summary as `not_assessed`.
  - `fail` creates a contract finding for every undeclared field.
- **REQ-CFG-031.** Undeclared reference and query fields MUST be aligned only when their input field names are identical.
- No name inference or source-name mapping is applied to undeclared fields.
- **REQ-CFG-032.** Fields with different names MUST be declared explicitly under a common canonical field definition if they are intended to correspond.
- **REQ-CFG-033.** `fields.definitions` MUST be a mapping keyed by unique canonical field name.
- **REQ-CFG-034.** `fields.definitions` MUST contain a definition for every field referenced by `fields.record_key`.
- **REQ-CFG-035.** `source.reference` and `source.query` MUST each contain a non-empty source field name. A declared field always defines correspondence between one reference field and one query field, regardless of whether either field is required to be present in every record.
- **REQ-CFG-036.** `required.reference` and `required.query` MUST be booleans.
- **REQ-CFG-037.** Absence of a field required on a particular side MUST create a contract finding.
- **REQ-CFG-038.** Absence of an optional field MUST NOT create a missing-field finding.
- **REQ-CFG-039.** A field observed in an input but absent from `fields.definitions` is an undeclared field and MUST be handled only according to `fields.undeclared`.
- **REQ-CFG-040.** `review_priority`, when present, MUST be `low`, `normal`, or `high`. When omitted, it defaults to `normal` in the effective configuration.
- **REQ-CFG-041.** A declared field's resolved `review_priority` MUST be attached to every finding attributable to that canonical field, including missing-field, null-policy, type, parsing, mapping, and value-mismatch findings.
- **REQ-CFG-042.** Review priority MUST NOT be inherited by findings that cannot be attributed to a declared field, such as missing or extra records.
- **REQ-CFG-043.** Review priority is presentation and review-workflow metadata only. It MUST NOT change comparison behaviour, determine whether a finding is emitted, alter counts, affect run or phase status, affect exit codes, or constitute a laboratory acceptance decision.
- **REQ-CFG-044.** Human-readable reports MAY use review priority for grouping, ordering, filtering, icons, or colour coding.
- **REQ-CFG-045.** Colour MUST NOT be the only means of communicating review priority.
- **REQ-CFG-046.** Reports and documentation MUST NOT describe review priority as clinical significance.
- **REQ-CFG-047.** Reports and documentation MUST NOT describe review priority as an execution-error classification.

#### 6.2.6 Logical types and null policy

**REQ-CFG-048.** For a scalar field, `logical_type` MUST be one of `string`, `integer`, `decimal`, `boolean`, `date`, or `datetime`.

**REQ-CFG-049.** `logical_type` MAY be omitted only when the comparator is `preserved_exact` and no typed parsing, mapping, or typed normalisation is configured.

**REQ-CFG-050.** For a collection field, `logical_type` MUST use this form:

```yaml
logical_type:
  name: "list"                 # list, set, or multiset
  element_type: "string"       # scalar logical type
  element_comparator:
    name: "typed_exact"
```

**REQ-CFG-051.** Nested collection types MUST be rejected.

**REQ-CFG-052.** The comparator named for the field itself MUST correspond to the collection kind: `list_exact`, `set_exact`, or `multiset_exact`.

**REQ-CFG-053.** Every declared field MUST contain a `nulls` mapping:

- **REQ-CFG-054.** `allowed` and `nulls_equal` MUST be booleans.
- **REQ-CFG-055.** `nulls_equal` MUST be `false` when `allowed` is `false`.
- **REQ-CFG-056.** `missing_tokens` MAY be omitted; omission means that no additional source values are interpreted as null. Parser-native JSON null remains null independently of this property.
- **REQ-CFG-057.** When `missing_tokens` is present, it MUST contain `reference`, `query`, or both. Each present side MUST be a non-empty list of source-value descriptors. An omitted side has no configured textual missing tokens. A matched token is converted to null at processing step 3 in Section 6.8.

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

**REQ-CFG-058.** `category` MUST be `string`, `integer`, `decimal`, `boolean`, or `null`.

**REQ-CFG-059.** `value` MUST be present for every category except `null`. It MUST be a quoted lexical string for `string`, `integer`, and `decimal`. It MUST be `true` or `false` for `boolean`. The lexical value MUST be valid for its stated category.

Descriptors are matched using parser-native category and value equality under Section 5.6. The retained lexical form remains evidence but does not create a distinct numerical value. This explicit representation prevents YAML scalar resolution from changing mapping keys or missing tokens.

#### 6.2.7 Normalisation and value mapping

**REQ-CFG-060.** `source_normalisation` MAY be omitted. Omission means that no source-text normalisation is applied.

**REQ-CFG-061.** When present, `source_normalisation` MUST contain `reference`, `query`, or both. Each present side MUST be a non-empty ordered list of operations applied only to values from that dataset. An omitted side has no source-text operations.

**REQ-CFG-062.** `typed_normalisation` MAY be omitted. Omission means that no typed-value normalisation is applied.

**REQ-CFG-063.** When present, `typed_normalisation` MUST be a non-empty ordered list applied to the canonical typed values on both sides. Each operation entry has this form:

```yaml
- operation: "trim"
  parameters:
    side: "both"
```

**REQ-CFG-064.** `parameters` MAY be omitted only when the registered operation has no parameters.

**REQ-CFG-065.** `operation` MUST name an operation defined by the applicable schema version. Its parameters MUST validate against that operation’s published parameter schema. An unknown operation MUST invalidate the comparison configuration. An unknown parameter MUST invalidate the comparison configuration.

List order is execution order. The permitted processing stages and their overall order are fixed by Section 6.8.

The first-release source-text operation identifiers are:

- `unicode_normalise`, requiring `form` with one of `NFC`, `NFD`, `NFKC`, or `NFKD`;
- `trim`, requiring `side` with one of `leading`, `trailing`, or `both`; here `side` identifies which end or ends of the text are trimmed, not the reference or query dataset; and
- `case_fold`, which takes no parameters.

The first-release typed-value operation identifiers are:

- `decimal_quantise`, requiring a non-negative integer `places` and `rounding` with one of `half_even`, `half_up`, or `down`; and
- `datetime_truncate`, requiring `precision` with one of `second`, `millisecond`, or `microsecond`.

**REQ-CFG-066.** A source-text operation MUST appear only in `source_normalisation.reference` or `source_normalisation.query`. It applies only to the corresponding dataset.

**REQ-CFG-067.** A typed-value operation MUST appear only in `typed_normalisation`. It applies identically to both datasets.

**REQ-CFG-068.** Operation semantics MUST be published with the schema and recorded sufficiently for reproducibility. This information MUST include the Unicode-data version used by Unicode operations.

**REQ-CFG-069.** `value_mapping` MAY be omitted. Omission means that no value mapping is applied.

**REQ-CFG-070.** When present, `value_mapping` MUST contain `reference`, `query`, or both. Each present side MUST be a non-empty ordered list of entries with the following form. An omitted side has no value mapping:

```yaml
- from:
    category: "string"
    value: "resistant"
  to:
    category: "string"
    value: "R"
```

- **REQ-CFG-071.** `from` and `to` MUST be source-value descriptors as defined in Section 6.2.6.
- A `from` descriptor is matched against the source value after the applicable `source_normalisation` operations and missing-token recognition have been performed, in accordance with the processing order in Section 6.8.
- A `to` descriptor with `category: "null"` explicitly maps to null and is distinct from absence of a mapping entry.
- **REQ-CFG-072.** Each `from` value MUST occur at most once within one side’s mapping.
- **REQ-CFG-073.** Conflicting entries MUST invalidate the comparison configuration.
- **REQ-CFG-074.** Unreachable entries MUST invalidate the comparison configuration.
- A value mapping requires a scalar `logical_type`; value mapping of collection fields is not supported in the first release. Its `to` values are parsed as the destination type after mapping.
- When a side has a value mapping, a source value with no mapping entry creates a contract finding. Pass-through of unmapped values is not supported in the first release.

**REQ-CFG-075.** Before comparison, the tool MAY expand omitted optional processing properties and omitted dataset sides into explicit empty internal structures for internal use.

**REQ-CFG-076.** Such expansion is implementation state. It MUST NOT replace the validated configuration document selected for the run and embedded in the canonical result. It MUST NOT alter that document. Omission changes no behaviour beyond declaring that the corresponding processing step is absent.

#### 6.2.8 Comparator declarations

**REQ-CFG-077.** Every field definition MUST contain `comparator.name`.

**REQ-CFG-078.** `name` MUST be one of the comparator identifiers in Section 7.4.

**REQ-CFG-079.** A `parameters` mapping MUST be present only when the selected comparator requires parameters. It MUST contain only parameters valid for that comparator.

- **REQ-CFG-080.** `preserved_exact`, `typed_exact`, `normalised_string`, `numeric_exact`, `date_exact`, `datetime_exact`, `list_exact`, `set_exact`, and `multiset_exact` take no field-level parameters in the first release; `parameters` MUST be omitted for these comparators.
- **REQ-CFG-081.** `numeric_tolerance` MUST contain a `parameters` mapping with exactly one of `absolute_tolerance` or `relative_tolerance`.
- **REQ-CFG-082.** Supplying neither tolerance MUST invalidate the comparison configuration.
- **REQ-CFG-083.** Supplying both tolerances MUST invalidate the comparison configuration.
- **REQ-CFG-084.** The supplied tolerance MUST be a quoted, non-negative finite decimal string.
- **REQ-CFG-085.** The comparator MUST be compatible with `logical_type`: string comparators with `string`, numeric comparators with `integer` or `decimal`, date comparators with their corresponding temporal type, and collection comparators with their corresponding collection type.
- `normalised_string` requires at least one operation in `source_normalisation.reference`, `source_normalisation.query`, or `typed_normalisation` that is applicable to strings.

#### 6.2.9 Normative machine-readable schema and semantic validation

The normative JSON Schema Draft 2020-12 definition of comparison-configuration schema version `1.0` is [`src/adviso_validation/schemas/comparison-configuration-v1.0.schema.json`](src/adviso_validation/schemas/comparison-configuration-v1.0.schema.json).

**REQ-CFG-086.** A YAML configuration MUST first be loaded using Section 6.2.1. The resulting JSON-compatible data structure MUST then validate against that schema before either input dataset is read.

The standalone schema file is the authoritative machine-readable definition.

**REQ-CFG-087.** It MUST be version controlled in the source repository. It MUST be included as package data in the installed `adviso_validation.schemas` package. It MUST be loaded at runtime through the package-resource API rather than through a path relative to the working directory.

**REQ-CFG-088.** CI MUST verify the schema's presence in built distributions. CI MUST validate every documented example against it. CI MUST validate every controlled configuration fixture against it.

**REQ-CFG-090.** JSON Schema cannot reliably express every relationship involving user-defined mapping keys, uniqueness across separate arrays, or references between distant parts of a document. After schema validation, the implementation MUST therefore apply the following semantic checks before reading either dataset:

- **REQ-CFG-104.** every name in `fields.record_key` exists in `fields.definitions`;
- **REQ-CFG-105.** every key field is required on both sides, non-nullable, scalar, and uses `typed_exact`;
- **REQ-CFG-106.** a field without `logical_type` uses `preserved_exact` and has no typed normalisation or value mapping;
- **REQ-CFG-107.** each comparator and normalisation operation is compatible with the field’s logical type and processing stage;
- **REQ-CFG-108.** source-value descriptors contain lexically valid values for their declared categories, and each side’s value mapping has unique `from` values;

**REQ-CFG-091.** A failure of any semantic check MUST be reported as an invalid comparison configuration with the relevant configuration path and violated rule.

### 6.3 Record keys

- **REQ-REC-001.** A record key MUST contain one or more named fields.
- **REQ-REC-002.** Composite-key field order MUST be stable and recorded.
- **REQ-REC-003.** Key fields MUST be present, valid under their declared field definitions, and non-null.
- **REQ-REC-004.** Key values MUST NOT undergo implicit numeric or boolean conversion.
- **REQ-REC-005.** Normalisation of key values MUST be explicitly configured.
- **REQ-REC-006.** Alternative key names and composite keys MUST be declared in a custom configuration.
- **REQ-REC-007.** Key names MUST NOT be inferred.
- **REQ-REC-008.** Command-line key overrides MUST NOT be supported in the first release.
- **REQ-REC-009.** The normalised key MUST uniquely identify one record within its dataset.
- **REQ-REC-010.** A missing, null, invalid, or duplicate record key prevents construction of an unambiguous record model and MUST be an input error in every comparison.
- **REQ-REC-011.** The resulting execution error MUST identify the affected dataset.
- **REQ-REC-012.** The resulting execution error MUST identify the key or key field involved.
- **REQ-REC-013.** Where available, the resulting execution error MUST identify the relevant source-record locations.
- **REQ-REC-014.** Duplicate records MUST never overwrite one another silently.
- **REQ-REC-015.** Findings and reports MUST retain enough information to distinguish every source record.

### 6.4 Field declarations and preserved values

**REQ-VAL-001.** The comparison engine MUST support preserved, untyped values. It MUST also support explicitly declared logical types.

A type declaration is required for a field that uses typed parsing, normalisation, mapping, or a type-specific comparator.

**REQ-VAL-002.** Every custom configuration MUST explicitly declare how undeclared fields are treated: `compare`, `exclude`, or `fail`. There MUST be no implicit policy. An `exclude` policy MUST be represented as an assessment exclusion in accordance with Section 7.5.

**REQ-VAL-003.** Every declared field MUST define its canonical name, reference source name, query source name, required status on each side, null policy, and comparator.

**REQ-VAL-004.** Every declared field MUST declare a logical type except where Section 6.2.6 permits omission for `preserved_exact`.

Normalisation, value mapping, and review priority are optional. An omitted review priority resolves to `normal` in the effective configuration. The authoritative YAML representation and validation rules are defined in Section 6.2.

### 6.5 Logical types and typed parsing

**REQ-VAL-005.** The comparison engine MUST support custom configurations declaring scalar logical types `string`, `integer`, `decimal`, `boolean`, `date`, and `datetime`.

**REQ-VAL-006.** The comparison engine MUST support typed `list`, `set`, and `multiset` collections. Collection fields MUST declare their element type. Null is a distinct value state governed by field policy, not a logical type.

**REQ-VAL-007.** Type parsing MUST be field-specific and declared.

**REQ-VAL-008.** The tool MUST NOT infer a logical type from observed text.

**REQ-VAL-009.** Values of different logical types MUST NOT be implicitly equal.

Intended equivalence between differing source representations requires both sides to be parsed as the same declared destination logical type, with an explicit value mapping where the source representation cannot be parsed directly.

**REQ-VAL-010.** The original source value or lexical representation MUST remain available to the comparison engine. It MAY be included in evidence when required to explain a finding.

**REQ-VAL-011.** An invalid typed value in a non-key field that remains attributable to an unambiguous record MUST be a contract finding. It MUST make that value `not_assessable`. It MUST NOT be an execution error.

#### 6.5.1 String

- **REQ-VAL-012.** A string MUST preserve its Unicode code points exactly by default.
- **REQ-VAL-013.** `typed_exact` equality MUST be code-point-for-code-point equality.
- **REQ-VAL-014.** Empty strings, whitespace-only strings, nulls, and absent fields MUST remain distinct.

#### 6.5.2 Integer

- **REQ-VAL-015.** Textual integers MUST use signed base-10 notation consisting of an optional `+` or `-` followed by one or more ASCII digits.
- **REQ-VAL-016.** Decimal points, exponent notation, booleans, and other characters MUST be invalid after source-text normalisation and mapping.
- **REQ-VAL-017.** Leading zeros MUST be accepted and have no numerical significance. Identifiers for which leading zeros are significant MUST be declared as strings.
- **REQ-VAL-018.** Integer representation MUST support arbitrary precision within documented resource limits.

#### 6.5.3 Decimal

- **REQ-VAL-019.** Decimals MUST be parsed and represented using decimal arithmetic without an intermediate binary floating-point conversion.
- **REQ-VAL-020.** Plain and scientific decimal notation MUST be accepted.
- **REQ-VAL-021.** Numerically equivalent finite representations such as `1.0`, `1.00`, and `1e0` MUST have the same canonical value.
- **REQ-VAL-022.** Parsing MUST preserve all supplied numerical precision.
- **REQ-VAL-023.** `NaN`, positive infinity, and negative infinity MUST be invalid.

#### 6.5.4 Boolean

- **REQ-VAL-024.** Native JSON booleans MUST be accepted.
- **REQ-VAL-025.** Textual boolean parsing MUST accept only lowercase `true` and `false`.
- **REQ-VAL-026.** Integers, uppercase boolean-like values, `yes`, `no`, `on`, `off`, and other representations MUST require an explicit value mapping.
- **REQ-VAL-027.** Booleans MUST NOT be treated as integers.

#### 6.5.5 Date

- **REQ-VAL-028.** Dates MUST use the ISO 8601 full-date form `YYYY-MM-DD`.
- **REQ-VAL-029.** Values MUST represent valid Gregorian calendar dates.
- **REQ-VAL-030.** Partial dates and locale-dependent forms MUST be invalid.
- **REQ-VAL-031.** The canonical value MUST be the represented calendar date.

#### 6.5.6 Datetime

- **REQ-VAL-032.** Datetimes MUST use an RFC 3339-compatible representation containing a full date, time, and `Z` or numeric UTC offset.
- **REQ-VAL-033.** Local datetimes without an offset MUST be invalid.
- **REQ-VAL-034.** Equivalent instants expressed with different offsets MUST have the same canonical value.
- **REQ-VAL-035.** Fractional seconds MUST be preserved unless explicit precision normalisation is configured.
- **REQ-VAL-036.** Leap-second representations MUST be invalid in the first release.

#### 6.5.7 Collections

- **REQ-VAL-037.** Every collection MUST declare its element logical type and element comparator.
- **REQ-VAL-038.** A `list` MUST preserve order and duplicates.
- **REQ-VAL-039.** A `set` MUST be unordered.
- **REQ-VAL-040.** A `set` MUST reject duplicate source elements rather than silently collapse them.
- **REQ-VAL-041.** A `multiset` MUST be unordered.
- **REQ-VAL-042.** A `multiset` MUST preserve element occurrence counts.
- **REQ-VAL-043.** JSON collections MUST use arrays.
- **REQ-VAL-044.** A CSV or TSV collection cell MUST use valid JSON-array syntax.
- **REQ-VAL-045.** Ordinary delimited text MUST NOT be inferred to be a collection.
- **REQ-VAL-046.** Collection elements MUST be non-null in version 1. A parser-native null element MUST produce an `invalid_field_value` finding, prevent construction of a canonical collection value, and make that field comparison `not_assessable`.
- Nested collections are outside the first-release scope.

### 6.6 Null, blank, and absent values

**REQ-VAL-047.** The comparison configuration MUST distinguish absent fields, explicit nulls, empty strings, whitespace-only strings, and configured missing tokens such as `NA`, `.`, or `null`. No two states are equivalent unless a field-specific policy declares them equivalent. Applied equivalence rules MUST be recorded.

- **REQ-VAL-048.** Two explicit nulls MUST match only when the field permits null and its policy declares them equivalent.
- **REQ-VAL-049.** Null MUST NOT implicitly equal empty string, absent field, zero, boolean false, or a missing token.
- **REQ-VAL-050.** A missing token MUST become null only through an explicit field policy.
- **REQ-VAL-051.** Two absent required fields MUST produce contract findings.
- **REQ-VAL-052.** Two absent required fields MUST NOT constitute a value match.
- **REQ-VAL-053.** A null and non-null pair MUST be a value mismatch when both states are valid and comparable.
- **REQ-VAL-054.** A prohibited null MUST be a contract finding.
- **REQ-VAL-055.** A prohibited null MUST make the affected value `not_assessable` unless another treatment is explicitly configured.

The bundled strict-exact configuration permits parser-native nulls. Under that configuration, null matches only null and remains distinct from an absent field, an empty string, and every non-null value.

The field-level null policy governs the collection value as a whole and does not permit null collection elements. Version 1 has no separate element-null policy.

### 6.7 Mappings

#### 6.7.1 Column mappings

- **REQ-VAL-056.** Reference and query fields MAY map to a canonical field name.
- **REQ-VAL-057.** Mappings MUST be one-to-one unless an explicitly defined transformation supports another cardinality.
- **REQ-VAL-058.** Conflicting target mappings MUST be rejected.
- **REQ-VAL-059.** Unknown source fields MUST follow the undeclared-field policy.
- **REQ-VAL-060.** Required mapped fields that are absent MUST be reported.
- **REQ-VAL-061.** All applied mappings MUST be identifiable in the evidence.

#### 6.7.2 Value mappings

- **REQ-VAL-062.** A value mapping MUST operate on a preserved source value before typed parsing.
- **REQ-VAL-063.** The mapping output MUST be parsed as the declared destination logical type.
- **REQ-VAL-064.** A map MUST declare its source representation and destination logical type.
- **REQ-VAL-065.** Unknown source values MUST default to a contract finding, not pass through silently.
- **REQ-VAL-066.** Many-to-one mappings MUST be allowed only when intentionally declared.
- **REQ-VAL-067.** Mapping to null MUST be distinguished from a missing map entry.
- **REQ-VAL-068.** Values used in mappings MUST be represented using the typed source-value descriptor. The parser MUST NOT infer their intended category from YAML scalar syntax.
- **REQ-VAL-069.** Applied mappings MUST be identifiable in the evidence.

### 6.8 Normalisation and processing order

**REQ-VAL-070.** Normalisation MUST be opt-in, field-specific, ordered deterministically, and recorded. Source-text normalisation is distinct from typed-value normalisation.

**REQ-VAL-071.** Source-text normalisation MAY include Unicode normalisation, leading or trailing whitespace trimming, and case folding. Typed-value normalisation MAY include datetime offset normalisation, declared precision reduction, and stable ordering of collections declared to be unordered.

**REQ-VAL-072.** Typed processing MUST occur in this order:

1. preserve the source value and representation;
2. apply the source-text normalisation declared for the applicable dataset side;
3. recognise configured null or missing tokens;
4. apply a declared source-value mapping;
5. parse the declared logical type;
6. apply declared typed-value normalisation;
7. compare canonical values.

**REQ-VAL-073.** Column-name mapping MUST occur before field-value processing.

**REQ-VAL-074.** A failure at any stage MUST identify the stage and attributable record and field.

**REQ-VAL-075.** The source value MUST be included in the evidence package only when required to explain the failure. It MUST NOT be reproduced in routine logs, progress output, terminal diagnostics, or execution-error diagnostics.

### 6.9 Bundled strict-exact configuration

**REQ-CFG-092.** If `--configuration` is omitted, the tool MUST select the bundled strict-exact configuration. It MUST be distributed as a documented template from which laboratories can develop controlled custom configurations, and the selected effective configuration MUST be recorded in provenance. Supplying `--configuration` MUST select the named custom configuration.

**REQ-CFG-093.** The bundled default configuration MUST:

- **REQ-CFG-109.** declare one key whose canonical, reference, and query field names are all `record_id`;
- **REQ-CFG-110.** include every shared non-key field without requiring field-specific declarations;
- **REQ-CFG-111.** preserve parser-native types and use `preserved_exact` comparison;
- **REQ-CFG-112.** perform no type inference, implicit coercion, mapping, normalisation, or tolerance;
- **REQ-CFG-113.** permit parser-native null values and compare them according to Section 6.6;
- **REQ-CFG-114.** treat two syntactically valid zero-record datasets as having zero missing records, zero extra records, and zero value mismatches, while evaluating contract findings as required by Sections 5.7 and 7.2;
- **REQ-CFG-115.** treat reference-only and query-only fields as contract findings.

**REQ-CFG-094.** Because parser-native types differ between formats, strict-exact comparison across different input formats MAY report type mismatches for lexically similar values. A custom typed configuration is required when cross-format logical equivalence is intended.

## 7. Comparison behaviour

### 7.1 Comparison phases

**REQ-CMP-001.** Every comparison MUST perform all three phases in this order:

1. **Contract:** assess fields, logical types, key definitions, nullability, mappings, and declared data-contract constraints.
2. **Records:** align valid record identities and assess matching, missing, and extra records.
3. **Values:** compare corresponding values using declared comparators.

**REQ-CMP-002.** A finding or `not_assessable` item in an earlier phase MUST NOT automatically prevent later assessment.

**REQ-CMP-003.** Later comparison MUST continue wherever its prerequisites remain satisfied.

**REQ-CMP-004.** Configured content that cannot be compared safely MUST be `not_assessable`. Content deliberately excluded by field policy MUST be `not_assessed`.

**REQ-CMP-005.** A run MUST conceptually:

1. validate the effective comparison configuration;
2. identify and hash inputs;
3. parse inputs without silent loss;
4. perform the contract phase;
5. align and compare records;
6. compare values for safely aligned records;
7. determine whether every configured assessment was completed;
8. write results and provenance atomically.

### 7.2 Contract comparison

**REQ-CMP-006.** The contract phase MUST assess declared and observed fields from both directions for every record. It MUST distinguish:

- **REQ-CMP-034.** field present and valid;
- **REQ-CMP-035.** required field missing from the reference or query;
- **REQ-CMP-036.** observed undeclared field and the treatment required by `fields.undeclared`;
- **REQ-CMP-037.** invalid logical type, null state, mapping, or controlled value;
- **REQ-CMP-038.** field deliberately `not_assessed`;
- **REQ-CMP-039.** field `not_assessable` because a prerequisite failed.

**REQ-CMP-007.** One record’s observed field set MUST NOT be assumed to represent every other record.

**REQ-CMP-008.** Key presence, validity, and uniqueness MUST always be assessed because later interpretation depends on an unambiguous record model.

**REQ-CMP-009.** For a zero-record dataset, contract requirements that can be evaluated from available structural information, such as CSV or TSV headers, MUST still be assessed.

**REQ-CMP-010.** A requirement that depends on examining a record and cannot be evaluated because no records exist MUST be reported as `not_assessable`. It MUST NOT be treated as satisfied merely because no contradictory record was observed.

### 7.3 Records comparison

**REQ-CMP-011.** For the union of normalised valid record keys, the records phase MUST classify each key as matching, missing from the query, or extra in the query. Duplicate or otherwise invalid keys are execution errors under Section 8.3, not ordinary record findings.

**REQ-CMP-012.** Missing records MUST be reported individually. Extra records MUST be reported individually. Query-only records MUST NOT be ignored. Missing or extra records MUST NOT prevent value comparison of the safely aligned intersection.

### 7.4 Values comparison and comparators

**REQ-CMP-013.** The values phase MUST compare every configured, valid field in safely aligned records.

**REQ-CMP-014.** A value whose contract or alignment prerequisite failed MUST be `not_assessable`. Other values MUST continue to be compared.

**REQ-CMP-015.** The first release MUST support the following deterministic comparators with stable identifiers.

#### 7.4.1 `preserved_exact`

Used by the bundled strict-exact configuration. Values match according to the parser-native value model and equality rules in Section 5.6. No inference, coercion, mapping, normalisation, or tolerance is applied. Textual `"1"`, integer `1`, decimal `1.0`, and boolean `true` are distinct.

#### 7.4.2 `typed_exact`

Values match only when both are present, valid under their field policies, have the same declared logical type, and have equal canonical values. Null handling follows Section 6.6. Cross-type equality is not implicit.

#### 7.4.3 `normalised_string`

**REQ-CMP-016.** Only configured string normalisations are applied in their declared order. Equality is exact code-point equality after transformation. Applied transformations MUST be identifiable in the evidence.

#### 7.4.4 `numeric_exact`

**REQ-CMP-017.** Integer or decimal comparison MUST use canonical arbitrary-precision values. Integer and decimal remain different logical types. Differing source representations are comparable only when both are explicitly parsed as the same declared logical type, using a mapping where required.

#### 7.4.5 `numeric_tolerance`

```text
difference = abs(reference - query)
```

- **REQ-CMP-018.** Exactly one of `absolute_tolerance` or `relative_tolerance` MUST be specified.
- With `absolute_tolerance`, values match when `difference <= absolute_tolerance`.
- With `relative_tolerance`, values match when `difference <= relative_tolerance * abs(reference)`. A relative tolerance is expressed as a fraction; for example, `"0.05"` means five percent.
- **REQ-CMP-019.** Tolerances MUST be non-negative finite decimals.
- **REQ-CMP-020.** The boundary MUST be inclusive.
- **REQ-CMP-021.** Relative tolerance MUST be calculated using the magnitude of the reference value: `relative_tolerance × abs(reference)`. The reference and query therefore have distinct roles in this calculation. The same tolerance applies to query values above and below the reference.
- **REQ-CMP-022.** When the reference value is zero, a relative tolerance permits only an exactly equal query value. An absolute tolerance MUST be used when non-zero differences around a zero reference are intended to match.
- **REQ-CMP-023.** Rounding or significant-figure normalisation MUST occur explicitly before comparison.

#### 7.4.6 `date_exact` and `datetime_exact`

**REQ-CMP-024.** Dates match when their canonical calendar dates are equal. Datetimes match when they represent the same instant after UTC-offset normalisation. Any precision reduction MUST be explicitly configured before comparison.

#### 7.4.7 `list_exact`, `set_exact`, and `multiset_exact`

- **REQ-CMP-025.** Lists use ordered element-by-element comparison and their lengths MUST match.
- Sets use order-independent comparison of unique elements; duplicate source elements are invalid under Section 6.5.7.
- Multisets use order-independent comparison that preserves occurrence counts.
- Elements use the declared element comparator.

### 7.5 Completeness, subsets, and determinism

- **REQ-CMP-026.** Comparison findings MUST NOT terminate a normal run.
- **REQ-CMP-027.** All assessable differences MUST be collected.
- **REQ-CMP-028.** A malformed record that prevents a complete and unambiguous record model MUST be an input error.
- **REQ-CMP-029.** A malformed record MUST NOT disappear silently.
- **REQ-CMP-030.** Key fields MUST always be processed.
- **REQ-CMP-031.** Under `fields.undeclared: "exclude"`, undeclared fields MUST be represented by a summary rather than by an individual finding for every excluded occurrence. The canonical report MUST record a stable exclusion code, the policy, the affected input field names, and the number of excluded records or values where calculable.
- **REQ-CMP-032.** Record order MUST NOT affect results unless explicitly declared significant.
- **REQ-CMP-033.** Output ordering MUST be deterministic and independent of hash-map ordering and locale.

## 8. Findings and run status

### 8.1 Finding structure

**REQ-FND-001.** Every finding MUST follow the structured representation in Section 9.1.2 and the normative results schema.

**REQ-FND-002.** Every finding MUST contain a stable finding code, deterministic report-local ID, phase, affected side, and human-readable message.

**REQ-FND-003.** Record identity, source locations, canonical or source field name, review priority, and value evidence MUST be present exactly where required by the finding code and data-minimisation rules.

**REQ-FND-004.** Human-readable messages MUST NOT be the sole machine-readable representation of a finding.

**REQ-FND-005.** Successful field matches MUST be represented in summary counts. Successful record matches MUST be represented in summary counts. Successful matches MUST NOT produce individual findings.

### 8.2 Minimum finding categories

**REQ-FND-006.** Stable finding codes MUST exist for at least:

- **REQ-FND-008.** missing record;
- **REQ-FND-009.** extra record;
- **REQ-FND-010.** missing required field;
- **REQ-FND-011.** undeclared field;
- **REQ-FND-012.** type mismatch;
- **REQ-FND-013.** invalid field value, including an attributable field-level parse or data-contract failure;
- **REQ-FND-014.** null-policy violation;
- **REQ-FND-015.** mapping failure;
- **REQ-FND-016.** value mismatch;
- **REQ-FND-017.** not assessable;

**REQ-FND-007.** Execution errors MUST NOT be represented as findings or assigned finding codes. In particular, invalid invocation or configuration, malformed input structure, invalid record keys, resource failure, I/O failure, and internal failure are execution errors governed by Section 8.3.

### 8.3 Run status

**REQ-RUN-001.** Run status MUST be one of:

- **REQ-RUN-015.** `complete`: every configured assessment was performed wherever the configuration and inputs made it applicable;
- **REQ-RUN-016.** `incomplete`: the inputs and record model remain sufficiently trustworthy for a useful comparison, but one or more configured assessments could not be completed safely because a comparison prerequisite was not satisfied;
- **REQ-RUN-017.** `error`: no trustworthy comparison result could be produced because of an invalid invocation or comparison configuration, malformed or unreadable input syntax or structure, a missing, null, invalid, or duplicate record key, an incomplete or ambiguous record model, an enforced resource limit, resource exhaustion, an input/output failure, or an unexpected internal failure.

**REQ-RUN-002.** Differences between valid, assessable reference and query content — including contract findings, missing or extra records, and value mismatches — MUST NOT by themselves change a run from `complete` to `incomplete` or `error`. The run status describes completeness and operational validity, not acceptability.

**REQ-RUN-003.** Any configured content classified as `not_assessable` MUST make the run `incomplete`.

**REQ-RUN-004.** Deliberately `not_assessed` content MUST NOT make the run `incomplete`.

**REQ-RUN-005.** An incomplete report MUST identify the affected content. It MUST identify why the comparison prerequisite was not satisfied.

**REQ-RUN-006.** Content that is parseable and attributable to an unambiguous record but violates the declared data contract MUST be recorded as a comparison finding rather than an error.

**REQ-RUN-007.** Comparisons that remain assessable MUST continue.

**REQ-RUN-008.** An error report SHOULD be written where possible. When written, it MUST be identified as an error report.

An error report is a diagnostic artefact, not a comparison result or evidence package.

**REQ-RUN-009.** When an error report can be written safely, it MUST contain `run_status: error`, a stable execution error code and category, a concise actionable message, and sufficient non-sensitive context to locate the cause.

**REQ-RUN-010.** An error report MUST NOT contain findings, finding codes, comparison summary metrics, or phase statuses.

**REQ-RUN-011.** Findings accumulated internally before the error occurred MUST NOT be published as a partial comparison result.

**REQ-RUN-012.** Each phase MUST record whether it was `complete` or `incomplete`.

Overall status is `complete` only when all three phases are complete.

**REQ-RUN-013.** The tool MUST report raw findings and metrics without applying acceptance thresholds. It MUST NOT produce a pass/fail verdict.

### 8.4 Laboratory decision

The run status and reported differences do not constitute a laboratory validation, approval, or acceptance decision. Any acceptance criteria and their application belong to a separately governed process outside the tool.

**REQ-RUN-014.** Reports MUST label these concepts separately. Reports MUST NOT describe the output as “ISO 15189 compliant”, “clinically validated”, or equivalent.

## 9. Output and evidence

**REQ-OUT-001.** A non-error comparison, whether `complete` or `incomplete`, MUST create an evidence-package directory at the destination selected by `--output`.

**REQ-OUT-002.** The evidence package MUST contain the canonical JSON result. It MUST contain the HTML report. A CSV findings export MAY also be included.

**REQ-OUT-003.** Package member names MUST be stable and documented. Package layout MUST be stable and documented.

### 9.1 Machine-readable output

**REQ-OUT-004.** JSON MUST be the canonical output format. Its normative JSON Schema Draft 2020-12 definition is [`src/adviso_validation/schemas/comparison-results-v1.0.schema.json`](src/adviso_validation/schemas/comparison-results-v1.0.schema.json).

**REQ-OUT-005.** The standalone results-schema file MUST be version controlled. It MUST be included as package data in `adviso_validation.schemas`. It MUST be resolvable together with the comparison-configuration schema that it references.

The result-schema version and comparison-configuration-schema version are independent.

**REQ-OUT-006.** The canonical result MUST contain exactly these top-level properties:

- **REQ-OUT-050.** `results_schema_version`;
- **REQ-OUT-051.** `run`;
- **REQ-OUT-052.** `phases`;
- **REQ-OUT-053.** `software`;
- **REQ-OUT-054.** `runtime`;
- **REQ-OUT-055.** `inputs`;
- **REQ-OUT-056.** `record_key_fields`;
- **REQ-OUT-057.** `comparison_configuration`;
- **REQ-OUT-058.** `summary`;
- **REQ-OUT-059.** `exclusions`;
- **REQ-OUT-060.** `findings`.

Every property is required, including empty `exclusions` and `findings` arrays.

**REQ-OUT-007.** Unknown properties MUST be rejected at every defined object level.

**REQ-OUT-008.** The schema accepts only non-error results with run status `complete` or `incomplete`. An execution-error diagnostic under Section 8.3 is not a canonical comparison result and MUST NOT validate against this schema.

**REQ-OUT-009.** The `run` object MUST contain a randomly generated UUID `id`, `status`, and `completed_at`.

**REQ-OUT-010.** `completed_at` MUST be an RFC 3339 UTC timestamp using `Z`.

**REQ-OUT-011.** Start time MUST NOT be included. Elapsed duration MUST NOT be included.

**REQ-OUT-012.** Run ID and completion time are deliberately variable metadata. They MAY be excluded from semantic-determinism comparisons.

**REQ-OUT-013.** The `phases` object MUST contain `contract`, `records`, and `values`, each with status `complete` or `incomplete`.

**REQ-OUT-014.** Overall run status MUST be `complete` if and only if all three phases are complete.

**REQ-OUT-015.** The `software` object MUST identify `adviso-validation` and its version. A build identifier MAY be included when available.

**REQ-OUT-016.** The `runtime` object MUST record Python version, a normalized non-identifying platform identifier, and the Unicode-data version.

**REQ-OUT-017.** Hostname, username, environment variables, working directory, absolute paths, raw command line, and a full dependency inventory MUST NOT be included.

**REQ-OUT-018.** Each input object MUST contain its automatically captured basename, selected format, UTF-8 encoding, byte size, and SHA-256 digest of the exact input bytes.

**REQ-OUT-019.** Absolute paths MUST NOT be included.

Basenames form part of the potentially sensitive evidence covered by Section 11.

**REQ-OUT-020.** V1 MUST use one fixed documented interpretation for CSV. It MUST use one fixed documented interpretation for TSV. Because format uniquely determines that interpretation, no dialect identifier appears in the result.

**REQ-OUT-021.** `record_key_fields` MUST declare the ordered source key-field names for the reference and query and the ordered canonical key-field names. Findings identify records through corresponding ordered arrays of source lexical values and canonical textual values. A single-field key is represented by a one-element array. Each identity array MUST have the same length as its corresponding field-name array. The reference or query identity is JSON null when that record is absent on that side; the canonical identity is always present.

**REQ-OUT-022.** `comparison_configuration.document` MUST contain the complete validated JSON-compatible representation of the comparison configuration, including the bundled configuration when no custom file was supplied.

**REQ-OUT-023.** The embedded document MUST validate against the referenced comparison-configuration schema.

No comparison-configuration digest or command-invocation object is included in version 1.

**REQ-OUT-024.** Consumers MUST validate `results_schema_version` before interpreting a result.

**REQ-OUT-025.** Consumers MUST use structured properties and finding codes for program logic. They MUST NOT infer semantics by parsing human-readable finding messages.

#### 9.1.1 Value evidence

**REQ-OUT-026.** When a finding includes field evidence, `values.reference` and `values.query` MUST each state whether the field is `present` or `absent`. An absent side has no source or canonical value. An explicit null is present and is represented explicitly rather than as absence.

**REQ-OUT-027.** Parser-native source values MUST use typed objects. Strings retain their text; integer and decimal values retain their source lexical text; booleans use JSON booleans; null has no `value`; arrays contain recursively typed source values; and objects map member names to recursively typed source values.

**REQ-OUT-028.** Object member order has no semantic significance. Object members MUST be serialized in Unicode code-point order.

**REQ-OUT-029.** Canonical scalar values MUST contain their logical type and value. Strings use JSON strings, booleans use JSON booleans, and dates and datetimes use canonical ISO text. Integers and decimals use normalized exact decimal text: no leading plus sign or unnecessary leading or trailing zeros, zero represented as `"0"`, and normalized lowercase scientific notation permitted where needed. Canonical collections contain the collection logical type, scalar element type, and an array of compact canonical element values. Lists preserve order; sets and multisets use deterministic canonical order; multisets retain duplicates. Null uses the declared logical type with a JSON null value. A `preserved_exact` field has no typed canonical value.

**REQ-OUT-030.** Values MUST be included only as follows:

- **REQ-OUT-061.** missing and extra record findings contain no field values;
- **REQ-OUT-062.** missing-required-field findings contain presence states but do not reproduce the present side's value;
- **REQ-OUT-063.** undeclared-field findings contain no field value;
- **REQ-OUT-064.** type-mismatch findings contain source values for affected sides and canonical values only where parsing succeeded;
- **REQ-OUT-065.** invalid-field-value and mapping-failure findings contain the affected source value and no failed canonical value;
- **REQ-OUT-066.** null-policy-violation findings contain the affected source and canonical null representation;
- **REQ-OUT-067.** value-mismatch findings contain source and canonical values for both sides;
- **REQ-OUT-068.** not-assessable findings contain only values necessary to explain the failed prerequisite.

**REQ-OUT-031.** Implementations MUST NOT add additional source values merely for convenience.

#### 9.1.2 Findings

**REQ-OUT-032.** Every finding MUST contain a deterministic report-local ID, finding code, phase, human-readable English message, and affected side.

**REQ-OUT-033.** A message is presentation text derived deterministically from structured properties. It MUST NOT add facts absent from those properties. Consumers MUST NOT parse it for program logic.

Specification-requirement identifiers and a separate finding category are not included in version 1.

The closed version 1 finding-code vocabulary is:

- `missing_record`;
- `extra_record`;
- `missing_required_field`;
- `undeclared_field`;
- `type_mismatch`;
- `invalid_field_value`;
- `null_policy_violation`;
- `mapping_failure`;
- `value_mismatch`;
- `not_assessable`.

**REQ-OUT-034.** `affected_side` MUST be `reference`, `query`, or `both`. A finding attributable to a declared canonical field MUST contain that field name and its resolved review priority. An undeclared-field finding instead contains the source field name. Record-specific findings MUST contain record identity and source locations; dataset-level findings omit record identity.

For CSV and TSV, a source location records the one-based data-record number where applicable, the one-based starting physical line number, and the source field name where applicable. For JSON, it records an RFC 6901 JSON Pointer. The reference and query locations are represented independently; a location is null when the corresponding record or field does not exist.

**REQ-OUT-035.** Findings MUST be sorted deterministically by phase, canonical record identity, canonical field name, finding code, affected side, and source location, using locale-independent Unicode code-point ordering. IDs `F000001`, `F000002`, and so on MUST be assigned after sorting. IDs are stable within one result but are not persistent identifiers across materially different comparisons.

**REQ-OUT-036.** Comparator parameters, mappings, and normalisation declarations MUST NOT be repeated in findings. Consumers and the HTML renderer obtain them from the embedded configuration using the canonical field name. Source and canonical values show their effect for the affected record.

#### 9.1.3 Summary and exclusions

**REQ-OUT-037.** The summary MUST contain complete fixed-shape counts, including zero-valued entries. Record counts comprise reference records, query records, matched records, missing records, and extra records. Value counts comprise matched, mismatched, and not-assessable in-scope non-key value opportunities. Finding counts comprise total findings, every version 1 finding code, and review priorities `low`, `normal`, `high`, and `unassigned`.

**REQ-OUT-038.** Record counts MUST reconcile as follows:

```text
reference = matched + missing
query = matched + extra
```

**REQ-OUT-039.** Every in-scope non-key value opportunity MUST be classified exactly once as matched, mismatched, or not assessable. Record-key fields are not compared or counted again in the values phase. For declared non-key fields in aligned records:

- **REQ-OUT-069.** both valid present values are compared normally;
- **REQ-OUT-070.** two absent optional fields match;
- **REQ-OUT-071.** one absent optional field and one present field mismatch;
- **REQ-OUT-072.** absence on a required side is not assessable;
- **REQ-OUT-073.** an invalid or prohibited value that prevents comparison is not assessable.

Under `fields.undeclared: compare`, undeclared non-key fields in aligned records are value opportunities: fields present on both sides use `preserved_exact`; one-sided fields create an undeclared-field finding and are not assessable. Under `exclude`, they are not value opportunities. Under `fail`, they create undeclared-field findings, are not compared, and are counted as not assessable.

**REQ-OUT-040.** `summary.findings.total` MUST equal the number of emitted findings. Counts by code and counts by review priority MUST each sum to the total. Findings not attributable to a declared field, including record and undeclared-field findings, count as `unassigned` review priority.

**REQ-OUT-041.** `exclusions` MUST always be an array. Under `fields.undeclared: exclude`, it contains one entry per source field and dataset side, recording code `undeclared_field_excluded`, side, source field name, and the number of records containing the field. Entries MUST be ordered by side and source field name. Exclusions are not findings, do not have review priorities, and do not contribute to value counts. A column known from a zero-record CSV or TSV header has record count zero.

### 9.2 Human-readable output

**REQ-OUT-042.** The first release MUST produce an HTML human-readable report. The report SHOULD include:

- **REQ-OUT-074.** purpose of the run and the three comparison phases performed;
- **REQ-OUT-075.** prominent run status and per-phase completion status;
- **REQ-OUT-076.** identities of reference, query, and comparison configuration;
- **REQ-OUT-077.** summary counts;
- **REQ-OUT-078.** measured counts and findings, without an acceptance verdict;
- **REQ-OUT-079.** grouped discrepancy details;
- **REQ-OUT-080.** limitations, exclusions, and unassessed content;
- **REQ-OUT-081.** provenance and reproduction information;
- **REQ-OUT-082.** space or linkage for review and approval outside the tool.

**REQ-OUT-043.** CSV MAY be provided as an export of findings, but MUST:

- **REQ-OUT-083.** be produced using a conforming CSV writer;
- **REQ-OUT-084.** preserve record identifiers;
- **REQ-OUT-085.** quote delimiters, quotes, and newlines correctly;
- **REQ-OUT-086.** use a stable documented column schema;
- **REQ-OUT-087.** mitigate spreadsheet formula injection when intended for spreadsheet use;
- **REQ-OUT-088.** never be the only canonical evidence format.

### 9.3 Atomicity and overwrite protection

- **REQ-OUT-044.** Output files MUST be written atomically where supported.
- **REQ-OUT-045.** The complete evidence-package directory MUST be published atomically where the platform supports it.
- **REQ-OUT-046.** An existing destination MUST NOT be overwritten unless the user supplies `--overwrite`.
- **REQ-OUT-047.** The actual selected output directory MUST be reported clearly.
- **REQ-OUT-048.** File suffixes MUST be handled structurally, not with character stripping.
- **REQ-OUT-049.** A failed or interrupted write MUST NOT publish a partial directory at the selected destination as if it were a complete evidence package. Temporary output MUST be identifiable as temporary and cleaned up where possible.

## 10. Command-line interface

### 10.1 General behaviour

- **REQ-CLI-001.** A subcommand MUST be required.
- **REQ-CLI-002.** Invalid argument combinations MUST be rejected before input processing.
- **REQ-CLI-003.** Modes and formats MUST use enumerated choices.
- **REQ-CLI-004.** `--help` and `--version` MUST work without other arguments.
- **REQ-CLI-005.** Errors MUST be concise on standard error and actionable.
- **REQ-CLI-006.** Normal summaries SHOULD be written to standard output.
- **REQ-CLI-007.** Comparison progress SHOULD be optional.
- **REQ-CLI-008.** Comparison progress MUST NOT contaminate machine-readable output.

### 10.2 Proposed comparison interface

The conceptual interface is:

```text
adviso-validation compare \
  --reference REFERENCE \
  --query QUERY \
  --output OUTPUT \
  [--configuration CONFIGURATION] \
  [--overwrite]
```

**REQ-CLI-009.** `--configuration` MUST be optional.

**REQ-CLI-010.** Omission of `--configuration` MUST select the bundled strict-exact configuration. When `--configuration` is present, its value MUST be treated as the path to a custom comparison-configuration file.

**REQ-CLI-011.** `--output` MUST name the evidence-package directory described in Section 9.

**REQ-CLI-012.** `--overwrite` MUST provide the explicit overwrite authorisation required by Section 9.3.

**REQ-CLI-013.** Input formats MUST be determined as specified in Section 5.2. Version 1 provides no command-line format overrides.

### 10.3 Exit codes

**REQ-CLI-014.** Exit codes MUST distinguish at least:

| Code | Meaning |
| ---: | --- |
| 0 | Run status is `complete`, whether or not differences were found |
| 1 | Run status is `incomplete` |
| 2 | Invocation, comparison-configuration, input, resource-limit, resource-exhaustion, or I/O error |
| 3 | Unexpected internal error |

**REQ-CLI-015.** These exit-code meanings MUST be stable. They MUST be documented.

**REQ-CLI-016.** A complete comparison that finds differences MUST still exit with code 0. It MUST write the evidence package.

Error classes represented by exit codes 2 and 3 have run status `error`. The distinct codes allow automation to distinguish expected operational errors from unexpected implementation failures.

### 10.4 Additional commands

**REQ-CLI-017.** The version 1 executable MUST expose no user-facing subcommand other than `compare`.

## 11. Security and data governance

- **REQ-SEC-001.** Input datasets and evidence packages MAY contain sensitive patient or laboratory information. Version 1 provides only the data-minimisation and non-disclosure safeguards specified below; it does not de-identify data or replace the laboratory's access-control and information-governance arrangements.
- **REQ-SEC-002.** The tool MUST operate locally.
- **REQ-SEC-003.** The tool MUST NOT transmit input data, comparison configurations, logs, or results over a network.
- **REQ-SEC-004.** Routine logs, progress output, terminal diagnostics, and execution-error diagnostics MUST NOT contain record identifiers or source values.
- **REQ-SEC-005.** Evidence packages MAY contain record identifiers and source values only where required to identify or explain findings.
- **REQ-SEC-006.** Human-readable reports MUST state prominently that the evidence package may contain sensitive information.
- **REQ-SEC-007.** Absolute paths, raw command lines, environment variables, and secrets MUST NOT be included in results, reports, or routine logs.
- **REQ-SEC-008.** Input basenames MUST be treated as potentially sensitive evidence.
- **REQ-SEC-009.** If temporary files are used, they MUST NOT be made more accessible than the intended output.
- **REQ-SEC-010.** Temporary files MUST be removed after successful completion.
- **REQ-SEC-011.** Temporary files SHOULD be removed following an error where this can be done safely.
- **REQ-SEC-012.** Comparison-configuration YAML MUST be parsed using the safe-loader rules in Section 6.2.1.
- **REQ-SEC-013.** Spreadsheet-oriented exports MUST mitigate formula injection.
- **REQ-SEC-014.** The tool SHOULD document filesystem permission expectations. The laboratory is responsible for supplying appropriately pseudonymised input data where required and for controlling access to, retention of, and disposal of inputs and evidence packages.
- Automated redaction, identifier pseudonymisation, keyed hashing, and field-level sensitivity policies are outside the scope of version 1.0.

## 12. Deployment, accessibility, and reliability

- **REQ-DEP-001.** all core comparison functionality MUST operate fully offline;
- **REQ-DEP-002.** the toolkit MUST NOT require a hosted service, account, licence server, or telemetry connection;
- **REQ-DEP-003.** an offline-installable artefact with integrity information SHOULD be provided;
- **REQ-DEP-004.** reports MUST use open formats;
- **REQ-DEP-005.** reports MUST NOT require proprietary software;
- **REQ-DEP-006.** errors and documentation SHOULD be usable without specialist Python knowledge;
- **REQ-DEP-007.** documentation and examples SHOULD be available offline;
- **REQ-DEP-008.** localisation SHOULD remain possible without changing result semantics.

**REQ-DEP-009.** Releases SHOULD state any enforced resource or input-size limits.

**REQ-DEP-010.** Every valid comparison accepted for processing MUST attempt to assess all configured content.

**REQ-DEP-011.** Exceeding a documented resource or input-size limit MUST produce an error. Encountering resource exhaustion at any stage MUST produce an error. A resource-limit or resource-exhaustion error MUST NOT produce a partial comparison result.

**REQ-DEP-012.** Interrupted runs MUST NOT leave apparently complete reports.

**REQ-DEP-013.** Results MUST remain deterministic across supported Python versions and operating systems.

**REQ-DEP-014.** Internal exceptions MUST be captured in an error report where safe. Concise diagnostics MUST be presented to the user.

## 13. Software quality and release requirements

### 13.1 Testing

**REQ-TST-001.** The project MUST include:

- **REQ-TST-009.** unit tests for parsing, typing, mapping, normalisation, and comparators;
- **REQ-TST-010.** behavioural contract tests for result semantics;
- **REQ-TST-011.** end-to-end CLI tests including exit codes;
- **REQ-TST-012.** schema validation tests for comparison configurations and canonical results;
- **REQ-TST-013.** installation tests from wheel and source distribution;
- **REQ-TST-014.** regression tests for every corrected material defect;
- **REQ-TST-015.** tests across all supported Python versions;
- **REQ-TST-016.** deterministic-output tests;
- **REQ-TST-017.** representative malformed and adversarial inputs;
- **REQ-TST-018.** tests for duplicate/composite keys and missing/extra content in both directions;
- **REQ-TST-019.** boundary tests for comparator tolerances.

**REQ-TST-002.** Property-based testing SHOULD be used for parsing and comparison invariants.

**REQ-TST-003.** Mutation testing SHOULD be used to assess whether the suite detects deliberately introduced comparison defects.

### 13.2 Test data

**REQ-TST-004.** Controlled test cases SHOULD record:

- **REQ-TST-020.** stable scenario identifier;
- **REQ-TST-021.** requirement(s) tested;
- **REQ-TST-022.** purpose and rationale;
- **REQ-TST-023.** input data and comparison configuration;
- **REQ-TST-024.** expected findings, counts, run status, per-phase statuses, and exit code;
- **REQ-TST-025.** fixture provenance or generation method;
- **REQ-TST-026.** fixture version and digest;
- **REQ-TST-027.** independent review status where used as formal validation evidence.

**REQ-TST-005.** Generated fixtures MUST be reproducible.

**REQ-TST-006.** Clinically derived fixtures MUST be appropriately de-identified and governed.

**REQ-TST-007.** Controlled test fixtures, including test comparison configurations, MUST be maintained by the development team under version control and its documented review process.

In operational use, each laboratory is responsible for creating, approving, maintaining, and retaining its own comparison configurations under its local quality-management arrangements. The AdvISO project does not centrally approve or manage laboratory configurations.

### 13.3 Continuous integration

**REQ-TST-008.** CI MUST:

- **REQ-TST-028.** run on proposed changes and protected branches;
- **REQ-TST-029.** install the built package, not rely solely on the source checkout;
- **REQ-TST-030.** test the console entry point;
- **REQ-TST-031.** test the supported Python matrix;
- **REQ-TST-032.** fail on enforced lint, type, test, and build errors;
- **REQ-TST-033.** validate that generated schemas and examples are current;
- **REQ-TST-034.** avoid publishing releases when required checks fail.

### 13.4 User documentation

**REQ-DOC-001.** Version 1 MUST include a version-controlled user guide or manual. The guide MUST be distributed with the software. It MUST be available offline. It MUST be written for users of the command-line tool and describe:

- **REQ-DOC-006.** installation and verification of the installed executable;
- **REQ-DOC-007.** the complete command-line interface, including inputs, outputs, defaults, exit codes, overwrite behaviour, and worked invocations;
- **REQ-DOC-008.** the supported input formats and their parsing, encoding, record, field, and filename-extension requirements;
- **REQ-DOC-009.** how to use the bundled strict-exact comparison configuration and how to create, validate, and govern a custom comparison configuration;
- **REQ-DOC-010.** every property in the comparison-configuration schema, including its purpose, permitted values, required or optional status, default or omission semantics, constraints, and interactions with other properties;
- **REQ-DOC-011.** the comparison phases, processing order, comparators, mappings, normalisation operations, null handling, undeclared-field behaviour, and review priorities;
- **REQ-DOC-012.** the contents and interpretation of the evidence package;
- **REQ-DOC-013.** every property in the canonical results JSON schema, including finding codes, typed source and canonical values, counts, exclusions, run and phase statuses, and provenance fields;
- **REQ-DOC-014.** execution-error diagnostics and common corrective actions;
- **REQ-DOC-015.** the tool's intended use, non-claims, security and data-governance boundaries, and known limitations; and
- **REQ-DOC-016.** the toolkit, comparison-configuration-schema, and results-schema versions to which the documentation applies.

**REQ-DOC-002.** The guide MUST include complete, runnable examples covering the bundled configuration and representative custom configuration features.

**REQ-DOC-003.** Configuration examples MUST validate against the published comparison-configuration schema. Results examples MUST validate against the published results schema.

**REQ-DOC-004.** Documentation MUST distinguish machine-enforced schema constraints from explanatory guidance. It MUST accurately describe the behaviour of the documented toolkit version and MUST NOT contradict the machine-readable schemas it supports. Any material inconsistency is a release-blocking documentation defect.

**REQ-DOC-005.** Command-line `--help` output MUST provide a concise description of every command and option. It MUST direct users to the full guide.

### 13.5 Releases and change control

**REQ-REL-001.** Each release SHOULD provide:

- **REQ-REL-006.** an immutable semantic version;
- **REQ-REL-007.** release notes and known limitations;
- **REQ-REL-008.** compatibility statements for comparison-configuration and results schemas;
- **REQ-REL-009.** documented change-impact assessment;
- **REQ-REL-010.** signed or otherwise attestable source and build artefacts where practical;
- **REQ-REL-011.** a reproducible lockfile or equivalent dependency record;
- **REQ-REL-012.** evidence that required verification tests passed.

**REQ-REL-002.** Comparison-configuration schema versions, results-schema versions, and toolkit versions MUST be independent.

**REQ-REL-003.** Each toolkit release MUST document the comparison-configuration schema versions it supports. It MUST document the results schema versions it supports.

**REQ-REL-004.** An unsupported schema version MUST be rejected clearly rather than interpreted approximately.

**REQ-REL-005.** The project MUST publish migration and compatibility rules before changing either schema. It MUST provide a migration path or documented transition period for any incompatible change.

## 14. Acceptance-test catalogue

This catalogue summarises minimum executable scenarios for the first release. It verifies, but does not independently define, the normative behaviour above. Every scenario lists the requirements it verifies.

### 14.1 Input and contract scenarios

- **AT-CON-001:** Identical typed datasets satisfy their contract.
  - Verifies: `REQ-VAL-003`, `REQ-VAL-004`, `REQ-CMP-006`, `REQ-RUN-002`
- **AT-CON-002:** Required missing fields produce contract findings in both directions and across heterogeneous records; optional missing fields do not. Observed undeclared fields are handled according to each `fields.undeclared` mode and aligned only by identical input names under `compare`. This consolidated parameterized scenario also covers: `fields.undeclared` is required and accepts only `compare`, `exclude`, or `fail`; omission and unknown policies are rejected. Every declared field supplies non-empty `source.reference` and `source.query` names, including when the field is optional on either side; the `required` flags govern record-level presence rather than whether a correspondence is declared.
  - Verifies: `REQ-CFG-030`, `REQ-CFG-031`, `REQ-CFG-037`, `REQ-CFG-038`, `REQ-CFG-039`, `REQ-CMP-006`, `REQ-CMP-007`, `REQ-CMP-034`, `REQ-CMP-035`, `REQ-CMP-036`, `REQ-FND-010`, `REQ-FND-011`, `REQ-VAL-002`, `REQ-CFG-035`, `REQ-CFG-036`
- **AT-CON-004:** Null, empty string, whitespace-only string, absent field, and configured missing tokens remain distinct according to policy. This consolidated parameterized scenario also covers: The bundled strict-exact configuration treats parser-native null as equal only to null and distinguishes null, absent fields, and empty strings.
  - Verifies: `REQ-CFG-053`, `REQ-CFG-054`, `REQ-CFG-055`, `REQ-CFG-056`, `REQ-CFG-057`, `REQ-VAL-014`, `REQ-VAL-047`, `REQ-VAL-048`, `REQ-VAL-049`, `REQ-VAL-050`, `REQ-VAL-051`, `REQ-VAL-052`, `REQ-VAL-053`, `REQ-VAL-054`, `REQ-VAL-055`, `REQ-INP-028`, `REQ-CFG-113`
- **AT-CON-005:** Unknown, conflicting, and incomplete mappings fail clearly; mapping to null differs from a missing map entry. This consolidated parameterized scenario also covers: Source-value descriptors distinguish strings, numbers, booleans, and null; mapping to null remains distinct from an absent mapping entry. Parameterized mapping fixtures verify reference/query-to-canonical field mapping, required-field reporting, undeclared-field handling, declared source and destination types, permitted intentional many-to-one mappings, and rejection of accidental non-one-to-one mappings.
  - Verifies: `REQ-CFG-065`, `REQ-CFG-071`, `REQ-CFG-072`, `REQ-CFG-073`, `REQ-CFG-074`, `REQ-VAL-058`, `REQ-VAL-065`, `REQ-VAL-067`, `REQ-CFG-058`, `REQ-CFG-059`, `REQ-VAL-068`, `REQ-VAL-056`, `REQ-VAL-057`, `REQ-VAL-059`, `REQ-VAL-060`, `REQ-VAL-064`, `REQ-VAL-066`
- **AT-CON-006:** Malformed syntax or structure, empty or duplicate column names, and irregular tabular rows receive their specified error classification without silent data loss. This consolidated parameterized scenario also covers: A table-driven parser suite verifies the fixed CSV and TSV dialects, UTF-8-only decoding, CRLF/LF equivalence, quoted delimiters, doubled quotes, embedded line breaks, source-row retention, and initial string preservation.
  - Verifies: `REQ-INP-021`, `REQ-INP-022`, `REQ-INP-023`, `REQ-INP-024`, `REQ-INP-025`, `REQ-INP-034`, `REQ-INP-035`, `REQ-INP-036`, `REQ-INP-037`, `REQ-INP-038`, `REQ-CMP-028`, `REQ-CMP-029`, `REQ-PRN-002`, `REQ-PRN-008`, `REQ-INP-010`, `REQ-INP-011`, `REQ-INP-012`, `REQ-INP-014`, `REQ-INP-015`, `REQ-INP-016`, `REQ-INP-017`, `REQ-INP-018`, `REQ-INP-019`, `REQ-INP-020`, `REQ-INP-026`, `REQ-INP-027`, `REQ-INP-063`, `REQ-INP-064`
- **AT-CON-007:** For two syntactically valid zero-record datasets, the records phase reports no missing or extra records and the values phase performs no comparisons under every configuration. Independently assessable contract requirements are still evaluated, and requirements that depend on examining a record are `not_assessable`. One-sided empty datasets produce all applicable missing or extra record findings.
  - Verifies: `REQ-INP-052`, `REQ-INP-053`, `REQ-INP-054`, `REQ-INP-055`, `REQ-INP-056`, `REQ-INP-057`, `REQ-INP-058`, `REQ-INP-059`, `REQ-CMP-009`, `REQ-CMP-010`, `REQ-CFG-114`
- **AT-CON-008:** Comparison-configuration YAML scalar resolution and cross-format typed dataset parsing are deterministic across supported environments.
  - Verifies: `REQ-CFG-006`, `REQ-INP-039`, `REQ-INP-040`, `REQ-INP-041`, `REQ-INP-042`, `REQ-INP-043`, `REQ-INP-044`, `REQ-DEP-013`
- **AT-CON-011:** A complete custom YAML configuration conforming to Section 6.2 validates; omitted optional processing properties and dataset sides expand to empty internal structures in the effective configuration, while explicitly empty placeholder lists or mappings are rejected.
  - Verifies: `REQ-CFG-003`, `REQ-CFG-005`, `REQ-CFG-014`, `REQ-CFG-060`, `REQ-CFG-061`, `REQ-CFG-062`, `REQ-CFG-063`, `REQ-CFG-069`, `REQ-CFG-070`, `REQ-CFG-075`, `REQ-CFG-076`
- **AT-CON-012:** Duplicate or unknown YAML keys, unsafe YAML features, unsupported schema versions, invalid enumerations, and incompatible type/comparator combinations are rejected with precise configuration paths. This consolidated parameterized scenario also covers: Safe-loader tests confirm that configuration parsing cannot construct arbitrary objects or execute tagged payloads.
  - Verifies: `REQ-CFG-007`, `REQ-CFG-008`, `REQ-CFG-009`, `REQ-CFG-010`, `REQ-CFG-013`, `REQ-CFG-017`, `REQ-CFG-048`, `REQ-CFG-051`, `REQ-CFG-052`, `REQ-CFG-065`, `REQ-CFG-078`, `REQ-CFG-079`, `REQ-CFG-080`, `REQ-CFG-085`, `REQ-CFG-091`, `REQ-SEC-012`
- **AT-CON-014:** The authoritative schema is present in the source tree and built distribution, can be loaded through the installed package-resource API, and validates every complete configuration example and controlled configuration fixture. This consolidated parameterized scenario also covers: The packaged results schema resolves its configuration-schema reference, accepts representative complete and incomplete canonical results, rejects unknown properties and execution-error diagnostics, and requires exactly the documented top-level result properties.
  - Verifies: `REQ-CFG-016`, `REQ-CFG-087`, `REQ-CFG-088`, `REQ-OUT-004`, `REQ-OUT-005`, `REQ-OUT-006`, `REQ-OUT-007`, `REQ-OUT-050`, `REQ-OUT-051`, `REQ-OUT-052`, `REQ-OUT-053`, `REQ-OUT-054`, `REQ-OUT-055`, `REQ-OUT-056`, `REQ-OUT-057`, `REQ-OUT-058`, `REQ-OUT-059`, `REQ-OUT-060`
- **AT-CON-015:** Configurations that are structurally schema-valid but violate a semantic rule in Section 6.2.9 are rejected with the relevant configuration path and rule.
  - Verifies: `REQ-CFG-090`, `REQ-CFG-091`, `REQ-CFG-104`, `REQ-CFG-105`, `REQ-CFG-106`, `REQ-CFG-107`, `REQ-CFG-108`
- **AT-CON-016:** `review_priority` accepts only `low`, `normal`, or `high`; omission resolves to `normal` in the effective configuration.
  - Verifies: `REQ-CFG-040`
- **AT-CON-017:** `fields.record_key` is required, non-empty, ordered, and free of duplicate component fields; every entry names a field in `fields.definitions` that satisfies all key-field constraints.
  - Verifies: `REQ-CFG-024`, `REQ-CFG-025`, `REQ-CFG-026`, `REQ-CFG-027`, `REQ-CFG-029`, `REQ-CFG-034`, `REQ-CFG-104`, `REQ-CFG-105`
- **AT-CON-018:** `metadata.id` and `metadata.revision` are required non-empty strings; title and description are optional, and metadata does not alter comparison behaviour.
  - Verifies: `REQ-CFG-018`, `REQ-CFG-020`, `REQ-CFG-022`
- **AT-CON-021:** A table-driven JSON parser suite verifies the record-oriented root structure, preserved string-like tokens and numerical lexical forms, and the distinct finding, `not_assessable`, continuation, and execution-error outcomes for non-finite values in non-key fields and record keys.
  - Verifies: `REQ-INP-029`, `REQ-INP-030`, `REQ-INP-033`, `REQ-INP-047`, `REQ-INP-048`, `REQ-INP-049`, `REQ-INP-050`, `REQ-INP-051`, `REQ-INP-065`
- **AT-CON-022:** Every comparison resolves one effective configuration whose schema version, identifier, revision, record key, field definitions, undeclared-field policy, and comparison rules are validated before either dataset is read; unknown keys fail with actionable locations, and the validated configuration is embedded in results.
  - Verifies: `REQ-CFG-001`, `REQ-CFG-002`, `REQ-CFG-012`, `REQ-CFG-086`, `REQ-CFG-095`, `REQ-CFG-096`, `REQ-CFG-097`, `REQ-CFG-098`, `REQ-CFG-099`, `REQ-CFG-100`, `REQ-CFG-101`, `REQ-CFG-102`, `REQ-CFG-103`
- **AT-CON-023:** Parameterized configuration fixtures verify canonical field-name mapping, collection logical-type structure, legal omission of `logical_type` and operation parameters, placement and side-specific application of source and typed normalisation, and the required comparator declaration.
  - Verifies: `REQ-CFG-028`, `REQ-CFG-032`, `REQ-CFG-033`, `REQ-CFG-049`, `REQ-CFG-050`, `REQ-CFG-064`, `REQ-CFG-066`, `REQ-CFG-067`, `REQ-CFG-077`
- **AT-CON-024:** The bundled configuration is schema-valid and implements the documented strict-exact behavior: `record_id` is the key on both sides, shared non-key fields require no declarations, reference-only and query-only fields become contract findings, and cross-format parser-native type differences remain distinguishable. This consolidated parameterized scenario also covers: `preserved_exact` follows the parser-native category table, including deterministic same-format and cross-format comparisons.
  - Verifies: `REQ-CFG-093`, `REQ-CFG-094`, `REQ-CFG-109`, `REQ-CFG-110`, `REQ-CFG-115`, `REQ-INP-039`, `REQ-INP-046`, `REQ-CFG-111`, `REQ-CFG-112`, `REQ-CMP-032`

### 14.2 Record scenarios

- **AT-REC-001:** Every reference-only record is reported as missing and every query-only record as extra, including when both occur together.
  - Verifies: `REQ-INP-058`, `REQ-INP-059`, `REQ-CMP-011`, `REQ-CMP-012`, `REQ-FND-008`, `REQ-FND-009`, `REQ-PRN-003`
- **AT-REC-002:** Duplicate single and composite keys produce execution errors without overwriting data; each error identifies the affected dataset, duplicate normalised key, and available source-record locations.
  - Verifies: `REQ-REC-003`, `REQ-REC-009`, `REQ-REC-010`, `REQ-REC-011`, `REQ-REC-012`, `REQ-REC-013`, `REQ-REC-014`
- **AT-REC-003:** Composite keys preserve multiple legitimate records belonging to one sample.
  - Verifies: `REQ-REC-001`, `REQ-REC-002`, `REQ-CFG-024`
- **AT-REC-005:** Parameterized key fixtures verify that key names, aliases, composites, and normalisation are configuration-defined; key values are not implicitly converted; no command-line key override exists; and findings retain enough source identity to distinguish records.
  - Verifies: `REQ-REC-004`, `REQ-REC-005`, `REQ-REC-006`, `REQ-REC-007`, `REQ-REC-008`, `REQ-REC-015`

### 14.3 Typed value and comparator scenarios

- **AT-VAL-001:** Boolean `true`, integer `1`, decimal `1.0`, and textual `"1"` remain distinct under the applicable exact comparator. The parameterized suite also verifies declared parsing rather than inference and enumerates the stable comparator registry.
  - Verifies: `REQ-VAL-009`, `REQ-VAL-027`, `REQ-CMP-017`, `REQ-VAL-001`, `REQ-VAL-005`, `REQ-VAL-007`, `REQ-VAL-008`, `REQ-CMP-015`
- **AT-VAL-002:** Typed strings remain code-point-exact unless configured normalisations are applied in declared order.
  - Verifies: `REQ-INP-013`, `REQ-VAL-012`, `REQ-VAL-013`, `REQ-VAL-070`, `REQ-CMP-016`
- **AT-VAL-003:** Integer parsing accepts signed ASCII decimal integers and leading zeros but rejects decimal points, exponents, booleans, and invalid text. This consolidated parameterized scenario also covers: Leading-zero identifiers remain strings unless explicitly transformed.
  - Verifies: `REQ-VAL-015`, `REQ-VAL-016`, `REQ-VAL-017`, `REQ-VAL-018`
- **AT-VAL-004:** Decimal parsing is exact, accepts scientific notation, and rejects `NaN` and infinities. Invalid attributable non-key decimals are also checked as contract findings that become `not_assessable`, not execution errors.
  - Verifies: `REQ-INP-031`, `REQ-INP-032`, `REQ-INP-045`, `REQ-INP-046`, `REQ-VAL-019`, `REQ-VAL-020`, `REQ-VAL-021`, `REQ-VAL-022`, `REQ-VAL-023`, `REQ-VAL-011`
- **AT-VAL-005:** Boolean parsing accepts native booleans and lowercase textual `true` or `false`; other representations require a mapping.
  - Verifies: `REQ-VAL-024`, `REQ-VAL-025`, `REQ-VAL-026`, `REQ-VAL-027`
- **AT-VAL-006:** Dates reject invalid or non-ISO full dates; datetimes require offsets and compare as instants.
  - Verifies: `REQ-VAL-028`, `REQ-VAL-029`, `REQ-VAL-030`, `REQ-VAL-031`, `REQ-VAL-032`, `REQ-VAL-033`, `REQ-VAL-034`, `REQ-VAL-035`, `REQ-VAL-036`, `REQ-CMP-024`
- **AT-VAL-007:** Lists preserve order and duplicates, sets reject duplicates and ignore order, and multisets ignore order while preserving occurrence counts. This consolidated parameterized scenario also covers: Collection parsing accepts JSON arrays in JSON and JSON-array cell syntax in CSV/TSV, rejects ordinary delimited text, and rejects null collection elements with the specified finding and `not_assessable` evidence. The suite covers every supported typed collection kind and its required element declaration.
  - Verifies: `REQ-VAL-037`, `REQ-VAL-038`, `REQ-VAL-039`, `REQ-VAL-040`, `REQ-VAL-041`, `REQ-VAL-042`, `REQ-CMP-025`, `REQ-VAL-043`, `REQ-VAL-044`, `REQ-VAL-045`, `REQ-VAL-046`, `REQ-VAL-006`
- **AT-VAL-008:** Typed transformations follow Section 6.8 and retain evidence of the attributable source value. This consolidated parameterized scenario also covers: Parameterized normalisation fixtures exercise every registered source-text and typed-value operation, including Unicode, whitespace, case, datetime offset, precision, and unordered-collection ordering, and verify that rounding or significant-figure changes occur only when explicitly configured. The suite also verifies retention of source lexical evidence.
  - Verifies: `REQ-VAL-061`, `REQ-VAL-062`, `REQ-VAL-063`, `REQ-VAL-069`, `REQ-VAL-070`, `REQ-VAL-072`, `REQ-VAL-073`, `REQ-VAL-074`, `REQ-VAL-075`, `REQ-VAL-071`, `REQ-CMP-023`, `REQ-VAL-010`
- **AT-VAL-009:** Numeric tolerance accepts exactly one absolute or relative tolerance and rejects configurations containing neither or both. Each form uses exact decimal arithmetic and an inclusive boundary, with below, at, and above boundary cases; relative tolerance is reference-directed and permits no non-zero difference when the reference is zero.
  - Verifies: `REQ-CFG-081`, `REQ-CFG-082`, `REQ-CFG-083`, `REQ-CFG-084`, `REQ-CMP-018`, `REQ-CMP-019`, `REQ-CMP-020`, `REQ-CMP-021`, `REQ-CMP-022`
- **AT-VAL-010:** All assessable differences are collected in one run.
  - Verifies: `REQ-CMP-026`, `REQ-CMP-027`
- **AT-VAL-011:** Every defined field is included in comparison; under `fields.undeclared: "exclude"`, undeclared fields are `not_assessed` and represented by the required exclusion summary.
  - Verifies: `REQ-CFG-039`, `REQ-CMP-004`, `REQ-CMP-013`, `REQ-CMP-031`, `REQ-OUT-041`

### 14.4 Phase and run-status scenarios

- **AT-OUT-001:** Every comparison performs the contract, records, and values phases in order and records a completion status for each.
  - Verifies: `REQ-CMP-001`, `REQ-RUN-012`, `REQ-OUT-013`
- **AT-OUT-002:** A finding or `not_assessable` item in an earlier phase does not prevent later assessment where prerequisites remain satisfied.
  - Verifies: `REQ-CMP-002`, `REQ-CMP-003`, `REQ-RUN-007`
- **AT-OUT-005:** Complete, incomplete, invocation or input error, and unexpected internal error produce their documented exit behaviour. This consolidated parameterized scenario also covers: A fully performed comparison is `complete` whether it finds no differences or any combination of contract findings, missing records, extra records, and value mismatches.
  - Verifies: `REQ-RUN-001`, `REQ-RUN-015`, `REQ-RUN-016`, `REQ-RUN-017`, `REQ-CLI-014`, `REQ-CLI-015`, `REQ-CLI-016`, `REQ-RUN-002`
- **AT-OUT-006:** Configured `not_assessable` content produces `incomplete`; deliberately `not_assessed` content does not. This consolidated parameterized scenario also covers: Content excluded deliberately is `not_assessed`; configured content blocked by a failed prerequisite is `not_assessable`.
  - Verifies: `REQ-RUN-003`, `REQ-RUN-004`, `REQ-RUN-005`, `REQ-RUN-016`, `REQ-CMP-004`
- **AT-OUT-007:** Invalid configuration, malformed or unreadable input, an incomplete or ambiguous record model, an enforced resource limit, and resource exhaustion produce `error`, never `incomplete` or a partial comparison result.
  - Verifies: `REQ-RUN-017`, `REQ-RUN-010`, `REQ-RUN-011`, `REQ-DEP-011`
- **AT-OUT-008:** An end-to-end mixed-defect comparison exercises every conceptual processing step, including invalid contract values, deliberate exclusions, failed prerequisites, mandatory key processing, and continued comparison of unaffected values. This consolidated parameterized scenario also covers: A large mixed-content fixture verifies that every configured value opportunity is either assessed or explicitly classified and that no valid accepted content is silently skipped.
  - Verifies: `REQ-CMP-005`, `REQ-CMP-008`, `REQ-CMP-014`, `REQ-CMP-030`, `REQ-CMP-037`, `REQ-CMP-038`, `REQ-CMP-039`, `REQ-RUN-006`, `REQ-DEP-010`
- **AT-OUT-010:** A table-driven finding suite generates every finding code and verifies its structured fields, required contextual evidence, deterministic local ID, human-readable message, summary-only successful matches, and absence of message-only semantics. This consolidated parameterized scenario also covers: For every finding code, result fixtures enforce the code-specific inclusion and omission of source and canonical values, deterministic messages derived from structured data, deterministic sorting, and sequential report-local finding IDs.
  - Verifies: `REQ-PRN-006`, `REQ-FND-001`, `REQ-FND-002`, `REQ-FND-003`, `REQ-FND-004`, `REQ-FND-005`, `REQ-FND-006`, `REQ-FND-012`, `REQ-FND-013`, `REQ-FND-014`, `REQ-FND-015`, `REQ-FND-016`, `REQ-FND-017`, `REQ-OUT-032`, `REQ-OUT-033`, `REQ-OUT-035`, `REQ-OUT-061`, `REQ-OUT-062`, `REQ-OUT-063`, `REQ-OUT-064`, `REQ-OUT-065`, `REQ-OUT-066`, `REQ-OUT-067`, `REQ-OUT-068`

### 14.5 Evidence, CLI, and packaging scenarios

- **AT-EVD-001:** Identical runs produce semantically identical canonical results except for explicitly variable run metadata. This consolidated parameterized scenario also covers: Record order does not alter findings, metrics, or run and phase statuses.
  - Verifies: `REQ-PRN-005`, `REQ-CMP-033`, `REQ-OUT-012`, `REQ-DEP-013`, `REQ-CMP-032`
- **AT-EVD-002:** Results contain exact-byte SHA-256 input digests and input basenames without exposing absolute paths, raw command lines, environment variables, or secrets; the complete validated comparison configuration is embedded without a separate configuration digest.
  - Verifies: `REQ-CFG-023`, `REQ-OUT-017`, `REQ-OUT-018`, `REQ-OUT-019`, `REQ-OUT-022`, `REQ-OUT-023`, `REQ-SEC-007`, `REQ-SEC-008`
- **AT-EVD-003:** If the optional CSV findings export is provided, findings containing commas, quotes, newlines, or formula prefixes are exported safely.
  - Verifies: `REQ-OUT-043`, `REQ-OUT-083`, `REQ-OUT-084`, `REQ-OUT-085`, `REQ-OUT-087`, `REQ-SEC-013`
- **AT-EVD-004:** An output failure or interrupted write cannot leave an evidence package that appears complete. This consolidated parameterized scenario also covers: Success and injected-failure runs verify that temporary files are no more accessible than the destination and are removed after success and, where safe, after errors.
  - Verifies: `REQ-OUT-044`, `REQ-OUT-045`, `REQ-OUT-049`, `REQ-DEP-012`, `REQ-SEC-009`, `REQ-SEC-010`, `REQ-SEC-011`
- **AT-EVD-005:** Every complete comparison exits with code 0 and produces its evidence package, including when differences are reported.
  - Verifies: `REQ-PRN-004`, `REQ-RUN-002`, `REQ-OUT-001`, `REQ-OUT-002`, `REQ-CLI-016`
- **AT-EVD-008:** A complete or incomplete run creates the documented JSON and HTML evidence package, refuses an existing destination by default, and replaces it only with `--overwrite`. This consolidated parameterized scenario also covers: Output-directory reporting and filename handling preserve the exact selected destination and manipulate suffixes structurally rather than by character stripping.
  - Verifies: `REQ-OUT-001`, `REQ-OUT-002`, `REQ-OUT-046`, `REQ-CLI-011`, `REQ-CLI-012`, `REQ-OUT-047`, `REQ-OUT-048`
- **AT-EVD-009:** When an output location can be established and an error report can be written, invocation, configuration, input, resource, output, and internal errors produce a clearly identified diagnostic artefact with a stable execution error code. It contains no findings, finding codes, comparison summary metrics, or phase statuses and cannot be mistaken for a comparison result or evidence package.
  - Verifies: `REQ-FND-007`, `REQ-RUN-008`, `REQ-RUN-009`, `REQ-RUN-010`, `REQ-RUN-011`, `REQ-OUT-008`, `REQ-DEP-014`
- **AT-EVD-010:** Routine logs, progress output, terminal diagnostics, and execution-error diagnostics omit record identifiers and source values.
  - Verifies: `REQ-PRN-007`, `REQ-SEC-004`, `REQ-VAL-075`
- **AT-EVD-011:** Evidence packages warn that they may contain sensitive information, and findings contain record identifiers or source values only where needed to identify or explain the finding.
  - Verifies: `REQ-PRN-007`, `REQ-OUT-030`, `REQ-OUT-031`, `REQ-SEC-005`, `REQ-SEC-006`
- **AT-EVD-012:** Core comparison completes without network access and makes no attempt to transmit inputs, comparison configurations, logs, or results.
  - Verifies: `REQ-SEC-002`, `REQ-SEC-003`, `REQ-DEP-001`, `REQ-DEP-002`
- **AT-EVD-013:** Findings attributable to declared fields inherit their resolved review priority; other findings do not. HTML presentation may distinguish priorities but does not rely on colour alone, and priority never changes findings, counts, status, or exit code.
  - Verifies: `REQ-CFG-041`, `REQ-CFG-042`, `REQ-CFG-043`, `REQ-CFG-044`, `REQ-CFG-045`, `REQ-OUT-034`
- **AT-PKG-001:** The built distribution is named `adviso-validation`, contains an importable `adviso_validation` package and every required subpackage, installs the `adviso-validation` executable, and completes an end-to-end comparison through that executable. This consolidated parameterized scenario also covers: The release artefact can be installed and used without network access, contains offline documentation and integrity information, and supports an end-to-end comparison in an isolated environment.
  - Verifies: `REQ-PRD-001`, `REQ-PRD-003`, `REQ-CFG-087`, `REQ-TST-013`, `REQ-TST-030`, `REQ-DEP-003`, `REQ-DEP-007`
- **AT-EVD-015:** Canonical results contain valid run, phase, software, runtime, and fixed-dialect metadata; timestamps are UTC RFC 3339 values; start time and duration are absent; and overall status reconciles with phase statuses.
  - Verifies: `REQ-OUT-009`, `REQ-OUT-010`, `REQ-OUT-011`, `REQ-OUT-014`, `REQ-OUT-015`, `REQ-OUT-016`, `REQ-OUT-020`
- **AT-EVD-016:** Parameterized single and composite record identities verify ordered source and canonical key arrays, null identities for an absent side, presence-state distinctions, recursive parser-native typed values, canonical scalar and collection encodings, and deterministic object-member ordering.
  - Verifies: `REQ-OUT-021`, `REQ-OUT-026`, `REQ-OUT-027`, `REQ-OUT-028`, `REQ-OUT-029`
- **AT-EVD-018:** Parameterized result fixtures verify fixed-shape zero-inclusive summaries, record-count reconciliation, finding totals by code and priority, and exactly one matched, mismatched, or not-assessable classification for every in-scope non-key value opportunity, including optional, required, invalid, and prohibited values.
  - Verifies: `REQ-OUT-037`, `REQ-OUT-038`, `REQ-OUT-039`, `REQ-OUT-040`, `REQ-OUT-069`, `REQ-OUT-070`, `REQ-OUT-071`, `REQ-OUT-072`, `REQ-OUT-073`
- **AT-EVD-019:** HTML generated solely from canonical JSON uses an open non-proprietary format and presents the run purpose, phase and run statuses, input and configuration identities, counts, findings, discrepancies, limitations, exclusions, unassessed content, provenance, and no acceptance verdict; HTML is never the sole canonical evidence format. This consolidated parameterized scenario also covers: Complete and incomplete reports contain raw findings and metrics but no acceptance threshold, pass/fail verdict, or equivalent inferred laboratory decision.
  - Verifies: `REQ-OUT-042`, `REQ-OUT-074`, `REQ-OUT-075`, `REQ-OUT-076`, `REQ-OUT-077`, `REQ-OUT-078`, `REQ-OUT-079`, `REQ-OUT-080`, `REQ-OUT-081`, `REQ-OUT-088`, `REQ-DEP-004`, `REQ-DEP-005`, `REQ-RUN-013`
- **AT-EVD-021:** Installed-CLI tests cover the required `adviso-validation compare` form, required reference, query, and output arguments, optional configuration, enumerated choices, invalid combinations before input access, normal summaries on standard output, and optional progress that never contaminates machine-readable output. This consolidated parameterized scenario also covers: Omitting `--configuration` selects and records the bundled strict-exact configuration; a supplied value is treated only as a custom comparison-configuration path. The reference and query formats are independently determined and recorded from recognised, case-insensitive filename extensions; a missing, unknown, or ambiguous extension causes an input error, and content that does not conform to the indicated format is rejected. Command-line `--help` describes every version 1 command and option and directs users to the full guide.
  - Verifies: `REQ-PRD-002`, `REQ-INP-001`, `REQ-INP-002`, `REQ-INP-004`, `REQ-INP-060`, `REQ-INP-061`, `REQ-INP-062`, `REQ-CLI-001`, `REQ-CLI-002`, `REQ-CLI-003`, `REQ-CLI-006`, `REQ-CLI-007`, `REQ-CLI-008`, `REQ-INP-003`, `REQ-CFG-092`, `REQ-CLI-009`, `REQ-CLI-010`, `REQ-INP-005`, `REQ-INP-006`, `REQ-INP-007`, `REQ-INP-008`, `REQ-INP-009`, `REQ-CLI-013`, `REQ-CLI-004`, `REQ-DOC-005`

### 14.6 Documentation scenarios

- **AT-DOC-001:** The built distribution contains an offline user guide covering every topic required by Section 13.4, and the guide identifies the toolkit and schema versions to which it applies. This consolidated parameterized scenario also covers: Every complete comparison-configuration and canonical-results example in the guide validates against its corresponding packaged schema, and every documented command-line invocation uses the version 1 interface.
  - Verifies: `REQ-DOC-001`, `REQ-DOC-006`, `REQ-DOC-007`, `REQ-DOC-008`, `REQ-DOC-009`, `REQ-DOC-010`, `REQ-DOC-011`, `REQ-DOC-012`, `REQ-DOC-013`, `REQ-DOC-014`, `REQ-DOC-015`, `REQ-DOC-016`, `REQ-DOC-002`, `REQ-DOC-003`, `REQ-DOC-004`

### 14.7 Fixture and compatibility scenarios

- **AT-TRC-002:** Regenerating every generated fixture from its recorded source or generator produces byte-identical or semantically identical controlled test data, as applicable.
  - Verifies: `REQ-TST-005`
- **AT-TRC-003:** Every supported and unsupported comparison-configuration and results-schema version is exercised to confirm exact supported-version handling and clear rejection of unsupported versions.
  - Verifies: `REQ-REL-004`

## 15. Status of the current prototype

**REQ-PRD-011.** The existing prototype was created only to stimulate requirements analysis and has never been used operationally. Its code, command-line interface, outputs, Python APIs, module structure, terminology, and behaviour impose no compatibility requirements on version 1. The version 1 implementation is not required to reuse any prototype code. Version 1 behaviour MUST NOT be derived implicitly from the prototype.
