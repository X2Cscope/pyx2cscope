"""Check the package version before a release.

Used by the GitHub workflows (pull requests into ``develop`` are not checked):

- pull requests into ``main`` (``--compare-ref origin/main --pypi``): the version in
  ``pyproject.toml`` and ``pyx2cscope/__init__.py`` must match, be higher than the one on
  ``main``, and must not be on PyPI yet;
- the release workflow (``--pypi``): the version must not be on PyPI yet, so a merge without a
  version bump stops before the documentation is published.

Usage::

    python scripts/check_version.py [--compare-ref origin/main] [--pypi]

Exits with 0 when all checks pass and 1 otherwise.
"""

import argparse
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

PACKAGE_NAME = "pyx2cscope"
PYPI_URL = "https://pypi.org/pypi/{package}/{version}/json"
PYPI_TIMEOUT_S = 15
HTTP_NOT_FOUND = 404
ROOT = Path(__file__).resolve().parent.parent

_PYPROJECT_VERSION = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
_INIT_VERSION = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def parse_version(text: str, pattern: re.Pattern, source: str) -> str:
    """Return the version found in a file's text.

    Args:
        text: The file content.
        pattern: Regex with one group for the version.
        source: Name of the file, for the error message.

    Returns:
        str: The version, e.g. "0.7.1".

    Raises:
        ValueError: If no version is found.
    """
    match = pattern.search(text)
    if not match:
        raise ValueError(f"No version found in {source}")
    return match.group(1)


def version_key(version: str):
    """Return a sortable key for a version string.

    Uses packaging when it is installed, otherwise compares the numeric parts (0.7.10 > 0.7.9).

    Args:
        version: The version, e.g. "0.7.1".

    Returns:
        A value that sorts like the version.
    """
    try:
        from packaging.version import Version

        return Version(version)
    except ImportError:
        return tuple(int(part) for part in re.findall(r"\d+", version))


def version_on_ref(ref: str) -> str:
    """Return the version in pyproject.toml of a git reference, e.g. origin/main.

    Args:
        ref: The git reference.

    Returns:
        str: The version on that reference.

    Raises:
        ValueError: If the file cannot be read from git or has no version.
    """
    result = subprocess.run(
        ["git", "show", f"{ref}:pyproject.toml"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ValueError(f"Cannot read pyproject.toml from {ref}: {result.stderr.strip()}")
    return parse_version(result.stdout, _PYPROJECT_VERSION, f"{ref}:pyproject.toml")


def is_on_pypi(version: str, package: str = PACKAGE_NAME) -> bool:
    """Return True if this version of the package is already published on PyPI.

    Args:
        version: The version to look up.
        package: The package name.

    Returns:
        bool: True if PyPI has the version, False if it does not.

    Raises:
        ValueError: If PyPI cannot be reached; the check must not pass silently.
    """
    url = PYPI_URL.format(package=package, version=version)
    try:
        with urllib.request.urlopen(url, timeout=PYPI_TIMEOUT_S):
            return True
    except urllib.error.HTTPError as e:
        if e.code == HTTP_NOT_FOUND:
            return False
        raise ValueError(f"PyPI answered {e.code} for {url}") from e
    except urllib.error.URLError as e:
        raise ValueError(f"Cannot reach PyPI ({url}): {e.reason}") from e


def run_checks(compare_ref: str | None = None, check_pypi: bool = False) -> list:
    """Run the version checks.

    Args:
        compare_ref: Git reference whose version must be lower, e.g. origin/main.
        check_pypi: Also require that the version is not on PyPI yet.

    Returns:
        list: Error messages; empty when all checks pass.
    """
    errors = []
    pyproject = parse_version((ROOT / "pyproject.toml").read_text(encoding="utf-8"), _PYPROJECT_VERSION,
                              "pyproject.toml")
    init = parse_version((ROOT / PACKAGE_NAME / "__init__.py").read_text(encoding="utf-8"), _INIT_VERSION,
                         f"{PACKAGE_NAME}/__init__.py")
    print(f"Version: {pyproject} (pyproject.toml), {init} ({PACKAGE_NAME}/__init__.py)")
    if pyproject != init:
        errors.append(
            f"Version mismatch: pyproject.toml has {pyproject}, {PACKAGE_NAME}/__init__.py has {init}. "
            "Run 'python scripts/update_version.py'."
        )

    if compare_ref:
        base = version_on_ref(compare_ref)
        print(f"Version on {compare_ref}: {base}")
        if version_key(pyproject) <= version_key(base):
            errors.append(
                f"Version {pyproject} is not higher than {base} on {compare_ref}. "
                "Bump the version in pyproject.toml; pull requests for features go to develop."
            )

    if check_pypi:
        if is_on_pypi(pyproject):
            errors.append(f"Version {pyproject} is already published on PyPI. Bump the version in pyproject.toml.")
        else:
            print(f"Version {pyproject} is not on PyPI yet")
    return errors


def main(argv: list | None = None) -> int:
    """Run the checks from the command line.

    Args:
        argv: Command-line arguments without the program name.

    Returns:
        int: 0 when all checks pass, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--compare-ref", help="git reference whose version must be lower, e.g. origin/main")
    parser.add_argument("--pypi", action="store_true", help="fail if the version is already on PyPI")
    args = parser.parse_args(argv)

    try:
        errors = run_checks(args.compare_ref, args.pypi)
    except ValueError as e:
        errors = [str(e)]
    for error in errors:
        print(f"ERROR: {error}")
    if not errors:
        print("Version checks passed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
