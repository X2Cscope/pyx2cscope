"""Tests for the Dashboard tab: variable data sources and the variable bridge.

Tests run headless using QT_QPA_PLATFORM=offscreen and need no hardware.
"""

import os
import time
from unittest.mock import MagicMock

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest

from pyx2cscope.gui.qt.dashboard.variables import VariableBridge, make_source, parse_source

VALUE = 42.5
SLIDER_READ = 30
SLIDER_WRITE = 70
TIMEOUT_S = 2.0


def test_source_round_trip():
    """Variable data sources encode and decode names and the SFR flag."""
    assert make_source("motor.speed") == "$motor.speed"
    assert make_source("PORTA", sfr=True) == "$sfr:PORTA"
    assert parse_source("$motor.speed") == ("motor.speed", False)
    assert parse_source("$sfr:PORTA") == ("PORTA", True)
    assert parse_source("sine") is None
    assert parse_source("@slider") is None


def test_bridge_reads_in_background():
    """The bridge returns the values read by its thread, and 0.0 for unknown sources."""
    reader = MagicMock(return_value=VALUE)
    bridge = VariableBridge(reader)
    bridge.start(["sine", "$speed", "@other"])
    try:
        deadline = time.time() + TIMEOUT_S
        while bridge.value("$speed") != VALUE and time.time() < deadline:
            time.sleep(0.01)
        assert bridge.value("$speed") == VALUE
        assert bridge.value("$unknown") == 0.0
    finally:
        bridge.stop()
    reader.assert_called_with("speed", False)


def test_bridge_survives_reader_errors():
    """A failing reader neither stops the thread nor produces values."""
    bridge = VariableBridge(MagicMock(side_effect=RuntimeError("lost")))
    bridge.start(["$speed"])
    time.sleep(0.05)
    assert bridge.value("$speed") == 0.0
    bridge.stop()


def test_app_state_read_variable_value():
    """AppState reads variables by name, caches the variable and handles missing names."""
    from pyx2cscope.gui.qt.models.app_state import AppState

    state = AppState()
    assert state.read_variable_value("speed") is None  # not connected
    scope = MagicMock()
    scope.list_variables.return_value = ["speed"]
    var = MagicMock()
    var.get_value.return_value = [VALUE, 1]
    scope.get_variable.side_effect = lambda name, sfr=False: var if name == "speed" else None
    state.set_x2cscope(scope)
    assert state.read_variable_value("speed") == VALUE
    assert state.read_variable_value("speed") == VALUE
    assert scope.get_variable.call_count == 1
    assert state.read_variable_value("missing") is None


def test_dashboard_run_uses_variable(qtbot):
    """A gauge with a variable source shows the value of the variable in Run mode."""
    from PyQt5.QtCore import QRect

    from pyx2cscope.gui.qt.dashboard.main_window import DashboardWindow
    from pyx2cscope.gui.qt.models.app_state import AppState

    state = AppState()
    scope = MagicMock()
    scope.list_variables.return_value = ["speed"]
    scope.list_sfr.return_value = []
    scope.get_variable.return_value.get_value.return_value = VALUE
    state.set_x2cscope(scope)

    win = DashboardWindow(state)
    qtbot.addWidget(win)
    win.canvas.clear()
    frame = win.canvas.add_widget("lcd", QRect(0, 0, 100, 40), {"source": "$speed"})
    assert win.variable_names() == (["speed"], [])
    win.toggle_run(True)
    try:
        deadline = time.time() + TIMEOUT_S
        while win.bridge.value("$speed") != VALUE and time.time() < deadline:
            time.sleep(0.01)
        win._tick()
        assert frame.inner.value() == pytest.approx(VALUE)
    finally:
        win.toggle_run(False)
    assert win.confirm_close()


def test_slider_reads_and_writes_variable(qtbot):
    """A slider follows its variable and writes the variable when the user moves it."""
    from PyQt5.QtCore import QRect

    from pyx2cscope.gui.qt.dashboard.main_window import DashboardWindow
    from pyx2cscope.gui.qt.models.app_state import AppState

    state = AppState()
    scope = MagicMock()
    scope.list_variables.return_value = ["speed"]
    scope.list_sfr.return_value = []
    var = scope.get_variable.return_value
    var.get_value.return_value = SLIDER_READ
    state.set_x2cscope(scope)

    win = DashboardWindow(state)
    qtbot.addWidget(win)
    win.canvas.clear()
    frame = win.canvas.add_widget("slider", QRect(0, 0, 200, 40), {"source": "$speed"})
    win.toggle_run(True)
    try:
        deadline = time.time() + TIMEOUT_S
        while win.bridge.value("$speed") != SLIDER_READ and time.time() < deadline:
            time.sleep(0.01)
        win._tick()
        assert frame.inner.value() == SLIDER_READ
        frame.inner._slider.setValue(SLIDER_WRITE)  # the user moves the slider
        deadline = time.time() + TIMEOUT_S
        while not var.set_value.called and time.time() < deadline:
            time.sleep(0.01)
        var.set_value.assert_called_with(SLIDER_WRITE)
    finally:
        win.toggle_run(False)


@pytest.mark.parametrize("extension", ["yml", "pkl"])
def test_dashboard_variables_from_yml_pkl(mocker, tmp_path, extension):
    """The Dashboard offers the variables of an exported YML/PKL file and reads them like ELF variables."""
    from pyx2cscope.gui.qt.dashboard.main_window import DashboardWindow
    from pyx2cscope.gui.qt.models.app_state import AppState
    from pyx2cscope.variable.variable_factory import FileType
    from pyx2cscope.x2cscope import X2CScope
    from tests import data
    from tests.utils.serial_stub import fake_serial

    elf = os.path.join(os.path.dirname(data.__file__), "qspin_foc_same54.elf")
    fake_serial(mocker, 32, device_profile="arm")
    exporter = X2CScope(elf_file=elf, port="COM0")
    name = exporter.list_variables()[0]
    exported = str(tmp_path / f"vars.{extension}")
    exporter.export_variables(exported, ext=FileType.YAML if extension == "yml" else FileType.PICKLE,
                              items=[exporter.get_variable(name)])
    exporter.disconnect()

    fake_serial(mocker, 32, device_profile="arm")
    state = AppState()
    scope = X2CScope(port="COM0")
    scope.import_variables(exported)  # the same call the GUI's connection manager makes
    state.set_x2cscope(scope)
    win = DashboardWindow(state)
    assert win.variable_names()[0] == [name]
    assert state.read_variable_value(name) is not None
    state.x2cscope.disconnect()


def test_viewer_loads_dashboard_and_runs(qtbot, tmp_path):
    """The Dashboard tab loads a saved dashboard and shows the live value of its variables."""
    import json

    from PyQt5.QtCore import QRect

    from pyx2cscope.gui.qt.dashboard.main_window import DashboardWindow
    from pyx2cscope.gui.qt.dashboard.viewer import DashboardViewer
    from pyx2cscope.gui.qt.models.app_state import AppState

    state = AppState()
    scope = MagicMock()
    scope.list_variables.return_value = ["speed"]
    scope.list_sfr.return_value = []
    scope.get_variable.return_value.get_value.return_value = VALUE
    state.set_x2cscope(scope)

    creator = DashboardWindow(state)
    qtbot.addWidget(creator)
    creator.canvas.clear()
    creator.canvas.add_widget("lcd", QRect(0, 0, 100, 40), {"source": "$speed"})
    path = tmp_path / "test.dash.json"
    path.write_text(json.dumps(creator.canvas.to_dict()), encoding="utf-8")

    viewer = DashboardViewer(state)
    qtbot.addWidget(viewer)
    assert viewer.load(str(path))
    try:
        deadline = time.time() + TIMEOUT_S
        while viewer.bridge.value("$speed") != VALUE and time.time() < deadline:
            time.sleep(0.01)
        viewer._tick()
        assert viewer.canvas.frames[0].inner.value() == pytest.approx(VALUE)
    finally:
        viewer.shutdown()
