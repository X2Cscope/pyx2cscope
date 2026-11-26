"""Tests for X2CScope.reboot() and the Reboot Device button of the Qt GUI."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pyx2cscope.x2cscope import RebootResult, X2CScope, _legacy_reboot_error_id
from tests import data
from tests.utils.lnet_frames import lnet_response
from tests.utils.serial_stub import fake_serial

elf_file_16 = os.path.join(os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf")

SERVICE_REBOOT = 0x19
ERROR_FORMAT = 0x14
ERROR_NOT_AVAILABLE = 0x21
ERROR_INVALID_DSP_STATE = 0x22


class DeviceError(Exception):
    """Stand-in for mchplnet's LNetDeviceError (not available in every mchplnet version)."""

    def __init__(self, error_id):
        """Store the device error ID like LNetDeviceError does."""
        super().__init__(f"device error 0x{error_id:02X}")
        self.error_id = error_id


@pytest.fixture
def scope(mocker):
    """X2CScope on a fake serial port."""
    fake_serial(mocker, 16)
    return X2CScope(elf_file=elf_file_16, port="COM11")


@pytest.mark.parametrize(
    ("reboot_device", "expected"),
    [
        ({"return_value": None}, RebootResult.SUCCESS),  # no answer: the device restarts
        ({"side_effect": TimeoutError("no answer")}, RebootResult.SUCCESS),  # older mchplnet
        ({"side_effect": DeviceError(ERROR_NOT_AVAILABLE)}, RebootResult.NOT_IMPLEMENTED),
        ({"side_effect": DeviceError(ERROR_INVALID_DSP_STATE)}, RebootResult.REFUSED),
        ({"side_effect": DeviceError(ERROR_FORMAT)}, RebootResult.FAILED),
        ({"side_effect": ConnectionError("port closed")}, RebootResult.FAILED),
        # older mchplnet returns the raw response frame instead of raising
        ({"return_value": lnet_response(SERVICE_REBOOT, error_id=ERROR_NOT_AVAILABLE)}, RebootResult.NOT_IMPLEMENTED),
        ({"return_value": lnet_response(SERVICE_REBOOT, error_id=ERROR_INVALID_DSP_STATE)}, RebootResult.REFUSED),
        ({"return_value": lnet_response(0x02, error_id=0x00)}, RebootResult.FAILED),  # not a Reboot response
    ],
)
def test_reboot_result(scope, mocker, reboot_device, expected):
    """reboot() maps the outcome of the Reboot request to a RebootResult."""
    mock = mocker.patch.object(scope.lnet, "reboot_device", **reboot_device)
    assert scope.reboot() is expected
    mock.assert_called_once_with()


def test_reboot_with_mchplnet_device_error(scope, mocker):
    """reboot() understands mchplnet's own LNetDeviceError, where available."""
    errors = pytest.importorskip("mchplnet.errors")
    mocker.patch.object(
        scope.lnet, "reboot_device", side_effect=errors.LNetDeviceError(SERVICE_REBOOT, ERROR_NOT_AVAILABLE)
    )
    assert scope.reboot() is RebootResult.NOT_IMPLEMENTED


def test_legacy_reboot_error_id_skips_fill_bytes():
    """The raw frame 55 02 00 01 19 21 <crc> carries a fill byte after SIZE 0x02."""
    frame = lnet_response(SERVICE_REBOOT, error_id=ERROR_NOT_AVAILABLE)
    assert frame[:6] == bytearray([0x55, 0x02, 0x00, 0x01, SERVICE_REBOOT, ERROR_NOT_AVAILABLE])
    assert _legacy_reboot_error_id(frame) == ERROR_NOT_AVAILABLE
    assert _legacy_reboot_error_id(b"\x55\x02") is None


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
        """AppState.reboot_device() forwards to X2CScope.reboot() and handles no connection."""
        from pyx2cscope.gui.qt.models.app_state import AppState

        app_state = AppState()
        assert app_state.reboot_device() is RebootResult.FAILED

        x2c = mocker.MagicMock()
        x2c.list_variables.return_value = []
        x2c.reboot.return_value = RebootResult.REFUSED
        app_state.set_x2cscope(x2c)
        assert app_state.reboot_device() is RebootResult.REFUSED

        x2c.reboot.side_effect = RuntimeError("boom")
        assert app_state.reboot_device() is RebootResult.FAILED

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
        ("result", "box", "text"),
        [
            (RebootResult.SUCCESS, "information", "Reboot successful"),
            (RebootResult.NOT_IMPLEMENTED, "warning", "Reboot not implemented"),
            (RebootResult.REFUSED, "warning", "Reboot failed"),
            (RebootResult.FAILED, "critical", "Reboot failed"),
        ],
    )
    def test_popup_shows_result(self, window, mocker, result, box, text):
        """The result of the reboot is shown in a message box; on success the GUI disconnects."""
        win, message_box = window
        reboot = mocker.patch.object(win._app_state, "reboot_device", return_value=result)
        disconnect = mocker.patch.object(win._connection_manager, "disconnect")

        win._on_reboot_requested()

        reboot.assert_called_once_with()
        popup = getattr(message_box, box)
        popup.assert_called_once()
        assert text in popup.call_args.args[2]
        assert disconnect.called == (result is RebootResult.SUCCESS)

    def test_cancel_does_not_reboot(self, window, mocker):
        """Answering No in the confirmation does not send the request."""
        win, message_box = window
        message_box.question.return_value = message_box.No
        reboot = mocker.patch.object(win._app_state, "reboot_device")

        win._on_reboot_requested()

        reboot.assert_not_called()
