"""Checks for the runnable, maintained user-guide examples."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from adviso_compare.application import execute_comparison
from adviso_compare.invocation import ComparisonInvocation
from tests.support.evidence import assert_run_package
from tests.support.schemas import configuration_validator, results_validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "docs" / "examples"


@pytest.mark.parametrize(
    ("example", "reference_name", "query_name", "configuration_name"),
    [
        ("automatic", "reference.csv", "query.csv", None),
        ("introductory", "reference.csv", "query.csv", "configuration.yaml"),
        ("custom", "reference.json", "query.csv", "configuration.yaml"),
    ],
)
def test_user_guide_examples_run_with_the_documented_outcome(
    tmp_path: Path,
    example: str,
    reference_name: str,
    query_name: str,
    configuration_name: str | None,
) -> None:
    """Each guide example is runnable and produces schema-valid evidence."""
    guide = (PROJECT_ROOT / "docs" / "USER_GUIDE.md").read_text(
        encoding="utf-8"
    )
    working = tmp_path / example
    if example == "introductory":
        assert configuration_name is not None
        working.mkdir()
        tutorial = guide.split(" A small custom comparison\n", 1)[1]
        tutorial = tutorial.split("\n### ", 1)[0]
        inputs = re.findall(r"```csv\n(.*?)\n```", tutorial, re.S)
        configurations = re.findall(r"```yaml\n(.*?)\n```", tutorial, re.S)
        assert len(inputs) == 2
        assert len(configurations) == 1
        for name, content in zip(
            (reference_name, query_name, configuration_name),
            (*inputs, configurations[0]),
        ):
            (working / name).write_text(content + "\n", encoding="utf-8")
    else:
        shutil.copytree(EXAMPLES / example, working)
    configuration = (
        working / configuration_name if configuration_name is not None else None
    )
    if configuration is not None:
        document = yaml.safe_load(configuration.read_text(encoding="utf-8"))
        configuration_validator().validate(document)

    outcome = execute_comparison(
        ComparisonInvocation(
            reference=working / reference_name,
            query=working / query_name,
            output=working / "evidence",
            configuration=configuration,
        )
    )
    selected = assert_run_package(working / "evidence", outcome.output)
    result = json.loads(
        (selected / "comparison-results.json").read_text(
            encoding="utf-8"
        )
    )

    results_validator().validate(result)
    saved = json.loads(
        (selected / "comparison-configuration.json").read_text(
            encoding="utf-8"
        )
    )
    if configuration is not None:
        assert saved == document
    else:
        assert saved["metadata"]["id"] == "org.adviso.automatic-strict-exact"
    assert outcome.run_status == "complete"
    assert outcome.comparison_differences == 1
    assert outcome.assessment_issues == 0
    assert outcome.exit_code == 0
    validation_section = guide.split(
        " Structural and semantic validation\n", 1
    )[1].split("\n## ", 1)[0]
    snippets = re.findall(r"```python\n(.*?)\n```", validation_section, re.S)
    assert len(snippets) == 1
    checked = subprocess.run(
        [sys.executable, "-c", snippets[0]],
        cwd=selected,
        check=True,
        capture_output=True,
        text=True,
    )
    assert checked.stdout == "Package checks passed for the saved evidence.\n"
    assert checked.stderr == ""


def test_user_guide_identifies_supported_schemas_and_maintained_examples() -> None:
    """The offline guide names its supported schemas and both example modes."""
    guide = (PROJECT_ROOT / "docs" / "USER_GUIDE.md").read_text(encoding="utf-8")

    assert "comparison-configuration-v1.0.schema.json" in guide
    assert "comparison-results-v1.0.schema.json" in guide
    assert "Automatic strict-exact mode" in guide
    assert "Runnable custom example" in guide
