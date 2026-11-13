# Contributing to `adviso-compare`

Read the repository [contribution guide](../../CONTRIBUTING.md) and applicable
[agent guidance](../../AGENTS.md). The
[architecture guide](docs/ARCHITECTURE.md) explains the implementation and
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
[test conventions](tests/README.md) describe shared fixtures and schema helpers.

Additional local checks are:

```console
python -m pip check
python -m compileall -q packages/adviso-compare/src packages/adviso-compare/tests
git diff --check
```

No formatter, linter, or type checker is currently configured. The
[CI workflow](../../.github/workflows/adviso-compare-ci.yml) runs the existing
test, schema, example, build, and installed-product checks.

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

The [user guide](docs/USER_GUIDE.md) and `docs/examples/` are installed with the
distribution. Check their runnable examples and installed copies with:

```console
python -m pytest packages/adviso-compare/tests/test_documentation.py packages/adviso-compare/tests/test_distribution.py -q
```

An editable installation does not keep installed documentation copies in sync
with edits to their source files. Use the maintained source guide during
development; the distribution test checks the guide installed from a fresh
wheel against that source.

The [specification](docs/SPECIFICATION.md) and packaged schemas define the
current behavioural contract. The original `IMPLEMENTATION_PLAN.md` describes
the initial delivery sequence, and `VERIFICATION_REPORT.md` contains dated
verification records. Consult their dates and scope when assessing evidence
for the current source revision.

Release verification still requires successful runs across the supported
Python/OS matrix, CI enforcement, and applicable release review. A configured
workflow or passing local suite alone does not establish those checks.

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

Start with the [specification](docs/SPECIFICATION.md) and the relevant packaged
[schema definitions](src/adviso_compare/schemas/). Resolve any disagreement
between those sources before changing behaviour. The architecture guide's
[change map](docs/ARCHITECTURE.md#where-to-make-a-change) helps locate the
implementation and existing tests.

For a behaviour change, review the existing tests first: adapt or remove cases
whose expectations are no longer specified, and add cases for uncovered rules.
Run the affected tests to confirm the expected failure, implement the change,
then run the complete suite and relevant schema and distribution checks.
For documentation-only work, check links and examples; run the documentation
and distribution tests when changing published instructions or installed files.

Keep the specification, schemas, controlled examples, and user guide aligned
with the implemented behaviour. Update the architecture guide when module
responsibilities or data flow change. These developer guides explain how to
maintain the software; they do not add product requirements.

When submitting a change, describe its effect, tests and commands run, and any
remaining verification limits. Distinguish a passing local suite from checks
performed across the supported environments.
