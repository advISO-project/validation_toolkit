# `adviso-compare`

`adviso-compare` is a command-line tool for comparing a reference dataset with a query dataset. It uses explicit configuration rules to translate different source representations into a common canonical representation, then reports post-translation differences separately from issues that prevented assessment.

The project is intended to support bioinformatics validation and verification activities associated with ISO 15189 accreditation. It produces comparison evidence; it does not determine whether a pipeline is valid, acceptable, or compliant.

## Project status

The tool is implemented and unreleased. Release verification is ongoing.
It supports automatic strict-exact comparisons
and custom YAML comparison configurations across CSV, TSV, and JSON inputs. A
non-error run produces canonical JSON results, the complete effective
configuration as JSON, and a self-contained HTML report.

For installation, commands, configuration rules, output fields, examples, and
troubleshooting, read the [user guide](docs/USER_GUIDE.md).

The basic command is:

```text
adviso-compare \
  --reference REFERENCE \
  --query QUERY \
  --output OUTPUT \
  [--configuration CONFIGURATION]
```

`--output` selects a parent directory. Each complete or incomplete run creates
its own child named `YYYYMMDDTHHMMSSZ-<run-id>`, containing exactly
`comparison-results.json`, `comparison-configuration.json`, and
`comparison-report.html`. Results record the SHA-256 digest of the exact saved
configuration bytes. Repeated runs preserve existing evidence. The completion
summary identifies the published run directory.

Both JSON formats use their own root `schema_version` and are independently
versioned. Version 1 supports results schema `1.0` with configuration schema
`1.0`. Keep the three files together; see the user guide's
[package-validation procedure](docs/USER_GUIDE.md#73-structural-and-semantic-validation).

The current normative artefacts are:

- [Behaviour specification](docs/SPECIFICATION.md)
- [Comparison-configuration schema](src/adviso_compare/schemas/comparison-configuration-v1.0.schema.json)
- [Canonical-results schema](src/adviso_compare/schemas/comparison-results-v1.0.schema.json)

The distribution and executable are named `adviso-compare`; the Python import
package is `adviso_compare`.

## Development

Read the repository [contribution guide](../../CONTRIBUTING.md) and applicable
[agent guidance](../../AGENTS.md). The commands below run from the repository
root and apply to this package. Other tools have their own development setup.

### Environment and editable installation

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

### Tests and checks

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

### Build distributions

With the development dependencies installed, build a wheel and source archive:

```console
python -m build --no-isolation --outdir packages/adviso-compare/dist packages/adviso-compare
```

The output directory is generated content. The distribution test builds into a
temporary directory and verifies installed resources and the wheel's command.
It supplies dependencies from the development environment's site-packages;
it does not verify clean dependency resolution. Source-archive installation
is checked for an importable package, without repeating the full CLI scenarios.

### Documentation and examples

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
