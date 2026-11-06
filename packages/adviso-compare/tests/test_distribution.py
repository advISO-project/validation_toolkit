"""Baseline checks for schema resources in built distributions."""

from __future__ import annotations

import subprocess
import sys
import tarfile
import venv
import zipfile
from email.parser import BytesParser
from pathlib import Path

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


def test_built_distributions_contain_import_package_and_schemas(
    tmp_path: Path,
) -> None:
    """Both distribution formats carry the import package and normative schemas."""
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
