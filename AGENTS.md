# Agent guidance for `validation_toolkit`

## Purpose and authority

This repository is being reimplemented as `adviso-validation`, a tool that translates reference and query datasets from their source dialects into a declared canonical representation, compares them, and reports both post-translation differences and assessment issues.

For version 1 behaviour, use this order of authority:

1. `SPECIFICATION.md` — normative behaviour and requirement identifiers.
2. `src/adviso_validation/schemas/comparison-configuration-v1.0.schema.json` — normative structural schema for comparison configurations.
3. `src/adviso_validation/schemas/comparison-results-v1.0.schema.json` — normative structural schema for canonical results.
4. Version 1 tests and controlled fixtures, once created — executable verification of the sources above.
5. User documentation — explanatory material that must agree with the normative sources.

Do not infer version 1 behaviour from the prototype, its README, or its tests. If the specification and a schema appear inconsistent, stop and report the conflict. Do not silently choose one, weaken either, or invent compatibility behaviour.

## Repository state

The repository currently contains two generations of work:

- `SPECIFICATION.md` and `src/adviso_validation/schemas/` define the intended version 1 product.
- `validation_toolkit/`, `tests/table_validator_tests/`, the current `README.md`, and parts of the packaging configuration describe an unused exploratory prototype.

The prototype has no compatibility status. Its CLI, APIs, output formats, terminology, internal structure, and tests are not version 1 requirements. Do not copy prototype code merely to accelerate implementation. Reuse something only after confirming that it satisfies the version 1 specification and improves the new design.

Do not delete or rewrite prototype material unless the assigned task or an approved implementation plan explicitly calls for it. Keeping old and new work separate during the transition is preferable to partially converting legacy modules.

## Product identities

Preserve these distinct names:

- Distribution and executable: `adviso-validation`
- Python import package: `adviso_validation`
- Sole version 1 subcommand: `compare`

New production code belongs under `src/adviso_validation/`. Do not add new production modules under the legacy `validation_toolkit/` package.

## Working method

Before implementing behaviour:

1. Read the relevant specification sections in full, including referenced requirements in other sections.
2. Read both schemas when the work touches configuration, findings, results, or reporting.
3. Identify the requirement IDs affected by the change.
4. Add or update the smallest coherent set of tests that verifies those requirements.
5. Implement until those tests pass.
6. Run the proportionate wider test suite and static checks.

Use test-driven development for the reimplementation. A failing test is useful only when it represents current specified behaviour. Do not add tests for discarded design ideas, prototype compatibility, renamed properties that never entered version 1, or other historical “fossils.”

Tests should cite the requirement IDs they verify. Prefer a focused parameterized test that covers a coherent rule table over many near-duplicate tests. Do not merge unrelated behaviours merely to reduce the test count. Not every implementation, documentation, release-process, or quality requirement needs a direct automated test.

## Change control

- Do not change `SPECIFICATION.md`, either schema, or established requirement semantics unless the task explicitly authorizes a specification change.
- Behaviour changes must update all affected normative text, schemas, tests, fixtures, and user documentation together.
- Preserve existing requirement IDs. Add new IDs rather than renumbering requirements after insertion or deletion.
- Preserve schema version identifiers and canonical `$id` values unless a deliberate schema-version change has been approved.
- Treat unknown configuration and result properties as errors; do not add permissive extension points speculatively.
- Do not add CLI options, comparators, normalisers, file formats, report formats, plugin systems, compatibility shims, or acceptance logic outside the specified v1 scope.
- Keep commits and patches narrowly scoped. Do not mix behavioural work with unrelated restructuring or formatting.

When a requirement is ambiguous, contradictory, or not implementable as written, present the exact conflict and its consequences to the repository owner. Do not resolve product decisions through undocumented assumptions.

## Design guardrails

- Keep the top-level CLI thin. Put comparison behaviour in independently testable internal modules.
- Keep parsing, configuration validation, canonicalisation, record alignment, comparison, result construction, semantic result validation, and rendering as distinct responsibilities.
- Prefer small explicit interfaces and ordinary modules. Version 1 does not need a general plugin framework.
- Keep the comparison kernel independent of CLI parsing and HTML presentation.
- Model the three processing phases (`contract`, `records`, and `values`) separately from finding classification (`comparison_difference` and `assessment_issue`).
- Treat the reference and query as having distinct roles where the specification does so, including directional relative tolerance.
- Never use binary floating-point arithmetic for specified decimal parsing, normalisation, tolerance calculation, or canonical rendering.
- Preserve source lexical evidence where required while keeping canonical typed values distinct from source values.
- Make ordering explicit. Never rely on dictionary, set, filesystem, locale, or hash iteration order for canonical output.
- Collect all safely assessable findings. Do not stop normal comparison at the first difference.
- Keep execution errors outside canonical comparison results and findings.
- Generate HTML only from validated canonical JSON and fixed renderer resources.

## Validation boundaries

Configuration processing has two mandatory layers:

1. structural validation against the packaged comparison-configuration schema;
2. semantic validation of the cross-property rules in `SPECIFICATION.md`.

Canonical-result validation likewise has two layers:

1. structural validation against the packaged results schema, with Draft 2020-12 format assertion enabled;
2. semantic validation of reconciliation, ordering, classification, configuration agreement, and other cross-property invariants.

Never publish an evidence package unless both result-validation layers pass. A generated-result validation failure is `internal.unexpected`, not a user finding.

Load packaged schemas and the bundled configuration through the package-resource API. Core comparison must work without network access and must not resolve schemas by downloading their canonical HTTPS identifiers.

## Python quality

- Use type annotations for production interfaces and non-trivial internal functions.
- Prefer explicit domain types, enums, and immutable value objects where they prevent invalid states.
- Keep functions focused and make transformation stages easy to test in isolation.
- Raise or return domain-specific errors at architectural boundaries; do not use broad exception handling to hide defects.
- Convert unexpected exceptions into the specified CLI diagnostic only at the outer application boundary.
- Do not expose tracebacks during ordinary CLI operation.
- Avoid mutable global state and import-time side effects.
- Keep dependencies minimal, justified, pinned or bounded appropriately, and separated into runtime and development dependencies.
- Use safe YAML loading with the restrictions required by the specification. Never construct arbitrary Python objects from configuration input.
- Use secure temporary-file and atomic-publication patterns. Never broaden filesystem permissions.

Do not introduce a formatter, linter, type checker, build backend, or supported-Python change as an incidental edit. Such project-wide tooling choices belong in the implementation plan and must be configured consistently before being enforced.

## Testing guardrails

The version 1 suite should be organized around public behaviour and stable internal contracts, not private implementation details. It must eventually include the test families specified in Section 14 of `SPECIFICATION.md`.

In particular:

- Use controlled, synthetic, non-sensitive fixtures.
- Keep fixtures small enough to review, except for tests specifically concerned with scale or resource behaviour.
- Record why generated fixtures exist and make their regeneration deterministic.
- Test both directions where reference/query symmetry is required.
- Test boundary values, malformed inputs, Unicode, composite keys, null versus absence, exact decimal behaviour, and deterministic ordering.
- Validate representative results against the packaged schema and the semantic result validator.
- Test the installed `adviso-validation` entry point, not only direct Python calls.
- Test the built wheel and source distribution rather than relying only on an editable source checkout.
- Do not update expected outputs blindly. Review semantic changes in canonical JSON fixtures field by field.

Until a new v1 suite is established, do not treat passing `tests/table_validator_tests/` as evidence that v1 requirements are satisfied.

## Security and clinical-data handling

Assume inputs and evidence packages may contain sensitive clinical or laboratory information.

- Never place real patient data, identifiers, credentials, absolute local paths, or secrets in source, tests, fixtures, snapshots, logs, or examples.
- Routine logs, progress output, terminal diagnostics, and execution-error diagnostics must not reproduce record identifiers or source values.
- Findings may contain identifiers or values only where the specification requires them to identify or explain a finding.
- Do not add telemetry, remote schema lookup, remote assets, or any other network transmission.
- Treat input basenames as potentially sensitive.
- Preserve the specification's overwrite, symlink, temporary-file, and atomic-publication protections.

## Documentation

The eventual user guide must describe the released behaviour, complete CLI, configuration schema, results schema, finding taxonomy, evidence package, and corrective guidance for execution errors. Documentation examples must validate against the packaged schemas.

Do not update the current prototype README piecemeal so that it appears to describe a usable hybrid product. Replace it as a deliberate implementation milestone when the corresponding v1 interface is ready.

## Before declaring work complete

For the scope changed, confirm and report:

- affected requirement IDs;
- tests added or updated and why they are sufficient;
- commands run and their results;
- schema validation performed, including format assertion where applicable;
- any checks not run and the reason;
- documentation or fixture changes;
- remaining assumptions, limitations, or follow-up work.

Do not claim completion while relevant tests, schema checks, packaging checks, or documentation are knowingly inconsistent with the implementation.
