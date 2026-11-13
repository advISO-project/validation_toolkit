# `adviso-compare`

`adviso-compare` is a command-line tool for comparing a reference dataset with a query dataset. It uses explicit configuration rules to translate different source representations into a common canonical representation, then reports post-translation differences separately from issues that prevented assessment.

The project is intended to support bioinformatics validation and verification activities associated with ISO 15189 accreditation. It produces comparison evidence; it does not determine whether a pipeline is valid, acceptable, or compliant.

## Project status

The tool is implemented and unreleased. Release verification is ongoing.
The tool is fully supported on Linux with CPython 3.11–3.15. Windows and macOS
are expected to work, with full CI coverage limited to CPython 3.15 on those
platforms. Python 3.11 is the installation minimum.
It supports automatic strict-exact comparisons
and custom YAML comparison configurations across CSV, TSV, and JSON inputs. A
non-error run produces canonical JSON results, the complete effective
configuration as JSON, and a self-contained HTML report.

For installation, commands, configuration rules, output fields, examples, and
troubleshooting, read the [user guide](docs/user-guide.md).

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
[package-validation procedure](docs/user-guide.md#73-structural-and-semantic-validation).

The behavioural contract is defined by subject:

- [User guide](docs/user-guide.md): observable behaviour and semantic rules.
- [Comparison-configuration schema](src/adviso_compare/schemas/comparison-configuration-v1.0.schema.json)
- [Canonical-results schema](src/adviso_compare/schemas/comparison-results-v1.0.schema.json)

The schemas define JSON structure and structural constraints. Disagreements
between the schemas and the guide must be resolved explicitly; tests verify
this contract rather than override it.

The distribution and executable are named `adviso-compare`; the Python import
package is `adviso_compare`.

## Development

See the [package contribution guide](CONTRIBUTING.md) for environment setup,
tests, builds, and the change workflow. The [implementation guide](docs/implementation-guide.md)
explains the implementation, data flow, and validation boundaries.
