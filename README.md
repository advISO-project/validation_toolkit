# AdvISO validation toolkit

This repository is a monorepo for independently installable AdvISO tools that
support bioinformatics validation and verification work. Repository membership
groups related software; it does not imply a shared executable, Python package,
dependency set, version, or release lifecycle.

## Tools

| Tool | Purpose | Status |
| --- | --- | --- |
| [`adviso-compare`](packages/adviso-compare/README.md) | Translate and compare structured reference and query datasets | Version 1 specified; implementation not yet started |

Each tool lives under `packages/` with its own packaging metadata, source,
tests, documentation, normative artefacts, and release version. A future
dataset-oriented tool can be added as a peer package without adding unrelated
commands or dependencies to `adviso-compare`.

Repository-wide contribution and code-quality guidance is in
[`AGENTS.md`](AGENTS.md). Product behaviour is defined within each tool's own
specification and schemas.
