"""Built-distribution and installed-product checks."""

from __future__ import annotations

import json
import os
import site
import subprocess
import sys
import tarfile
import venv
import zipfile
from email.parser import BytesParser
from pathlib import Path

from tests.support.documents import minimal_configuration

REQUIRED_PACKAGE_MEMBERS = {
    "adviso_compare/__init__.py",
    "adviso_compare/schemas/__init__.py",
    "adviso_compare/schemas/comparison-configuration-v1.0.schema.json",
    "adviso_compare/schemas/comparison-results-v1.0.schema.json",
}


def _relative_sdist_members(archive: Path) -> set[str]:
    """Return source-distribution members without its generated root directory."""
    with tarfile.open(archive, mode="r:gz") as distribution:
        members = {member.name for member in distribution.getmembers()}

    roots = {member.partition("/")[0] for member in members}
    assert len(roots) == 1
    root = roots.pop()
    return {
        member.removeprefix(f"{root}/")
        for member in members
        if member != root
    }


def _installed_python(environment: Path) -> Path:
    """Return the Python executable created by ``venv`` on this platform."""
    executable = "python.exe" if sys.platform == "win32" else "python"
    return environment / ("Scripts" if sys.platform == "win32" else "bin") / executable


def _installed_executable(environment: Path) -> Path:
    """Return the installed AdvISO Compare command on this platform."""
    executable = (
        "adviso-compare.exe" if sys.platform == "win32" else "adviso-compare"
    )
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    return environment / scripts / executable


def test_distributions_and_installed_executable_cover_the_product_path(
    tmp_path: Path,
) -> None:
    """Built artefacts carry resources and support installed command execution."""
    project_root = Path(__file__).resolve().parents[1]
    output = tmp_path / "dist"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--outdir",
            str(output),
            str(project_root),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    wheel = next(output.glob("*.whl"))
    source_distribution = next(output.glob("*.tar.gz"))

    with zipfile.ZipFile(wheel) as distribution:
        wheel_members = set(distribution.namelist())
        metadata_member = next(
            member
            for member in wheel_members
            if member.endswith(".dist-info/METADATA")
        )
        metadata = BytesParser().parsebytes(distribution.read(metadata_member))
    sdist_members = _relative_sdist_members(source_distribution)

    assert metadata["Name"] == "adviso-compare"
    assert REQUIRED_PACKAGE_MEMBERS <= wheel_members
    assert {
        f"src/{member}" for member in REQUIRED_PACKAGE_MEMBERS
    } <= sdist_members

    environment = tmp_path / "installed"
    venv.EnvBuilder(with_pip=True).create(environment)
    installed_python = _installed_python(environment)
    subprocess.run(
        [
            str(installed_python),
            "-m",
            "pip",
            "install",
            "--no-deps",
            str(wheel),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    resource_check = (
        "import json; "
        "from importlib.resources import files; "
        "root = files('adviso_compare.schemas'); "
        "names = ['comparison-configuration-v1.0.schema.json', "
        "'comparison-results-v1.0.schema.json']; "
        "assert all(json.loads(root.joinpath(name).read_text(encoding='utf-8')) "
        "for name in names)"
    )
    subprocess.run(
        [str(installed_python), "-c", resource_check],
        check=True,
        capture_output=True,
        text=True,
    )

    executable = _installed_executable(environment)
    runtime_environment = os.environ.copy()
    runtime_environment["PYTHONPATH"] = os.pathsep.join(site.getsitepackages())
    installed_location_check = (
        "from pathlib import Path; import adviso_compare; "
        "assert Path(adviso_compare.__file__).is_relative_to("
        f"Path({str(environment)!r}))"
    )
    subprocess.run(
        [str(installed_python), "-c", installed_location_check],
        check=True,
        capture_output=True,
        text=True,
        env=runtime_environment,
    )
    automatic = tmp_path / "automatic"
    automatic.mkdir()
    automatic_reference = automatic / "reference.json"
    automatic_query = automatic / "query.json"
    automatic_output = automatic / "evidence"
    automatic_reference.write_text(
        '[{"record_id":"S1","result":1}]',
        encoding="utf-8",
    )
    automatic_query.write_text(
        '[{"record_id":"S1","result":2}]',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            str(executable),
            "--reference",
            str(automatic_reference),
            "--query",
            str(automatic_query),
            "--output",
            str(automatic_output),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=runtime_environment,
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert "Run status: complete\n" in completed.stdout
    assert str(tmp_path) not in completed.stdout
    assert sorted(path.name for path in automatic_output.iterdir()) == [
        "comparison-report.html",
        "comparison-results.json",
    ]

    custom = tmp_path / "custom"
    custom.mkdir()
    custom_reference = custom / "reference.json"
    custom_query = custom / "query.json"
    custom_configuration = custom / "configuration.yaml"
    custom_output = custom / "evidence"
    custom_reference.write_text(
        '[{"reference_id":"S1","expected_value":1}]',
        encoding="utf-8",
    )
    custom_query.write_text('[{"query_id":"S1"}]', encoding="utf-8")
    custom_configuration.write_text(
        json.dumps(minimal_configuration()),
        encoding="utf-8",
    )
    incomplete = subprocess.run(
        [
            str(executable),
            "--reference",
            str(custom_reference),
            "--query",
            str(custom_query),
            "--output",
            str(custom_output),
            "--configuration",
            str(custom_configuration),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=runtime_environment,
    )
    assert incomplete.returncode == 1
    assert incomplete.stderr == ""
    assert "Run status: incomplete\n" in incomplete.stdout
    assert str(tmp_path) not in incomplete.stdout
    assert sorted(path.name for path in custom_output.iterdir()) == [
        "comparison-report.html",
        "comparison-results.json",
    ]

    failed_output = tmp_path / "failed-evidence"
    failed = subprocess.run(
        [
            str(executable),
            "--reference",
            str(tmp_path / "missing.json"),
            "--query",
            str(automatic_query),
            "--output",
            str(failed_output),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=runtime_environment,
    )
    assert failed.returncode == 2
    assert failed.stdout == ""
    assert failed.stderr == (
        "ERROR [input.unreadable]: reference input could not be read\n"
    )
    assert not failed_output.exists()
