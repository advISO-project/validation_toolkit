# Contributing to the AdvISO validation toolkit

This repository contains independently installable tools. Start by selecting
the package you intend to change under `packages/` and reading its README.
Each tool owns its dependencies, development setup, tests, documentation, and
release process. Use that tool's documented commands and runtime requirements.

The first tool is [`adviso-compare`](packages/adviso-compare/README.md).
Its [development instructions](packages/adviso-compare/CONTRIBUTING.md)
cover editable installation, testing, and building distributions.

## Where guidance belongs

| Location | Purpose |
| --- | --- |
| Repository README | Tool catalogue and repository overview. |
| This guide | Contribution workflow shared across tools. |
| `AGENTS.md` files | Applicable agent instructions and code-quality guidance. |
| Package README | Tool status, entry points, and links to developer guidance. |
| Package contribution guide, where provided | Tool-specific setup, tests, builds, and change workflow. |
| Package `docs/` | User documentation, architecture guidance, and applicable product/development records. |
| Package `tests/` | Executable verification and controlled synthetic fixtures. |

Keep tool-specific implementation and dependencies within the relevant package.
A future tool can have a different dependency set or release schedule. Shared
code or tooling should follow a concrete need agreed for the affected packages.

## Working on a change

1. Read the applicable `AGENTS.md` instructions and the selected package's
   documentation, including its behaviour specification and schemas where
   provided.
2. Run the relevant existing tests to establish a baseline.
3. For an approved behavioural change or defect fix, adapt existing tests where
   possible and add focused regression cases for uncovered behaviour. Confirm
   that a new regression fails for the expected reason before implementing it.
4. Keep the implementation scoped to the selected package. Run focused checks
   during development, then its wider tests and applicable packaging checks.
5. Update affected documentation and examples, and check their links and
   commands. The user guide describes the tool; developer setup belongs in
   developer-facing documentation.
6. Report what changed, how it was verified, and any checks or platforms that
   remain unverified. When changing shared guidance or another package, include
   the checks relevant to each affected tool.

Use synthetic, non-sensitive examples and fixtures. Detailed code-quality,
change-control, and testing guidance is in [AGENTS.md](AGENTS.md).

## Releases

Release decisions belong to each tool. Consult its current verification records
and declared support policy. A passing local suite is evidence for that
environment; report separately any outstanding platform, dependency-installation,
or independent-review checks.
