# AdvISO Compare version 1 release-candidate verification

Date: 10 November 2026

## Candidate reviewed

This review covers the version 1 implementation in
`packages/adviso-compare`, based on Git revision `d1fd7a3` plus the uncommitted
Step 12 documentation, example, packaging, and verification changes present in
the working tree on the date above. It is therefore a development-candidate
review, not an attestation of an immutable release artefact.

The behaviour specification and both version 1.0 schemas were treated as the
sources of truth. The candidate supports Python 3.10 or later in its package
metadata. Verification in this environment used CPython 3.10.12 on
Linux x86_64.

## Outcome

The implementation and documentation checks available in this environment
passed. The complete automated suite contains 300 passing tests. Both
user-guide examples completed through the real application and produced the
documented results. The wheel and source archive were built, inspected, and
installed in isolated environments. The installed executable completed the
tested automatic, custom, incomplete, and expected-error paths.

This is not yet sufficient evidence for a final release decision. The supported
Python and operating-system matrix, CI enforcement, and independent review are
not available in this workspace and remain release-time evidence.

## Automated evidence

Command:

```console
.venv/bin/pytest -q
```

Result: `300 passed in 29.48s`.

The suite covers:

- CSV, TSV, and JSON parsing, malformed inputs, retained locations, exact JSON
  numbers, and deterministic field discovery;
- custom configuration loading, schema validation, semantic checks, mappings,
  normalisation, collection representations, and automatic configuration;
- custom, preferred `record_id`, and discovered record keys, including invalid,
  duplicate, and ambiguous keys;
- contract, record alignment, all version 1 comparators, findings, counts,
  exclusions, completeness, ordering, and determinism;
- canonical-result assembly, JSON Schema validation with format assertion, and
  semantic self-validation;
- HTML rendering, atomic publication, overwrite protection, rollback, and
  cleanup;
- command options, completion summaries, exit codes, expected diagnostics, and
  the unexpected-error boundary;
- wheel and source-archive construction and installation, packaged schemas,
  wheel integrity metadata, the installed command, and end-to-end operation;
  and
- structural validation and end-to-end execution of the automatic and custom
  examples supplied with the user guide.

Focused documentation and distribution checks were also run before the full
suite. After the final documentation edit, the full suite reran all of them.

## Inspection-based evidence

The user guide was reviewed against the command interface and both schema
property sets. It documents:

- installation, verification, all command options, overwrite rules, exit
  codes, and offline operation after installation;
- CSV, TSV, and JSON input rules;
- automatic key selection and generated strict-exact comparison behaviour;
- every custom-configuration property, optional-property behaviour,
  operations, mappings, collections, comparators, and processing order;
- phases, classifications, finding codes, run status, and the absence of an
  acceptance verdict;
- every canonical-results property and the conditional finding forms;
- the distinction between JSON Schema validation and semantic result
  validation, including a format-asserting validation example;
- evidence-package and HTML interpretation, diagnostics and corrective action,
  security boundaries, limitations, and fixture reproduction; and
- software and schema versions to which the guide applies.

The examples use only small synthetic data. Their source files are maintained
directly under `docs/examples`; no hidden generator or external data is needed.
Each run has one comparison difference, no assessment issue, and complete
status. Variable run IDs, completion times, software/runtime provenance, and
byte evidence are deliberately not treated as fixed fixture output.

The package README now points users to the full guide and gives the complete
command shape. Command-line help describes every option and directs users to
the guide. The guide and examples are present in both built distribution forms
and install under `share/doc/adviso-compare`.

## Static, schema, and packaging checks

The following checks passed:

```console
git diff --check
.venv/bin/python -m compileall -q src tests
.venv/bin/adviso-compare --help
.venv/bin/adviso-compare --version
```

Both JSON schemas pass Draft 2020-12 schema checks in the test suite. Test
documents and generated example results are validated with format assertion and
the configuration-schema reference registered locally.

No formatter, linter, type checker, Markdown checker, or link checker is
configured for this package. None was introduced during Step 12. Consequently,
there is no claim that such a check passed.

## Process and release-time evidence still required

The following items cannot be established by this local candidate review:

- execution across the full supported Python and operating-system matrix;
- cross-environment invariance, including Unicode-sensitive behaviour;
- CI operation on proposed changes and protected branches;
- independent review of the release candidate and its controlled fixtures;
- immutable release version, release notes, compatibility statement, and
  change-impact assessment;
- signing or other attestation of final source and build artefacts, if adopted;
  and
- confirmation that the final published artefacts are byte-for-byte the ones
  reviewed and approved.

The current environment exposes only CPython 3.10.12. Package metadata says
`>=3.10`, so testing only this interpreter does not satisfy the supported-
version matrix requirement. The repository currently has no CI workflow to
provide that missing evidence. These are release blockers under the present
specification, not failures of the local behavioural suite.

## Resource statement

The candidate sets no fixed input-size or record-count safeguard. Comparisons
attempt to assess all configured content. Practical capacity depends on the
available memory, storage, and operating-system resources. The error boundary
handles memory exhaustion without publishing a partial evidence package, but
this review did not establish operational capacity limits for particular
dataset sizes.

## Release-decision summary

The candidate is suitable for independent review and supported-matrix testing.
No failure found in this Step 12 review requires a change to the documented
comparison behaviour or either normative schema. A final version 1 release
should not be declared solely from this report: the matrix, CI, independent
review, and immutable release evidence listed above still need to be supplied
or the corresponding release requirements deliberately revised.
