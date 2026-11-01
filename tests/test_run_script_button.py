"""Tests for the Run Script button on the Data Views tab (issue #132).

Tests cover:
- The ScriptingTab API used by the button (set_script, script_path, is_running, run/stop)
- ScriptRunControl: disabled without script, Run/Stop text, status after the run
"""

import os

import pytest

# Set headless mode before importing Qt modules
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SIGNAL_TIMEOUT_MS = 5000
EXIT_CODE_ERROR = 3

QUICK_SCRIPT = 'print("hello from script")\n'
FAILING_SCRIPT = f"import sys\nsys.exit({EXIT_CODE_ERROR})\n"
LOOP_SCRIPT = (
    "import time\n"
    'stop_requested = globals().get("stop_requested", lambda: False)\n'
    "while not stop_requested():\n"
    "    time.sleep(0.01)\n"
)


@pytest.fixture
def scripting_tab(qtbot):
    """Create a Scripting tab without connection."""
    from pyx2cscope.gui.qt.models.app_state import AppState
    from pyx2cscope.gui.qt.tabs.scripting_tab import ScriptingTab

    tab = ScriptingTab(AppState())
    qtbot.addWidget(tab)
    yield tab
    # Make sure no worker thread outlives the test
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


def _write_script(tmp_path, content, name="script.py"):
    """Write a script file and return its path."""
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


class TestScriptingTabApi:
    """Tests for the ScriptingTab methods used by the button."""

    def test_no_script_initially(self, scripting_tab):
        """Test no script is loaded and nothing runs at start."""
        assert scripting_tab.script_path == ""
        assert scripting_tab.is_running() is False

    def test_set_script_emits_selected(self, scripting_tab, qtbot, tmp_path):
        """Test set_script loads the script and emits script_selected."""
        path = _write_script(tmp_path, QUICK_SCRIPT)

        with qtbot.waitSignal(scripting_tab.script_selected, timeout=SIGNAL_TIMEOUT_MS) as blocker:
            scripting_tab.set_script(path)

        assert blocker.args == [path]
        assert scripting_tab.script_path == path

    def test_run_script(self, scripting_tab, qtbot, tmp_path):
        """Test run_script runs the loaded script to completion."""
        scripting_tab.set_script(_write_script(tmp_path, QUICK_SCRIPT))

        with qtbot.waitSignal(scripting_tab.script_finished, timeout=SIGNAL_TIMEOUT_MS) as blocker:
            scripting_tab.run_script()

        assert blocker.args == [0]
        assert scripting_tab.is_running() is False


class TestScriptRunControl:
    """Tests for the Run/Stop control on the Data Views tab."""

    def test_disabled_without_script(self, control):
        """Test the button is disabled and explains why when no script is loaded."""
        assert control.button.isEnabled() is False
        assert control.button.text() == control.RUN_TEXT
        assert control.button.toolTip() == control.NO_SCRIPT_TIP

    def test_enabled_after_loading_script(self, control, scripting_tab, tmp_path):
        """Test the button is enabled once a script is loaded in the Scripting tab."""
        scripting_tab.set_script(_write_script(tmp_path, QUICK_SCRIPT, name="my_test.py"))

        assert control.button.isEnabled() is True
        assert control.button.text() == control.RUN_TEXT
        assert "my_test.py" in control.button.toolTip()

    def test_click_runs_script(self, control, scripting_tab, qtbot, tmp_path):
        """Test clicking the button runs the script and shows Completed."""
        scripting_tab.set_script(_write_script(tmp_path, QUICK_SCRIPT))

        with qtbot.waitSignal(scripting_tab.script_finished, timeout=SIGNAL_TIMEOUT_MS):
            control.button.click()

        assert control.status_text == "Completed"
        assert control.button.text() == control.RUN_TEXT

    def test_failed_script_shows_exit_code(self, control, scripting_tab, qtbot, tmp_path):
        """Test a script ending with an error shows its exit code."""
        scripting_tab.set_script(_write_script(tmp_path, FAILING_SCRIPT))

        with qtbot.waitSignal(scripting_tab.script_finished, timeout=SIGNAL_TIMEOUT_MS):
            control.button.click()

        assert f"code {EXIT_CODE_ERROR}" in control.status_text

    def test_click_while_running_stops_script(self, control, scripting_tab, qtbot, tmp_path):
        """Test the button becomes Stop while running and a click stops the script."""
        scripting_tab.set_script(_write_script(tmp_path, LOOP_SCRIPT))

        with qtbot.waitSignal(scripting_tab.script_started, timeout=SIGNAL_TIMEOUT_MS):
            control.button.click()
        assert control.button.text() == control.STOP_TEXT
        assert control.status_text == "Running..."

        with qtbot.waitSignal(scripting_tab.script_finished, timeout=SIGNAL_TIMEOUT_MS) as blocker:
            control.button.click()

        assert blocker.args == [0]
        assert control.button.text() == control.RUN_TEXT
        assert control.status_text == "Completed"

    def test_execute_in_scripting_tab_updates_button(self, control, scripting_tab, qtbot, tmp_path):
        """Test running from the Scripting tab's Execute button also updates the control."""
        scripting_tab.set_script(_write_script(tmp_path, LOOP_SCRIPT))

        with qtbot.waitSignal(scripting_tab.script_started, timeout=SIGNAL_TIMEOUT_MS):
            scripting_tab._execute_btn.click()
        assert control.button.text() == control.STOP_TEXT

        with qtbot.waitSignal(scripting_tab.script_finished, timeout=SIGNAL_TIMEOUT_MS):
            scripting_tab._stop_btn.click()
        assert control.button.text() == control.RUN_TEXT
