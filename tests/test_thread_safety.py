"""
Thread safety tests for X2CScope class.
"""

import os
import threading
import pytest

from pyx2cscope.x2cscope import X2CScope
from tests import data
from tests.utils.serial_stub import fake_serial, BIT_LENGTH_16


class TestThreadSafety:
    """Test thread safety of X2CScope class."""

    elf_file = os.path.join(
        os.path.dirname(data.__file__), "MCAF_ZSMT_dsPIC33CK.elf"
    )

    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        """Set up test environment before each test."""
        # Patch the serial interface
        fake_serial(mocker, BIT_LENGTH_16)

        # Create X2CScope instance
        self.scope = X2CScope(elf_file=self.elf_file, port="COM0")

        # Get the hardwareUiEnabled variable from the scope
        # The address 0x1000 is defined in the serial_stub.py
        self.hardware_ui_enabled = self.scope.get_variable("app.hardwareUiEnabled")

        # Set initial value
        self.hardware_ui_enabled.set_value(0)

        yield

        # Cleanup
        self.scope = None
        self.hardware_ui_enabled = None

    def read_hardware_ui_enabled(self, results, index):
        """Helper method to read hardware UI enabled status."""
        try:
            results[index] = self.hardware_ui_enabled.get_value()
        except Exception as e:
            results[index] = str(e)

    def write_hardware_ui_enabled(self, value, results, index):
        """Helper method to write hardware UI enabled status."""
        try:
            self.hardware_ui_enabled.set_value(value)
            results[index] = True
        except Exception as e:
            results[index] = str(e)

    def test_concurrent_reads(self):
        """Test concurrent reads of the same variable."""
        # Set initial value
        self.hardware_ui_enabled.set_value(1)

        # Create multiple reader threads
        num_threads = 10
        results = [None] * num_threads
        threads = []

        for i in range(num_threads):
            t = threading.Thread(
                target=self.read_hardware_ui_enabled,
                args=(results, i)
            )
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify all reads returned the correct value
        assert all(result == 1 for result in results), \
            f"All reads should return 1, but got: {results}"

    def test_concurrent_writes(self):
        """Test concurrent writes to the same variable."""
        # Create multiple writer threads
        num_threads = 5
        results = [None] * num_threads
        threads = []

        for i in range(num_threads):
            value = i % 2  # Alternate between 0 and 1
            t = threading.Thread(
                target=self.write_hardware_ui_enabled,
                args=(value, results, i)
            )
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify all writes completed successfully
        assert all(result is True for result in results), \
            f"All writes should complete successfully, but got: {results}"

        # Verify the final value is either 0 or 1 (last writer wins)
        final_value = self.hardware_ui_enabled.get_value()
        assert final_value in (0, 1), \
            f"Final value should be 0 or 1, but got: {final_value}"

    def test_concurrent_reads_and_writes(self):
        """Test concurrent reads and writes to the same variable."""
        # Set initial value
        self.hardware_ui_enabled.set_value(0)

        # Create reader and writer threads
        num_threads = 10
        read_results = [None] * num_threads
        write_results = [None] * num_threads
        threads = []

        # Create reader threads
        for i in range(num_threads // 2):
            t = threading.Thread(
                target=self.read_hardware_ui_enabled,
                args=(read_results, i)
            )
            threads.append(t)

        # Create writer threads (alternate between 0 and 1)
        for i in range(num_threads // 2):
            value = i % 2
            t = threading.Thread(
                target=self.write_hardware_ui_enabled,
                args=(value, write_results, i)
            )
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=5)  # Add timeout to prevent hanging

        # Verify all operations completed successfully
        assert all(isinstance(result, int) or result is None for result in read_results), \
            f"All reads should return an integer or None, but got: {read_results}"
        assert all(result is True for result in write_results if result is not None), \
            f"All writes should complete successfully, but got: {write_results}"

        # Get final value
        final_value = self.hardware_ui_enabled.get_value()
        assert final_value in (0, 1), \
            f"Final value should be 0 or 1, but got: {final_value}"

        # If there were any reads after the last write, they should match the final value
        # This is a best-effort check since we don't track the exact order of operations
        for result in read_results:
            if isinstance(result, int):
                assert result in (0, 1), \
                    f"Read values should be 0 or 1, but got: {result}"