"""Tests for showing the project name of the loaded ELF file beside the version (issue #127).

Tests cover:
- pyx2cscope.utils.get_project_name for MPLAB X, VS Code and plain file paths
- Web GUI: WebScope.project_name, /is-connected, /connect and the navbar badge
- Qt GUI: SetupTab.elf_file_changed and the main window title
"""

import json
import os
import re
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pyx2cscope.utils import get_project_name

# Set headless mode before Qt modules are imported
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HTTP_OK = 200


def _touch(path):
    """Create an empty file and its parent folders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")
    return path


class TestGetProjectName:
    """Tests for get_project_name."""

    def test_empty_path(self):
        """Test an empty path gives an empty name."""
        assert get_project_name("") == ""
        assert get_project_name(None) == ""

    def test_plain_file_name(self):
        """Test a file name without folders gives its stem."""
        assert get_project_name("motor_control.elf") == "motor_control"
        assert get_project_name("variables.yml") == "variables"

    def test_mplabx_project_folder(self, tmp_path):
        """Test an ELF inside an MPLAB X project gives the project name without .X."""
        elf = _touch(tmp_path / "my_motor.X" / "dist" / "default" / "production" / "my_motor.X.production.elf")

        assert get_project_name(str(elf)) == "my_motor"

    def test_vscode_project_file(self, tmp_path):
        """Test an ELF inside a VS Code MPLAB project gives the name of the .mplab.json file."""
        project = tmp_path / "MyProject"
        _touch(project / ".vscode" / "launch.json")
        _touch(project / ".vscode" / "MyProject.mplab.json")
        elf = _touch(project / "out" / "myproject" / "default.elf")

        assert get_project_name(str(elf)) == "MyProject"

    def test_no_project_found_gives_file_name(self, tmp_path):
        """Test the file name without extension is used when no project folder is found."""
        elf = _touch(tmp_path / "workspace" / "out" / "dspic33_demo" / "default.elf")

        assert get_project_name(str(elf)) == "default"

    def test_reference_elf_file(self, elf_file_path):
        """Test a committed reference ELF file gives its stem."""
        assert get_project_name(elf_file_path) == "mc_foc_sl_fip_dspic33ck_mclv48v300w"


class TestWebProjectName:
    """Tests for the project name in the web GUI."""

    def test_initial_project_name_empty(self, web_scope_instance):
        """Test a new WebScope has no project name."""
        assert web_scope_instance.project_name == ""

    def test_set_file_sets_project_name(self, web_scope_instance):
        """Test set_file derives the project name from the import file."""
        web_scope_instance.x2c_scope = MagicMock()

        web_scope_instance.set_file("motor_control.elf")

        assert web_scope_instance.project_name == "motor_control"

    def test_set_file_uses_source_name(self, web_scope_instance):
        """Test set_file prefers the original file name over the stored upload path."""
        web_scope_instance.x2c_scope = MagicMock()

        web_scope_instance.set_file(os.path.join("upload", "stored.elf"), source_name="motor_control.elf")

        assert web_scope_instance.project_name == "motor_control"

    def test_disconnect_clears_project_name(self, web_scope_instance):
        """Test disconnect clears the project name."""
        web_scope_instance.x2c_scope = MagicMock()
        web_scope_instance.set_file("motor_control.elf")

        web_scope_instance.disconnect()

        assert web_scope_instance.project_name == ""

    def test_is_connected_returns_project(self, flask_client, mocker):
        """Test /is-connected returns the project name."""
        from pyx2cscope.gui.web.scope import web_scope

        mocker.patch.object(web_scope, "project_name", "motor_control")

        data = json.loads(flask_client.get("/is-connected").data)

        assert data["project"] == "motor_control"

    def test_connect_returns_project(self, flask_client, mocker, elf_file_path, tmp_path):
        """Test /connect returns the project name of the uploaded ELF file."""
        mocker.patch("pyx2cscope.gui.web.scope.X2CScope", return_value=MagicMock())
        # Store the upload in a temporary folder instead of pyx2cscope/gui/web/upload
        mocker.patch("pyx2cscope.gui.web.app.web", SimpleNamespace(__file__=str(tmp_path / "web.py")))

        with open(elf_file_path, "rb") as elf_file:
            response = flask_client.post(
                "/connect",
                data={
                    "interfaceType": "SERIAL",
                    "interfaceArgument": "port",
                    "interfaceValue": "COM1",
                    "elfFile": (elf_file, "motor_control.elf"),
                },
                content_type="multipart/form-data",
            )

        assert response.status_code == HTTP_OK
        assert json.loads(response.data)["project"] == "motor_control"

    def test_navbar_shows_project(self, flask_client, mocker):
        """Test the navbar and the page title show the project name."""
        from pyx2cscope.gui.web.scope import web_scope

        mocker.patch.object(web_scope, "project_name", "motor_control")

        html = flask_client.get("/").data.decode()

        assert 'id="project-name"' in html
        assert ">motor_control</span>" in html
        assert "<title>pyX2Cscope - motor_control</title>" in html

    def test_navbar_hides_empty_project(self, flask_client):
        """Test the project badge is hidden when no ELF file is loaded."""
        html = flask_client.get("/").data.decode()

        badge = re.search(r'<span id="project-name"[^>]*>', html)
        assert "<title>pyX2Cscope</title>" in html
        assert badge and "d-none" in badge.group(0)


class TestQtProjectName:
    """Tests for the project name in the Qt GUI."""

    @pytest.fixture
    def setup_tab(self, qtbot):
        """Create a SetupTab."""
        from pyx2cscope.gui.qt.models.app_state import AppState
        from pyx2cscope.gui.qt.tabs.setup_tab import SetupTab

        tab = SetupTab(AppState())
        qtbot.addWidget(tab)
        return tab

    def test_setting_elf_path_emits_changed(self, setup_tab, qtbot):
        """Test setting the ELF path emits elf_file_changed with the path."""
        with qtbot.waitSignal(setup_tab.elf_file_changed, timeout=1000) as blocker:
            setup_tab.elf_file_path = "motor_control.elf"

        assert blocker.args == ["motor_control.elf"]

    @staticmethod
    def _title_for(elf_path):
        """Return the window title MainWindow sets for an ELF path."""
        import pyx2cscope
        from pyx2cscope.gui.qt.main_window import MainWindow

        window = SimpleNamespace(
            _setup_tab=SimpleNamespace(elf_file_path=elf_path),
            setWindowTitle=MagicMock(),
        )
        MainWindow._update_window_title(window)
        title = window.setWindowTitle.call_args.args[0]
        assert title.startswith(f"pyX2Cscope - v{pyx2cscope.__version__}")
        return title

    def test_title_without_elf(self, qtbot):
        """Test the title shows only the version when no ELF file is selected."""
        import pyx2cscope

        assert self._title_for("") == f"pyX2Cscope - v{pyx2cscope.__version__}"

    def test_title_with_elf(self, qtbot):
        """Test the title shows the project name beside the version."""
        assert self._title_for("motor_control.elf").endswith(" - motor_control")
