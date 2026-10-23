# AdvISO Validation Toolkit: `compare` Behaviour Specification

**Document status:** Draft for review  
**Specification version:** 0.1.0-draft  
**Applies to:** The `compare` command and its supporting comparison engine  
**Normative language:** The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** indicate requirement strength.

## 1. Purpose

This document defines a specification for version 1.0 of the AdvISO Validation Toolkit: a command-line namespace for cohesive capabilities that support bioinformatics validation and verification activities associated with ISO 15189 accreditation.

The initial sole user-facing subcommand within the toolkit is `compare`. It is designed for two datasets that describe the same kinds of samples or observations but may express their fields and values using different names, types, vocabularies, or other source dialects. The declared comparison configuration translates those representations into a common canonical representation, after which the tool compares the canonical records and values. It produces deterministic, machine-readable findings and a human-readable summary suitable for review and retention as one component of a bioinformatics pipeline validation or verification record.

The tool distinguishes differences that remain after successful translation from issues that prevented some intended translation or assessment. It is intended to answer these questions:

> Given these identified inputs and declared translation and comparison rules, which expected and observed records and values are equivalent, different, missing, or extra after translation? Which input or configuration-related issues prevented an intended assessment?

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
- configuration-defined record keys and conservative single-field key selection in automatic mode;
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

1. **REQ-PRN-001.** **Explicit over inferred:** A custom comparison configuration MUST declare comparison behaviour rather than relying on observed-data inference. The automatic strict-exact mode defined in Section 6.9 is the sole version 1 exception: it MAY infer same-name field correspondence and a single record key only by the fixed rules in that section, and MUST NOT infer types, conversions, mappings, normalisation, tolerance, or biological equivalence.
2. **REQ-PRN-002.** **No silent data loss:** Input records, duplicate keys, unmapped values, and unsupported structures MUST NOT be silently discarded or overwritten.
3. **REQ-PRN-003.** **Symmetry:** Missing and extra content MUST be assessed in both directions.
4. **REQ-PRN-009.** **Separation of concerns:** Run status, comparison evidence, and the laboratory's acceptance decision MUST remain distinct concepts.
5. **REQ-PRN-004.** **Complete evidence:** A normal comparison mismatch MUST still produce a complete report.
6. **REQ-PRN-005.** **Determinism:** The same exact input bytes, input basenames, configuration selection, toolkit version, and runtime identity MUST produce identical result content except for the explicitly variable run identifier and completion time. Configuration selection includes omission of `--configuration`, in which case automatic construction MUST itself be deterministic. Comparison outcomes MUST additionally satisfy the invariance rules in Section 9.1.
7. **REQ-PRN-006.** **Traceability:** Findings MUST identify the rule, record, and field that produced them.
8. **REQ-PRN-007.** **Data minimisation:** Reports MUST include only the source identifiers and values necessary to explain and review the comparison. Routine logs, progress output, terminal diagnostics, and execution-error diagnostics MUST NOT reproduce them.
9. **REQ-PRN-008.** **Fail clearly:** Invalid or ambiguous input MUST produce an explicit error rather than an assumed interpretation.

## 4. Terminology

- **Reference dataset:** The dataset containing the approved expected or comparator records. “Reference” does not imply intrinsic truth.
- **Query dataset:** The dataset being evaluated against the reference.
- **Custom comparison configuration:** A versioned YAML document supplied by the user to declare the data contract, normalisation, and comparison behaviour.
- **Effective comparison configuration:** The schema-valid configuration used for a run: either the validated custom configuration or the deterministic configuration generated by automatic strict-exact mode.
- **Automatic strict-exact mode:** The configuration-free mode used when `--configuration` is omitted. It constructs an effective comparison configuration from the inputs using only the rules in Section 6.9.
- **Not assessed:** Outside the canonical fields selected by `fields.in_scope`.
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

**REQ-INP-003.** If a custom comparison configuration is omitted, the tool MUST use the automatic strict-exact mode defined in Section 6.9.

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
- **REQ-INP-014.** Changing only accepted LF and CRLF line endings MUST NOT affect the comparison outcome defined in Section 9.1. Exact-byte size and digest evidence MAY differ.

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
- **REQ-INP-026.** the one-based data-record number and one-based starting physical line number of every record MUST be retained for traceability; the header is not a data record;
- **REQ-INP-027.** Input values MUST initially remain strings unless a custom configuration declares a null representation or type conversion.
- **REQ-INP-028.** CSV and TSV cells, including empty cells, MUST initially remain strings before any configured field processing.

### 5.5 JSON parsing

- **REQ-INP-029.** A JSON input MUST contain one root-level array of record objects. A dataset containing one record MUST use a one-element array; a root-level record object is not supported:

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
- **REQ-INP-034.** A root-level JSON value that is not an array MUST cause an input error, including a root-level object that could otherwise represent one record.
- **REQ-INP-035.** A root-level scalar MUST cause an input error.
- **REQ-INP-036.** A root-level array containing any item that is not an object MUST cause an input error.
- **REQ-INP-037.** An invalid-root error MUST identify the invalid root value or array item.
- **REQ-INP-038.** An invalid-root error MUST explain the required structure.
- **REQ-INP-070.** Duplicate member names in any JSON object MUST cause an input error, including duplicates in record objects and nested object-valued fields. A parser MUST detect duplicates before constructing a mapping that could overwrite an earlier member.

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
- `NaN`, positive infinity, and negative infinity are not valid JSON numerical values or valid declared decimals.
- **REQ-INP-047.** An unquoted non-finite token such as `NaN`, `Infinity`, or `-Infinity` in a JSON input MUST cause an input error because the document is not valid JSON, irrespective of the field in which it occurs.
- **REQ-INP-048.** A quoted representation such as `"NaN"` in JSON, CSV, or TSV MUST initially remain a parser-native string.
- **REQ-INP-049.** If such a string is parsed as a declared decimal in an attributable non-key field, it MUST produce an `invalid_field_value` finding, make that value opportunity `not_assessable`, and allow other assessable content to continue.
- **REQ-INP-050.** If such a string is parsed as a declared decimal record-key field, the invalid key MUST produce an execution error.
- **REQ-INP-051.** The JSON parser MUST reject non-standard non-finite tokens rather than enabling a permissive extension. Every accepted parser-native JSON number is therefore a finite exact integer or decimal.

### 5.7 Empty inputs

- **REQ-INP-052.** Zero-byte files and datasets with zero records MUST be recognised explicitly and distinguished. A valid zero-record JSON dataset is `[]`; a valid zero-record CSV or TSV dataset contains a valid header and no data records. A zero-byte JSON file is malformed JSON, and a zero-byte CSV or TSV file is an input error because it lacks the required header.
- **REQ-INP-053.** If both datasets are syntactically valid, contain no records, and provide or permit construction of a valid effective comparison configuration and record key, the records phase MUST report no missing records.
- **REQ-INP-054.** Under the conditions in `REQ-INP-053`, the records phase MUST report no extra records.
- **REQ-INP-055.** Under the conditions in `REQ-INP-053`, the values phase MUST perform no comparisons.
- **REQ-INP-056.** Contract requirements that can be evaluated without records MUST still be checked.
- **REQ-INP-057.** The tool MUST NOT infer that an empty dataset is unsuitable merely because it is empty.
- **REQ-INP-066.** Per-record requirements have no applicable opportunities in a zero-record dataset and MUST NOT produce findings or not-assessable classifications merely because no records exist.
- **REQ-INP-067.** Available dataset-level structure MUST still be assessed. A zero-record CSV or TSV header MAY establish configured, missing, or otherwise excluded source columns. A JSON empty array exposes no field structure, so field presence or absence MUST NOT be inferred from it.
- **REQ-INP-068.** When the conditions in `REQ-INP-053` are satisfied, two valid zero-record datasets MUST have complete records and values phases, zero matched, missing, and extra records, and zero value opportunities. Header-derived contract findings do not alter those phase statuses.
- **REQ-INP-069.** When exactly one dataset has records and a valid effective comparison configuration and record key are available, every record on that side MUST be reported as missing or extra as applicable; because there are no aligned records, there are zero value opportunities and the records and values phases remain complete.
- **REQ-INP-071.** In automatic strict-exact mode, two empty JSON arrays do not expose a field from which a record key can be selected and MUST produce an `input.invalid_record_key` execution error. A valid custom configuration can compare the same inputs.
- Any minimum-size acceptance criterion belongs to the external laboratory decision process.
- **REQ-INP-058.** When a valid effective comparison configuration and record key are available, a non-empty reference and empty query MUST report every expected record as missing.
- **REQ-INP-059.** When a valid effective comparison configuration and record key are available, an empty reference and non-empty query MUST report every observed record as extra.

## 6. Comparison configurations

### 6.1 General requirements

**REQ-CFG-001.** Every comparison uses an effective comparison configuration. A custom configuration MUST:

- **REQ-CFG-095.** use a published, independently versioned comparison-configuration schema supported by the installed toolkit release;
- **REQ-CFG-096.** declare its schema version and a stable configuration identifier and revision;
- **REQ-CFG-097.** be validated fully before either dataset is compared;
- **REQ-CFG-098.** reject unknown configuration keys by default;
- **REQ-CFG-099.** provide actionable validation errors with configuration locations;
- **REQ-CFG-100.** be embedded in the canonical comparison result.

An automatically generated effective configuration is constructed only after both datasets have been parsed and their dataset-wide field names have been discovered. It MUST satisfy the comparison-configuration schema and semantic rules before any contract, record, or value comparison is performed, and it MUST be embedded in the canonical comparison result.

**REQ-CFG-002.** A valid comparison configuration MUST declare at least:

- **REQ-CFG-101.** record key fields;
- **REQ-CFG-102.** field definitions and an explicit list of fields in scope for comparison;
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
  in_scope:
    - "record_id"
    - "field_example_1"
    - "field_example_2"
    - "field_example_3"
  definitions:
    record_id:
      source_fields:
        reference: "sample_id"
        query: "specimen_id"
      required:
        reference: true
        query: true
      logical_type: "string"
      null_policy:
        allowed: false
        nulls_equal: false
      comparator:
        name: "typed_exact"
    field_example_1:
      source_fields:
        reference: "expected_result"
        query: "reported_result"
      required:
        reference: true
        query: true
      logical_type: "decimal"
      null_policy:
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
      source_fields:
        reference: "expected_interpretation"
        query: "reported_interpretation"
      required:
        reference: true
        query: true
      logical_type: "string"
      null_policy:
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
    field_example_3:
      source_fields:
        reference: "expected_markers"
        query: "reported_markers"
      required:
        reference: true
        query: true
      logical_type:
        collection_type: "set"
        element_type: "string"
        element_comparator:
          name: "typed_exact"
      null_policy:
        allowed: false
        nulls_equal: false
      collection_representation:
        query:
          format: "delimited_text"
          delimiter: "/"
          element_normalisation:
            - operation: "trim"
              parameters:
                side: "both"
            - operation: "case_fold"
          element_mapping:
            - from:
                category: "string"
                value: "wild_type"
              to:
                category: "string"
                value: "WT"
            - from:
                category: "string"
                value: "mutant"
              to:
                category: "string"
                value: "MUT"
      comparator:
        name: "set_exact"

```

The template is illustrative rather than a recommendation to use these particular rules.

**REQ-CFG-016.** The published machine-readable schema MUST encode the complete version 1 comparison-configuration structure and constraints.

The four field definitions illustrate different configuration roles: `record_id` is a renamed exact key; `field_example_1` is parsed as an exact decimal and quantised before tolerance comparison; `field_example_2` demonstrates source-text normalisation, side-specific missing tokens, and mapping different source vocabularies to common canonical string values; and `field_example_3` compares a reference JSON array with a slash-delimited query string after element-level normalisation and mapping. The deliberately generic names make clear that these are user-defined canonical field names rather than reserved configuration keywords. These example rules are not domain recommendations.

#### 6.2.3 Top-level keys and identity

The only permitted top-level keys are `schema_version`, `metadata`, and `fields`.

- **REQ-CFG-017.** `schema_version` MUST be a quoted string identifying a supported comparison-configuration schema version.
- **REQ-CFG-018.** `metadata.id` MUST be a stable, non-empty identifier for the comparison configuration.
- **REQ-CFG-020.** `metadata.revision` MUST be a non-empty string.
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

- `fields.definitions` declares canonical fields and their reference-to-query correspondence. Declaration alone does not select a field for assessment.
- **REQ-CFG-030.** `fields.in_scope` is required and MUST be a non-empty list of unique canonical field names. Every listed name MUST exist in `fields.definitions`.
- **REQ-CFG-031.** The order of names in `fields.in_scope` MUST NOT affect the comparison outcome or the ordering of findings and exclusions. The embedded configuration preserves the effective list as provenance.
- **REQ-CFG-116.** Source-field names MUST be discovered dataset-wide. For CSV and TSV, the header defines the observed names even when there are no records. For JSON, the observed names are the union of member names across all record objects.
- **REQ-CFG-117.** A field present in `fields.definitions` but absent from `fields.in_scope` is deliberately excluded from assessment. It MUST produce exactly one `configured_field_excluded` entry naming its canonical field, regardless of whether either source field is observed in the inputs.
- **REQ-CFG-118.** A source field observed on a dataset side but not named by any field definition for that side is outside scope. It MUST produce one `undeclared_field_excluded` entry for that dataset side and source field.
- **REQ-CFG-119.** Excluded fields MUST NOT be compared, create findings, create value opportunities, or affect run or phase status.
- **REQ-CFG-120.** Exclusions MUST be summarised rather than repeated for individual records and MUST use the exact forms and deterministic ordering defined in Section 9.1.3.
- **REQ-CFG-121.** An `undeclared_field_excluded` entry MUST record the number of records on that dataset side that contain the source field. A field known only from a zero-record CSV or TSV header has a record count of zero.
- **REQ-CFG-032.** Fields with different names MUST be declared explicitly under a common canonical field definition if they are intended to correspond.
- **REQ-CFG-033.** `fields.definitions` MUST be a mapping keyed by unique canonical field name.
- **REQ-CFG-034.** `fields.definitions` MUST contain a definition for every field referenced by `fields.record_key`, and every record-key field MUST also occur in `fields.in_scope`.
- **REQ-CFG-035.** `source_fields.reference` and `source_fields.query` MUST each contain a non-empty source field name. A declared field always defines correspondence between one reference field and one query field, regardless of whether either field is required to be present in every record.
- **REQ-CFG-036.** `required.reference` and `required.query` MUST be booleans.
- **REQ-CFG-037.** Absence of a field required on a particular side MUST create a contract finding.
- **REQ-CFG-038.** Absence of an optional field MUST NOT create a missing-field finding.
- **REQ-CFG-039.** A source field observed in an input but not represented by a field definition for that dataset side MUST be excluded as specified by `REQ-CFG-118`. It MUST NOT be aligned or compared implicitly, even when the same source-field name occurs on both sides.
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

**REQ-CFG-049.** `logical_type` MUST be omitted when, and only when, the comparator is `preserved_exact`. A `preserved_exact` field MUST also omit `source_normalisation`, `collection_representation`, `value_mapping`, `typed_normalisation`, and `null_policy.missing_tokens`. Its requiredness and null policy still apply, and parser-native JSON null remains governed by that null policy, but no additional source representation is transformed or interpreted as null.

**REQ-CFG-050.** For a collection field, `logical_type` MUST use this form:

```yaml
logical_type:
  collection_type: "list"      # list, set, or multiset
  element_type: "string"       # scalar logical type
  element_comparator:
    name: "typed_exact"
```

**REQ-CFG-051.** Nested collection types MUST be rejected.

**REQ-CFG-052.** The comparator named for the field itself MUST correspond to the collection kind: `list_exact`, `set_exact`, or `multiset_exact`.

**REQ-CFG-124.** A `set` or `multiset` element comparator MUST be `typed_exact`.

**REQ-CFG-125.** A `list` element comparator MUST be `typed_exact` or `numeric_tolerance`. `numeric_tolerance` MUST be permitted only when `element_type` is `integer` or `decimal` and MUST use the same parameter rules as a field-level numeric-tolerance comparator.

**REQ-CFG-126.** `preserved_exact`, `normalised_string`, `numeric_exact`, `date_exact`, `datetime_exact`, and the collection comparators MUST NOT be used as element comparators in version 1. Exact comparison of any declared scalar element type uses `typed_exact`.

**REQ-CFG-053.** Every declared field MUST contain a `null_policy` mapping:

- **REQ-CFG-054.** `allowed` and `nulls_equal` MUST be booleans.
- **REQ-CFG-055.** `nulls_equal` MUST be `false` when `allowed` is `false`.
- **REQ-CFG-056.** `missing_tokens` MAY be omitted; omission means that no additional source values are interpreted as null. Parser-native JSON null remains null independently of this property.
- **REQ-CFG-057.** When `missing_tokens` is present, it MUST contain `reference`, `query`, or both. Each present side MUST be a non-empty list of non-null source-value descriptors. An omitted side has no configured missing tokens. A matched token is converted to null at processing step 3 in Section 6.8.

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

**REQ-CFG-122.** A descriptor with `category: null` MUST be permitted only as the `to` destination of a value-mapping entry. It MUST NOT be permitted as a missing token or as a mapping `from` value, because parser-native null is recognised without configuration and null values bypass mapping.

Descriptors are matched using parser-native category and value equality under Section 5.6. The retained lexical form remains evidence but does not create a distinct numerical value. This explicit representation prevents YAML scalar resolution from changing mapping keys or missing tokens.

#### 6.2.7 Normalisation, collection representation, and value mapping

**REQ-CFG-060.** `source_normalisation` MAY be omitted. Omission means that no source-text normalisation is applied.

**REQ-CFG-061.** When present, `source_normalisation` MUST contain `reference`, `query`, or both. Each present side MUST be a non-empty ordered list of operations applied only to values from that dataset. An omitted side has no source-text operations.

**REQ-CFG-062.** `typed_normalisation` MAY be omitted. Omission means that no typed-value normalisation is applied.

**REQ-CFG-063.** When present, `typed_normalisation` MUST be a non-empty ordered list applied to the canonical typed values on both sides. Each operation entry has this form:

```yaml
- operation: "decimal_quantise"
  parameters:
    places: 3
    rounding: "half_even"
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

**REQ-CFG-066.** A source-text operation MUST appear only in `source_normalisation.reference`, `source_normalisation.query`, or a side's `collection_representation.<side>.element_normalisation`. It applies only to values or decoded elements, respectively, from the corresponding dataset side.

**REQ-CFG-123.** A source-text operation MUST apply only when the current parser-native value is a string. A non-string value MUST pass through the source-normalisation stage unchanged; it MUST NOT be stringified, transformed, or rejected merely because a source-text operation is configured.

**REQ-CFG-067.** A typed-value operation MUST appear only in `typed_normalisation`. It applies identically to both datasets.

**REQ-CFG-068.** Operation semantics MUST be published with the schema and recorded sufficiently for reproducibility. This information MUST include the Unicode-data version used by Unicode operations.

**REQ-CFG-137.** `collection_representation` MAY be present only for a collection logical type. It MAY contain `reference`, `query`, or both; each present side declares how that dataset side represents the collection and MAY declare element-level source processing. An omitted side uses `json_array` with no element normalisation or element mapping.

**REQ-CFG-138.** Each present side of `collection_representation` MUST contain `format`, which MUST be `json_array` or `delimited_text`.

- `json_array` means a parser-native array in JSON or a parser-native string containing one valid JSON array in CSV or TSV.
- `delimited_text` means a parser-native string split using an explicitly configured delimiter. It does not mean a CSV or TSV row-level dialect.

**REQ-CFG-139.** A `delimited_text` declaration MUST contain a non-empty string `delimiter`. A `json_array` declaration MUST omit `delimiter`.

**REQ-CFG-140.** `element_normalisation`, when present, MUST be a non-empty ordered list of the source-text operations defined in this section. The operations apply only to string elements from the declared dataset side. Non-string elements pass through unchanged.

**REQ-CFG-141.** `element_mapping`, when present, MUST be a non-empty ordered list using the same `from` and `to` structure as `value_mapping`. Both descriptors MUST be non-null. Each `from` value MUST occur at most once within one side's element mapping; conflicting or unreachable entries MUST invalidate the comparison configuration. Many-to-one element mappings are permitted when declared explicitly.

**REQ-CFG-142.** When an element mapping is present, an element with no matching entry MUST produce a `mapping_failure` contract finding, prevent construction of that field's canonical collection value, and make that value opportunity `not_assessable`. Unmapped elements MUST NOT pass through implicitly.

**REQ-CFG-143.** An empty optional `collection_representation`, `element_normalisation`, or `element_mapping` mapping or list MUST be rejected. Absence MUST be represented by omission.

**REQ-CFG-145.** A collection field MUST omit field-level `source_normalisation`, `value_mapping`, and `typed_normalisation`. Source processing of collection elements MUST be declared through the applicable side of `collection_representation`. The field-level null policy and missing-token recognition continue to apply to the collection value as a whole before representation decoding.

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

- **REQ-CFG-071.** `from` MUST be a non-null source-value descriptor and `to` MUST be a source-value descriptor as defined in Section 6.2.6.
- A `from` descriptor is matched against the source value after the applicable `source_normalisation` operations and missing-token recognition have been performed, in accordance with the processing order in Section 6.8.
- A `to` descriptor with `category: "null"` explicitly maps a non-null source value to null and is distinct from absence of a mapping entry. The null policy is then applied and typed parsing is bypassed.
- **REQ-CFG-072.** Each `from` value MUST occur at most once within one side’s mapping.
- **REQ-CFG-073.** Conflicting entries MUST invalidate the comparison configuration.
- **REQ-CFG-074.** Unreachable entries MUST invalidate the comparison configuration.
- A field-level `value_mapping` requires a scalar `logical_type`; whole-collection value mapping is not supported in the first release. Collection elements may instead use `collection_representation.<side>.element_mapping`. A field-level mapping's `to` values are parsed as the destination type after mapping.
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

The normative JSON Schema Draft 2020-12 definition of comparison-configuration schema version `1.0` is [`src/adviso_validation/schemas/comparison-configuration-v1.0.schema.json`](../src/adviso_validation/schemas/comparison-configuration-v1.0.schema.json).

**REQ-CFG-128.** The schema MUST use `https://adviso-project.github.io/validation_toolkit/schemas/comparison-configuration-v1.0.schema.json` as its canonical `$id`.

**REQ-CFG-086.** A YAML configuration MUST first be loaded using Section 6.2.1. The resulting JSON-compatible data structure MUST then validate against that schema before either input dataset is read.

The standalone schema file is the authoritative machine-readable definition.

**REQ-CFG-087.** It MUST be version controlled in the source repository. It MUST be included as package data in the installed `adviso_validation.schemas` package. It MUST be loaded at runtime through the package-resource API rather than through a path relative to the working directory.

**REQ-CFG-088.** CI MUST verify the schema's presence in built distributions. CI MUST validate every documented example against it. CI MUST validate every controlled configuration fixture against it.

**REQ-CFG-090.** JSON Schema cannot reliably express every relationship involving user-defined mapping keys, uniqueness across separate arrays, or references between distant parts of a document. After schema validation, the implementation MUST therefore apply the following semantic checks before reading either dataset:

- **REQ-CFG-104.** every name in `fields.record_key` exists in `fields.definitions`;
- **REQ-CFG-129.** every name in `fields.in_scope` exists in `fields.definitions`, and every name in `fields.record_key` also occurs in `fields.in_scope`;
- **REQ-CFG-105.** every key field is required on both sides, non-nullable, scalar, and uses `typed_exact`;
- **REQ-CFG-106.** a field without `logical_type` uses `preserved_exact` and has no source normalisation, collection representation, value mapping, typed normalisation, or configured missing tokens; conversely, a field using `preserved_exact` omits `logical_type` and all of those processing properties;
- **REQ-CFG-107.** each comparator and normalisation operation is compatible with the field’s logical type and processing stage;
- **REQ-CFG-108.** source-value descriptors contain lexically valid values for their declared categories, and each side’s value mapping has unique `from` values;
- **REQ-CFG-144.** each `collection_representation` is used only with a collection logical type, and each side's element mapping has unique `from` values and contains no conflicting or unreachable entries;
- **REQ-CFG-127.** the `source_fields.reference` names are unique across canonical field definitions, and the `source_fields.query` names are independently unique across canonical field definitions;
- **REQ-CFG-136.** a custom configuration does not use the reserved automatic-mode identifier `org.adviso.automatic-strict-exact`;

**REQ-CFG-091.** A failure of any semantic check MUST be reported as an invalid comparison configuration with the relevant configuration path and violated rule.

### 6.3 Record keys

- **REQ-REC-001.** A record key MUST contain one or more named fields.
- **REQ-REC-002.** Composite-key field order MUST be stable and recorded.
- **REQ-REC-003.** Key fields MUST be present, valid under their declared field definitions, and non-null.
- **REQ-REC-004.** Key values MUST NOT undergo implicit numeric or boolean conversion.
- **REQ-REC-005.** Normalisation of key values MUST be explicitly configured.
- **REQ-REC-006.** Composite keys MUST be declared in a custom configuration. A non-`record_id` single-field key MAY be selected without a custom configuration only by the automatic discovery rules in Section 6.9.
- **REQ-REC-007.** Key names MUST NOT be inferred except by the automatic strict-exact mode defined in Section 6.9.
- **REQ-REC-008.** Command-line key overrides MUST NOT be supported in the first release.
- **REQ-REC-009.** The normalised key MUST uniquely identify one record within its dataset.
- **REQ-REC-010.** A missing, null, invalid, duplicate, undiscoverable, or ambiguous record key prevents construction of an unambiguous record model and MUST be an input error in every comparison.
- **REQ-REC-011.** The resulting execution error MUST identify the affected dataset when the defect is attributable to one side. An automatic discovery failure or ambiguity MUST state that both inputs were considered.
- **REQ-REC-012.** The resulting execution error MUST identify the selected key or candidate field names where they exist. A no-candidate error MUST state that no field satisfied the automatic key criteria.
- **REQ-REC-013.** Where available, the resulting execution error MUST identify the relevant source-record locations.
- **REQ-REC-014.** Duplicate records MUST never overwrite one another silently.
- **REQ-REC-015.** Findings and reports MUST retain enough information to distinguish every source record.

### 6.4 Field declarations and preserved values

**REQ-VAL-001.** The comparison engine MUST support preserved, untyped values. It MUST also support explicitly declared logical types.

A type declaration is required for a field that uses typed parsing, normalisation, mapping, or a type-specific comparator.

**REQ-VAL-002.** Every custom configuration MUST explicitly list the canonical fields selected for assessment in `fields.in_scope`. Defined fields omitted from that list and observed source fields not represented by a definition are outside scope and MUST be represented as exclusions in accordance with Section 7.5.

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

The accepted parser-native inputs for each declared logical type are fixed as follows:

- **REQ-VAL-076.** A `string` field MUST accept only a parser-native string. No other parser-native category is converted to text implicitly.
- **REQ-VAL-077.** An `integer` field MUST accept a parser-native integer or a parser-native string satisfying the textual integer grammar in Section 6.5.2. A parser-native decimal MUST be rejected even when it represents a mathematically integral value.
- **REQ-VAL-078.** A `decimal` field MUST accept a parser-native integer, parser-native decimal, or parser-native string matching `[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?`. Conversion of a parser-native integer to a decimal is exact. Text such as `.5` and `1.` MUST be rejected.
- **REQ-VAL-079.** A `boolean` field MUST accept a parser-native boolean or a parser-native string accepted by Section 6.5.4.
- **REQ-VAL-080.** A `date` or `datetime` field MUST accept only a parser-native string, which MUST then satisfy the applicable grammar in Sections 6.5.5 and 6.5.6.
- **REQ-VAL-081.** A collection side using the default or explicitly declared `json_array` representation MUST accept a parser-native array from JSON or a parser-native string containing one valid JSON array from CSV or TSV. No other parser-native category is accepted for that representation.
- **REQ-VAL-082.** After a collection has been decoded and any configured element processing has been applied, each element MUST be parsed independently according to the declared scalar element type and the same source-category rules.
- **REQ-VAL-083.** A parser-native object MUST be invalid for every declared version 1 logical type. An untyped field using `preserved_exact` MAY still preserve and compare a parser-native object.
- **REQ-VAL-084.** A source representation not accepted directly by this matrix MUST require an explicit value mapping to an accepted representation. The implementation MUST NOT introduce any additional implicit conversion.
- **REQ-VAL-085.** Null recognition and null-policy handling MUST occur before typed parsing. Null is therefore not an accepted typed-parser input category.

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
- **REQ-VAL-035.** Supplied fractional-second precision MUST remain available in the source lexical evidence. The canonical datetime representation MUST remove unnecessary trailing fractional-second zeros and omit a zero-valued fractional component. Any reduction that changes the represented instant, rather than only its redundant lexical form, MUST require explicit precision normalisation.
- **REQ-VAL-036.** Leap-second representations MUST be invalid in the first release.

#### 6.5.7 Collections

- **REQ-VAL-037.** Every collection MUST declare its element logical type and element comparator.
- **REQ-VAL-038.** A `list` MUST preserve order and duplicates.
- **REQ-VAL-039.** A `set` MUST be unordered.
- **REQ-VAL-040.** A `set` MUST reject duplicate elements after typed parsing, using typed-exact canonical equality, rather than silently collapse them. Distinct source representations that parse to the same canonical value, such as textual integers `"01"` and `"1"`, are duplicates.
- **REQ-VAL-041.** A `multiset` MUST be unordered.
- **REQ-VAL-042.** A `multiset` MUST preserve element occurrence counts.
- **REQ-VAL-043.** A JSON collection using `json_array` representation MUST be a parser-native array.
- **REQ-VAL-044.** A CSV or TSV collection cell using `json_array` representation MUST use valid JSON-array syntax.
- **REQ-VAL-045.** Ordinary delimited text MUST NOT be inferred to be a collection. It is accepted only for a dataset side explicitly configured with `format: "delimited_text"`.
- **REQ-VAL-046.** Collection elements MUST be non-null in version 1. A parser-native null element MUST produce an `invalid_field_value` finding, prevent construction of a canonical collection value, and make that field comparison `not_assessable`.
- **REQ-VAL-087.** A `delimited_text` representation MUST accept only a parser-native string. The configured delimiter MUST be matched literally, not as a regular expression, and splitting MUST proceed deterministically from left to right using non-overlapping occurrences.
- **REQ-VAL-088.** CSV or TSV quoting and escaping MUST be resolved by the dataset parser before collection splitting. Delimited collection text has no additional quoting or escaping syntax in version 1; delimiter text within an element cannot be represented by that encoding.
- **REQ-VAL-089.** An empty delimited string MUST decode to an empty collection. Otherwise, leading, trailing, or consecutive delimiters MUST produce empty-string elements, which then undergo the configured element processing and typed parsing normally. Whitespace MUST NOT be trimmed implicitly.
- **REQ-VAL-090.** For each decoded collection element, configured `element_normalisation` operations MUST run in declared order before configured `element_mapping`; the resulting non-null value MUST then undergo scalar element-type parsing. No whole-field missing-token or null-policy rule is reapplied to individual elements.
- **REQ-VAL-091.** Element mappings MUST use parser-native category and value equality after element normalisation. A configured element mapping is closed: every non-null element must match an entry. Applied element mappings MUST remain identifiable through the embedded comparison configuration and the source and canonical evidence required for a finding.
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

For a nullable configured field, null matches only null when `nulls_equal` is true and remains distinct from an absent field, an empty string, and every non-null value.

The field-level null policy governs the collection value as a whole and does not permit null collection elements. Version 1 has no separate element-null policy.

### 6.7 Mappings

#### 6.7.1 Column mappings

- **REQ-VAL-056.** Reference and query fields MAY map to a canonical field name.
- **REQ-VAL-057.** Column-name mappings MUST be one-to-one in version 1. One source field MUST NOT feed multiple canonical fields, and one canonical field MUST NOT receive multiple source fields from the same dataset side.
- **REQ-VAL-058.** Reuse of a source name by more than one canonical field on the same dataset side MUST invalidate the comparison configuration before either dataset is read. Reference and query namespaces are independent, so the same source name MAY occur once on each side.
- **REQ-VAL-059.** Unknown source fields MUST be excluded from assessment and summarised in the canonical result. They MUST NOT be inferred, mapped, or compared implicitly.
- **REQ-VAL-060.** Required mapped fields that are absent MUST be reported.
- **REQ-VAL-061.** All applied mappings MUST be identifiable in the evidence.

#### 6.7.2 Value mappings

Requirements in this subsection describe field-level `value_mapping` unless they explicitly mention element mapping. Collection-element mapping has the additional constraints and processing order in Sections 6.2.7 and 6.5.7.

- **REQ-VAL-062.** A value mapping MUST operate on a preserved source value before typed parsing.
- **REQ-VAL-063.** The mapping output MUST be parsed as the declared destination logical type.
- **REQ-VAL-064.** A map MUST declare its source representation and destination logical type.
- **REQ-VAL-065.** Unknown source values MUST default to a contract finding, not pass through silently.
- **REQ-VAL-066.** Many-to-one mappings MUST be allowed only when intentionally declared.
- **REQ-VAL-067.** Mapping to null MUST be distinguished from a missing map entry.
- **REQ-VAL-068.** Values used in mappings MUST be represented using the typed source-value descriptor. The parser MUST NOT infer their intended category from YAML scalar syntax.
- **REQ-VAL-069.** Applied mappings MUST be identifiable in the evidence.

**REQ-VAL-086.** Parser-native null and values converted to null by missing-token recognition MUST bypass value mapping and typed parsing. A non-null value explicitly mapped to null MUST bypass typed parsing after the null policy has been applied. Mapping from null is not supported.

### 6.8 Normalisation and processing order

**REQ-VAL-070.** Normalisation MUST be opt-in, field-specific, ordered deterministically, and recorded. Source-text normalisation is distinct from typed-value normalisation.

**REQ-VAL-071.** Source-text normalisation MAY include Unicode normalisation, leading or trailing whitespace trimming, and case folding. Typed-value normalisation MAY include datetime offset normalisation and declared precision reduction. Deterministic serialization order for sets and multisets is canonical output handling, not a configured typed-normalisation operation.

**REQ-VAL-072.** Typed processing MUST occur in this order:

1. preserve the source value and representation;
2. if the current value is a parser-native string, apply the source-text normalisation declared for the applicable dataset side; otherwise pass it through unchanged;
3. recognise parser-native null or a configured non-null missing token;
4. if the value is null, apply the null policy and bypass value mapping and typed parsing;
5. for a non-null value, apply a declared source-value mapping and produce a `mapping_failure` finding if a configured mapping has no matching entry;
6. if the mapping output is null, apply the null policy and bypass typed parsing;
7. otherwise parse the declared logical type; for a collection, first decode the side's declared or default collection representation, then apply element normalisation, element mapping, and scalar element-type parsing to each element in that order;
8. apply declared typed-value normalisation;
9. compare canonical values.

**REQ-VAL-073.** Column-name mapping MUST occur before field-value processing.

**REQ-VAL-074.** A failure at any stage MUST identify the stage and attributable record and field.

**REQ-VAL-075.** The source value MUST be included in the evidence package only when required to explain the failure. It MUST NOT be reproduced in routine logs, progress output, terminal diagnostics, or execution-error diagnostics.

### 6.9 Automatic strict-exact mode

**REQ-CFG-092.** If `--configuration` is omitted, the tool MUST construct an effective comparison configuration deterministically from the parsed inputs using this section. Supplying `--configuration` MUST disable automatic construction and select only the named custom configuration.

**REQ-CFG-093.** Automatic strict-exact mode MUST discover source-field names dataset-wide using `REQ-CFG-116`. Field-name matching MUST be exact and case-sensitive. It MUST NOT apply aliases, approximate matching, or Unicode, case, or whitespace normalisation to field names.

#### 6.9.1 Automatic record-key selection

- **REQ-CFG-109.** If the exact field name `record_id` is observed on both dataset sides, it MUST be selected as the single-field record key.
- **REQ-CFG-110.** An automatically selected `record_id` MUST be present in every record, non-null, parser-native string-valued, and unique within each dataset. It MAY be selected from matching CSV or TSV headers when both datasets contain zero records.
- **REQ-CFG-111.** If an automatically selected `record_id` fails any key requirement, the run MUST produce an `input.invalid_record_key` execution error. The tool MUST NOT fall back to another candidate key.
- **REQ-CFG-112.** If `record_id` is not observed on both sides, an automatic key candidate MUST satisfy all of the following conditions:
  1. the exact same field name is observed on both sides;
  2. the field is present in every record on both sides;
  3. every value is a non-null parser-native string;
  4. values are unique within each dataset; and
  5. the reference and query value sets have at least one exactly equal value in common.
- **REQ-CFG-113.** Candidate assessment MUST use preserved source strings without conversion or normalisation. It MUST NOT rank candidates by column position, name patterns, preferred-name lists, value-set overlap, or any other heuristic.
- **REQ-CFG-114.** If exactly one field satisfies `REQ-CFG-112`, it MUST be selected as the single-field record key. If none qualifies, the run MUST produce an `input.invalid_record_key` execution error explaining that no automatic key could be established. If more than one qualifies, the same error code MUST identify the candidate field names and explain that key selection is ambiguous. Source key values MUST NOT be reproduced in the diagnostic.
- **REQ-CFG-115.** Automatic mode MUST NOT construct a composite key. A composite key requires a custom comparison configuration.

#### 6.9.2 Generated field definitions

- **REQ-CFG-130.** The generated effective configuration MUST use `schema_version: "1.0"`, `metadata.id: "org.adviso.automatic-strict-exact"`, and `metadata.revision: "1.0"`. The identifier is reserved for tool-generated automatic configurations so that result consumers can identify the configuration's origin without an additional results property.
- **REQ-CFG-131.** The selected key field's canonical, reference source, and query source names MUST be identical. It MUST be declared as required and non-nullable on both sides, with logical type `string` and comparator `typed_exact`.
- **REQ-CFG-132.** Every non-key source-field name observed on both sides MUST become one generated canonical field whose canonical, reference source, and query source names are identical. It MUST be included in `fields.in_scope`, be optional on both sides, permit null with null equal to null, use `preserved_exact`, and have no logical type, missing tokens, mapping, normalisation, coercion, or tolerance.
- **REQ-CFG-133.** A source field observed on only one side MUST remain undefined in the generated configuration and MUST be represented by an `undeclared_field_excluded` entry under Section 9.1.3. It MUST NOT produce a finding or value opportunity.
- **REQ-CFG-134.** The generated `fields.record_key` MUST contain only the selected key. `fields.in_scope` and `fields.definitions` MUST contain the selected key and every same-name field observed on both sides, ordered by Unicode code point with the key first.
- **REQ-CFG-135.** The generated document MUST validate against the comparison-configuration schema and all applicable semantic configuration rules before the contract phase begins. It MUST be embedded unchanged in the canonical result as the effective comparison configuration.

**REQ-CFG-094.** Automatic mode MUST perform no type inference, implicit coercion, value mapping, normalisation, or tolerance. Non-key values compare according to `preserved_exact`, so lexically or scientifically equivalent representations can differ, particularly across input formats. The HTML report MUST identify automatic mode prominently, explain that only identically named fields observed on both sides were compared, and direct the user to review exclusions before interpreting the findings. A custom configuration is required whenever record identity, field correspondence, or value equivalence requires domain knowledge.

## 7. Comparison behaviour

### 7.1 Comparison phases

**REQ-CMP-001.** Every comparison MUST perform all three phases in this order:

1. **Contract:** assess fields, logical types, key definitions, nullability, mappings, and declared data-contract constraints.
2. **Records:** align valid record identities and assess matching, missing, and extra records.
3. **Values:** compare corresponding values using declared comparators.

**REQ-CMP-002.** A finding or `not_assessable` item in an earlier phase MUST NOT automatically prevent later assessment.

**REQ-CMP-003.** Later comparison MUST continue wherever its prerequisites remain satisfied.

**REQ-CMP-004.** In-scope content that cannot be compared safely MUST be `not_assessable`. Content outside `fields.in_scope` MUST be `not_assessed`.

**REQ-CMP-005.** A run MUST conceptually:

1. validate a supplied custom comparison configuration, if any;
2. identify and hash inputs;
3. parse inputs without silent loss;
4. when no custom configuration was supplied, construct and validate the automatic effective comparison configuration;
5. perform the contract phase;
6. align and compare records;
7. compare values for safely aligned records;
8. determine whether every configured assessment was completed;
9. write results and provenance atomically.

### 7.2 Contract comparison

**REQ-CMP-006.** The contract phase MUST assess declared and observed fields from both directions for every record. It MUST distinguish:

- **REQ-CMP-034.** field present and valid;
- **REQ-CMP-035.** required field missing from the reference or query;
- **REQ-CMP-036.** configured in-scope field or content excluded from assessment;
- **REQ-CMP-037.** invalid logical type, null state, mapping, or controlled value;
- **REQ-CMP-038.** field deliberately `not_assessed`;
- **REQ-CMP-039.** field `not_assessable` because a prerequisite failed.

**REQ-CMP-007.** One record’s observed field set MUST NOT be assumed to represent every other record.

**REQ-CMP-008.** Key presence, validity, and uniqueness MUST always be assessed because later interpretation depends on an unambiguous record model.

**REQ-CMP-009.** For a zero-record dataset, contract requirements that can be evaluated from available structural information, such as CSV or TSV headers, MUST still be assessed.

**REQ-CMP-010.** A per-record requirement with no applicable record opportunity MUST be treated as not applicable, not as satisfied, violated, `not_assessed`, or `not_assessable`. It MUST contribute no finding or value count. This rule does not suppress contract checks supported by available dataset-level structure.

### 7.3 Records comparison

**REQ-CMP-011.** For the union of normalised valid record keys, the records phase MUST classify each key as matching, missing from the query, or extra in the query. Duplicate or otherwise invalid keys are execution errors under Section 8.3, not ordinary record findings.

**REQ-CMP-012.** Missing records MUST be reported individually. Extra records MUST be reported individually. Query-only records MUST NOT be ignored. Missing or extra records MUST NOT prevent value comparison of the safely aligned intersection.

### 7.4 Values comparison and comparators

**REQ-CMP-013.** The values phase MUST compare every valid non-key field listed in `fields.in_scope` in safely aligned records.

**REQ-CMP-014.** A value whose contract or alignment prerequisite failed MUST be `not_assessable`. Other values MUST continue to be compared.

**REQ-CMP-015.** The first release MUST support the following deterministic comparators with stable identifiers.

#### 7.4.1 `preserved_exact`

Values match according to the parser-native value model and equality rules in Section 5.6. No logical type, additional missing-token recognition, inference, coercion, mapping, normalisation, or tolerance is applied. Textual `"1"`, integer `1`, decimal `1.0`, and boolean `true` are distinct.

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
- **REQ-CMP-040.** List elements use their declared element comparator positionally: element `n` in the reference is compared only with element `n` in the query. Numeric tolerance is therefore unambiguous for lists.
- **REQ-CMP-041.** Set and multiset elements use typed-exact equality. Version 1 MUST NOT perform tolerance-based or other fuzzy matching within an unordered collection.

### 7.5 Completeness, subsets, and determinism

- **REQ-CMP-026.** Findings MUST NOT terminate a normal run.
- **REQ-CMP-027.** All assessable differences MUST be collected.
- **REQ-CMP-028.** A malformed record that prevents a complete and unambiguous record model MUST be an input error.
- **REQ-CMP-029.** A malformed record MUST NOT disappear silently.
- **REQ-CMP-030.** Key fields MUST always be processed.
- **REQ-CMP-031.** Out-of-scope content MUST be represented by exclusion summaries rather than individual findings or per-record exclusions. The canonical report MUST distinguish fields deliberately omitted from `fields.in_scope` from observed source fields not represented in `fields.definitions`.
- **REQ-CMP-032.** Record order MUST NOT affect the comparison outcome defined in Section 9.1. Input digests, source locations, messages containing those locations, and report-local finding IDs MAY differ as permitted by the provenance and ordering rules.
- **REQ-CMP-033.** Output ordering MUST be deterministic and independent of hash-map ordering and locale.

## 8. Findings and run status

### 8.1 Finding structure

**REQ-FND-001.** Every finding MUST follow the structured representation in Section 9.1.2 and the normative results schema.

**REQ-FND-002.** Every finding MUST contain a stable finding code, finding classification, deterministic report-local ID, phase, affected side, and human-readable message.

**REQ-FND-003.** Record identity, source locations, canonical or source field name, review priority, and value evidence MUST be present exactly where required by the finding code and data-minimisation rules.

**REQ-FND-004.** Human-readable messages MUST NOT be the sole machine-readable representation of a finding.

**REQ-FND-005.** Successful field matches MUST be represented in summary counts. Successful record matches MUST be represented in summary counts. Successful matches MUST NOT produce individual findings.

### 8.2 Finding codes and classifications

**REQ-FND-006.** Stable finding codes MUST exist for at least:

- **REQ-FND-008.** missing record;
- **REQ-FND-009.** extra record;
- **REQ-FND-010.** missing required field;
- **REQ-FND-012.** type mismatch: the parser-native category of a non-null source value is not accepted by the field's declared logical type under the matrix in Section 6.5;
- **REQ-FND-013.** invalid field value: the parser-native category is accepted by the declared logical type, but the value fails its lexical, domain, collection-content, or other field-level validity rule;
- **REQ-FND-014.** null-policy violation;
- **REQ-FND-015.** mapping failure;
- **REQ-FND-016.** value mismatch: both values are valid and assessable, but the selected comparator determines that they differ;

**REQ-FND-023.** Every finding MUST have exactly one of two classifications. Classification expresses the meaning of a finding, while phase records where in processing it was detected; neither replaces the other.

- **REQ-FND-024.** `comparison_difference` means that translation succeeded sufficiently to compare the relevant records or values and a difference remained. `missing_record`, `extra_record`, and `value_mismatch` MUST have this classification.
- **REQ-FND-025.** `assessment_issue` means that the declared translation or assessment could not be applied cleanly to some input content. `missing_required_field`, `type_mismatch`, `invalid_field_value`, `null_policy_violation`, and `mapping_failure` MUST have this classification.

Finding classification does not assert scientific or clinical significance. In particular, an assessment issue such as an unrecognised mapped value may be important to investigate, but the tool cannot report it as a post-translation difference because translation did not succeed.

**REQ-FND-018.** `type_mismatch`, `invalid_field_value`, and `value_mismatch` are mutually exclusive for one affected value or value opportunity. A parser-native category difference under `preserved_exact` MUST be a `value_mismatch`, not a `type_mismatch`, because no logical type contract has been declared.

**REQ-FND-019.** A record-specific missing-required-field, type-mismatch, invalid-field-value, null-policy-violation, or mapping-failure finding MUST describe one record, one canonical field, and one affected dataset side. If reference and query independently violate the same field rule, the tool MUST emit two findings, one with `affected_side: reference` and one with `affected_side: query`. It MUST NOT combine the independent violations into one `both` finding. The dataset-level zero-record missing-field case is the explicit exception defined by `REQ-FND-022`.

**REQ-FND-020.** A value-mismatch finding MUST describe one comparison between two individually valid, assessable values and MUST use `affected_side: both`. Missing-record and extra-record findings remain one finding per affected record key.

**REQ-FND-022.** If a zero-record CSV or TSV header omits a declared source column that is required on that dataset side, the tool MUST emit one dataset-level `missing_required_field` finding for that canonical field and side. It contains the canonical field and review priority but no record identity, source location, or value evidence. An empty JSON array cannot produce this finding because it exposes no field structure.

**REQ-FND-017.** `not_assessable` MUST be a value-opportunity classification, not a finding code. Every not-assessable opportunity MUST be explained by its applicable causal finding, such as `missing_required_field`, `type_mismatch`, `invalid_field_value`, `null_policy_violation`, or `mapping_failure`. The tool MUST NOT emit an additional finding merely to repeat that the affected opportunity is not assessable.

**REQ-FND-007.** Execution errors MUST NOT be represented as findings or assigned finding codes. In particular, invalid invocation or configuration, malformed input structure, invalid record keys, resource failure, I/O failure, and internal failure are execution errors governed by Section 8.3.

### 8.3 Run status

**REQ-RUN-001.** Run status MUST be one of:

- **REQ-RUN-015.** `complete`: every configured assessment was performed wherever the configuration and inputs made it applicable;
- **REQ-RUN-016.** `incomplete`: the inputs and record model remain sufficiently trustworthy for a useful comparison, but one or more configured assessments could not be completed safely because a comparison prerequisite was not satisfied;
- **REQ-RUN-017.** `error`: no trustworthy comparison result could be produced because of an invalid invocation or comparison configuration, malformed or unreadable input syntax or structure, a missing, null, invalid, or duplicate record key, an incomplete or ambiguous record model, an enforced resource limit, resource exhaustion, an input/output failure, or an unexpected internal failure.

**REQ-RUN-002.** Findings, whether classified as `comparison_difference` or `assessment_issue`, MUST NOT by themselves change a run from `complete` to `incomplete` or `error`. A finding may identify a not-assessable opportunity that independently makes the run incomplete under `REQ-RUN-003`. Run status describes completeness and operational validity, not acceptability.

**REQ-RUN-003.** Any configured content classified as `not_assessable` MUST make the run `incomplete`.

**REQ-RUN-004.** Deliberately `not_assessed` content MUST NOT make the run `incomplete`.

**REQ-RUN-005.** An incomplete report MUST identify the affected content. It MUST identify why the comparison prerequisite was not satisfied.

**REQ-RUN-006.** Content that is parseable and attributable to an unambiguous record but violates the declared data contract MUST be recorded as an `assessment_issue` finding rather than an execution error.

**REQ-RUN-007.** Comparisons that remain assessable MUST continue.

**REQ-RUN-008.** An errored run MUST write a concise diagnostic to standard error and MUST NOT publish an evidence-package directory or any filesystem report.

**REQ-RUN-009.** The diagnostic MUST contain a stable execution-error code and category, a concise actionable message, and sufficient non-sensitive context to locate the cause.

**REQ-RUN-010.** The diagnostic MUST NOT contain findings, finding codes, comparison summary metrics, phase statuses, record identifiers, or source values.

**REQ-RUN-024.** Version 1 execution errors MUST use exactly one of the following category and code combinations:

| Category | Code | Meaning |
| --- | --- | --- |
| `invocation` | `invalid_arguments` | Command-line arguments are missing, invalid, or mutually incompatible |
| `configuration` | `unreadable` | The selected comparison configuration cannot be read |
| `configuration` | `invalid_syntax` | The comparison configuration is not permitted YAML syntax |
| `configuration` | `schema_violation` | The parsed comparison configuration does not satisfy its JSON Schema |
| `configuration` | `semantic_violation` | The configuration is schema-valid but violates a semantic configuration rule |
| `configuration` | `unsupported_version` | The configuration names an unsupported schema version |
| `input` | `unreadable` | A reference or query input cannot be read |
| `input` | `unsupported_format` | An input has a missing, unknown, or ambiguous filename extension |
| `input` | `invalid_encoding` | An input is not valid UTF-8 |
| `input` | `invalid_syntax` | Input text is malformed for the format selected by its extension |
| `input` | `invalid_structure` | Parsed input does not satisfy the required dataset or record structure |
| `input` | `invalid_record_key` | A record key is missing, null, invalid, duplicated, undiscoverable, ambiguous, or otherwise unable to form an unambiguous record model |
| `resource` | `limit_exceeded` | A documented implementation safeguard stops assessment |
| `resource` | `exhausted` | An unplanned resource exhaustion prevents completion |
| `output` | `invalid_destination` | The selected output destination violates destination or overwrite rules |
| `output` | `write_failed` | The evidence package cannot be written or published |
| `internal` | `unexpected` | An unexpected implementation failure occurs, including generated-result self-validation failure |

**REQ-RUN-025.** The execution-error code MUST be the dotted combination `<category>.<code>`. The first diagnostic line MUST have the exact form `ERROR [<category>.<code>]: <message>`. The message MUST be non-empty and MUST NOT contain a line break. Additional non-sensitive context MAY follow on subsequent lines.

**REQ-RUN-026.** Every execution-error code except `internal.unexpected` MUST return exit code 2. `internal.unexpected` MUST return exit code 3.

**REQ-RUN-011.** Findings accumulated internally before the error occurred MUST NOT be published as a partial comparison result.

**REQ-RUN-012.** Each phase MUST record whether it was `complete` or `incomplete`.

Overall status is `complete` only when all three phases are complete.

**REQ-RUN-018.** The contract phase MUST be `complete` when every applicable contract check was performed. Contract findings, including missing-field, type, invalid-value, null-policy, and mapping findings, MUST NOT by themselves make the contract phase incomplete.

**REQ-RUN-019.** The records phase MUST be `complete` when valid record keys were constructed and every record was aligned and classified. Missing-record and extra-record findings MUST NOT make the records phase incomplete. A key or record-model failure that prevents this assessment is an execution error and produces no comparison phase statuses.

**REQ-RUN-020.** The values phase MUST be `complete` when every applicable in-scope value opportunity was compared. It MUST be `incomplete` when at least one such opportunity is `not_assessable`.

**REQ-RUN-021.** A finding MUST NOT by itself make a phase incomplete. A phase is incomplete only when an intended assessment within that phase could not be performed safely.

**REQ-RUN-022.** Content classified as `not_assessed` because it is outside `fields.in_scope` MUST NOT make any phase incomplete.

**REQ-RUN-023.** Overall run status MUST be `complete` if and only if the contract, records, and values phases are all `complete`; otherwise a non-error comparison run MUST be `incomplete`.

**REQ-RUN-013.** The tool MUST report raw findings and metrics without applying acceptance thresholds. It MUST NOT produce a pass/fail verdict.

### 8.4 Laboratory decision

The run status and reported differences do not constitute a laboratory validation, approval, or acceptance decision. Any acceptance criteria and their application belong to a separately governed process outside the tool.

**REQ-RUN-014.** Reports MUST label these concepts separately. Reports MUST NOT describe the output as “ISO 15189 compliant”, “clinically validated”, or equivalent.

## 9. Output and evidence

**REQ-OUT-001.** A non-error comparison, whether `complete` or `incomplete`, MUST create an evidence-package directory at the destination selected by `--output`.

**REQ-OUT-002.** The evidence package MUST contain the canonical JSON result and the HTML report. Version 1 MUST NOT produce any additional report or findings-export format.

**REQ-OUT-115.** The canonical JSON result MUST be named `comparison-results.json`, and the HTML report MUST be named `comparison-report.html`. These names are fixed for evidence-package version 1.

No separate package manifest is required in version 1; `comparison-results.json` contains the comparison and provenance metadata.

**REQ-OUT-003.** Package member names MUST be stable and documented. Package layout MUST be stable and documented.

### 9.1 Machine-readable output

**REQ-OUT-004.** JSON MUST be the canonical output format. Its normative JSON Schema Draft 2020-12 definition is [`src/adviso_validation/schemas/comparison-results-v1.0.schema.json`](../src/adviso_validation/schemas/comparison-results-v1.0.schema.json).

**REQ-OUT-125.** `comparison-results.json` MUST be serialized as RFC 8259 JSON encoded as UTF-8 without a byte-order mark, using two-space indentation, LF line endings, and exactly one final newline. Non-ASCII characters MUST be emitted directly rather than escaped unless escaping is required by JSON syntax. Members of fixed-schema objects MUST be emitted in their documented schema order; members of dynamically named objects MUST be emitted in Unicode code-point order.

**REQ-OUT-112.** The results schema MUST use `https://adviso-project.github.io/validation_toolkit/schemas/comparison-results-v1.0.schema.json` as its canonical `$id`.

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

**REQ-OUT-009.** The `run` object MUST contain `id`, `status`, and `completed_at`. `id` MUST be a randomly generated UUID version 4 in canonical lowercase hyphenated form.

**REQ-OUT-010.** `completed_at` MUST be an RFC 3339 UTC timestamp using `Z` and whole-second precision, in the exact form `YYYY-MM-DDTHH:MM:SSZ`.

**REQ-OUT-011.** Start time MUST NOT be included. Elapsed duration MUST NOT be included.

**REQ-OUT-012.** Run ID and completion time are deliberately variable metadata and MUST be excluded from repeat-determinism comparisons.

**REQ-OUT-095.** For determinism requirements, the comparison outcome consists of run and phase statuses; summary counts; exclusions considered without input occurrence order; and each finding's classification, code, phase, affected side, record identity, canonical or source field identity, review priority, and value evidence. It excludes run ID, completion time, software-runtime provenance, input byte provenance, source locations, human-readable messages that reproduce variable locations, and report-local finding IDs.

**REQ-OUT-096.** Given the same exact input bytes, input basenames, configuration selection, toolkit version, and runtime identity, all canonical result content other than `run.id` and `run.completed_at` MUST be identical. Repeated automatic-mode runs therefore MUST generate byte-identical effective configuration documents.

**REQ-OUT-097.** Changing only input record order or accepted LF/CRLF line endings MUST leave the comparison outcome unchanged. Exact-byte input size and digest, source locations, location-dependent messages, and report-local finding IDs MAY change. The result for each particular ordered byte input MUST still satisfy all deterministic ordering rules.

**REQ-OUT-098.** Across supported Python versions and operating systems, the comparison outcome MUST remain invariant for identical inputs and configuration selection. Recorded runtime provenance MAY differ. Release testing MUST verify that Unicode-data differences do not silently change comparison outcomes across the supported matrix.

**REQ-OUT-013.** The `phases` object MUST contain `contract`, `records`, and `values`, each with status `complete` or `incomplete`.

**REQ-OUT-014.** Overall run status MUST be `complete` if and only if all three phases are complete.

**REQ-OUT-015.** The `software` object MUST identify `adviso-validation` and its version. A build identifier MAY be included when available.

**REQ-OUT-016.** The `runtime` object MUST record Python version, a normalized non-identifying platform identifier, and the Unicode-data version.

**REQ-OUT-121.** `runtime.python` MUST have the form `<implementation>-<major>.<minor>.<micro>`, using a lowercase implementation name and the full runtime version, for example `cpython-3.12.7`. A prerelease suffix MAY follow the micro version when applicable.

**REQ-OUT-122.** `runtime.platform` MUST have the form `<operating-system-family>-<architecture>` using lowercase normalized names, for example `linux-x86_64`, `linux-aarch64`, `windows-x86_64`, or `macos-aarch64`. `amd64` MUST be normalized to `x86_64`, and `arm64` MUST be normalized to `aarch64`. The supported release matrix determines the permitted combinations.

**REQ-OUT-123.** `runtime.platform` MUST NOT include a distribution name, distribution version, kernel version, hostname, or other host-specific detail.

**REQ-OUT-124.** `runtime.unicode_version` MUST be the exact runtime Unicode database version in `<major>.<minor>.<patch>` form.

**REQ-OUT-017.** Hostname, username, environment variables, working directory, absolute paths, raw command line, and a full dependency inventory MUST NOT be included.

**REQ-OUT-018.** Each input object MUST contain its automatically captured basename, selected format, UTF-8 encoding, byte size, and SHA-256 digest of the exact input bytes.

**REQ-OUT-019.** Absolute paths MUST NOT be included.

Basenames form part of the potentially sensitive evidence covered by Section 11.

**REQ-OUT-020.** V1 MUST use one fixed documented interpretation for CSV. It MUST use one fixed documented interpretation for TSV. Because format uniquely determines that interpretation, no dialect identifier appears in the result.

**REQ-OUT-021.** `record_key_fields` MUST declare the ordered source key-field names for the reference and query and the ordered canonical key-field names. Findings identify records through corresponding ordered arrays of source lexical values and canonical textual values. Canonical key components MUST use the scalar rendering rules in `REQ-OUT-029`. A single-field key is represented by a one-element array. Each identity array MUST have the same length as its corresponding field-name array. The reference or query identity is JSON null when that record is absent on that side; the canonical identity is always present.

**REQ-OUT-022.** `comparison_configuration.document` MUST contain the complete validated JSON-compatible effective comparison configuration. In automatic mode, this MUST be the generated document defined in Section 6.9.

**REQ-OUT-023.** The embedded document MUST validate against the referenced comparison-configuration schema.

**REQ-OUT-113.** A result with `results_schema_version: "1.0"` MUST embed a comparison configuration with `schema_version: "1.0"`. Support for a later comparison-configuration schema version requires a corresponding results-schema version that explicitly references that configuration-schema version.

No comparison-configuration digest or command-invocation object is included in version 1.

#### 9.1.1 Value evidence

**REQ-OUT-026.** When a finding includes field evidence, `values.reference` and `values.query` MUST each state whether the field is `present` or `absent`. An absent side has no source or canonical value. An explicit null is present and is represented explicitly rather than as absence.

**REQ-OUT-027.** Parser-native source values MUST use typed objects. Strings retain their text; integer and decimal values retain their source lexical text; booleans use JSON booleans; null has no `value`; arrays contain recursively typed source values; and objects map member names to recursively typed source values.

**REQ-OUT-028.** Object member order has no semantic significance. Object members MUST be serialized in Unicode code-point order.

**REQ-OUT-029.** Canonical scalar values MUST contain their logical type and one uniquely rendered value:

- **REQ-OUT-089.** A canonical integer MUST use ordinary base-10 text with no leading plus sign or unnecessary leading zeros; zero is `"0"`.
- **REQ-OUT-090.** A canonical decimal zero, including negative zero, MUST be `"0"`. Every non-zero canonical decimal MUST use normalized scientific form with exactly one non-zero digit before the optional decimal point, no trailing fractional zeros, lowercase `e`, no `e0`, no positive exponent sign, and no exponent leading zeros. For example, `1.00`, `1000`, `12.30`, `0.0010`, and `-0.0` become `"1"`, `"1e3"`, `"1.23e1"`, `"1e-3"`, and `"0"` respectively.
- **REQ-OUT-091.** A canonical date MUST use `YYYY-MM-DD`.
- **REQ-OUT-092.** A canonical datetime MUST be converted to UTC, use uppercase `Z`, remove unnecessary trailing fractional-second zeros, and omit a zero-valued fractional component.
- **REQ-OUT-093.** A canonical boolean MUST use a JSON boolean. A canonical string MUST contain its Unicode text after configured processing without any additional transformation.
- **REQ-OUT-094.** Canonical collections MUST contain the collection logical type, scalar element type, and an array of compact canonical element values. Lists preserve order. Sets and multisets MUST be serialized in locale-independent Unicode code-point order of the canonical element strings; multiset duplicates remain adjacent. Null uses the declared logical type with a JSON null value. A `preserved_exact` field has no typed canonical value.

**REQ-OUT-030.** Values MUST be included only as follows:

- **REQ-OUT-061.** missing and extra record findings contain no field values;
- **REQ-OUT-062.** record-specific missing-required-field findings contain presence states but do not reproduce the present side's value; the dataset-level zero-record form contains no value evidence;
- **REQ-OUT-064.** type-mismatch findings contain source values for affected sides and canonical values only where parsing succeeded;
- **REQ-OUT-065.** invalid-field-value and mapping-failure findings contain the affected source value and no failed canonical value;
- **REQ-OUT-066.** null-policy-violation findings contain the affected source and canonical null representation;
- **REQ-OUT-067.** value-mismatch findings MUST state the presence state of both sides. Each present side MUST contain its source value and, for a declared typed field, its canonical value. An absent side contains neither value. A mismatch of two present untyped values contains no typed canonical values.
- **REQ-OUT-068.** A causal finding for a not-assessable value opportunity MUST contain only the values permitted for that finding code and necessary to explain the failed prerequisite. It MUST NOT contain separate or duplicated not-assessable evidence.

**REQ-OUT-031.** Implementations MUST NOT add additional source values merely for convenience.

#### 9.1.2 Findings

**REQ-OUT-032.** Every finding MUST contain a deterministic report-local ID, finding classification, finding code, phase, human-readable English message, and affected side.

**REQ-OUT-033.** A message is presentation text derived deterministically from structured properties. It MUST NOT add facts absent from those properties, and every machine-significant fact in a message MUST also be represented by a structured property or finding code.

Specification-requirement identifiers are not included in version 1. Finding classification is included explicitly and MUST agree with the finding code according to Section 8.2.

The closed version 1 finding-code vocabulary is:

- `missing_record`;
- `extra_record`;
- `missing_required_field`;
- `type_mismatch`;
- `invalid_field_value`;
- `null_policy_violation`;
- `mapping_failure`;
- `value_mismatch`.

**REQ-OUT-034.** `affected_side` MUST be `reference`, `query`, or `both` as required by the finding code. A finding attributable to a declared canonical field MUST contain that field name and its resolved review priority. Record-specific findings MUST contain record identity and source locations; dataset-level missing-required-field findings omit record identity and source locations.

**REQ-OUT-117.** For CSV and TSV, every record-specific source location MUST contain the one-based data-record number, excluding the header, and the one-based physical line number on which the record begins. Embedded newlines in a quoted field do not change that record's starting line. A location for a present field MUST also contain its source field name; a record-level location or a location for an absent field MUST omit the field name.

**REQ-OUT-118.** For JSON, a record-level source location MUST contain the RFC 6901 JSON Pointer to the array element, such as `/3`. A location for a present field MUST contain the full pointer to that member, such as `/3/result`, with `~` and `/` escaped as `~0` and `~1`. A location for an absent field MUST identify its containing record because the absent member has no source location.

**REQ-OUT-119.** Reference and query locations MUST be represented independently. A location MUST be null when the corresponding record does not exist. If the record exists but the relevant field is absent, the location MUST identify the containing record as specified above.

**REQ-OUT-035.** Findings MUST be sorted by this complete, locale-independent order:

1. classification: `comparison_difference`, `assessment_issue`;
2. phase: `contract`, `records`, `values`;
3. dataset-level findings before record-specific findings;
4. canonical record identity, compared component-by-component as Unicode strings;
5. canonical field name, with no field sorting component for record findings;
6. finding code in the fixed vocabulary order listed in Section 9.1.2;
7. affected side: `reference`, `query`, `both`;
8. source locations, comparing reference before query, with a null location before a present location; tabular locations compare by record number, physical line number, and field name, while JSON locations compare by JSON Pointer using Unicode code-point order; and
9. canonical JSON serialization of all remaining structured finding properties except `id` and `message`.

**REQ-OUT-099.** Two candidate findings identical under the final ordering key represent the same finding and MUST be coalesced rather than emitted twice. IDs `F000001`, `F000002`, and so on MUST be assigned only after coalescence and sorting. IDs are stable within one result but are not persistent identifiers across materially different comparisons.

**REQ-OUT-036.** Comparator parameters, mappings, and normalisation declarations MUST NOT be repeated in findings. Consumers and the HTML renderer obtain them from the embedded configuration using the canonical field name. Source and canonical values show their effect for the affected record.

#### 9.1.3 Summary and exclusions

**REQ-OUT-037.** The summary MUST contain complete fixed-shape counts, including zero-valued entries. Record counts comprise reference records, query records, matched records, missing records, and extra records. Value counts comprise matched, mismatched, and not-assessable in-scope non-key value opportunities. Finding counts comprise total findings, both finding classifications, every version 1 finding code, and review priorities `low`, `normal`, `high`, and `unassigned`.

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

Fields absent from `fields.in_scope`, including observed source fields not represented by any field definition, do not contribute value opportunities.

**REQ-OUT-040.** `summary.findings.total` MUST equal the number of emitted findings. Counts by classification, by code, and by review priority MUST each sum to the total. Record findings, which are not attributable to a declared non-key field, count as `unassigned` review priority.

**REQ-OUT-041.** `exclusions` MUST always be an array containing exactly these two forms:

- one `configured_field_excluded` entry for every canonical field in `fields.definitions` but absent from `fields.in_scope`; each such entry contains only `code` and `canonical_field`;
- one `undeclared_field_excluded` entry for every observed source field not represented by a field definition on that dataset side; each such entry contains `code`, `side`, `source_field`, and the number of records containing the field.

Configured-field exclusions MUST be ordered first by `canonical_field` using Unicode code-point order. Undeclared-field exclusions follow, ordered first by side (`reference`, then `query`) and then by `source_field` using Unicode code-point order. Exclusions are not findings, do not have review priorities, and do not contribute to value counts. A source field known only from a zero-record CSV or TSV header has record count zero.

#### 9.1.4 Structural and semantic result validation

**REQ-OUT-100.** The results schema MUST define each finding form as an exact alternative. For each finding code it MUST require the applicable classification and properties and reject properties that are not permitted for that form, including the record-specific and dataset-level forms of `missing_required_field`.

**REQ-OUT-101.** Schema validation alone is not sufficient to establish that a canonical result is internally coherent. The implementation MUST also apply semantic result validation.

**REQ-OUT-102.** Semantic result validation MUST verify that overall run status agrees with all phase statuses.

**REQ-OUT-103.** Semantic result validation MUST verify the record-count reconciliation equations in `REQ-OUT-038`.

**REQ-OUT-104.** Semantic result validation MUST verify that every finding count agrees with the findings array and that counts by classification, code, and review priority each sum to the total.

**REQ-OUT-105.** Semantic result validation MUST verify that every record-key field-name array and corresponding record-identity value array has the required common length and component order.

**REQ-OUT-106.** Semantic result validation MUST verify that findings and exclusions use the required order, including classification-first finding order, that duplicate findings are absent, and that finding IDs are sequential after sorting.

**REQ-OUT-107.** Semantic result validation MUST verify that each finding's classification, presence states, value evidence, locations, affected side, field identity, and review priority are consistent with its code, form, embedded configuration, and causal condition.

**REQ-OUT-108.** Semantic result validation MUST verify that `record_key_fields`, finding field identities, review priorities, configured-field exclusions, and other configuration-derived metadata agree with the embedded comparison configuration. It MUST also verify that undeclared-field exclusions agree with the source fields observed on each dataset side.

**REQ-OUT-109.** Before publishing an evidence package, the tool MUST validate the generated canonical result against the results schema and every semantic result rule.

**REQ-OUT-110.** Failure of generated-result validation MUST be treated as an unexpected internal error. The invalid canonical result and any HTML derived from it MUST NOT be published as an evidence package.

**REQ-OUT-111.** The user guide MUST distinguish structural JSON Schema validation from semantic result validation and document the invariants checked by each layer.

**REQ-OUT-114.** Generated-result schema validation MUST enable JSON Schema Draft 2020-12 format assertion. Invalid values for recognised formats, including UUIDs, dates, and date-times, MUST fail self-validation. The user guide's documented procedure for validating canonical results MUST instruct users to enable equivalent format assertion.

### 9.2 Human-readable output

**REQ-OUT-042.** The first release MUST produce an HTML human-readable report. The report MUST include:

- **REQ-OUT-074.** purpose of the run and the three comparison phases performed;
- **REQ-OUT-075.** prominent run status and per-phase completion status;
- **REQ-OUT-076.** identities of reference, query, and comparison configuration;
- **REQ-OUT-077.** summary counts;
- **REQ-OUT-078.** measured counts and findings, without an acceptance verdict;
- **REQ-OUT-079.** grouped discrepancy details;
- **REQ-OUT-080.** limitations, exclusions, and unassessed content;
- **REQ-OUT-081.** provenance and reproduction information;
- **REQ-OUT-082.** space or linkage for review and approval outside the tool.

**REQ-OUT-127.** The report's headline summary MUST present run completeness, total `comparison_difference` findings, and total `assessment_issue` findings as distinct measures. It MUST NOT describe either finding count as an acceptance or validation verdict.

**REQ-OUT-128.** Detailed findings MUST be organized primarily by classification, with comparison differences presented before assessment issues. Phase MUST remain visible as secondary traceability information and MAY be used for subgrouping within each classification.

**REQ-OUT-120.** `comparison-report.html` MUST be generated solely from the validated contents of `comparison-results.json` and fixed renderer resources. It MUST NOT contain additional comparison facts, findings, metrics, provenance, or run metadata unavailable in the canonical JSON. Fixed explanatory text and blank or generic external review and approval space MAY be added by the renderer.

**REQ-OUT-126.** `comparison-report.html` MUST be self-contained and fully usable offline. Required styling MUST be embedded. The report MUST NOT load external scripts, stylesheets, fonts, images, tracking resources, or any other network resource. Core content and navigation MUST remain usable with scripting disabled. Embedded scripting MAY provide non-essential navigation or filtering enhancements but MUST NOT change or supply comparison content.

### 9.3 Atomicity and overwrite protection

- **REQ-OUT-044.** Output files MUST be written atomically where supported.
- **REQ-OUT-045.** The complete evidence-package directory MUST be published atomically where the platform supports it.
- **REQ-OUT-046.** Without `--overwrite`, any existing filesystem object at the selected destination MUST cause an output error. With `--overwrite`, the tool MAY replace only an existing regular directory that is recognisably a complete version 1 evidence package containing exactly `comparison-results.json` and `comparison-report.html`. It MUST reject an existing regular file, symbolic link, special filesystem object, empty directory, partial package, or directory containing any additional entry, even when `--overwrite` is supplied.
- **REQ-OUT-116.** When replacing an existing evidence package, the tool MUST leave the existing package intact until the replacement package has been fully generated and has passed structural and semantic self-validation. A failed replacement MUST preserve the existing package.
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

**REQ-CLI-010.** Omission of `--configuration` MUST select automatic strict-exact mode. When `--configuration` is present, its value MUST be treated only as the path to a custom comparison-configuration file.

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

**REQ-DEP-013.** Comparison outcomes, as defined by `REQ-OUT-095`, MUST remain invariant across supported Python versions and operating systems. Runtime provenance MAY differ.

**REQ-DEP-014.** Internal exceptions MUST be converted into the standard-error diagnostic required by Section 8.3. A traceback MUST NOT be shown during ordinary CLI use.

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
- **REQ-DOC-009.** how automatic strict-exact mode selects a key, generates its effective configuration, compares shared fields, handles exclusions, and can fail when key selection is impossible or ambiguous, together with how to create, validate, and govern a custom comparison configuration;
- **REQ-DOC-010.** every property in the comparison-configuration schema, including its purpose, permitted values, required or optional status, default or omission semantics, constraints, and interactions with other properties;
- **REQ-DOC-011.** the translation-to-canonical comparison model, field-scope and exclusion behaviour, finding classifications, comparison phases, processing order, comparators, mappings, normalisation operations, null handling, and review priorities;
- **REQ-DOC-012.** the contents and interpretation of the evidence package;
- **REQ-DOC-013.** every property in the canonical results JSON schema, including finding classifications and codes, typed source and canonical values, counts, exclusions, run and phase statuses, and provenance fields; the guide MUST explain that software consuming a result must first validate `results_schema_version` and must use structured properties, classifications, and finding codes rather than parsing presentation messages;
- **REQ-DOC-014.** execution-error diagnostics and common corrective actions;
- **REQ-DOC-015.** the tool's intended use, non-claims, security and data-governance boundaries, and known limitations; and
- **REQ-DOC-016.** the toolkit, comparison-configuration-schema, and results-schema versions to which the documentation applies.

**REQ-DOC-002.** The guide MUST include complete, runnable examples covering automatic strict-exact mode, including automatic key discovery, and representative custom configuration features.

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

**REQ-REL-002.** Comparison-configuration schemas, results schemas, and toolkit releases MUST each have their own version identifier and MUST NOT be assumed to advance in lockstep or to use matching version numbers. Each results-schema version nevertheless references the exact comparison-configuration schema version or versions permitted in that result, as required by `REQ-OUT-113`.

**REQ-REL-003.** Each toolkit release MUST document the comparison-configuration schema versions it supports. It MUST document the results schema versions it supports.

**REQ-REL-004.** An unsupported schema version MUST be rejected clearly rather than interpreted approximately.

**REQ-REL-005.** The project MUST publish migration and compatibility rules before changing either schema. It MUST provide a migration path or documented transition period for any incompatible change.

## 14. Acceptance-test catalogue

This catalogue summarises minimum executable scenarios for the first release. It verifies, but does not independently define, the normative behaviour above. Every scenario lists the requirements it verifies.

### 14.1 Input and contract scenarios

- **AT-CON-001:** Identical typed datasets satisfy their contract.
  - Verifies: `REQ-VAL-003`, `REQ-VAL-004`, `REQ-CMP-006`, `REQ-RUN-002`
- **AT-CON-002:** Required missing fields produce side-specific contract findings in both directions and across heterogeneous records; optional missing fields do not. Dataset-wide field discovery uses tabular headers and the union of JSON record members. `fields.in_scope` is required, non-empty, unique, and contains only defined canonical fields; list order does not affect behaviour. Defined fields omitted from it and observed source fields not represented by a definition produce the two exact exclusion forms, never findings or value opportunities. Undeclared exclusions are consolidated by side and source field with accurate record counts. Every declared field supplies non-empty `source_fields.reference` and `source_fields.query` names, including when the field is optional on either side; the `required` flags govern record-level presence rather than whether a correspondence is declared.
  - Verifies: `REQ-CFG-030`, `REQ-CFG-031`, `REQ-CFG-037`, `REQ-CFG-038`, `REQ-CFG-039`, `REQ-CFG-116`, `REQ-CFG-117`, `REQ-CFG-118`, `REQ-CFG-119`, `REQ-CFG-120`, `REQ-CFG-121`, `REQ-CMP-006`, `REQ-CMP-007`, `REQ-CMP-034`, `REQ-CMP-035`, `REQ-CMP-036`, `REQ-FND-010`, `REQ-VAL-002`, `REQ-CFG-035`, `REQ-CFG-036`, `REQ-OUT-041`
- **AT-CON-004:** Null, empty string, whitespace-only string, absent field, and configured non-null missing tokens remain distinct according to policy. Parser-native null and recognised missing tokens bypass mapping and typed parsing; mapping to null applies the null policy and bypasses typed parsing; and null is rejected as a missing token or mapping source.
  - Verifies: `REQ-CFG-053`, `REQ-CFG-054`, `REQ-CFG-055`, `REQ-CFG-056`, `REQ-CFG-057`, `REQ-CFG-122`, `REQ-VAL-014`, `REQ-VAL-047`, `REQ-VAL-048`, `REQ-VAL-049`, `REQ-VAL-050`, `REQ-VAL-051`, `REQ-VAL-052`, `REQ-VAL-053`, `REQ-VAL-054`, `REQ-VAL-055`, `REQ-VAL-086`, `REQ-INP-028`
- **AT-CON-005:** Unknown, conflicting, and incomplete value mappings fail clearly; mapping to null differs from a missing map entry, and mapping from null is rejected. This consolidated parameterized scenario also covers: Source-value descriptors distinguish strings, numbers, booleans, and null in their permitted positions; mapping to null remains distinct from an absent mapping entry. Parameterized mapping fixtures verify reference/query-to-canonical field mapping, required-field reporting, exclusion of unknown source fields, declared source and destination types, permitted intentional many-to-one value mappings, and rejection of reused source column names or any other non-one-to-one column mapping within either dataset side.
  - Verifies: `REQ-CFG-065`, `REQ-CFG-071`, `REQ-CFG-072`, `REQ-CFG-073`, `REQ-CFG-074`, `REQ-CFG-127`, `REQ-VAL-058`, `REQ-VAL-065`, `REQ-VAL-067`, `REQ-CFG-058`, `REQ-CFG-059`, `REQ-VAL-068`, `REQ-VAL-056`, `REQ-VAL-057`, `REQ-VAL-059`, `REQ-VAL-060`, `REQ-VAL-064`, `REQ-VAL-066`
- **AT-CON-006:** Malformed syntax or structure, non-array JSON roots (including a single record object), JSON arrays containing non-object items, duplicate JSON member names at any depth, empty or duplicate tabular column names, and irregular tabular rows receive their specified error classification without silent data loss. This consolidated parameterized scenario also covers: A table-driven parser suite verifies the fixed CSV and TSV dialects, UTF-8-only decoding, CRLF/LF equivalence, quoted delimiters, doubled quotes, embedded line breaks, retention of one-based data-record and starting physical line numbers, and initial string preservation.
  - Verifies: `REQ-INP-021`, `REQ-INP-022`, `REQ-INP-023`, `REQ-INP-024`, `REQ-INP-025`, `REQ-INP-034`, `REQ-INP-035`, `REQ-INP-036`, `REQ-INP-037`, `REQ-INP-038`, `REQ-INP-070`, `REQ-CMP-028`, `REQ-CMP-029`, `REQ-PRN-002`, `REQ-PRN-008`, `REQ-INP-010`, `REQ-INP-011`, `REQ-INP-012`, `REQ-INP-014`, `REQ-INP-015`, `REQ-INP-016`, `REQ-INP-017`, `REQ-INP-018`, `REQ-INP-019`, `REQ-INP-020`, `REQ-INP-026`, `REQ-INP-027`, `REQ-INP-063`, `REQ-INP-064`
- **AT-CON-007:** JSON `[]` and header-only CSV/TSV are valid zero-record datasets, while zero-byte inputs receive their format-specific input errors. With a custom configuration, two valid zero-record datasets have complete records and values phases with no record differences or value opportunities. In automatic mode, two header-only tabular datasets containing `record_id` behave likewise, while two empty JSON arrays produce `input.invalid_record_key` because they expose no selectable key. Per-record requirements produce neither findings nor not-assessable classifications; available tabular header structure still produces applicable dataset-level contract findings. A one-sided zero-record comparison reports every record as missing or extra when a valid key is available and otherwise receives the specified automatic-key error.
  - Verifies: `REQ-INP-052`, `REQ-INP-053`, `REQ-INP-054`, `REQ-INP-055`, `REQ-INP-056`, `REQ-INP-057`, `REQ-INP-058`, `REQ-INP-059`, `REQ-INP-066`, `REQ-INP-067`, `REQ-INP-068`, `REQ-INP-069`, `REQ-INP-071`, `REQ-CMP-009`, `REQ-CMP-010`, `REQ-FND-022`
- **AT-CON-008:** Comparison-configuration YAML scalar resolution and cross-format typed dataset parsing are deterministic across supported environments.
  - Verifies: `REQ-CFG-006`, `REQ-INP-039`, `REQ-INP-040`, `REQ-INP-041`, `REQ-INP-042`, `REQ-INP-043`, `REQ-INP-044`, `REQ-DEP-013`
- **AT-CON-011:** A complete custom YAML configuration conforming to Section 6.2 validates; omitted optional processing properties, collection representations, and dataset sides expand to their specified default or empty internal structures, while explicitly empty placeholder lists or mappings are rejected.
  - Verifies: `REQ-CFG-003`, `REQ-CFG-005`, `REQ-CFG-014`, `REQ-CFG-060`, `REQ-CFG-061`, `REQ-CFG-062`, `REQ-CFG-063`, `REQ-CFG-069`, `REQ-CFG-070`, `REQ-CFG-075`, `REQ-CFG-076`, `REQ-CFG-137`, `REQ-CFG-138`, `REQ-CFG-139`, `REQ-CFG-140`, `REQ-CFG-141`, `REQ-CFG-143`
- **AT-CON-012:** Duplicate or unknown YAML keys, unsafe YAML features, unsupported schema versions, invalid enumerations, incompatible type/comparator combinations, and collection fields using field-level processing properties are rejected with precise configuration paths. This consolidated parameterized scenario also covers: Safe-loader tests confirm that configuration parsing cannot construct arbitrary objects or execute tagged payloads.
  - Verifies: `REQ-CFG-007`, `REQ-CFG-008`, `REQ-CFG-009`, `REQ-CFG-010`, `REQ-CFG-013`, `REQ-CFG-017`, `REQ-CFG-048`, `REQ-CFG-051`, `REQ-CFG-052`, `REQ-CFG-065`, `REQ-CFG-078`, `REQ-CFG-079`, `REQ-CFG-080`, `REQ-CFG-085`, `REQ-CFG-091`, `REQ-CFG-145`, `REQ-SEC-012`
- **AT-CON-014:** Each authoritative schema has its specified canonical `$id`, is present in the source tree and built distribution, can be loaded through the installed package-resource API, and validates every complete configuration example and controlled configuration fixture. This consolidated parameterized scenario also covers: The packaged results schema resolves its configuration-schema reference, accepts representative complete and incomplete canonical results, rejects unknown properties and execution-error diagnostics, requires exactly the documented top-level result properties, and enforces the exact permitted shape of every finding form.
  - Verifies: `REQ-CFG-128`, `REQ-OUT-004`, `REQ-OUT-005`, `REQ-OUT-100`, `REQ-OUT-112`
  - Verifies: `REQ-CFG-016`, `REQ-CFG-087`, `REQ-CFG-088`, `REQ-OUT-004`, `REQ-OUT-005`, `REQ-OUT-006`, `REQ-OUT-007`, `REQ-OUT-050`, `REQ-OUT-051`, `REQ-OUT-052`, `REQ-OUT-053`, `REQ-OUT-054`, `REQ-OUT-055`, `REQ-OUT-056`, `REQ-OUT-057`, `REQ-OUT-058`, `REQ-OUT-059`, `REQ-OUT-060`, `REQ-OUT-100`
- **AT-CON-015:** Configurations that are structurally schema-valid but violate a semantic rule in Section 6.2.9, including an in-scope or key name absent from the appropriate list or definitions, reuse of a source field name within one dataset side, invalid collection-representation placement or element mappings, and use of the reserved automatic-mode identifier by a custom configuration, are rejected with the relevant configuration path and rule.
  - Verifies: `REQ-CFG-090`, `REQ-CFG-091`, `REQ-CFG-104`, `REQ-CFG-105`, `REQ-CFG-106`, `REQ-CFG-107`, `REQ-CFG-108`, `REQ-CFG-127`, `REQ-CFG-129`, `REQ-CFG-136`, `REQ-CFG-144`
- **AT-CON-016:** `review_priority` accepts only `low`, `normal`, or `high`; omission resolves to `normal` in the effective configuration.
  - Verifies: `REQ-CFG-040`
- **AT-CON-017:** `fields.record_key` is required, non-empty, ordered, and free of duplicate component fields; every entry names a field in `fields.definitions` that satisfies all key-field constraints.
  - Verifies: `REQ-CFG-024`, `REQ-CFG-025`, `REQ-CFG-026`, `REQ-CFG-027`, `REQ-CFG-029`, `REQ-CFG-034`, `REQ-CFG-104`, `REQ-CFG-105`
- **AT-CON-018:** `metadata.id` and `metadata.revision` are required non-empty strings; title and description are optional, and metadata does not alter comparison behaviour.
  - Verifies: `REQ-CFG-018`, `REQ-CFG-020`, `REQ-CFG-022`
- **AT-CON-021:** A table-driven JSON parser suite verifies the record-oriented root structure, preserved string-like tokens and numerical lexical forms, and rejection of unquoted `NaN`, `Infinity`, and `-Infinity` as malformed JSON in every location. Results-schema fixtures accept only valid JSON integer lexical forms for `integer` source evidence and valid JSON numerical forms containing a fraction or exponent for `decimal` source evidence. Quoted non-finite representations remain strings; when explicitly parsed as decimals they produce an `invalid_field_value` and not-assessable opportunity in an attributable non-key field, but an execution error in a record-key field.
  - Verifies: `REQ-INP-029`, `REQ-INP-030`, `REQ-INP-033`, `REQ-INP-047`, `REQ-INP-048`, `REQ-INP-049`, `REQ-INP-050`, `REQ-INP-051`, `REQ-INP-065`
- **AT-CON-022:** Every comparison resolves one effective configuration whose schema version, identifier, revision, record key, in-scope fields, field definitions, and comparison rules are validated and embedded in results. A supplied custom configuration is validated before either dataset is read; an automatically generated configuration is constructed after input parsing and field discovery but validated before comparison begins. Unknown custom keys fail with actionable locations.
  - Verifies: `REQ-CFG-001`, `REQ-CFG-002`, `REQ-CFG-012`, `REQ-CFG-086`, `REQ-CFG-095`, `REQ-CFG-096`, `REQ-CFG-097`, `REQ-CFG-098`, `REQ-CFG-099`, `REQ-CFG-100`, `REQ-CFG-101`, `REQ-CFG-102`, `REQ-CFG-103`
- **AT-CON-023:** Parameterized configuration fixtures verify canonical field-name mapping, collection logical-type structure, the bidirectional relationship between omission of `logical_type` and `preserved_exact`, rejection of every processing property on a `preserved_exact` field, legal omission of operation parameters, placement and side-specific application of source and typed normalisation, and the required comparator declaration. They use the public names `source_fields`, `null_policy`, and `logical_type.collection_type`.
  - Verifies: `REQ-CFG-028`, `REQ-CFG-032`, `REQ-CFG-033`, `REQ-CFG-049`, `REQ-CFG-050`, `REQ-CFG-064`, `REQ-CFG-066`, `REQ-CFG-067`, `REQ-CFG-077`
- **AT-CON-024:** Automatic strict-exact fixtures verify exact dataset-wide field discovery and deterministic generation of a schema-valid embedded effective configuration. `record_id` is preferred when present on both sides and, if invalid, produces `input.invalid_record_key` without fallback. Without a shared `record_id`, exactly one common, complete, non-null, unique string field with at least one shared value is selected; zero candidates and multiple candidates produce actionable key errors, the latter listing candidate field names but no values. Tests reject numeric, null, missing, duplicate, heuristic, positional, ranked, and composite automatic keys. Every same-name non-key field is compared with `preserved_exact`; one-sided fields are exclusions; and no mapping, normalisation, coercion, tolerance, or type inference occurs. The HTML report presents the required automatic-mode warning.
  - Verifies: `REQ-PRN-001`, `REQ-CFG-092`, `REQ-CFG-093`, `REQ-CFG-094`, `REQ-CFG-109`, `REQ-CFG-110`, `REQ-CFG-111`, `REQ-CFG-112`, `REQ-CFG-113`, `REQ-CFG-114`, `REQ-CFG-115`, `REQ-CFG-130`, `REQ-CFG-131`, `REQ-CFG-132`, `REQ-CFG-133`, `REQ-CFG-134`, `REQ-CFG-135`, `REQ-CFG-136`, `REQ-REC-006`, `REQ-REC-007`, `REQ-REC-008`, `REQ-REC-010`

### 14.2 Record scenarios

- **AT-REC-001:** Every reference-only record is reported as missing and every query-only record as extra, including when both occur together.
  - Verifies: `REQ-INP-058`, `REQ-INP-059`, `REQ-CMP-011`, `REQ-CMP-012`, `REQ-FND-008`, `REQ-FND-009`, `REQ-PRN-003`
- **AT-REC-002:** Duplicate single and composite keys produce execution errors without overwriting data; each error identifies the affected dataset, duplicate normalised key, and available source-record locations.
  - Verifies: `REQ-REC-003`, `REQ-REC-009`, `REQ-REC-010`, `REQ-REC-011`, `REQ-REC-012`, `REQ-REC-013`, `REQ-REC-014`
- **AT-REC-003:** Composite keys preserve multiple legitimate records belonging to one sample.
  - Verifies: `REQ-REC-001`, `REQ-REC-002`, `REQ-CFG-024`
- **AT-REC-005:** Parameterized key fixtures verify that custom key names, aliases, composites, and normalisation are configuration-defined; the sole automatic-key exception follows Section 6.9; key values are not implicitly converted; no command-line key override exists; and findings retain enough source identity to distinguish records.
  - Verifies: `REQ-REC-004`, `REQ-REC-005`, `REQ-REC-006`, `REQ-REC-007`, `REQ-REC-008`, `REQ-REC-015`

### 14.3 Typed value and comparator scenarios

- **AT-VAL-001:** Boolean `true`, integer `1`, decimal `1.0`, and textual `"1"` remain distinct under the applicable exact comparator. A parameterized source-category matrix verifies every directly accepted category, exact integer-to-decimal widening, rejection of implicit narrowing and stringification, rejection of parser-native objects for typed fields, explicit mapping for representations outside the matrix, null handling before typed parsing, and element-wise application to collections. The suite also verifies declared parsing rather than inference and enumerates the stable comparator registry.
  - Verifies: `REQ-VAL-009`, `REQ-VAL-027`, `REQ-CMP-017`, `REQ-VAL-001`, `REQ-VAL-005`, `REQ-VAL-007`, `REQ-VAL-008`, `REQ-VAL-076`, `REQ-VAL-077`, `REQ-VAL-078`, `REQ-VAL-079`, `REQ-VAL-080`, `REQ-VAL-081`, `REQ-VAL-082`, `REQ-VAL-083`, `REQ-VAL-084`, `REQ-VAL-085`, `REQ-CMP-015`
- **AT-VAL-002:** Typed strings remain code-point-exact unless configured normalisations are applied in declared order.
  - Verifies: `REQ-INP-013`, `REQ-VAL-012`, `REQ-VAL-013`, `REQ-VAL-070`, `REQ-CMP-016`
- **AT-VAL-003:** Integer parsing accepts signed ASCII decimal integers and leading zeros but rejects decimal points, exponents, booleans, and invalid text. This consolidated parameterized scenario also covers: Leading-zero identifiers remain strings unless explicitly transformed.
  - Verifies: `REQ-VAL-015`, `REQ-VAL-016`, `REQ-VAL-017`, `REQ-VAL-018`
- **AT-VAL-004:** Decimal parsing is exact; accepts parser-native integers and decimals and textual forms such as `+1.2`, `01.2`, `1`, and `1E+2`; rejects `.5`, `1.`, `NaN`, and infinities; and never passes through binary floating-point. Invalid attributable non-key decimals are also checked as contract findings that become `not_assessable`, not execution errors.
  - Verifies: `REQ-INP-031`, `REQ-INP-032`, `REQ-INP-045`, `REQ-INP-046`, `REQ-VAL-019`, `REQ-VAL-020`, `REQ-VAL-021`, `REQ-VAL-022`, `REQ-VAL-023`, `REQ-VAL-078`, `REQ-VAL-011`
- **AT-VAL-005:** Boolean parsing accepts native booleans and lowercase textual `true` or `false`; other representations require a mapping.
  - Verifies: `REQ-VAL-024`, `REQ-VAL-025`, `REQ-VAL-026`, `REQ-VAL-027`
- **AT-VAL-006:** Dates reject invalid or non-ISO full dates; datetimes require offsets and compare as instants.
  - Verifies: `REQ-VAL-028`, `REQ-VAL-029`, `REQ-VAL-030`, `REQ-VAL-031`, `REQ-VAL-032`, `REQ-VAL-033`, `REQ-VAL-034`, `REQ-VAL-035`, `REQ-VAL-036`, `REQ-CMP-024`
- **AT-VAL-007:** Lists preserve order and duplicates, sets reject typed-canonical duplicates and ignore order, and multisets ignore order while preserving occurrence counts. List elements support positional typed-exact comparison and numeric tolerance for numeric element types; sets and multisets accept only typed-exact element comparison, and every other element-comparator combination is rejected. This consolidated parameterized scenario also covers: the default and explicit `json_array` representations accept JSON arrays in JSON and JSON-array cell syntax in CSV/TSV; ordinary delimited text is rejected unless `delimited_text` is explicitly configured for that side; literal single- and multi-character delimiters, empty input, empty elements, lack of collection-level escaping, element normalisation, closed element mapping, and element typed parsing follow the defined order; and null collection elements produce the specified finding and `not_assessable` evidence. The suite covers every supported typed collection kind and its required element declaration.
  - Verifies: `REQ-CFG-124`, `REQ-CFG-125`, `REQ-CFG-126`, `REQ-CFG-137`, `REQ-CFG-138`, `REQ-CFG-139`, `REQ-CFG-140`, `REQ-CFG-141`, `REQ-CFG-142`, `REQ-VAL-037`, `REQ-VAL-038`, `REQ-VAL-039`, `REQ-VAL-040`, `REQ-VAL-041`, `REQ-VAL-042`, `REQ-CMP-025`, `REQ-CMP-040`, `REQ-CMP-041`, `REQ-VAL-043`, `REQ-VAL-044`, `REQ-VAL-045`, `REQ-VAL-046`, `REQ-VAL-006`, `REQ-VAL-081`, `REQ-VAL-082`, `REQ-VAL-087`, `REQ-VAL-088`, `REQ-VAL-089`, `REQ-VAL-090`, `REQ-VAL-091`
- **AT-VAL-008:** Typed transformations follow Section 6.8 and retain evidence of the attributable source value. This consolidated parameterized scenario also covers: Parameterized normalisation fixtures exercise every registered source-text and typed-value operation, verify that source-text operations affect strings but pass non-strings through unchanged, and cover Unicode normalization, whitespace trimming, case folding, decimal quantisation, and datetime truncation. Rounding or precision reduction occurs only when explicitly configured. Deterministic set and multiset output ordering is verified as canonical serialization rather than configured normalisation. The suite also verifies retention of source lexical evidence.
  - Verifies: `REQ-CFG-123`, `REQ-VAL-061`, `REQ-VAL-062`, `REQ-VAL-063`, `REQ-VAL-069`, `REQ-VAL-070`, `REQ-VAL-072`, `REQ-VAL-073`, `REQ-VAL-074`, `REQ-VAL-075`, `REQ-VAL-071`, `REQ-CMP-023`, `REQ-VAL-010`
- **AT-VAL-009:** Numeric tolerance accepts exactly one absolute or relative tolerance and rejects configurations containing neither or both. Each form uses exact decimal arithmetic and an inclusive boundary, with below, at, and above boundary cases; relative tolerance is reference-directed and permits no non-zero difference when the reference is zero.
  - Verifies: `REQ-CFG-081`, `REQ-CFG-082`, `REQ-CFG-083`, `REQ-CFG-084`, `REQ-CMP-018`, `REQ-CMP-019`, `REQ-CMP-020`, `REQ-CMP-021`, `REQ-CMP-022`
- **AT-VAL-010:** All assessable differences are collected in one run.
  - Verifies: `REQ-CMP-026`, `REQ-CMP-027`
- **AT-VAL-011:** Every field listed in `fields.in_scope` is assessed; defined fields omitted from that list and observed source fields not represented by a definition are `not_assessed` and represented by the required exclusion summaries.
  - Verifies: `REQ-CFG-039`, `REQ-CMP-004`, `REQ-CMP-013`, `REQ-CMP-031`, `REQ-OUT-041`

### 14.4 Phase and run-status scenarios

- **AT-OUT-001:** Every comparison performs the contract, records, and values phases in order and records a completion status for each. Overall status is complete if and only if all three phase statuses are complete.
  - Verifies: `REQ-CMP-001`, `REQ-RUN-012`, `REQ-RUN-023`, `REQ-OUT-013`, `REQ-OUT-014`
- **AT-OUT-002:** A finding or `not_assessable` item in an earlier phase does not prevent later assessment where prerequisites remain satisfied.
  - Verifies: `REQ-CMP-002`, `REQ-CMP-003`, `REQ-RUN-007`
- **AT-OUT-005:** Complete, incomplete, invocation or input error, and unexpected internal error produce their documented exit behaviour. This consolidated parameterized scenario also covers: Fully performed contract and record phases remain complete despite their findings, and a fully performed comparison is `complete` whether it finds no differences or any combination of contract findings, missing records, extra records, and value mismatches.
  - Verifies: `REQ-RUN-001`, `REQ-RUN-015`, `REQ-RUN-016`, `REQ-RUN-017`, `REQ-RUN-018`, `REQ-RUN-019`, `REQ-RUN-021`, `REQ-CLI-014`, `REQ-CLI-015`, `REQ-CLI-016`, `REQ-RUN-002`
- **AT-OUT-006:** A not-assessable value opportunity makes the values phase and run incomplete while leaving a fully performed contract phase complete; deliberately `not_assessed` content does not make any phase incomplete. This consolidated parameterized scenario also covers: Content excluded deliberately is `not_assessed`; configured content blocked by a failed prerequisite is `not_assessable`.
  - Verifies: `REQ-RUN-003`, `REQ-RUN-004`, `REQ-RUN-005`, `REQ-RUN-016`, `REQ-RUN-018`, `REQ-RUN-020`, `REQ-RUN-021`, `REQ-RUN-022`, `REQ-CMP-004`
- **AT-OUT-007:** Invalid configuration, malformed or unreadable input, an incomplete or ambiguous record model, an enforced resource limit, and resource exhaustion produce `error`, never `incomplete` or a partial comparison result.
  - Verifies: `REQ-RUN-017`, `REQ-RUN-010`, `REQ-RUN-011`, `REQ-DEP-011`
- **AT-OUT-008:** An end-to-end mixed-defect comparison exercises every conceptual processing step, including invalid contract values, deliberate exclusions, failed prerequisites, mandatory key processing, and continued comparison of unaffected values. This consolidated parameterized scenario also covers: A large mixed-content fixture verifies that every configured value opportunity is either assessed or explicitly classified and that no valid accepted content is silently skipped.
  - Verifies: `REQ-CMP-005`, `REQ-CMP-008`, `REQ-CMP-014`, `REQ-CMP-030`, `REQ-CMP-037`, `REQ-CMP-038`, `REQ-CMP-039`, `REQ-RUN-006`, `REQ-DEP-010`
- **AT-OUT-010:** A table-driven finding suite generates every finding code and verifies its fixed classification, structured fields, required contextual evidence, deterministic local ID, human-readable message, summary-only successful matches, and absence of message-only semantics. `missing_record`, `extra_record`, and `value_mismatch` are always `comparison_difference`; every other finding code is always `assessment_issue`; and phase remains independently correct. This consolidated parameterized scenario also covers: For every finding code, result fixtures enforce the code-specific inclusion and omission of source and canonical values, deterministic messages derived from structured data, classification-first total finding order, duplicate coalescence, and sequential post-sort report-local IDs. Category incompatibility, invalid content within an accepted category, and comparison of two valid unequal values produce mutually exclusive `type_mismatch`, `invalid_field_value`, and `value_mismatch` findings. Independent reference and query contract violations produce separate side-specific findings, while comparison of two valid unequal values produces one `both` finding. Each not-assessable value opportunity has one applicable causal finding and does not generate a separate `not_assessable` finding.
  - Verifies: `REQ-PRN-006`, `REQ-FND-001`, `REQ-FND-002`, `REQ-FND-003`, `REQ-FND-004`, `REQ-FND-005`, `REQ-FND-006`, `REQ-FND-012`, `REQ-FND-013`, `REQ-FND-014`, `REQ-FND-015`, `REQ-FND-016`, `REQ-FND-017`, `REQ-FND-018`, `REQ-FND-019`, `REQ-FND-020`, `REQ-FND-023`, `REQ-FND-024`, `REQ-FND-025`, `REQ-OUT-032`, `REQ-OUT-033`, `REQ-OUT-034`, `REQ-OUT-035`, `REQ-OUT-099`, `REQ-OUT-061`, `REQ-OUT-062`, `REQ-OUT-064`, `REQ-OUT-065`, `REQ-OUT-066`, `REQ-OUT-067`, `REQ-OUT-068`

### 14.5 Evidence, CLI, and packaging scenarios

- **AT-EVD-001:** Runs with identical exact bytes, basenames, configuration, toolkit version, and runtime identity produce byte-identical canonical JSON after normalizing only run ID and completion time. Serialization fixtures verify UTF-8 without a byte-order mark, two-space indentation, LF line endings, exactly one final newline, direct non-ASCII output, fixed-schema member order, and Unicode code-point order for dynamic members. Parameterized record-order and LF/CRLF variants preserve the defined comparison outcome while permitting only the documented byte-provenance, source-location, location-dependent message, and report-local ID differences. The comparison outcome also remains invariant across every supported Python and operating-system environment, including Unicode-sensitive fixtures.
  - Verifies: `REQ-PRN-005`, `REQ-INP-014`, `REQ-CMP-033`, `REQ-OUT-012`, `REQ-OUT-095`, `REQ-OUT-096`, `REQ-OUT-097`, `REQ-OUT-098`, `REQ-OUT-125`, `REQ-DEP-013`, `REQ-CMP-032`
- **AT-EVD-002:** Results contain exact-byte SHA-256 input digests and input basenames without exposing absolute paths, raw command lines, environment variables, or secrets; the complete validated comparison configuration is embedded without a separate configuration digest.
  - Verifies: `REQ-CFG-023`, `REQ-OUT-017`, `REQ-OUT-018`, `REQ-OUT-019`, `REQ-OUT-022`, `REQ-OUT-023`, `REQ-SEC-007`, `REQ-SEC-008`
- **AT-EVD-004:** An output failure or interrupted write cannot leave an evidence package that appears complete. This consolidated parameterized scenario also covers: Success and injected-failure runs verify that temporary files are no more accessible than the destination and are removed after success and, where safe, after errors; a failed attempted replacement preserves the existing evidence package byte for byte.
  - Verifies: `REQ-OUT-044`, `REQ-OUT-045`, `REQ-OUT-049`, `REQ-OUT-116`, `REQ-DEP-012`, `REQ-SEC-009`, `REQ-SEC-010`, `REQ-SEC-011`
- **AT-EVD-005:** Every complete comparison exits with code 0 and produces its evidence package, including when differences are reported.
  - Verifies: `REQ-PRN-004`, `REQ-RUN-002`, `REQ-OUT-001`, `REQ-OUT-002`, `REQ-CLI-016`
- **AT-EVD-008:** A complete or incomplete run creates the documented two-file evidence package containing `comparison-results.json` and `comparison-report.html`, with no separate manifest or additional report or findings-export format. It refuses every existing destination by default. With `--overwrite`, it replaces a complete two-file v1 evidence-package directory but rejects regular files, symbolic links, special filesystem objects, empty directories, partial packages, and directories with additional entries. This consolidated parameterized scenario also covers: Output-directory reporting and filename handling preserve the exact selected destination and manipulate suffixes structurally rather than by character stripping.
  - Verifies: `REQ-OUT-001`, `REQ-OUT-002`, `REQ-OUT-044`, `REQ-OUT-045`, `REQ-OUT-046`, `REQ-OUT-047`, `REQ-OUT-048`, `REQ-OUT-115`, `REQ-CLI-011`, `REQ-CLI-012`
- **AT-EVD-009:** A parameterized suite produces every version 1 invocation, configuration, input, resource, output, and internal execution-error code. Each case writes the exact `ERROR [<category>.<code>]: <message>` first-line form and only permitted non-sensitive continuation context, returns exit code 2 except for `internal.unexpected`, which returns 3, and publishes no evidence-package directory or filesystem report. Diagnostics contain no findings, finding codes, comparison summary metrics, phase statuses, record identifiers, source values, or ordinary-use traceback. Representative failures at each classification boundary verify that the most specific applicable code is selected.
  - Verifies: `REQ-FND-007`, `REQ-RUN-008`, `REQ-RUN-009`, `REQ-RUN-010`, `REQ-RUN-011`, `REQ-RUN-024`, `REQ-RUN-025`, `REQ-RUN-026`, `REQ-OUT-008`, `REQ-DEP-014`
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
- **AT-EVD-015:** Canonical results contain valid run, phase, software, runtime, and fixed-dialect metadata; run IDs are canonical lowercase UUIDv4 values; completion timestamps are UTC RFC 3339 values using `Z` and whole-second precision; Python implementation/version, normalized platform, and Unicode database version use their prescribed forms without identifying host details; start time and duration are absent; and overall status reconciles with phase statuses.
  - Verifies: `REQ-OUT-009`, `REQ-OUT-010`, `REQ-OUT-011`, `REQ-OUT-014`, `REQ-OUT-015`, `REQ-OUT-016`, `REQ-OUT-020`, `REQ-OUT-121`, `REQ-OUT-122`, `REQ-OUT-123`, `REQ-OUT-124`
- **AT-EVD-016:** Parameterized single and composite record identities verify ordered source and canonical key arrays, null identities for an absent side, presence-state distinctions, recursive parser-native typed values, unique canonical rendering of every scalar type, UTC datetime rendering, canonical key-component rendering, deterministic set and multiset element order, and deterministic object-member ordering. Source-location fixtures verify tabular data-record and starting-line numbers across multiline records, field-name inclusion only for present fields, record-level locations for absent fields, JSON record and field pointers, RFC 6901 escaping, and null locations for absent records.
  - Verifies: `REQ-OUT-021`, `REQ-OUT-026`, `REQ-OUT-027`, `REQ-OUT-028`, `REQ-OUT-029`, `REQ-OUT-089`, `REQ-OUT-090`, `REQ-OUT-091`, `REQ-OUT-092`, `REQ-OUT-093`, `REQ-OUT-094`, `REQ-OUT-117`, `REQ-OUT-118`, `REQ-OUT-119`
- **AT-EVD-018:** Parameterized result fixtures verify fixed-shape zero-inclusive summaries, record-count reconciliation, finding totals by classification, code, and priority, and exactly one matched, mismatched, or not-assessable classification for every in-scope non-key value opportunity, including optional, required, invalid, and prohibited values. Semantic checks also verify that configured-field exclusions agree with `fields.in_scope` and that undeclared-field exclusions agree with observed source fields and record counts.
  - Verifies: `REQ-OUT-037`, `REQ-OUT-038`, `REQ-OUT-039`, `REQ-OUT-040`, `REQ-OUT-069`, `REQ-OUT-070`, `REQ-OUT-071`, `REQ-OUT-072`, `REQ-OUT-073`, `REQ-OUT-101`, `REQ-OUT-102`, `REQ-OUT-103`, `REQ-OUT-104`, `REQ-OUT-105`, `REQ-OUT-106`, `REQ-OUT-107`, `REQ-OUT-108`
- **AT-EVD-022:** Before publication, representative generated results pass both structural and semantic self-validation with Draft 2020-12 format assertion enabled. Injected schema and semantic inconsistencies, including malformed UUIDs, dates, and date-times, produce an unexpected internal error and publish no canonical result, HTML report, or evidence-package directory.
  - Verifies: `REQ-OUT-109`, `REQ-OUT-110`, `REQ-OUT-114`
- **AT-EVD-019:** HTML generated solely from canonical JSON uses an open non-proprietary format and presents the run purpose, phase and run statuses, input and configuration identities, counts, findings, discrepancies, limitations, exclusions, unassessed content, provenance, and no acceptance verdict; HTML is never the sole canonical evidence format. Its headline distinguishes run completeness, comparison-difference count, and assessment-issue count. Detailed findings are organized primarily by classification with comparison differences first and phase retained as secondary traceability information. This consolidated parameterized scenario also covers: Complete and incomplete reports contain raw findings and metrics but no acceptance threshold, pass/fail verdict, or equivalent inferred laboratory decision.
  - Verifies: `REQ-PRN-009`, `REQ-OUT-042`, `REQ-OUT-074`, `REQ-OUT-075`, `REQ-OUT-076`, `REQ-OUT-077`, `REQ-OUT-078`, `REQ-OUT-079`, `REQ-OUT-080`, `REQ-OUT-081`, `REQ-OUT-120`, `REQ-OUT-126`, `REQ-OUT-127`, `REQ-OUT-128`, `REQ-DEP-004`, `REQ-DEP-005`, `REQ-RUN-013`
- **AT-EVD-021:** Installed-CLI tests cover the required `adviso-validation compare` form, required reference, query, and output arguments, optional configuration, enumerated choices, invalid combinations before input access, normal summaries on standard output, and optional progress that never contaminates machine-readable output. This consolidated parameterized scenario also covers: Omitting `--configuration` selects automatic strict-exact mode and records its generated effective configuration; a supplied value is treated only as a custom comparison-configuration path. The reference and query formats are independently determined and recorded from recognised, case-insensitive filename extensions; a missing, unknown, or ambiguous extension causes an input error, and content that does not conform to the indicated format is rejected. Command-line `--help` describes every version 1 command and option and directs users to the full guide.
  - Verifies: `REQ-PRD-002`, `REQ-INP-001`, `REQ-INP-002`, `REQ-INP-004`, `REQ-INP-060`, `REQ-INP-061`, `REQ-INP-062`, `REQ-CLI-001`, `REQ-CLI-002`, `REQ-CLI-003`, `REQ-CLI-006`, `REQ-CLI-007`, `REQ-CLI-008`, `REQ-INP-003`, `REQ-CFG-092`, `REQ-CLI-009`, `REQ-CLI-010`, `REQ-INP-005`, `REQ-INP-006`, `REQ-INP-007`, `REQ-INP-008`, `REQ-INP-009`, `REQ-CLI-013`, `REQ-CLI-004`, `REQ-DOC-005`

### 14.6 Documentation scenarios

- **AT-DOC-001:** The built distribution contains an offline user guide covering every topic required by Section 13.4, and the guide identifies the toolkit and schema versions to which it applies. This consolidated parameterized scenario also covers: Every complete comparison-configuration and canonical-results example in the guide validates against its corresponding packaged schema, and every documented command-line invocation uses the version 1 interface.
  - Verifies: `REQ-DOC-001`, `REQ-DOC-006`, `REQ-DOC-007`, `REQ-DOC-008`, `REQ-DOC-009`, `REQ-DOC-010`, `REQ-DOC-011`, `REQ-DOC-012`, `REQ-DOC-013`, `REQ-DOC-014`, `REQ-DOC-015`, `REQ-DOC-016`, `REQ-DOC-002`, `REQ-DOC-003`, `REQ-DOC-004`, `REQ-OUT-111`

### 14.7 Fixture and compatibility scenarios

- **AT-TRC-002:** Regenerating every generated fixture from its recorded source or generator produces byte-identical or semantically identical controlled test data, as applicable.
  - Verifies: `REQ-TST-005`
- **AT-TRC-003:** Every supported and unsupported comparison-configuration and results-schema version is exercised to confirm exact supported-version handling and clear rejection of unsupported versions. A version 1.0 result accepts only an embedded version 1.0 comparison configuration.
  - Verifies: `REQ-REL-002`, `REQ-REL-004`, `REQ-OUT-113`
