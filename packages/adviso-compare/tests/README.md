# Version 1 test conventions

Tests use descriptive behavioural names and assertions that remain meaningful
without the development specification. Test modules, names, markers, fixtures,
and snapshots do not embed specification requirement identifiers or acceptance
scenario identifiers. During development, any formal traceability is maintained
in the specification and review records as a one-way reference to the tests.

Give parameterized cases descriptive IDs when their inputs include complex
objects, mutations, or several expected values. Name the condition or boundary
being tested so a CI failure is understandable without decoding a parameter
dump. Simple scalar parameters such as `csv` or `complete` can keep their
default IDs. Keep related rule variants in one table; use separate tests when
different behaviours need substantially different setup or assertions. Small
local helpers can share mechanical setup while leaving inputs and expectations
visible in each test.

Reusable synthetic documents are built in `tests/support/documents.py`. Builders
return new objects on every call so tests can modify a document without leaking
state into another test. Fixed values are intentional: generated fixtures must
be deterministic and reviewable. A future generated on-disk fixture must record
its generator and regeneration command alongside the fixture.

Schema loading and validator construction live in `tests/support/schemas.py`.
Structural validators load each document's packaged schema independently and
enable JSON Schema format assertion.
