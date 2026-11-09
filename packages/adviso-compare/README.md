# AdvISO Compare

`adviso-compare` is a command-line tool for comparing a reference dataset with a query dataset. It uses explicit configuration rules to translate different source representations into a common canonical representation, then reports post-translation differences separately from issues that prevented assessment.

The project is intended to support bioinformatics validation and verification activities associated with ISO 15189 accreditation. It produces comparison evidence; it does not determine whether a pipeline is valid, acceptable, or compliant.

## Project status

Version 1 implementation is in progress. The schema-validation baseline,
command-line invocation layer, deterministic CSV, TSV, and JSON input parser,
custom comparison-configuration loader, and source-to-canonical field
translation pipeline are implemented. Automatic strict-exact configuration
generation and unambiguous custom or automatic record identity are also
implemented. The contract phase now assesses configured fields independently on
both sides, retains causal assessment issues, and consolidates field exclusions
without blocking unaffected content. The records phase deterministically aligns
canonical identities and retains every matched, missing, and extra record. Value
comparison now applies every version 1 comparator and accounts for matched,
mismatched, and not-assessable opportunities. Canonical evidence generation is
not yet available.

The current normative artefacts are:

- [Behaviour specification](docs/SPECIFICATION.md)
- [Comparison-configuration schema](src/adviso_compare/schemas/comparison-configuration-v1.0.schema.json)
- [Canonical-results schema](src/adviso_compare/schemas/comparison-results-v1.0.schema.json)

The proposed staged delivery sequence is documented in the
[version 1 implementation plan](docs/IMPLEMENTATION_PLAN.md).

The planned distribution and executable are named `adviso-compare`; the Python import package is `adviso_compare`.
