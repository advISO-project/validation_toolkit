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
from tests.support.evidence import assert_run_package

REQUIRED_PACKAGE_MEMBERS = {
    "adviso_compare/__init__.py",
    "adviso_compare/schemas/__init__.py",
    "adviso_compare/schemas/comparison-configuration-v1.0.schema.json",
    "adviso_compare/schemas/comparison-results-v1.0.schema.json",
}

REQUIRED_DOCUMENTATION_MEMBERS = {
    "share/doc/adviso-compare/USER_GUIDE.md",
    "share/doc/adviso-compare/examples/automatic/query.csv",
    "share/doc/adviso-compare/examples/automatic/reference.csv",
    "share/doc/adviso-compare/examples/custom/configuration.yaml",
    "share/doc/adviso-compare/examples/custom/query.csv",
    "share/doc/adviso-compare/examples/custom/reference.json",
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
        record_member = next(
            member for member in wheel_members if member.endswith(".dist-info/RECORD")
        )
        assert distribution.read(record_member)
    sdist_members = _relative_sdist_members(source_distribution)

    assert metadata["Name"] == "adviso-compare"
    assert REQUIRED_PACKAGE_MEMBERS <= wheel_members
    assert all(
        any(member.endswith(path) for member in wheel_members)
        for path in REQUIRED_DOCUMENTATION_MEMBERS
    )
    assert {
        f"src/{member}" for member in REQUIRED_PACKAGE_MEMBERS
    } <= sdist_members
    assert {
        "docs/USER_GUIDE.md",
        "docs/examples/automatic/query.csv",
        "docs/examples/automatic/reference.csv",
        "docs/examples/custom/configuration.yaml",
        "docs/examples/custom/query.csv",
        "docs/examples/custom/reference.json",
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
    installed_guide = (
        environment / "share" / "doc" / "adviso-compare" / "USER_GUIDE.md"
    )
    assert installed_guide.is_file()
    assert "# AdvISO Compare user guide" in installed_guide.read_text(
        encoding="utf-8"
    )
    assert installed_guide.read_bytes() == (
        project_root / "docs" / "USER_GUIDE.md"
    ).read_bytes()

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
    automatic_package = assert_run_package(automatic_output)
    saved_automatic = json.loads(
        (automatic_package / "comparison-configuration.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved_automatic["metadata"]["id"] == (
        "org.adviso.automatic-strict-exact"
    )
    displayed = Path(automatic_output.name) / automatic_package.name
    assert f"Evidence package: {displayed}\n" in completed.stdout
    original_bytes = {
        member.name: member.read_bytes()
        for member in automatic_package.iterdir()
    }
    repeated = subprocess.run(
        completed.args,
        check=False,
        capture_output=True,
        text=True,
        env=runtime_environment,
    )
    assert repeated.returncode == 0
    assert repeated.stderr == ""
    additional = set(automatic_output.iterdir()) - {automatic_package}
    assert len(additional) == 1
    repeated_package = assert_run_package(automatic_output, additional.pop())
    displayed = Path(automatic_output.name) / repeated_package.name
    assert f"Evidence package: {displayed}\n" in repeated.stdout
    assert str(tmp_path) not in repeated.stdout
    assert {
        member.name: member.read_bytes()
        for member in automatic_package.iterdir()
    } == original_bytes

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
    custom_package = assert_run_package(custom_output)
    assert json.loads(
        (custom_package / "comparison-configuration.json").read_text(
            encoding="utf-8"
        )
    ) == minimal_configuration()
    assert (
        f"Evidence package: {Path(custom_output.name) / custom_package.name}\n"
        in incomplete.stdout
    )

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

    source_environment = tmp_path / "installed-from-source"
    venv.EnvBuilder(with_pip=True).create(source_environment)
    source_python = _installed_python(source_environment)
    subprocess.run(
        [
            str(source_python),
            "-m",
            "pip",
            "install",
            "--no-build-isolation",
            "--no-deps",
            str(source_distribution),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=runtime_environment,
    )
    source_location_check = (
        "from pathlib import Path; import adviso_compare; "
        "assert Path(adviso_compare.__file__).is_relative_to("
        f"Path({str(source_environment)!r}))"
    )
    subprocess.run(
        [str(source_python), "-c", source_location_check],
        check=True,
        capture_output=True,
        text=True,
    )
