"""Thread safety tests for the X2CScope class."""

import os
import random
import threading
import time

import pytest

from pyx2cscope.x2cscope import X2CScope
from tests import data
from tests.utils.serial_stub import BIT_LENGTH_16, fake_serial

# Global counter to track operation sequence
operation_sequence = []
sequence_lock = threading.Lock()

class TestX2CScopeThreadSafety:
    """Thread safety tests for X2CScope class."""

    elf_file = os.path.join(
        os.path.dirname(data.__file__), "MCAF_ZSMT_dsPIC33CK.elf"
    )

    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        """Set up test environment before each test."""
        global operation_sequence
        operation_sequence = []  # Reset operation sequence

        # Create a mock with a longer delay to increase chance of race conditions
        fake_serial(mocker, BIT_LENGTH_16)

        # Patch the serial stub to have a longer delay
        from tests.utils.serial_stub import SerialStub
        original_get_ram = SerialStub._get_ram
        original_put_ram = SerialStub._put_ram

        def patched_get_ram(self):
            with sequence_lock:
                operation_sequence.append(('get_ram_start', time.time()))
            time.sleep(0.1)  # Increased delay
            result = original_get_ram(self)
            with sequence_lock:
                operation_sequence.append(('get_ram_end', time.time()))
            return result

        def patched_put_ram(self):
            with sequence_lock:
                operation_sequence.append(('put_ram_start', time.time()))
            time.sleep(0.1)  # Increased delay
            result = original_put_ram(self)
            with sequence_lock:
                operation_sequence.append(('put_ram_end', time.time()))
            return result

        mocker.patch.object(SerialStub, '_get_ram', patched_get_ram)
        mocker.patch.object(SerialStub, '_put_ram', patched_put_ram)

        self.scope = X2CScope(elf_file=self.elf_file, port="COM0")
        self.scope.connect()

        # Test variable we'll use for thread safety testing
        self.test_var_name = "app.hardwareUiEnabled"
        self.test_var = self.scope.get_variable(self.test_var_name)
        self.test_var.set_value(0)  # Reset to known state

        # For tracking test results
        self.results = []
        self.lock = threading.Lock()

        yield

        # Cleanup
        self.scope.disconnect()

    def _read_var_thread(self, results, thread_id, num_reads=10):
        """Helper method for reading variable value from a thread."""
        for i in range(num_reads):
            try:
                # Random delay to increase chance of race conditions
                time.sleep(random.uniform(0.05, 0.1))  # Increased delay

                # Read the value
                value = self.test_var.get_value()

                with self.lock:
                    results.append(('read', thread_id, i, value, time.time()))

            except Exception as e:
                with self.lock:
                    results.append(('error', thread_id, i, str(e), time.time()))

    def _write_var_thread(self, value, results, thread_id, num_writes=10):
        """Helper method for writing variable value from a thread."""
        for i in range(num_writes):
            try:
                # Random delay to increase chance of race conditions
                time.sleep(random.uniform(0.05, 0.1))  # Increased delay

                # Write the value
                self.test_var.set_value(value)

                with self.lock:
                    results.append(('write', thread_id, i, value, time.time()))

            except Exception as e:
                with self.lock:
                    results.append(('error', thread_id, i, str(e), time.time()))

    def test_operation_sequence(self):
        """Test that operations are properly serialized with the lock in place."""
        # This test verifies that operations don't overlap when the lock is in place

        # Reset the variable and operation sequence
        self.test_var.set_value(0)
        global operation_sequence
        operation_sequence = []

        # Function to perform operations
        def perform_operations(thread_id):
            for i in range(3):  # Fewer operations to make analysis easier
                # Alternate between read and write
                if i % 2 == 0:
                    self.test_var.set_value(thread_id)
                else:
                    self.test_var.get_value()

        # Create and start multiple threads
        num_threads = 3
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=perform_operations, args=(i,))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=5.0)

        # Print operation sequence for debugging
        # print("\nOperation sequence:")
        # for op in operation_sequence:
        #     print(f"  {op}")

        # Verify that operations don't overlap (start/end pairs should alternate)
        # This is a simple check - in practice, you'd want more sophisticated analysis
        last_op = None
        for op_type, timestamp in operation_sequence:
            if last_op is None:
                last_op = op_type
                continue

            # Check that we're not seeing overlapping operations of the same type
            if op_type.endswith('_start') and last_op.endswith('_start'):
                # Found two starts in a row - this indicates overlapping operations
                assert False, f"Found overlapping operations: {last_op} followed by {op_type}"

            last_op = op_type

    def test_thread_safety_without_lock(self, mocker):
        """Verify that test_operation_sequence fails when the lock is disabled."""

        # Create a no-op context manager to replace the lock
        class NoOpLock:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        # Replace the lock with our no-op version
        self.scope.lnet._lock = NoOpLock()

        # Run the operation sequence test and expect it to fail
        with pytest.raises(AssertionError) as excinfo:
            self.test_operation_sequence()

        # Verify the failure is due to overlapping operations
        assert "overlapping operations" in str(excinfo.value)