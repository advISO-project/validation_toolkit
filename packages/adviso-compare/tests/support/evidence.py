"""Assertions for the published evidence layout used by integration tests."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from tests.support.schemas import results_validator


def assert_run_package(parent: Path, child: Path | None = None) -> Path:
    """Check a child package's members, schema, and metadata-derived name."""
    if child is None:
        children = list(parent.iterdir())
        assert len(children) == 1
        child = children[0]
    assert child.parent == parent
    assert child.is_dir()
    assert sorted(path.name for path in child.iterdir()) == [
        "comparison-report.html",
        "comparison-results.json",
    ]
    result = json.loads(
        (child / "comparison-results.json").read_text(encoding="utf-8")
    )
    results_validator().validate(result)
    match = re.fullmatch(r"([0-9]{8}T[0-9]{6}Z)-([0-9a-f-]{36})", child.name)
    assert match is not None
    timestamp = datetime.strptime(match[1], "%Y%m%dT%H%M%SZ")
    completed_at = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert completed_at == result["run"]["completed_at"]
    assert match[2] == result["run"]["id"]
    return child
