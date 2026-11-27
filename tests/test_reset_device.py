"""Tests for X2CScope.reset_device() and the Reset Device button of the Qt GUI.

The reset request itself is handled and tested in mchplnet (LNet.reset_device()).
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pyx2cscope.x2cscope import ServiceResult, X2CScope
from tests import data
from tests.utils.serial_stub import fake_serial

elf_file_16 = os.path.join(os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf")

RESETTING = ServiceResult(0, "No error")
NOT_SUPPORTED = ServiceResult(0x21, "Service not available")


@pytest.fixture
def scope(mocker):
    """X2CScope on a fake serial port."""
    fake_serial(mocker, 16)
    return X2CScope(elf_file=elf_file_16, port="COM11")


@pytest.mark.parametrize("result", [RESETTING, NOT_SUPPORTED])
def test_reset_returns_mchplnet_result(scope, mocker, result):
    """reset_device() returns the (code, text) result of mchplnet unchanged."""
    mock = mocker.patch.object(scope.lnet, "reset_device", return_value=result)
    code, text = scope.reset_device()
    assert (code, text) == result
    mock.assert_called_once_with()


def test_reset_raises_mchplnet_errors(scope, mocker):
    """Errors that are not a device answer, e.g. a closed port, are raised."""
    mocker.patch.object(scope.lnet, "reset_device", side_effect=ConnectionError("port closed"))
    with pytest.raises(ConnectionError):
        scope.reset_device()


class TestQtReset:
    """Reset Device button on the Setup tab."""

    def test_button_follows_connection_state(self, qtbot):
        """The button is only enabled while connected and emits reset_requested."""
        from pyx2cscope.gui.qt.models.app_state import AppState
        from pyx2cscope.gui.qt.tabs.setup_tab import SetupTab

        tab = SetupTab(AppState())
        qtbot.addWidget(tab)
        assert not tab.reset_btn.isEnabled()

        tab.set_connected(True)
        assert tab.reset_btn.isEnabled()
        with qtbot.waitSignal(tab.reset_requested, timeout=1000):
            tab.reset_btn.click()

        tab.set_connected(False)
        assert not tab.reset_btn.isEnabled()

    def test_app_state_reset(self, qtbot, mocker):
        """AppState.reset_device() forwards to X2CScope.reset_device() and raises without a connection."""
        from pyx2cscope.gui.qt.models.app_state import AppState

        app_state = AppState()
        with pytest.raises(RuntimeError, match="No device connected"):
            app_state.reset_device()

        x2c = mocker.MagicMock()
        x2c.list_variables.return_value = []
        x2c.reset_device.return_value = NOT_SUPPORTED
        app_state.set_x2cscope(x2c)
        assert app_state.reset_device() == NOT_SUPPORTED

    @pytest.fixture
    def window(self, qtbot, mocker):
        """MainWindow with mocked message boxes."""
        mocker.patch("pyx2cscope.x2cscope.X2CScope")
        from pyx2cscope.gui.qt.main_window import MainWindow

        message_box = mocker.patch("pyx2cscope.gui.qt.main_window.QMessageBox")
        message_box.question.return_value = message_box.Yes
        win = MainWindow()
        qtbot.addWidget(win)
        yield win, message_box
        win.close()  # stops the DataPoller thread

    @pytest.mark.parametrize(
        ("reset", "box", "text"),
        [
            ({"return_value": RESETTING}, "information", "Reset successful"),
            ({"return_value": NOT_SUPPORTED}, "warning", "Reset not executed: Service not available (code 0x21)"),
            ({"side_effect": ConnectionError("port closed")}, "critical", "Reset failed: port closed"),
        ],
    )
    def test_popup_shows_result(self, window, mocker, reset, box, text):
        """The result of the reset is shown in a message box; on success the GUI disconnects."""
        win, message_box = window
        reset_device = mocker.patch.object(win._app_state, "reset_device", **reset)
        disconnect = mocker.patch.object(win._connection_manager, "disconnect")

        win._on_reset_requested()

        reset_device.assert_called_once_with()
        popup = getattr(message_box, box)
        popup.assert_called_once()
        assert text in popup.call_args.args[2]
        assert disconnect.called == (box == "information")

    def test_cancel_does_not_reset(self, window, mocker):
        """Answering No in the confirmation does not send the request."""
        win, message_box = window
        message_box.question.return_value = message_box.No
        reset = mocker.patch.object(win._app_state, "reset_device")

        win._on_reset_requested()

        reset.assert_not_called()
