"""Tests for the script folder and script dropdowns of the Qt GUI (issue #144).

Tests cover:
- list_scripts(): which files of a folder are listed
- ScriptingTab: script folder, shared script model, dropdown, refresh, restore of the folder
- ScriptRunControl: dropdown on the Data Views tab that shares the list of the Scripting tab
"""

import os

import pytest

# Set headless mode before importing Qt modules
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SIGNAL_TIMEOUT_MS = 5000
SCRIPT_COUNT = 3

QUICK_SCRIPT = 'print("hello from script")\n'
LOOP_SCRIPT = (
    "import time\n"
    'stop_requested = globals().get("stop_requested", lambda: False)\n'
    "while not stop_requested():\n"
    "    time.sleep(0.01)\n"
)


@pytest.fixture
def isolated_settings(monkeypatch, tmp_path):
    """Store the QSettings of the Scripting tab in a temporary ini file."""
    from PyQt5.QtCore import QSettings

    from pyx2cscope.gui.qt.tabs import scripting_tab as module

    settings_file = str(tmp_path / "settings.ini")
    monkeypatch.setattr(module, "QSettings", lambda *_args: QSettings(settings_file, QSettings.IniFormat))
    return settings_file


def _make_tab(qtbot):
    """Create a Scripting tab without connection."""
    from pyx2cscope.gui.qt.models.app_state import AppState
    from pyx2cscope.gui.qt.tabs.scripting_tab import ScriptingTab

    tab = ScriptingTab(AppState())
    qtbot.addWidget(tab)
    return tab


@pytest.fixture
def scripting_tab(qtbot, isolated_settings):
    """Create a Scripting tab with isolated settings."""
    tab = _make_tab(qtbot)
    yield tab
    worker = tab._worker
    if worker is not None and worker.isRunning():
        worker.request_stop()
        worker.wait(SIGNAL_TIMEOUT_MS)


@pytest.fixture
def control(qtbot, scripting_tab):
    """Create the Run Script control for the Scripting tab."""
    from pyx2cscope.gui.qt.tabs.scripting_tab import ScriptRunControl

    widget = ScriptRunControl(scripting_tab)
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def script_folder(tmp_path):
    """Create a folder with three scripts and files that must not be listed."""
    folder = tmp_path / "scripts"
    folder.mkdir()
    for name in ("b_script.py", "A_script.py", "c_loop.py"):
        content = LOOP_SCRIPT if name == "c_loop.py" else QUICK_SCRIPT
        (folder / name).write_text(content, encoding="utf-8")
    (folder / "__init__.py").write_text("", encoding="utf-8")
    (folder / "notes.txt").write_text("not a script", encoding="utf-8")
    (folder / "sub.py").mkdir()  # a folder named like a script
    return str(folder)


def _names(tab):
    """Return the file names shown in the script model."""
    model = tab.script_model
    return [model.item(row).text() for row in range(model.rowCount())]


class TestListScripts:
    """Tests for list_scripts()."""

    def test_lists_only_scripts_sorted(self, script_folder):
        """Test only .py files are listed, sorted case-insensitively, without dunder files."""
        from pyx2cscope.gui.qt.tabs.scripting_tab import list_scripts

        scripts = list_scripts(script_folder)

        assert [os.path.basename(p) for p in scripts] == ["A_script.py", "b_script.py", "c_loop.py"]
        assert all(os.path.isabs(p) for p in scripts)

    def test_missing_or_empty_folder(self, tmp_path):
        """Test a missing folder or no folder gives an empty list."""
        from pyx2cscope.gui.qt.tabs.scripting_tab import list_scripts

        assert list_scripts("") == []
        assert list_scripts(str(tmp_path / "missing")) == []


class TestScriptingTabFolder:
    """Tests for the script folder of the Scripting tab."""

    def test_no_folder_initially(self, scripting_tab):
        """Test there is no folder and the dropdown is disabled at start."""
        from pyx2cscope.gui.qt.tabs.scripting_tab import NO_FOLDER_TEXT

        assert scripting_tab.script_folder == ""
        assert scripting_tab.script_model.rowCount() == 0
        assert scripting_tab._script_combo.isEnabled() is False
        assert scripting_tab._script_combo.placeholderText() == NO_FOLDER_TEXT

    def test_set_folder_lists_scripts(self, scripting_tab, qtbot, script_folder):
        """Test setting the folder fills the dropdown and keeps no script loaded."""
        with qtbot.waitSignal(scripting_tab.script_folder_changed, timeout=SIGNAL_TIMEOUT_MS):
            scripting_tab.set_script_folder(script_folder)

        assert _names(scripting_tab) == ["A_script.py", "b_script.py", "c_loop.py"]
        assert scripting_tab._script_combo.isEnabled() is True
        assert scripting_tab._script_combo.currentIndex() == -1
        assert scripting_tab.script_path == ""

    def test_empty_folder_placeholder(self, scripting_tab, tmp_path):
        """Test a folder without scripts says so in the dropdown."""
        from pyx2cscope.gui.qt.tabs.scripting_tab import NO_SCRIPTS_TEXT

        scripting_tab.set_script_folder(str(tmp_path))

        assert scripting_tab._script_combo.isEnabled() is False
        assert scripting_tab._script_combo.placeholderText() == NO_SCRIPTS_TEXT

    def test_combo_selects_script(self, scripting_tab, qtbot, script_folder):
        """Test picking a script in the dropdown loads it."""
        scripting_tab.set_script_folder(script_folder)
        index = 1

        with qtbot.waitSignal(scripting_tab.script_selected, timeout=SIGNAL_TIMEOUT_MS):
            scripting_tab._script_combo.activated.emit(index)

        assert scripting_tab.script_path == os.path.join(scripting_tab.script_folder, "b_script.py")
        assert scripting_tab._edit_btn.isEnabled() is True
        assert scripting_tab._execute_btn.isEnabled() is True

    def test_set_script_switches_folder(self, scripting_tab, script_folder, tmp_path):
        """Test loading a script from another folder makes that folder the script folder."""
        scripting_tab.set_script_folder(script_folder)
        other = tmp_path / "other"
        other.mkdir()
        path = other / "elsewhere.py"
        path.write_text(QUICK_SCRIPT, encoding="utf-8")

        scripting_tab.set_script(str(path))

        assert scripting_tab.script_folder == str(other)
        assert _names(scripting_tab) == ["elsewhere.py"]
        assert scripting_tab._script_combo.currentIndex() == 0

    def test_refresh_adds_new_script(self, scripting_tab, qtbot, script_folder):
        """Test refresh_scripts lists a script created after the folder was selected."""
        scripting_tab.set_script_folder(script_folder)
        scripting_tab.set_script(os.path.join(script_folder, "b_script.py"))
        with open(os.path.join(script_folder, "0_first.py"), "w", encoding="utf-8") as f:
            f.write(QUICK_SCRIPT)

        with qtbot.waitSignal(scripting_tab.scripts_changed, timeout=SIGNAL_TIMEOUT_MS):
            scripting_tab.refresh_scripts()

        assert _names(scripting_tab)[0] == "0_first.py"
        # The loaded script stays selected after the list changed
        assert scripting_tab._script_combo.currentText() == "b_script.py"

    def test_refresh_without_change_does_not_emit(self, scripting_tab, qtbot, script_folder):
        """Test refresh_scripts keeps the model when the folder did not change."""
        scripting_tab.set_script_folder(script_folder)

        with qtbot.assertNotEmitted(scripting_tab.scripts_changed):
            scripting_tab.refresh_scripts()

    def test_folder_button_is_remembered(self, scripting_tab, qtbot, monkeypatch, script_folder):
        """Test a folder chosen with the Folder button is restored by a new tab."""
        from pyx2cscope.gui.qt.tabs import scripting_tab as module

        monkeypatch.setattr(module.QFileDialog, "getExistingDirectory", lambda *_args: script_folder)
        scripting_tab._folder_btn.click()
        assert scripting_tab.script_model.rowCount() == SCRIPT_COUNT

        new_tab = _make_tab(qtbot)
        assert new_tab.script_folder == os.path.abspath(script_folder)
        assert new_tab.script_model.rowCount() == SCRIPT_COUNT
        assert new_tab.script_path == ""


class TestRunControlDropdown:
    """Tests for the script dropdown on the Data Views tab."""

    def test_disabled_without_folder(self, control):
        """Test the dropdown is disabled and explains why without a folder."""
        assert control.combo.isEnabled() is False
        assert control.combo.toolTip() == control.NO_FOLDER_TIP

    def test_shares_model_with_scripting_tab(self, control, scripting_tab, script_folder):
        """Test the dropdown lists the scripts of the Scripting tab's folder."""
        scripting_tab.set_script_folder(script_folder)

        assert control.combo.model() is scripting_tab.script_model
        assert control.combo.count() == SCRIPT_COUNT
        assert control.combo.isEnabled() is True
        assert control.button.isEnabled() is False

    def test_pick_script_loads_it_and_enables_run(self, control, scripting_tab, qtbot, script_folder):
        """Test picking a script on the Data Views tab loads it in the Scripting tab."""
        scripting_tab.set_script_folder(script_folder)

        with qtbot.waitSignal(scripting_tab.script_selected, timeout=SIGNAL_TIMEOUT_MS):
            control.combo.activated.emit(0)

        assert os.path.basename(scripting_tab.script_path) == "A_script.py"
        assert scripting_tab._script_combo.currentIndex() == 0
        assert control.button.isEnabled() is True
        assert "A_script.py" in control.button.toolTip()

    def test_follows_selection_in_scripting_tab(self, control, scripting_tab, script_folder):
        """Test a script picked in the Scripting tab is shown in the Data Views dropdown."""
        scripting_tab.set_script_folder(script_folder)
        index = 2

        scripting_tab._script_combo.activated.emit(index)

        assert control.combo.currentIndex() == index
        assert control.combo.currentText() == "c_loop.py"

    def test_run_disabled_when_folder_has_no_scripts(self, control, scripting_tab, script_folder, tmp_path):
        """Test Run and Execute are disabled after switching to a folder without valid scripts."""
        scripting_tab.set_script(os.path.join(script_folder, "A_script.py"))
        assert control.button.isEnabled() is True
        empty = tmp_path / "empty"
        empty.mkdir()

        scripting_tab.set_script_folder(str(empty))

        assert control.combo.isEnabled() is False
        assert control.button.isEnabled() is False
        assert control.button.toolTip() == control.NO_VALID_SCRIPT_TIP
        assert scripting_tab._execute_btn.isEnabled() is False

    def test_run_disabled_when_script_not_listed(self, control, scripting_tab, tmp_path):
        """Test a loaded file that is not a listed script cannot be run."""
        path = tmp_path / "__hidden.py"
        path.write_text(QUICK_SCRIPT, encoding="utf-8")

        scripting_tab.set_script(str(path))

        assert scripting_tab.has_valid_script() is False
        assert control.button.isEnabled() is False
        assert scripting_tab._execute_btn.isEnabled() is False

    def test_run_disabled_when_script_deleted(self, control, scripting_tab, script_folder):
        """Test the Run button is disabled once the loaded script is removed from the folder."""
        path = os.path.join(script_folder, "A_script.py")
        scripting_tab.set_script(path)
        os.remove(path)

        scripting_tab.refresh_scripts()

        assert control.button.isEnabled() is False
        assert scripting_tab._execute_btn.isEnabled() is False

    def test_run_enabled_again_when_folder_restored(self, control, scripting_tab, script_folder, tmp_path):
        """Test going back to the script's folder enables Run again."""
        scripting_tab.set_script(os.path.join(script_folder, "A_script.py"))
        scripting_tab.set_script_folder(str(tmp_path))
        assert control.button.isEnabled() is False

        scripting_tab.set_script_folder(script_folder)

        assert control.button.isEnabled() is True
        assert scripting_tab._execute_btn.isEnabled() is True

    def test_dropdowns_disabled_while_running(self, control, scripting_tab, qtbot, script_folder):
        """Test the script cannot be changed while it runs, and can again afterwards."""
        scripting_tab.set_script(os.path.join(script_folder, "c_loop.py"))

        with qtbot.waitSignal(scripting_tab.script_started, timeout=SIGNAL_TIMEOUT_MS):
            control.button.click()
        assert control.combo.isEnabled() is False
        assert scripting_tab._script_combo.isEnabled() is False

        with qtbot.waitSignal(scripting_tab.script_finished, timeout=SIGNAL_TIMEOUT_MS):
            control.button.click()
        assert control.combo.isEnabled() is True
        assert scripting_tab._script_combo.isEnabled() is True
