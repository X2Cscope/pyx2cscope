"""Tests for X2CScope.reboot() and the Reboot Device button of the Qt GUI.

The Reboot request itself is handled and tested in mchplnet (LNet.reboot_device()).
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pyx2cscope.x2cscope import ServiceResult, X2CScope
from tests import data
from tests.utils.serial_stub import fake_serial

elf_file_16 = os.path.join(os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf")

REBOOTING = ServiceResult(0, "No error")
NOT_SUPPORTED = ServiceResult(0x21, "Service not available")


@pytest.fixture
def scope(mocker):
    """X2CScope on a fake serial port."""
    fake_serial(mocker, 16)
    return X2CScope(elf_file=elf_file_16, port="COM11")


@pytest.mark.parametrize("result", [REBOOTING, NOT_SUPPORTED])
def test_reboot_returns_mchplnet_result(scope, mocker, result):
    """reboot() returns the (code, text) result of mchplnet unchanged."""
    mock = mocker.patch.object(scope.lnet, "reboot_device", return_value=result)
    code, text = scope.reboot()
    assert (code, text) == result
    mock.assert_called_once_with()


def test_reboot_raises_mchplnet_errors(scope, mocker):
    """Errors that are not a device answer, e.g. a closed port, are raised."""
    mocker.patch.object(scope.lnet, "reboot_device", side_effect=ConnectionError("port closed"))
    with pytest.raises(ConnectionError):
        scope.reboot()


class TestQtReboot:
    """Reboot Device button on the Setup tab."""

    def test_button_follows_connection_state(self, qtbot):
        """The button is only enabled while connected and emits reboot_requested."""
        from pyx2cscope.gui.qt.models.app_state import AppState
        from pyx2cscope.gui.qt.tabs.setup_tab import SetupTab

        tab = SetupTab(AppState())
        qtbot.addWidget(tab)
        assert not tab.reboot_btn.isEnabled()

        tab.set_connected(True)
        assert tab.reboot_btn.isEnabled()
        with qtbot.waitSignal(tab.reboot_requested, timeout=1000):
            tab.reboot_btn.click()

        tab.set_connected(False)
        assert not tab.reboot_btn.isEnabled()

    def test_app_state_reboot(self, qtbot, mocker):
        """AppState.reboot_device() forwards to X2CScope.reboot() and raises without a connection."""
        from pyx2cscope.gui.qt.models.app_state import AppState

        app_state = AppState()
        with pytest.raises(RuntimeError, match="No device connected"):
            app_state.reboot_device()

        x2c = mocker.MagicMock()
        x2c.list_variables.return_value = []
        x2c.reboot.return_value = NOT_SUPPORTED
        app_state.set_x2cscope(x2c)
        assert app_state.reboot_device() == NOT_SUPPORTED

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
        ("reboot", "box", "text"),
        [
            ({"return_value": REBOOTING}, "information", "Reboot successful"),
            ({"return_value": NOT_SUPPORTED}, "warning", "Reboot not executed: Service not available (code 0x21)"),
            ({"side_effect": ConnectionError("port closed")}, "critical", "Reboot failed: port closed"),
        ],
    )
    def test_popup_shows_result(self, window, mocker, reboot, box, text):
        """The result of the reboot is shown in a message box; on success the GUI disconnects."""
        win, message_box = window
        reboot_device = mocker.patch.object(win._app_state, "reboot_device", **reboot)
        disconnect = mocker.patch.object(win._connection_manager, "disconnect")

        win._on_reboot_requested()

        reboot_device.assert_called_once_with()
        popup = getattr(message_box, box)
        popup.assert_called_once()
        assert text in popup.call_args.args[2]
        assert disconnect.called == (box == "information")

    def test_cancel_does_not_reboot(self, window, mocker):
        """Answering No in the confirmation does not send the request."""
        win, message_box = window
        message_box.question.return_value = message_box.No
        reboot = mocker.patch.object(win._app_state, "reboot_device")

        win._on_reboot_requested()

        reboot.assert_not_called()
