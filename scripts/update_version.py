"""Script to synchronize version between pyproject.toml and __init__.py."""
import re
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def update_version():
    """Update version in __init__.py to match pyproject.toml."""
    root = get_project_root()
    pyproject_path = root / "pyproject.toml"
    init_path = root / "pyx2cscope" / "__init__.py"

    # Read version from pyproject.toml
    pyproject_content = pyproject_path.read_text(encoding="utf-8")
    version_match = re.search(r'version\s*=\s*"([^"]+)"', pyproject_content)
    if not version_match:
        raise ValueError("Could not find version in pyproject.toml")
    version = version_match.group(1)

    # Update __init__.py
    init_content = init_path.read_text(encoding="utf-8")

    # Update version in docstring
    init_content = re.sub(
        r'Version:\s*\d+\.\d+\.\d+',
        f'Version: {version}',
        init_content
    )

    # Update __version__ variable
    init_content = re.sub(
        r'__version__\s*=\s*["\'].+["\']',
        f'__version__ = "{version}"',
        init_content
    )

    init_path.write_text(init_content, encoding="utf-8")
    print(f"Updated version to {version} in {init_path}")


if __name__ == "__main__":
    update_version()