# Contributing to `adviso-compare`

Read the repository [contribution guide](../../CONTRIBUTING.md) and applicable
[agent guidance](../../AGENTS.md). The
[architecture guide](docs/ARCHITECTURE.md) explains the implementation and
points to the code and tests for each responsibility. The commands below run
from the repository root and apply to this package. Other tools have their own
development setup.

## Environment and editable installation

Use Python 3.10 or later. Activate an existing development environment, or
create one with:

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

No formatter, linter, type checker, or CI workflow is currently configured.

## Build distributions

With the development dependencies installed, build a wheel and source archive:

```console
python -m build --no-isolation --outdir packages/adviso-compare/dist packages/adviso-compare
```

The output directory is generated content. The distribution test builds into a
temporary directory and verifies installed resources and the wheel's command.
It supplies dependencies from the development environment's site-packages;
it does not verify clean dependency resolution. Source-archive installation
is checked for an importable package, without repeating the full CLI scenarios.

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

Release verification still includes the supported Python/OS matrix, clean
dependency installation, CI enforcement, and independent review. Local test
success alone does not establish those checks.

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
