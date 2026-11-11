# AdvISO Compare

`adviso-compare` is a command-line tool for comparing a reference dataset with a query dataset. It uses explicit configuration rules to translate different source representations into a common canonical representation, then reports post-translation differences separately from issues that prevented assessment.

The project is intended to support bioinformatics validation and verification activities associated with ISO 15189 accreditation. It produces comparison evidence; it does not determine whether a pipeline is valid, acceptable, or compliant.

## Project status

The version 1 implementation is feature-complete and undergoing
release-candidate verification. It supports automatic strict-exact comparisons
and custom YAML comparison configurations across CSV, TSV, and JSON inputs. A
non-error run produces canonical JSON results and a self-contained HTML report.

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
its own child named `YYYYMMDDTHHMMSSZ-<run-id>`, containing the JSON result and
HTML report. Repeated runs preserve existing evidence. The completion summary
identifies the published run directory.

The current normative artefacts are:

- [Behaviour specification](docs/SPECIFICATION.md)
- [Comparison-configuration schema](src/adviso_compare/schemas/comparison-configuration-v1.0.schema.json)
- [Canonical-results schema](src/adviso_compare/schemas/comparison-results-v1.0.schema.json)

The proposed staged delivery sequence is documented in the
[version 1 implementation plan](docs/IMPLEMENTATION_PLAN.md).

The distribution and executable are named `adviso-compare`; the Python import
package is `adviso_compare`.
