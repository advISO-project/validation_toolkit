# AdvISO validation toolkit

This repository is a monorepo for independently installable AdvISO tools that
support bioinformatics validation and verification work. Repository membership
groups related software; it does not imply a shared executable, Python package,
dependency set, version, or release lifecycle.

## Tools

| Tool | Purpose | Status |
| --- | --- | --- |
| [`adviso-compare`](packages/adviso-compare/README.md) | Translate and compare structured reference and query datasets | Implemented; unreleased |

Each tool lives under `packages/` with its own packaging metadata, source,
tests, documentation, normative artefacts, and release version. `adviso-compare`
is the first tool. Additional tools will be added as peer packages as their
scope and implementation are agreed.

For development, start with the [contribution guide](CONTRIBUTING.md), then
follow the selected tool's developer guidance, linked from its README.
Repository-wide agent and code-quality guidance is in [`AGENTS.md`](AGENTS.md).
Each tool identifies its behavioural documentation and normative schemas in its
own README.
