"""Unit tests and integration tests related to the PyX2CScope class."""

import os
import warnings

import pytest

from pyx2cscope.x2cscope import X2CScope
from tests import data
from tests.utils.serial_stub import fake_serial

LNET_SAMPLE_TIME_THIRD_SAMPLE = 2

# Warnings raised by mchplnet when X2CScope is created without interface and port
NO_INTERFACE_WARNING = "No interface select, setting Serial as default."
NO_PORT_WARNING = "No port provided, will attempt auto-detection"


def _matching(recorded, text):
    """Return the indexes of the recorded warnings whose message contains text.

    Only the expected messages are checked, so warnings from unrelated code (for example a
    ResourceWarning emitted when the garbage collector frees an object of an earlier test)
    don't break the test.
    """
    return [i for i, item in enumerate(recorded) if text in str(item.message)]


class TestPyX2CScope:
    """Tests related to the PyX2CScope class."""

    elf_file = os.path.join(
        os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf"
    )
    arm_elf_file = os.path.join(
        os.path.dirname(data.__file__), "qspin_foc_same54.elf"
    )
    dspic33a_elf_file = os.path.join(
        os.path.dirname(data.__file__), "dsPIC33ak128mc106_foc.elf"
    )

    def test_missing_elf_file_16(self, mocker):
        """Check if the corresponding exception is raised in case of wrong 16 bit elf path."""
        fake_serial(mocker, 16)
        with pytest.raises(Exception, match=r"Error loading ELF file"):
            X2CScope(elf_file="wrong_elf_file.elf", port="COM0")

    def test_missing_elf_file_32(self, mocker):
        """Check if the corresponding exception is raised in case of wrong 32 bit elf path."""
        fake_serial(mocker, 32)
        with pytest.raises(Exception, match=r"Error loading ELF file"):
            X2CScope(elf_file="wrong_elf_file.elf", port="COM0")

    def test_missing_interface(self, mocker):
        """Check class behavior in case of non define COMM interface.

        In case a COMM interface is not defined, a Serial Interface is used as default.
        """
        fake_serial(mocker, 16)
        with warnings.catch_warnings(record=True) as w:
            # Cause all warnings to always be triggered
            warnings.simplefilter("always")

            # This should now generate a warning instead of raising an exception
            scope = X2CScope(elf_file=self.elf_file)

            # Verify the warnings were raised (other warnings, e.g. ResourceWarnings
            # released by the garbage collector, are ignored)
            interface_warnings = _matching(w, NO_INTERFACE_WARNING)
            port_warnings = _matching(w, NO_PORT_WARNING)
            all_messages = [str(item.message) for item in w]
            assert len(interface_warnings) == 1, all_messages
            assert len(port_warnings) == 1, all_messages
            assert interface_warnings[0] < port_warnings[0], all_messages

            # Clean up
            scope.disconnect()

    def test_missing_com_port(self, mocker):
        """Check class behavior in case of non COM-Port initialization.

        A com-port must not be provided, in this case, AUTO detection
        is attempted but a warning is generated on the console.
        """
        fake_serial(mocker, 16)
        with warnings.catch_warnings(record=True) as w:
            # Cause all warnings to always be triggered
            warnings.simplefilter("always")

            # This should now generate a warning instead of raising an exception
            scope = X2CScope(elf_file=self.elf_file)

            # Verify the warning was raised (unrelated warnings are ignored)
            assert len(_matching(w, NO_PORT_WARNING)) == 1, [str(item.message) for item in w]

            # Clean up
            scope.disconnect()

    def test_wrong_com_port(self):
        """Check handling of a non-existent COM-PORT input."""
        with pytest.raises(Exception, match=r"could not open port '?COM0'?"):
            X2CScope(elf_file=self.elf_file, port="COM0")

    def test_set_sample_time_uses_user_facing_factor(self, mocker):
        """Check sample time values are translated from 1-based API to 0-based LNET."""
        fake_serial(mocker, 16)
        scope = X2CScope(elf_file=self.elf_file, port="COM1")
        try:
            scope.set_sample_time(1)
            assert scope.scope_setup.sample_time_factor == 0

            scope.set_sample_time(3)
            assert scope.scope_setup.sample_time_factor == LNET_SAMPLE_TIME_THIRD_SAMPLE

            scope.set_sample_time(0)
            assert scope.scope_setup.sample_time_factor == 0
        finally:
            scope.disconnect()

    def test_incompatible_elf_emits_warning(self, mocker):
        """Check mismatched ELF and target families generate a warning."""
        fake_serial(mocker, 16)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            scope = X2CScope(elf_file=self.arm_elf_file, port="COM1")
            try:
                assert any("appears incompatible" in str(w.message) for w in captured)
            finally:
                scope.disconnect()

    def test_check_compatibility(self, mocker):
        """Check the compatibility API reports a matching dsPIC ELF correctly."""
        fake_serial(mocker, 16)
        scope = X2CScope(elf_file=self.elf_file, port="COM1")
        try:
            compatibility = scope.check_compatibility()
            assert compatibility["checked"] is True
            assert compatibility["compatible"] is True
            assert compatibility["file_family"] == "dspic"
            assert compatibility["device_family"] == "dspic"
            assert compatibility["file_signature"] == "dspic"
        finally:
            scope.disconnect()

    def test_check_compatibility_detects_dspic33a_mismatch(self, mocker):
        """Check the compatibility API distinguishes dsPIC33A from generic dsPIC targets."""
        fake_serial(mocker, 16)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            scope = X2CScope(elf_file=self.dspic33a_elf_file, port="COM1")
            try:
                compatibility = scope.check_compatibility()
                assert compatibility["checked"] is True
                assert compatibility["compatible"] is False
                assert compatibility["file_signature"] == "dspic33a"
                assert compatibility["device_signature"] == "dspic"
                assert any("appears incompatible" in str(w.message) for w in captured)
            finally:
                scope.disconnect()
