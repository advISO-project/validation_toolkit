# AdvISO Compare version 1 implementation plan

## 1. Purpose

This document divides the version 1 implementation of `adviso-compare` into
reviewable, test-driven increments. Each increment ends in a coherent and
demonstrable result. Work on the next increment starts only after the completed
increment has been reviewed and approved.

The behaviour specification and the two normative schemas remain the sources of
truth. This plan sequences their implementation; it does not add, remove, or
reinterpret product requirements.

The plan covers only `adviso-compare`. Dataset acquisition, dataset subsetting,
pipeline execution, validation-dataset curation, and the proposed
`adviso-datasets` product remain outside its scope. The implementation also does
not add a laboratory acceptance verdict: its output is comparison evidence for
the validation process.

## 2. Delivery method

Each implementation step follows the same cycle:

1. Re-read the relevant specification sections and schemas.
2. Identify the specified behaviours and validation scenarios in scope.
3. Add the smallest coherent set of tests and controlled fixtures for that
   behaviour. Confirm that new behavioural tests fail for the expected reason.
4. Implement only enough production code to satisfy the step.
5. Run the new tests and all previously passing tests.
6. Run the proportionate schema, packaging, static, and documentation checks
   that are already configured for the project.
7. Present the increment for review and approval.

Tests will use descriptive behavioural names and remain understandable without
the development specification. Parameterization will be used for genuine rule
tables, without merging unrelated behaviours merely to reduce the test count.
Fixtures will be synthetic, small, non-sensitive, and deterministically
reproducible.

No implementation difficulty will be resolved by silently changing the
specification or a schema. Any conflict, ambiguity, or impracticable requirement
will stop the affected step and be presented as a decision before implementation
continues.

### Approval packet for every step

The review at the end of each step will include:

- the implemented capability and its architectural boundaries;
- the specified behaviours and validation scenarios addressed;
- tests and fixtures added or changed;
- commands run and their results;
- any schema, packaging, static, or documentation checks performed;
- a focused demonstration using representative inputs;
- known limitations and behaviour intentionally deferred to later steps; and
- any questions or proposed deviations requiring a decision.

Approval means that the increment becomes the baseline for subsequent work. A
review may instead request corrections within the same step; those corrections
are completed and re-presented before the next step begins.

## 3. Implementation sequence

### Step 0 — Establish the verified baseline and test architecture

**Goal:** create a trustworthy starting point without implementing comparison
behaviour.

Work in this step:

- verify that the existing specification and both JSON Schemas can be loaded;
- verify their canonical `$id` values and internal schema references;
- define the test layout, behavioural naming convention, shared fixture builders,
  and deterministic fixture-generation approach;
- add schema-validation helpers that use Draft 2020-12 with format assertion;
- establish tests for loading packaged schemas through the package-resource API;
- build the source distribution and wheel and inspect their contents; and
- record any source/schema conflict as a blocker rather than choosing an
  interpretation.

This step does not create a comparison engine or claim that the executable is
usable.

**Approval demonstration:** the schemas validate themselves and representative
schema fixtures, packaged schema resources can be loaded, and both distribution
formats build reproducibly enough for inspection.

### Step 1 — Define package boundaries, domain vocabulary, and CLI invocation

**Goal:** establish stable outer interfaces before domain behaviour is added.

Work in this step:

- create the intended package/module boundaries for input, configuration,
  translation, comparison, results, reporting, and CLI orchestration;
- define narrowly scoped domain value types and exception categories at those
  boundaries, without speculative framework abstractions;
- implement parsing of the direct `adviso-compare` command form into an
  invocation value object;
- implement required arguments, `--configuration`, `--overwrite`, help, and
  invalid-invocation handling that does not access inputs; and
- keep orchestration injectable so CLI tests need not depend on private kernel
  details.

The executable will not be presented as end-to-end complete in this increment.
The installed entry point and complete diagnostic behaviour are closed in Step
11.

**Approval demonstration:** accepted arguments produce the expected invocation
object, invalid combinations fail before file access, subcommands are rejected,
and help accurately describes the version 1 interface.

### Step 2 — Implement deterministic input discovery and parsing

**Goal:** turn reference and query files into lossless parser-native datasets
with provenance, without yet interpreting configured field types.

Work in this step:

- determine CSV, TSV, and JSON formats independently from filename extensions;
- read exact input bytes, calculate SHA-256 digests, and retain basenames;
- enforce UTF-8 and the fixed tabular dialects;
- parse tabular headers and records while retaining record and physical-line
  locations;
- parse JSON arrays of objects while rejecting duplicate member names,
  non-object records, non-finite numbers, and invalid root structures;
- preserve parser-native categories, exact decimal values, numerical lexical
  evidence, presence state, and JSON Pointer locations;
- distinguish valid empty datasets from invalid zero-byte inputs; and
- implement the applicable input-error taxonomy without logging sensitive
  record content.

**Approval demonstration:** a table-driven parser suite shows accepted edge
cases and precise rejection of malformed inputs across all three formats, with
exact categories and source locations visible through the domain API.

### Step 3 — Load, validate, and resolve custom comparison configurations

**Goal:** convert a custom YAML document into one validated, immutable effective
configuration before either dataset is read.

Work in this step:

- load YAML safely using the required scalar resolution and duplicate-key
  handling;
- validate structure with the packaged configuration schema;
- implement every cross-property semantic validation rule that JSON Schema
  cannot express;
- report precise configuration paths and stable configuration error categories;
- expand only the documented defaults and omitted empty structures;
- validate field definitions, source-field correspondence, in-scope fields,
  record keys, logical types, collection representations, mappings,
  normalisations, comparators, and review priorities; and
- serialize the resolved configuration into its schema-valid embedded form.

**Approval demonstration:** representative valid configurations resolve to the
expected effective model, while a parameterized semantic-error suite produces
precise paths and reasons. A test proves that custom configuration failure
precedes dataset access.

### Step 4 — Implement the source-to-canonical translation pipeline

**Goal:** translate an individual declared field value from either dataset into
canonical typed evidence using the exact configured sequence of operations.

Work in this step:

- implement presence and null-policy handling;
- implement closed value mappings with typed source descriptors;
- implement source-text and typed-value normalisation registries;
- implement declared scalar parsing for string, integer, decimal, boolean,
  date, and datetime values using exact arithmetic where required;
- implement list, set, and multiset source representations, element processing,
  duplicate semantics, and deterministic canonical ordering;
- retain source and canonical evidence needed by later findings; and
- distinguish valid values, invalid attributable values, prohibited nulls, and
  deliberately out-of-scope content without yet deciding whole-run status.

**Approval demonstration:** table-driven unit tests trace representative scalar
and collection values through every configured operation, including failure
states, with no implicit coercion or inference.

### Step 5 — Resolve record identity and automatic strict-exact mode

**Goal:** obtain an unambiguous ordered record key for each dataset in custom and
configuration-free operation.

Work in this step:

- process configured single and composite record keys through the same explicit
  translation rules that apply to their declared fields;
- detect missing, null, invalid, and duplicate keys as execution errors without
  overwriting records;
- generate the automatic strict-exact effective configuration after parsing and
  dataset-wide field discovery;
- apply the specified `record_id` preference and conservative single-field key
  discovery algorithm, including its no-fallback rule;
- generate same-name non-key field definitions without type inference,
  mapping, normalisation, or coercion, while leaving one-sided fields undefined
  so that the contract phase can produce their exclusion summaries; and
- validate the generated configuration before comparison.

**Approval demonstration:** custom aliases and composite keys work; duplicate or
invalid keys fail with attributable locations; and automatic-mode fixtures show
deterministic success, zero-candidate failure, ambiguous-candidate failure, and
the special handling of shared `record_id`.

### Step 6 — Implement the contract phase

**Goal:** assess whether the declared correspondence can be applied to every
record while allowing unaffected content to proceed.

Work in this step:

- discover dataset-wide structure from tabular headers and the union of JSON
  members;
- apply required/optional field rules independently on each side;
- classify invalid, missing, null, prohibited, and type-incompatible configured
  values;
- create side-specific contract findings and causal not-assessable states;
- consolidate defined-but-out-of-scope and undeclared-source-field exclusions;
- attach resolved review priority where applicable; and
- mark the contract phase complete when it was fully performed, even when it
  contains findings.

**Approval demonstration:** a mixed dataset produces all expected contract
findings, exclusions, and blocked opportunities while still exposing unaffected
records and values to later phases.

### Step 7 — Implement the records phase

**Goal:** align records by canonical identity and report the complete set of
reference-only and query-only records.

Work in this step:

- construct collision-safe indexes for ordered single and composite keys;
- match record identities independently of input order;
- emit every missing-record and extra-record difference;
- retain the reference and query source identities required for readable
  evidence; and
- reconcile zero-record, one-sided-empty, and mixed missing/extra cases.

**Approval demonstration:** reordered datasets match identically, composite keys
preserve multiple records for a sample, and simultaneous missing and extra
records are all reported deterministically.

### Step 8 — Implement comparators and the values phase

**Goal:** compare every assessable in-scope non-key value and distinguish true
post-translation differences from assessment issues.

Work in this step:

- implement the fixed comparator registry and legal type/comparator
  combinations;
- implement preserved, typed, normalized-string, numeric, date, datetime, list,
  set, and multiset equality semantics;
- implement absolute or reference-directed relative numeric tolerance with exact
  decimal arithmetic and inclusive boundaries;
- classify every value opportunity as matched, mismatched, not assessable, or
  deliberately not assessed as specified;
- collect all assessable differences rather than stopping at the first; and
- preserve the independence of finding classification, phase, and review
  priority.

**Approval demonstration:** a matrix covering every comparator and its boundary
conditions produces the expected canonical outcomes, and one mixed comparison
accounts for every configured value opportunity.

### Step 9 — Assemble and validate canonical results

**Goal:** construct the complete canonical result document deterministically and
prove that it satisfies both structural and semantic invariants.

Work in this step:

- finalize the finding registry, fixed classifications, structured fields,
  deterministic messages, coalescence, total order, and report-local IDs;
- derive phase completion and overall `complete` or `incomplete` status;
- build fixed-shape, zero-inclusive summaries and exclusion summaries;
- render record identities, values, locations, software/runtime identity,
  dialect metadata, UUID, and completion timestamp in their prescribed forms;
- embed the effective configuration and exact input provenance;
- serialize canonical JSON using the required member order, Unicode handling,
  indentation, line endings, and final newline;
- validate the generated result against the packaged results schema with format
  assertion; and
- implement additional semantic self-validation and treat self-validation
  failure as an internal error.

**Approval demonstration:** representative complete and incomplete documents
validate structurally and semantically, summaries reconcile with findings and
opportunities, and repeated/order-varied runs differ only in the explicitly
permitted runtime and location evidence.

### Step 10 — Produce the evidence package and HTML report

**Goal:** publish a safe, atomic, human-readable two-file evidence package whose
canonical source is the validated JSON result.

Work in this step:

- generate `comparison-report.html` solely from canonical JSON;
- present completeness, comparison differences, assessment issues, phase
  traceability, exclusions, provenance, and sensitive-content warnings without
  an acceptance verdict;
- provide accessible priority presentation that does not rely on colour alone;
- implement exact destination and overwrite rules, including rejection of
  symlinks, special objects, partial packages, and directories with extra
  entries;
- stage and replace output atomically while preserving an existing package after
  failed replacement;
- apply restrictive temporary-file handling and cleanup; and
- keep operation wholly offline and avoid exposing identifiers or values in
  routine terminal output.

**Approval demonstration:** complete and incomplete sample packages contain
exactly the two required files; the HTML can be regenerated from JSON alone; and
fault-injection tests demonstrate safe creation, refusal, overwrite, rollback,
permissions, and cleanup.

### Step 11 — Integrate the installed CLI and execution-error boundary

**Goal:** deliver the complete product path from installed executable to
evidence package, with stable exit and diagnostic behaviour.

Work in this step:

- connect the CLI invocation, parsers, configuration resolution, comparison
  kernel, result construction, and evidence writer;
- implement normal standard-output summaries and optional progress without
  contaminating machine-readable evidence;
- map every expected invocation, configuration, input, resource, and output
  failure to its specified diagnostic and exit code;
- isolate unexpected internal failures, omit ordinary-use tracebacks, and
  publish no partial report for execution errors;
- confirm that comparison findings still produce exit code 0 when assessment is
  complete, and that not-assessable content produces the documented incomplete
  result and exit code;
- build and install the wheel in an isolated environment; and
- run representative custom and automatic comparisons through the installed
  `adviso-compare` executable without network access.

**Approval demonstration:** an installed wheel completes end-to-end successful,
difference-containing, incomplete, and expected-error runs with the precise
files, diagnostics, and exit codes required by the specification.

### Step 12 — Complete user documentation and release-candidate verification

**Goal:** make the implemented version understandable, reproducible, and ready
for a release decision.

Work in this step:

- write the offline user guide covering installation, supported inputs, custom
  and automatic operation, the complete configuration model, canonical result
  fields, HTML interpretation, exit behaviour, security cautions, and worked
  examples;
- validate every complete configuration and result example against its packaged
  schema;
- verify every documented command against the installed interface;
- document deterministic fixture regeneration;
- run the complete behavioural acceptance suite;
- run all configured schema, packaging, static, and documentation checks across
  the supported environments available to the project; and
- produce a final verification report that distinguishes automated,
  inspection-based, process, and release-time evidence.

This step does not silently introduce a formatter, linter, type checker,
dependency manager, CI system, or release policy. Any new project-wide tooling
or policy identified as desirable is proposed separately for approval.

**Approval demonstration:** a fresh user can install the built artefact offline,
follow the packaged guide, run both documented modes, validate the resulting
canonical JSON, interpret the HTML, and reproduce the controlled fixtures. The
final review identifies any requirements that remain dependent on manual or
release-process evidence.

## 4. Recommended review boundaries

The steps are intentionally ordered by dependency. In particular:

- result and report design is not allowed to drive undocumented changes to the
  comparison model;
- automatic mode is built on the same validated effective-configuration model as
  custom mode;
- the HTML report is built from canonical JSON rather than from private engine
  state; and
- installed-product testing follows component integration, but packaging and
  schema-resource checks begin at the baseline so problems are not deferred.

If a step proves too large for effective review, it may be divided into smaller
approval checkpoints without changing its scope or starting work assigned to a
later step. Conversely, steps should not be merged merely for speed: the purpose
of the sequence is to make behavioural and architectural corrections inexpensive
before later components depend on them.

## 5. Definition of version 1 implementation complete

Implementation is complete only when:

- the baseline step and all twelve implementation steps have been approved;
- the installed executable satisfies the normative specification and schemas;
- every acceptance-catalogue scenario passes in its intended test environment;
- tests and fixtures remain understandable without the development specification;
- generated configuration and result documents pass structural and semantic
  validation;
- the built distributions contain all required code, schemas, and offline
  documentation;
- no known inconsistency remains between implementation, tests, schemas, and
  documentation; and
- specified behaviours not directly automated are explicitly accounted for by
  inspection, packaging, environment, or release-process evidence.
