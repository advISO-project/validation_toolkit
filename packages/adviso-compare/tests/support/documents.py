"""Deterministic synthetic documents used by schema-level tests."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Literal


JsonObject = dict[str, Any]


def minimal_configuration() -> JsonObject:
    """Return a fresh, structurally valid comparison configuration."""
    return {
        "schema_version": "1.0",
        "metadata": {
            "id": "org.example.synthetic-exact-comparison",
            "revision": "1.0.0",
        },
        "fields": {
            "record_key": ["record_id"],
            "in_scope": ["record_id", "measured_value"],
            "definitions": {
                "record_id": {
                    "source_fields": {
                        "reference": "reference_id",
                        "query": "query_id",
                    },
                    "required": {"reference": True, "query": True},
                    "logical_type": "string",
                    "null_policy": {"allowed": False, "nulls_equal": False},
                    "comparator": {"name": "typed_exact"},
                },
                "measured_value": {
                    "source_fields": {
                        "reference": "expected_value",
                        "query": "observed_value",
                    },
                    "required": {"reference": True, "query": True},
                    "logical_type": "decimal",
                    "null_policy": {"allowed": False, "nulls_equal": False},
                    "comparator": {"name": "numeric_exact"},
                },
            },
        },
    }


def minimal_configuration_bytes() -> bytes:
    """Return deterministic saved bytes for the controlled configuration."""
    document = minimal_configuration()
    definitions = document["fields"]["definitions"]
    document["fields"]["definitions"] = {
        name: definitions[name] for name in sorted(definitions)
    }
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def minimal_result(
    *, status: Literal["complete", "incomplete"] = "complete"
) -> JsonObject:
    """Return a fresh, structurally valid canonical result."""
    zero_by_code = {
        "missing_record": 0,
        "extra_record": 0,
        "missing_required_field": 0,
        "type_mismatch": 0,
        "invalid_field_value": 0,
        "null_policy_violation": 0,
        "mapping_failure": 0,
        "value_mismatch": 0,
    }
    records = {
        "reference": 0,
        "query": 0,
        "matched": 0,
        "missing": 0,
        "extra": 0,
    }
    values = {"matched": 0, "mismatched": 0, "not_assessable": 0}
    findings: list[JsonObject] = []
    phases = {
        "contract": "complete",
        "records": "complete",
        "values": "complete",
    }

    if status == "incomplete":
        records = {
            "reference": 1,
            "query": 1,
            "matched": 1,
            "missing": 0,
            "extra": 0,
        }
        values = {"matched": 0, "mismatched": 0, "not_assessable": 1}
        zero_by_code["missing_required_field"] = 1
        phases["values"] = "incomplete"
        findings = [
            {
                "id": "F000001",
                "classification": "assessment_issue",
                "code": "missing_required_field",
                "phase": "contract",
                "message": "Required query field observed_value is absent.",
                "affected_side": "query",
                "record_identity": {
                    "reference": ["sample-1"],
                    "query": ["sample-1"],
                    "canonical": ["sample-1"],
                },
                "source_locations": {
                    "reference": {"json_pointer": "/0/expected_value"},
                    "query": {"json_pointer": "/0"},
                },
                "field": "measured_value",
                "review_priority": "normal",
                "values": {
                    "reference": {"state": "present"},
                    "query": {"state": "absent"},
                },
            }
        ]

    return {
        "schema_version": "1.0",
        "run": {
            "id": "123e4567-e89b-42d3-a456-426614174000",
            "status": status,
            "completed_at": "2026-01-02T03:04:05Z",
        },
        "phases": {
            **phases,
        },
        "software": {"name": "adviso-compare", "version": "1.0.0"},
        "runtime": {
            "python": "cpython-3.10.12",
            "platform": "linux-x86_64",
            "unicode_version": "14.0.0",
        },
        "inputs": {
            "reference": {
                "basename": "reference.json",
                "format": "json",
                "encoding": "utf-8",
                "size_bytes": 2,
                "digest": {"algorithm": "sha256", "value": "0" * 64},
            },
            "query": {
                "basename": "query.json",
                "format": "json",
                "encoding": "utf-8",
                "size_bytes": 2,
                "digest": {"algorithm": "sha256", "value": "1" * 64},
            },
        },
        "record_key_fields": {
            "reference": ["reference_id"],
            "query": ["query_id"],
            "canonical": ["record_id"],
        },
        "comparison_configuration_digest": {
            "algorithm": "sha256",
            "value": sha256(minimal_configuration_bytes()).hexdigest(),
        },
        "summary": {
            "records": records,
            "values": values,
            "findings": {
                "total": len(findings),
                "by_classification": {
                    "comparison_difference": 0,
                    "assessment_issue": len(findings),
                },
                "by_code": zero_by_code,
                "by_review_priority": {
                    "low": 0,
                    "normal": len(findings),
                    "high": 0,
                    "unassigned": 0,
                },
            },
        },
        "exclusions": [],
        "findings": findings,
    }
