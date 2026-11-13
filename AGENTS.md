# Agent guidance for the AdvISO validation toolkit

## Purpose of this file

This file governs how agents work in this monorepo. It does not define product behaviour. Product requirements belong in the applicable package's behavioural documentation and normative schemas; do not duplicate them here.

## Sources of truth

For `adviso-compare`, authority is assigned by subject:

- The packaged schemas in `packages/adviso-compare/src/adviso_compare/schemas/` define the permitted JSON structures and structural constraints for their respective document families.
- `packages/adviso-compare/docs/USER_GUIDE.md` defines observable behaviour and semantic rules that the schemas cannot express.
- `packages/adviso-compare/CONTRIBUTING.md` defines package development, verification, compatibility, and release procedures.
- `packages/adviso-compare/docs/ARCHITECTURE.md` explains the implementation; it does not define product behaviour.
- Tests and controlled fixtures verify the documented contract; they do not override it or supply undocumented requirements.

If these sources appear inconsistent, stop and report the exact conflict and its consequences. Do not silently choose an interpretation, weaken a requirement, or invent behaviour.

## Repository layout

- Keep each independently installable tool under `packages/<distribution-name>/`.
- Give each tool its own `pyproject.toml`, README, `docs/`, `src/`, and `tests/`.
- For `adviso-compare`, put production code and runtime resources under
  `packages/adviso-compare/src/adviso_compare/`, tests under
  `packages/adviso-compare/tests/`, and maintained product documentation under
  `packages/adviso-compare/docs/`.
- Keep repository-wide guidance at the repository root. Do not place
  product-specific requirements there.
- Treat generated version files, build outputs, caches, coverage output, and virtual environments as generated artefacts rather than source.

Do not create a package for a proposed tool until its scope and implementation work have been approved. Do not create new top-level directories or reorganize established modules without a concrete need in an approved plan.

## Working method

Before changing behaviour:

1. Read the relevant behavioural documentation in full, including referenced rules elsewhere in the document.
2. Read the relevant schema definitions.
3. Identify the specified behaviours affected by the work.
4. Add or update the smallest coherent set of tests that verifies those behaviours.
5. Implement until those tests pass.
6. Run proportionate wider tests, static checks, schema checks, and packaging checks.
7. Update affected documentation and controlled fixtures.

Use test-driven development for behavioural changes. A failing test is useful only when it represents current documented behaviour. Do not create tests for discarded ideas, historical decisions, or renamed and removed properties.

## Change control

- Do not change a package's behavioural contract, normative schemas, or established requirement semantics unless the task explicitly authorizes that change.
- Preserve schema version identifiers and canonical `$id` values unless a deliberate version change has been approved.
- When behaviour changes are authorized, update all affected normative text, schemas, tests, fixtures, and user documentation together.
- Do not add speculative features, extension points, compatibility layers, dependencies, or abstractions.
- Keep patches narrowly scoped. Do not mix behavioural work with unrelated restructuring or formatting.
- Preserve unrelated work already present in the worktree.

When a requirement is ambiguous, contradictory, or not implementable as written, ask for a decision rather than encoding an undocumented assumption.

## Code quality

- Follow PEP 8 and write idiomatic Python compatible with the project's supported Python versions.
- Follow PEP 257 for public-module, class, function, and method docstrings; document intent and constraints rather than restating the code.
- Where configured automated formatting, linting, or type-checking rules differ from general style guidance, the project configuration is authoritative.
- Avoid unrelated formatting changes that obscure the substantive content of a patch.
- Keep the command-line layer thin and keep domain logic independently testable.
- Separate I/O, domain logic, validation, and presentation responsibilities.
- Prefer small explicit interfaces and ordinary modules over framework-like abstraction.
- Use type annotations for production interfaces and non-trivial internal functions.
- Prefer explicit domain types and immutable value objects where they prevent invalid states.
- Keep functions focused and transformation stages testable in isolation.
- Avoid mutable global state and import-time side effects.
- Use domain-specific exceptions or result types at architectural boundaries.
- Do not use broad exception handling to conceal defects.
- Keep dependencies minimal and justified, with runtime and development dependencies separated.
- Write deterministic code; do not depend accidentally on unordered collections, filesystem order, locale, or hash iteration.

Do not introduce or replace a formatter, linter, type checker, build backend, test framework, dependency manager, or supported-Python policy as an incidental edit. Project-wide tooling choices require deliberate configuration and approval.

## Testing practice

- Give tests descriptive behavioural names that remain meaningful without a separate requirements catalogue.
- Do not embed requirement identifiers or acceptance-scenario identifiers in code, tests, fixtures, snapshots, or package metadata. Any formal development traceability belongs in review records and must remain a one-way reference from those records to the software artefacts.
- Prefer parameterization when it expresses one rule table clearly; do not merge unrelated behaviours merely to reduce test count.
- Test public behaviour and stable internal contracts rather than private implementation details.
- Use controlled, synthetic, non-sensitive fixtures.
- Keep fixtures small enough for meaningful review unless scale is the subject of the test.
- Document generated fixtures and make their regeneration deterministic.
- Test both directions where the documented behaviour requires symmetry.
- Exercise boundary values, malformed inputs, and failure paths, not only successful examples.
- Validate representative configuration and result documents against their packaged schemas.
- Include installed-entry-point and built-distribution tests as required by the package's verification policy.
- Do not update expected outputs blindly; review semantic changes field by field.

Not every implementation, documentation, release-process, or quality requirement needs a direct automated test. Add automated coverage where it provides a reliable and maintainable verification of observable behaviour.

## Sensitive data and repository safety

- Never place real patient data, clinical identifiers, credentials, secrets, or identifying local paths in source, tests, fixtures, snapshots, logs, examples, or documentation.
- Do not use destructive repository or filesystem operations unless the user has explicitly authorized them and the exact target has been verified.
- Never overwrite unrelated user changes to make a check pass.

Refer to the package's user guide for its security and data-governance behaviour.

## Documentation

- Keep the README and user documentation accurate for the implemented version.
- Do not document planned behaviour as already available.
- Ensure complete examples validate against the corresponding packaged schema.
- Link to normative material instead of copying substantial requirements into explanatory documentation.

## Before declaring work complete

Report:

- the specified behaviours affected;
- tests added or updated and why they are sufficient;
- commands run and their results;
- schema, static, packaging, and documentation checks performed;
- checks not run and the reason;
- remaining assumptions, limitations, or follow-up work.

Do not claim completion while relevant tests, schemas, documentation, or packaging metadata are knowingly inconsistent with the implementation.
