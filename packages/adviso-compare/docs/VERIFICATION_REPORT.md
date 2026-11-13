# `adviso-compare` version 1 release-candidate verification

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

## Output-parent publication verification — 11 November 2026

This additional development verification covers Git revision `47dbecd` plus
the output-parent specification, test, implementation, and documentation
changes in the working tree. It is not an immutable-release attestation. The
earlier candidate review above remains a record of that candidate.

The environment was CPython 3.12.16 on macOS arm64. The full suite command was:

```console
.venv/bin/python -m pytest packages/adviso-compare/tests -q --tb=short --junitxml=.venv/output-directory-implementation-results.xml
```

Result: **317 passed in 14.66s**, with no failures, errors, or skips.

The revised tests verify:

- complete and incomplete evidence published as a new immediate child of an
  eligible output parent, with the fixed two members and exact validated bytes;
- names derived from controlled completion timestamps and full run UUIDs;
- eligible existing parents with arbitrary contents, private parent creation,
  rejection of ineligible parents, and preserved existing permissions;
- successive and concurrent runs, including an initially absent shared parent
  and distinct runs with the same timestamp;
- occupied run paths of different filesystem kinds, both before staging and
  appearing after staging, preserved with a collision error;
- staging-write and publication failures, including unavailable exclusive
  rename support, with existing evidence preserved and owned staging cleaned;
- early errors that neither create a parent nor touch its existing contents;
- rejection of unsupported CLI arguments, updated help, and actual child-path
  reporting with relative, absolute, and filesystem-root parents;
- schema-valid controlled examples and both schema definitions; and
- wheel and source-archive builds and installation, packaged schemas and
  documentation, and installed-wheel CLI execution including repeated runs,
  complete and incomplete results, and expected errors. The installed guide
  is checked byte for byte against the maintained source guide.

The distribution harness retains its existing dependency arrangement: the
installed-command environments obtain dependencies through the development
environment's site-packages. This check does not establish independent clean
dependency resolution.

The following additional checks passed:

```console
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q packages/adviso-compare/src packages/adviso-compare/tests
.venv/bin/adviso-compare --help
.venv/bin/adviso-compare --version
git diff --check
```

Local links and fenced examples in the maintained README, guide, and
specification were checked. Requirement definitions are unique and their
references resolve. The schemas, their version identifiers and canonical
`$id` values, dependencies, and packaging configuration are unchanged. The
editable development installation was refreshed; its offline guide and
examples were synchronized separately because editable installation does not
copy these data files.

Publication uses exclusive directory rename rather than an existence check
followed by a potentially replacing rename. API behaviour was reviewed against
the [Linux rename documentation](https://man7.org/linux/man-pages/man2/rename.2.html),
[Apple's rename documentation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/man/man2/rename.2),
and [Python's Windows rename contract](https://docs.python.org/3/library/os.html#os.rename).
The macOS native operation was exercised by the suite. Linux and Windows
native operations were not executed: this environment has no corresponding
test hosts or Linux container runtime. Full supported-platform and Python
matrix verification, CI enforcement, and independent review remain release
work. No formatter, linter, type checker, or Markdown linter is configured;
none is claimed to have passed.

## User documentation verification — 11 November 2026

The output-directory plan's documentation step was reviewed against the
approved specification and implemented CLI. The package README and guide
describe the initial-release interface directly, including output-parent
eligibility and creation, run-directory names and members, safe publication,
errors, retention, and privacy-preserving completion paths. The guide includes
a representative completion summary and explains how to locate the HTML
report and repeat a comparison under the same parent. No interface evolution
or migration narrative was added.

The console commands in guide Sections 4.1 and 5.11 were extracted and executed
directly with the supplied synthetic fixtures in a temporary working directory.
Each command was run twice with the same output parent. All four invocations
completed with one comparison difference and no assessment issues. Each
produced a distinct two-file package, and each first package's canonical JSON
remained byte-identical after the second run. The Python validation snippet
from Section 8.5 was executed unchanged from each published run directory and
passed for all four results.

```console
.venv/bin/python -m pytest packages/adviso-compare/tests/test_documentation.py packages/adviso-compare/tests/test_distribution.py packages/adviso-compare/tests/test_schemas.py -q
git diff --check
```

Result: **10 passed in 13.21s**; `git diff --check` passed. These checks include
wheel and source-archive installation and equality of the installed wheel's
guide with the maintained guide. Local documentation links, code fences, and
current CLI references were checked. The editable environment's offline guide
was synchronized separately and confirmed to match the maintained guide.

Production code, tests, schemas, dependencies, and packaging metadata were
unchanged during this documentation step. The full behavioural suite was not
rerun; the preceding implementation verification remains 317 passing tests.
No additional platform-matrix, lint, or type checks were run for this step;
the limitations recorded above still apply.

## Separate configuration evidence verification — 11 November 2026

This development verification covers Git revision `b360d74` plus the working-tree
specification, schema, implementation, test, and documentation changes for the
three-file evidence package. It is not an immutable-release attestation. Earlier
sections remain records of their respective candidates.

The environment was CPython 3.12.16 on macOS arm64. The final suite command was:

```console
.venv/bin/python -m pytest packages/adviso-compare/tests -q --tb=short --junitxml=.venv/separate-configuration-final.xml
```

Result: **376 passed in 16.50s**, with no failures, errors, or skips.

The verified contract includes:

- exactly three fixed regular members: `comparison-results.json`,
  `comparison-configuration.json`, and `comparison-report.html`;
- complete effective configuration preservation in custom and automatic modes,
  including metadata, explicit declarations, list provenance, absent defaults,
  canonical UTF-8 serialization, and immutable independent document views;
- results root `schema_version` and top-level
  `comparison_configuration_digest`, with SHA-256 calculated from the exact
  configuration bytes published, including their final newline;
- independent family/version schema selection, preserved canonical schema IDs
  and `1.0` identifiers, no results-to-configuration schema reference, format
  assertion, and explicitly supported schema combinations;
- strict JSON parsing, required configuration context, missing/unreadable or
  non-regular configuration files, unsupported versions, malformed or duplicate
  members, digest tampering, and cross-document semantic contradictions;
- retained finding, count, status, key, priority, exclusion, input-provenance,
  and available comparison-context checks;
- HTML generation from the validated JSON pair, with no original-YAML reread;
- private staging of all three files, failure at each member write, exclusive
  publication, preservation of existing content, collision handling, and
  successive/concurrent runs; and
- automatic/custom and complete/incomplete integration, wheel and sdist builds
  and installation, installed resources, and installed-wheel command execution.

Existing tests were adapted at their established boundaries. The documentation
example test now extracts and executes the guide's package-validation snippet
against both generated example packages. No separate fixture family, helper
module, dependency, command, or test-framework change was introduced. The
configuration schema is unchanged. The revised results schema retains its
canonical ID and version while representing the initial-release contract.

The README and guide describe the package directly, including independent
schema identities, exact-byte linkage, saved configuration metadata, and the
supported version combination. The guide distinguishes structural validation,
digest verification, and semantic checks, including which checks require source
comparison context. Its runnable procedure calls the installed
`validate_evidence_package` function; the text also describes trusted schema
selection and equivalent format assertion for independent consumers. It
explicitly limits saved-package inspection to available evidence and does not
claim HTML authentication or reproduction of the comparison from its inputs.

The focused documentation, distribution, and schema check was:

```console
.venv/bin/python -m pytest packages/adviso-compare/tests/test_documentation.py packages/adviso-compare/tests/test_distribution.py packages/adviso-compare/tests/test_schemas.py -q --tb=short --junitxml=.venv/separate-configuration-step5.xml
```

Result: **41 passed in 14.40s**. The installed wheel's guide is checked byte for
byte against the maintained guide. The distribution harness uses development
site-packages for dependencies; this is not independent dependency resolution.

Both console commands from guide Sections 4.1 and 5.11 were separately extracted
and executed twice in a temporary copy of the supplied synthetic examples.
All four runs completed with one comparison difference and no assessment
issues. Each produced a distinct three-file package. The first package's three
files remained byte-identical after the second run. The Section 8.5 Python
snippet was extracted and executed unchanged from all four run directories;
all passed.

Compilation, dependency consistency, and `git diff --check` passed. Local links,
heading fragments, and code fences in the repository README, package README,
guide, and specification were checked. Normative requirement definitions are
unique and their references resolve. A source search found no obsolete result
version property or embedded-configuration access in runtime code, tests,
schemas, the specification, or maintained user documentation. Earlier
development plans and verification records were not rewritten as current
product instructions. The editable environment's offline guide was synchronized
and confirmed byte-identical; its installed examples also match source.

Production code, normative sources, dependencies, and packaging metadata were
unchanged during this documentation step. The implemented behaviour, schemas,
tests, and maintained documentation now agree on this functionality change.
Linux, Windows, other supported Python versions, CI enforcement, independent
review, and immutable release evidence remain release verification work. No
formatter, linter, type checker, or Markdown linter is configured, and none is
claimed to have run. Local completion of this change does not establish release
readiness across the supported matrix.

## CI configuration and Python support verification — 2026-11-12

The supported runtime matrix is now CPython 3.11–3.15 on Linux, macOS, and
Windows. Package metadata sets Python 3.11 as the installation minimum. The
specification, README, user guide, architecture guide, and contribution guide
reflect this policy. Earlier interpreter and CI statements in this report
record the environments and configuration at their respective verification dates.

The repository now contains `.github/workflows/adviso-compare-ci.yml`. It
configures all 15 Python/OS combinations, runs on pull requests into `main`,
pushes to `main`, a weekly schedule, and manual dispatch, and retains reports,
built archives, and dependency records for 30 days. The final
`adviso-compare CI passed` job requires every matrix job to succeed. No release
publication, formatter, linter, or type checker was added to the CI checks.

The existing distribution test is parameterized over wheel and source archive.
Each archive is installed with its declared dependencies in a fresh environment,
with source builds isolated, outside the checkout and without development
`PYTHONPATH`. Both cases exercise version reporting, installed resources,
automatic/custom comparisons, repeated publication, expected errors, and saved
package validation. Dependency consistency and installed module locations are
checked. The built metadata test was first confirmed to fail against the former
minimum, then passed after updating package metadata.

Local verification used CPython 3.12.16 on macOS ARM64:

```console
python -m pytest packages/adviso-compare/tests -q --junitxml=ci-output/tests.xml --basetemp=ci-output/tmp
```

Result: **397 passed in 35.33s**, with `ci-output/` created before invoking pytest.
The focused clean installation run also passed both archive cases. These checks
used network access to obtain declared dependencies. The development editable
installation was refreshed for the updated metadata and bundled guide.

Additional checks passed: temporary checksum-verified `actionlint` 1.7.12
validation (without optional shellcheck/pyflakes integrations), YAML trigger and
15-job matrix checks, action commit-pin checks, package metadata inspection,
`pip check`, Python compilation, local documentation links/anchors and code
fences, and `git diff --check`. No schema content or comparison behaviour changed.

This is local verification of the implementation, not evidence that the hosted
matrix passed. GitHub execution of all supported environments, branch-protection
configuration, and release review remain outstanding. Repository settings must
require the named final CI check; committing the workflow alone does not enforce
merging policy. Another person's approval is not a required merge check under
the chosen policy. These records do not attest an immutable release artefact.

## Finding presentation and example verification — 2026-11-13

The custom user-guide example now produces three comparison differences across
SAMPLE-001 and SAMPLE-002: interpretation, marker-set membership, and a numeric
tolerance failure. It remains complete with no assessment issues. The guide's
worked explanation and reproduction table describe those outcomes.

HTML field findings lead with query and reference source-field names. Query
values appear first; translated values remain visible as the values used for
comparison. Canonical field names and the saved rules are available in expandable
detail. Reasons are derived from finding codes, saved values, and configuration;
numeric reasons use shared exact difference/tolerance arithmetic, including
reference-directed relative tolerance. Canonical JSON messages, schemas, and
comparison rules were not changed.

A precision regression exposed existing rounding in canonical decimal text:
Decimal.normalize() applied ambient precision and exponent limits. Formatting
now removes insignificant coefficient zeros without numerical normalisation,
preserving exact values and large exponents in the existing canonical format.
Regression cases failed before this correction and passed afterwards.

Existing reporting and documentation tests were adapted first. Added cases
cover exact tolerance explanations, negative/zero references, post-quantisation
values, precision beyond the default decimal context, escaped source names, and
assessment-issue explanations. Example tests verify the exact three findings,
separate HTML finding articles, and agreement with the guide's outcome table.

On CPython 3.12.16/macOS ARM64, the full suite passed: **417 tests in 35.93s**.
After the final documentation update, documentation/distribution checks passed
(**8 tests**), including clean wheel/source installations and installed resources;
reporting checks passed (**56 tests**). Schema coverage ran in the full suite.
Compilation, dependency consistency, documentation links/anchors and code fences,
and git diff whitespace checks passed. A fresh custom evidence package passed
saved-package validation and its generated HTML contained all three named field
findings and their explanations.

The editable installation was refreshed. Its installed guide and changed example
were explicitly synchronized and checked against source, since editable installs
do not reliably refresh documentation data files. No browser or print visual
verification was completed. Other Python/OS combinations remain for hosted CI.
