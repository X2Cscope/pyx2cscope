"""Integration test to check if after install, PyX2CScope outputs the expected behavior."""

import os

import pyx2cscope
from mchplnet.services.frame_device_info import DeviceInfo
from mchplnet.services.frame_load_parameter import LoadScopeData
from pyx2cscope.x2cscope import X2CScope
from tests import data
from tests.utils.serial_stub import fake_serial

elf_file_16 = os.path.join(
    os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf"
)
elf_file_32 = os.path.join(os.path.dirname(data.__file__), "qspin_foc_same54.elf")

PROCESSOR_16_BIT_LENGTH = 2
PROCESSOR_32_BIT_LENGTH = 4


def test_x2cscope_install_serial_16(mocker):
    """Using a fake serial interface with a 16 bit device, check the device_info and scope_data frames."""
    fake_serial(mocker, 16)
    pyx2cscope = X2CScope(elf_file=elf_file_16, port="COM11")
    device_info: DeviceInfo = pyx2cscope.lnet.device_info
    assert device_info.uc_width == PROCESSOR_16_BIT_LENGTH, "wrong processor bit length"
    assert (
        device_info.processor_id == "__GENERIC_MICROCHIP_DSPIC__"
    ), "unknown processor"
    scope_data: LoadScopeData = pyx2cscope.lnet.scope_data
    assert scope_data.scope_state == 0, "wrong scope state value"
    assert scope_data.data_array_size == 15000, "wrong scope data size"  # noqa: PLR2004


def test_x2cscope_install_serial_32(mocker):
    """Using a fake serial interface with a 32 bit device, check the device_info and scope_data frames."""
    fake_serial(mocker, 32)
    pyx2cscope = X2CScope(elf_file=elf_file_32, port="COM11")
    device_info: DeviceInfo = pyx2cscope.lnet.device_info
    assert device_info.uc_width == PROCESSOR_32_BIT_LENGTH, "wrong processor bit length"
    assert (
        device_info.processor_id == "__GENERIC_MICROCHIP_PIC32__"
    ), "unknown processor"
    scope_data: LoadScopeData = pyx2cscope.lnet.scope_data
    assert scope_data.scope_state == 0, "wrong scope state value"
    assert scope_data.data_array_size == 8192, "wrong scope array size"  # noqa: PLR2004


def test_x2cscope_install_script_bin():
    """Test if the script scripts/pyx2cscope executable is installed correctly."""
    result = os.popen("pyx2cscope -v").read().split(" ")[1].strip("\n")
    assert result == pyx2cscope.__version__, "x2cscope script not working"


# def test_web_x2cscope_install():
#     """Test if all dependencies are there for web x2c.

#     An instance of the server is started and a request is sent to check if pyx2cscope is connected or not.
#     The result should be False, once the serial connection hasn't started yet. We check here that the
#     server started correctly and is able to manage requests.
#     """
#     # start a new process of flask with argument new=False (do not open a new browser window)
#     app_process = Process(target=app.main, kwargs={"new":False})
#     app_process.start()
#     response = requests.get("http://localhost:5000/is-connected")
#     is_connected = json.loads(response.text)["status"]
#     assert is_connected == False, "x2cscope should be disconnected"
#     app_process.terminate()
#     app_process.join()
