# AdvISO Validation

`adviso-validation` is a command-line tool for comparing a reference dataset with a query dataset. It uses explicit configuration rules to translate different source representations into a common canonical representation, then reports post-translation differences separately from issues that prevented assessment.

The project is intended to support bioinformatics validation and verification activities associated with ISO 15189 accreditation. It produces comparison evidence; it does not determine whether a pipeline is valid, acceptable, or compliant.

## Project status

Version 1 is currently specified but not yet implemented. The repository is being prepared for a test-driven implementation.

The current normative artefacts are:

- [Behaviour specification](docs/SPECIFICATION.md)
- [Comparison-configuration schema](src/adviso_validation/schemas/comparison-configuration-v1.0.schema.json)
- [Canonical-results schema](src/adviso_validation/schemas/comparison-results-v1.0.schema.json)

The planned distribution and executable are named `adviso-validation`; the Python import package is `adviso_validation`.
