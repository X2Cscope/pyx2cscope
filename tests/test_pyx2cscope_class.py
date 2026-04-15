"""Unit tests and integration tests related to the PyX2CScope class."""

import os
import warnings

import pytest

from pyx2cscope.x2cscope import X2CScope
from tests import data
from tests.utils.serial_stub import fake_serial


class TestPyX2CScope:
    """Tests related to the PyX2CScope class."""

    elf_file = os.path.join(
        os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf"
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

            # Verify the warning was raised
            assert len(w) == 2  # noqa: PLR2004
            assert issubclass(w[-1].category, Warning) is True
            assert "No interface select, setting Serial as default." in str(w[0].message)

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

            # Verify the warning was raised
            assert len(w) == 2  # noqa: PLR2004
            assert issubclass(w[-1].category, Warning) is True
            assert "No port provided, will attempt auto-detection" in str(w[-1].message)

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
            assert scope.scope_setup.sample_time_factor == 2

            scope.set_sample_time(0)
            assert scope.scope_setup.sample_time_factor == 0
        finally:
            scope.disconnect()
