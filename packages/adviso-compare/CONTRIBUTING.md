# Contributing to `adviso-compare`

Read the repository [contribution guide](../../CONTRIBUTING.md) and applicable
[agent guidance](../../AGENTS.md). The
[implementation guide](docs/implementation-guide.md) explains the implementation and
points to the code and tests for each responsibility. The commands below run
from the repository root and apply to this package. Other tools have their own
development setup.

## Environment and editable installation

Linux is fully supported with CPython 3.11, 3.12, 3.13, 3.14, and 3.15. Windows
and macOS are expected to work, with full CI coverage on CPython 3.15 only.
Use the latest available patch release. Python 3.11 is the installation minimum;
additional Python/platform combinations need verification before joining the
verified matrix. Activate an existing development environment, or create one with:

```console
python -m venv .venv
. .venv/bin/activate
```

On Windows Command Prompt, activate it with `.venv\Scripts\activate`; in
PowerShell, use `.venv\Scripts\Activate.ps1`.

Install the package and its development dependencies into that environment:

```console
python -m pip install -e "packages/adviso-compare[dev]"
```

The editable installation makes source changes available to the installed
`adviso-compare` command. Versions come from Git through `setuptools-scm`;
`src/adviso_compare/_version.py` is generated and is not maintained by hand.

## Tests and checks

Run the complete package suite with:

```console
python -m pytest packages/adviso-compare/tests -q
```

For a focused run, select a relevant test module, for example:

```console
python -m pytest packages/adviso-compare/tests/test_inputs.py -q
```

The suite includes configuration and results schema validation, CLI behaviour,
documentation examples, and distribution builds and installation. The
[test conventions](#test-conventions) describe shared fixtures and schema helpers.

Additional local checks are:

```console
python -m pip check
python -m compileall -q packages/adviso-compare/src packages/adviso-compare/tests
git diff --check
```

No formatter, linter, or type checker is currently configured. The
[CI workflow](../../.github/workflows/adviso-compare-ci.yml) runs the existing
test, schema, example, build, and installed-product checks.

### Test conventions

Tests use descriptive behavioural names and assertions. Test modules, names,
markers, fixtures, and snapshots do not embed requirement or acceptance-scenario
identifiers. Any formal traceability belongs in review records as a one-way
reference to the tests.

Maintain coverage of parsing, translation, comparators, result semantics,
schemas, CLI errors and exit codes, deterministic output, and clean wheel and
source-archive installations. Exercise malformed inputs, both directions of
missing/extra content, composite and duplicate keys, and tolerance boundaries.
Every corrected material defect needs suitable regression coverage; adapt an
existing test when it expresses the rule clearly. Property-based and mutation
testing are optional techniques to use where they add useful assurance, not
release gates. No additional testing framework is required.

Give parameterized cases descriptive IDs when their inputs include complex
objects, mutations, or several expected values. Name the condition or boundary
being tested so a CI failure is understandable without decoding a parameter
dump. Simple scalar parameters such as `csv` or `complete` can keep their
default IDs. Keep related rule variants in one table; use separate tests when
different behaviours need substantially different setup or assertions. Small
local helpers can share mechanical setup while leaving inputs and expectations
visible in each test.

Reusable synthetic documents are built in `tests/support/documents.py`. Builders
return new objects on every call so tests can modify a document without leaking
state into another test. Fixed values are intentional: generated fixtures must
be deterministic and reviewable. A future generated on-disk fixture must record
its generator and regeneration command alongside the fixture.

Keep controlled fixtures under version control with their purpose, inputs,
configuration, and expected outcome clear from the fixture or test. Use only
synthetic, non-sensitive data. When fixtures form part of retained release
verification evidence, identify their source revision or generation method and
record any additional review performed; fixture digests can supplement the
source revision. Do not imply independent review when none occurred.

Schema loading and validator construction live in `tests/support/schemas.py`.
Structural validators load each document's packaged schema independently and
enable JSON Schema format assertion.

## Build distributions

With the development dependencies installed, build a wheel and source archive:

```console
python -m build --no-isolation --outdir packages/adviso-compare/dist packages/adviso-compare
```

The output directory is generated content. The distribution test builds both
archives once, then installs each into a separate fresh virtual environment.
It resolves declared dependencies without borrowing development site-packages;
source-archive installation also uses isolated build dependencies. These tests
may need network access to a package index.

Both installations run outside the checkout, check dependency consistency and
installed resources, and exercise the same automatic, custom, repeated-run, and
error scenarios. Evidence is also validated using each installed package. The
archives and resolved dependency records remain in the pytest base temporary
directory for the run.

## Documentation and examples

The [user guide](docs/user-guide.md) and `docs/examples/` are installed with the
distribution. Check their runnable examples and installed copies with:

```console
python -m pytest packages/adviso-compare/tests/test_documentation.py packages/adviso-compare/tests/test_distribution.py -q
```

An editable installation does not keep installed documentation copies in sync
with edits to their source files. Use the maintained source guide during
development; the distribution test checks the guide installed from a fresh
wheel against that source.

The [user guide](docs/user-guide.md) defines observable behaviour and semantic
rules. The packaged [schemas](src/adviso_compare/schemas/) define permitted JSON
structures and structural constraints. Tests verify this contract; the
implementation guide explains its implementation. Resolve disagreements explicitly
rather than allowing one document or a passing test to silently override another.

The guide must remain usable offline and cover the complete CLI, supported
inputs, automatic and custom configuration rules, output fields, validation,
errors, limitations, and governance boundaries. Complete configuration and
results examples must validate against their respective schemas, and worked
commands must produce their documented outcomes. A material disagreement among
the guide, schemas, examples, and implementation blocks release.

## Continuous integration

The workflow runs on pull requests targeting `main` (including updates to those
pull requests), pushes to `main`, Tuesdays at 04:23 UTC, and manual requests.
Pushes to development branches without an open pull request do not trigger it.
It does not publish releases.

Each run executes the full suite, including schema/example checks, builds,
and clean wheel/source-archive installation scenarios, on all seven combinations
in the verification matrix using these standard GitHub-hosted runners:

| Runner | Architecture | CPython versions |
| --- | --- | --- |
| `ubuntu-24.04` | x86-64 | 3.11, 3.12, 3.13, 3.14, 3.15 |
| `macos-15` | ARM64 | 3.15 |
| `windows-2025` | x86-64 | 3.15 |

The same full suite and matrix apply to pull requests, `main`, scheduled runs,
and manual runs. Linux is the fully supported deployment platform. Windows and
macOS compatibility is checked on Python 3.15; other Python versions on those
platforms are outside the verified matrix. No reduced test selection is used
for any matrix job. Review this coverage when preparing a release or updating
the support policy.

These identify the environments exercised by CI, rather than every supported
OS release or architecture. Runner images and Python patch releases can change;
each job records the platform, architecture, Python version, checked-out commit,
and resolved test dependencies. The distribution tests also record dependencies
for each clean installation. Every job installs the package normally, rather
than relying on an editable source installation, before running the full suite.
The scheduled run resolves dependencies afresh, just as pull-request runs do.

The workflow retains JUnit test results, built wheel/source archives, and
version/dependency records for 30 days, including available reports on failure.
It does not upload the temporary comparison datasets or evidence packages.
Development CI artefacts are temporary verification records; release evidence
needs separate retention. Superseded pull-request runs are cancelled. Other
matrix jobs continue after a failure to show the full set of outcomes.

To reproduce the test command locally, use a supported Python environment with
the development dependencies installed:

```console
python -c "from pathlib import Path; Path('ci-output').mkdir(exist_ok=True)"
python -m pytest packages/adviso-compare/tests -q --junitxml=ci-output/tests.xml --basetemp=ci-output/tmp
```

`ci-output/` is ignored generated content. Pytest clears the selected base
temporary directory before a run; use this command only with that disposable
path. The normal test command above lets pytest manage its own temporary path.

### GitHub merge settings

After the workflow has run on GitHub, configure branch protection or a ruleset
for `main` to require a pull request and the **`adviso-compare CI passed`** status
check from GitHub Actions. This final job succeeds only when every matrix job
succeeds. Enable the requirement for the branch to be up to date before merging
so checks cover the current base branch. Another person's review approval is
not required by this project's chosen merge policy.

These settings are configured in GitHub, separately from the workflow file;
committing the workflow does not enable them. Workflow changes themselves are
part of the proposed change and deserve scrutiny, since a pull request runs the
workflow from its temporary merged state. Keep action commit pins and runner
labels current through deliberate updates and rerun CI when changing them.

## Making a change

Start with the [user guide](docs/user-guide.md) and the relevant packaged
[schema definitions](src/adviso_compare/schemas/). Resolve any disagreement
between those sources before changing behaviour. The implementation guide's
[change map](docs/implementation-guide.md#where-to-make-a-change) helps locate the
implementation and existing tests.

For a behaviour change, review the existing tests first: adapt or remove cases
whose expectations are no longer specified, and add cases for uncovered rules.
Run the affected tests to confirm the expected failure, implement the change,
then run the complete suite and relevant schema and distribution checks.
For documentation-only work, check links and examples; run the documentation
and distribution tests when changing published instructions or installed files.

Keep the schemas, controlled examples, and user guide aligned
with the implemented behaviour. Update the implementation guide when module
responsibilities or data flow change. These developer guides explain how to
maintain the software; the user guide and schemas define product behaviour.

When submitting a change, describe its effect, tests and commands run, and any
remaining verification limits. Distinguish a passing local suite from checks
performed across the supported environments.

## Compatibility and versioning

Software releases, comparison-configuration schemas, and results schemas have
independent version identifiers. Each release documents supported schema
versions and combinations in the user guide and release notes. Unknown versions
or unsupported combinations must be rejected clearly. A configuration change
does not by itself require a results-schema revision; assess whether results
structure or meaning needs a corresponding schema revision.

Before changing either schema, publish the compatibility rules. For an
incompatible change, provide a migration path or documented transition
arrangements. Treat changes to the distribution, executable, or import-package
name as compatibility changes too. Preserve existing schema identifiers unless
a deliberate version change has been approved.

## Preparing a release

Release publication is manual; the CI workflow builds and verifies distributions
but does not publish them. Each release needs:

- a fixed semantic version and immutable source identification;
- passing full-suite CI on all seven combinations in the verification matrix;
- passing documentation/example, schema, build, and installed-product checks;
- release notes stating changes, known limitations, supported runtimes, and
  supported schema versions and combinations; and
- retained verification evidence identifying the source commit, published
  artefacts and SHA-256 checksums, checks and outcomes, environments, and resolved
  dependencies.

Additional independent review, signing or build attestation, property-based
testing, and mutation testing are optional. Record them if performed. They are
not release gates, and another person's approval is not a merge requirement.

Use this sequence:

1. Prepare release notes and assess the impact on comparison semantics, evidence
   formats, compatibility, and existing users. Check the current documentation,
   examples, runtime matrix, and schema compatibility statements. Identify any
   known limitations explicitly.
2. Merge the prepared changes through the protected branch and select the exact
   release commit. Use a clean checkout. Choose the semantic version and create
   its release tag at that commit. `setuptools-scm` derives the distribution
   version from Git; check the resulting version rather than editing the
   generated `_version.py`. Never move a published release tag or replace its
   artefacts; corrections receive a new version.
3. Run the CI workflow for the release tag and require all seven matrix jobs to
   pass. Confirm the recorded source commit and built distribution versions are
   those intended for release. Retain the JUnit results and environment and
   dependency records before their 30-day CI retention expires. Matrix execution
   includes the controlled Unicode-sensitive and determinism tests; do not infer
   cross-platform verification from a local run alone.
4. Select one matching wheel/source-archive pair from a successful matrix job.
   The distribution tests exercise fresh installations of each of those exact
   archives. Record which job supplied them and their SHA-256 checksums. Publish
   these verified files rather than rebuilding them after verification. If a
   rebuild is necessary, verify the replacement archives and record their new
   checksums before publication.
5. Create a concise release verification record identifying the tag, commit,
   supplying CI run/job, all matrix outcomes, artefact filenames and checksums,
   environments and dependency records, documentation/example checks, and any
   limitations or additional review. Store it and the relevant CI evidence with
   the release, for example as GitHub Release attachments. Keep these records
   beyond routine CI retention; do not append them to a rolling source document.
6. Publish the release notes and verified wheel/source archive through the
   chosen release channel, such as a GitHub Release. Confirm that published
   artefact checksums match the retained record. Installing from a package index
   additionally requires publishing those same files to that index; a GitHub
   Release alone does not make them available there.

The build and installation commands above also support local preparation, but
a passing local suite does not replace the required matrix evidence. The
release procedure records dependency resolution for the tested artefacts; it
does not claim that users will resolve identical dependencies in the future.
