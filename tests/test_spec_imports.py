"""Test that all hiddenimports declared in PyInstaller spec files are importable."""

import ast
import importlib
import platform
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
WIN_SPEC = REPO_ROOT / "pyx2cscope_win.spec"
LINUX_SPEC = REPO_ROOT / "pyx2cscope_linux.spec"


def _extract_hiddenimports(spec_path: Path) -> list[str]:
    """Parse a .spec file and extract the hiddenimports list."""
    source = spec_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "hiddenimports" and isinstance(keyword.value, ast.List):
                    return [elt.s for elt in keyword.value.elts if isinstance(elt, ast.Constant)]
    return []


def _check_imports(imports: list[str]) -> list[str]:
    """Return list of modules that cannot be imported."""
    missing = []
    for module in imports:
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(module)
    return missing


def test_win_spec_hiddenimports():
    """All hiddenimports in pyx2cscope_win.spec must be importable on Windows."""
    if sys.platform != "win32":
        import pytest
        pytest.skip("Windows spec only tested on Windows")
    imports = _extract_hiddenimports(WIN_SPEC)
    assert imports, f"No hiddenimports found in {WIN_SPEC}"
    missing = _check_imports(imports)
    assert not missing, f"Missing hiddenimports in pyx2cscope_win.spec: {', '.join(missing)}"


def test_linux_spec_hiddenimports():
    """All hiddenimports in pyx2cscope_linux.spec must be importable on Linux."""
    if sys.platform != "linux":
        import pytest
        pytest.skip("Linux spec only tested on Linux")
    imports = _extract_hiddenimports(LINUX_SPEC)
    assert imports, f"No hiddenimports found in {LINUX_SPEC}"
    missing = _check_imports(imports)
    assert not missing, f"Missing hiddenimports in pyx2cscope_linux.spec: {', '.join(missing)}"


def test_spec_hiddenimports_cross_platform():
    """Common hiddenimports (non-OS-specific) must be importable on any platform."""
    # Modules expected on all platforms
    common = [
        "engineio.async_drivers.threading",
        "engineio.async_server",
        "engineio.async_socket",
        "can",
        "can.interfaces",
        "can.interfaces.pcan",
        "can.interfaces.kvaser",
        "can.interfaces.vector",
        "can.interfaces.virtual",
        "serial",
    ]
    missing = _check_imports(common)
    assert not missing, f"Missing common hiddenimports: {', '.join(missing)}"
