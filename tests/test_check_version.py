"""Tests for scripts/check_version.py, the version guard of the PR and release workflows.

Git and PyPI are mocked, so the tests need no network.
"""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_version.py"
EXIT_OK = 0
EXIT_ERROR = 1


@pytest.fixture
def check_version():
    """Import scripts/check_version.py as a module."""
    spec = importlib.util.spec_from_file_location("check_version", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path, check_version, monkeypatch):
    """Create a project folder with pyproject.toml and __init__.py and point the script at it."""

    def make(pyproject_version="0.7.2", init_version="0.7.2"):
        (tmp_path / "pyx2cscope").mkdir(exist_ok=True)
        (tmp_path / "pyproject.toml").write_text(
            f'[project]\nname = "pyx2cscope"\nversion = "{pyproject_version}"\n', encoding="utf-8"
        )
        (tmp_path / "pyx2cscope" / "__init__.py").write_text(
            f'"""Package.\n\nVersion: {init_version}\n"""\n__version__ = "{init_version}"\n', encoding="utf-8"
        )
        monkeypatch.setattr(check_version, "ROOT", tmp_path)

    return make


def test_repository_versions_match(check_version):
    """Test the committed pyproject.toml and __init__.py have the same version."""
    assert check_version.run_checks() == []


def test_version_order(check_version):
    """Test versions compare numerically, not as text."""
    assert check_version.version_key("0.7.10") > check_version.version_key("0.7.9")
    assert check_version.version_key("0.8.0") > check_version.version_key("0.7.1")
    assert check_version.version_key("0.7.1") == check_version.version_key("0.7.1")


def test_mismatch_between_files(check_version, project):
    """Test a version mismatch between pyproject.toml and __init__.py is reported."""
    project(pyproject_version="0.7.2", init_version="0.7.1")

    errors = check_version.run_checks()

    assert len(errors) == 1 and "update_version.py" in errors[0]


@pytest.mark.parametrize("main_version", ["0.7.2", "0.7.3"])
def test_not_higher_than_main(check_version, project, monkeypatch, main_version):
    """Test a PR into main must have a higher version than main (same or lower fails)."""
    project("0.7.2", "0.7.2")
    monkeypatch.setattr(check_version, "version_on_ref", lambda ref: main_version)

    errors = check_version.run_checks(compare_ref="origin/main")

    assert len(errors) == 1 and "not higher" in errors[0]


def test_higher_than_main(check_version, project, monkeypatch):
    """Test a bumped version passes the comparison with main."""
    project("0.7.2", "0.7.2")
    monkeypatch.setattr(check_version, "version_on_ref", lambda ref: "0.7.1")

    assert check_version.run_checks(compare_ref="origin/main") == []


def test_already_on_pypi(check_version, project, monkeypatch):
    """Test a version that is already published on PyPI fails."""
    project("0.7.1", "0.7.1")
    monkeypatch.setattr(check_version, "is_on_pypi", lambda version: True)

    errors = check_version.run_checks(check_pypi=True)

    assert len(errors) == 1 and "already published" in errors[0]


def test_not_on_pypi(check_version, project, monkeypatch):
    """Test a new version passes the PyPI check."""
    project("0.7.2", "0.7.2")
    monkeypatch.setattr(check_version, "is_on_pypi", lambda version: False)

    assert check_version.run_checks(check_pypi=True) == []


def test_pypi_unreachable_fails(check_version, project, monkeypatch, capsys):
    """Test the check fails, instead of passing silently, when PyPI cannot be reached."""
    project("0.7.2", "0.7.2")

    def unreachable(version):
        raise ValueError("Cannot reach PyPI")

    monkeypatch.setattr(check_version, "is_on_pypi", unreachable)

    assert check_version.main(["--pypi"]) == EXIT_ERROR
    assert "Cannot reach PyPI" in capsys.readouterr().out


def test_main_exit_codes(check_version, project, monkeypatch):
    """Test main() returns 0 when the checks pass and 1 when they fail."""
    project("0.7.2", "0.7.2")
    monkeypatch.setattr(check_version, "version_on_ref", lambda ref: "0.7.1")
    assert check_version.main(["--compare-ref", "origin/main"]) == EXIT_OK

    monkeypatch.setattr(check_version, "version_on_ref", lambda ref: "0.7.2")
    assert check_version.main(["--compare-ref", "origin/main"]) == EXIT_ERROR
