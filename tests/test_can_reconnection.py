"""Tests for CAN interface reconnection bug fix.

This test suite verifies that the CAN interface can be properly disconnected
and reconnected multiple times without errors, preventing the regression of
the "PCAN Channel has not been initialized" bug.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from mchplnet.interfaces.can import LNetCan
from pyx2cscope.x2cscope import X2CScope
from tests import data

EXPECTED_BUS_CALLS_AFTER_RECONNECT = 2
RECONNECT_CYCLES = 3
EXPECTED_BUS_CALLS_AFTER_CYCLES = RECONNECT_CYCLES + 1


@pytest.fixture
def mock_can_bus():
    """Create a mock CAN bus for testing."""
    with patch('can.interface.Bus') as mock_bus_class:
        mock_bus_instance = MagicMock()
        mock_bus_instance._is_shutdown = False
        mock_bus_instance.recv = MagicMock(return_value=None)
        mock_bus_instance.send = MagicMock()
        mock_bus_instance.shutdown = MagicMock()
        mock_bus_class.return_value = mock_bus_instance
        yield mock_bus_class, mock_bus_instance


class TestCANReconnection:
    """Test CAN interface reconnection scenarios."""

    elf_file = os.path.join(
        os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf"
    )

    def test_can_interface_start_cleans_up_existing_bus(self, mock_can_bus):
        """Test that start() properly cleans up an existing bus before creating a new one."""
        mock_bus_class, mock_bus_instance = mock_can_bus

        # Create CAN interface
        can_interface = LNetCan(
            bustype="pcan_usb",
            channel=1,
            baud_rate=500000,
            id_tx=0x110,
            id_rx=0x100,
        )

        # Start the interface (first time)
        can_interface.start()
        assert mock_bus_class.call_count == 1
        assert can_interface.bus is not None

        # Start again without stopping (simulates reconnection attempt)
        can_interface.start()

        # Verify shutdown was called on the old bus
        assert mock_bus_instance.shutdown.called
        # Verify a new bus was created (total 2 calls)
        assert mock_bus_class.call_count == EXPECTED_BUS_CALLS_AFTER_RECONNECT

    def test_can_interface_stop_clears_bus_reference(self, mock_can_bus):
        """Test that stop() properly clears the bus reference."""
        mock_bus_class, mock_bus_instance = mock_can_bus

        can_interface = LNetCan(
            bustype="pcan_usb",
            channel=1,
            baud_rate=500000,
        )

        # Start and stop
        can_interface.start()
        assert can_interface.bus is not None

        can_interface.stop()

        # Verify shutdown was called and bus is None
        assert mock_bus_instance.shutdown.called
        assert can_interface.bus is None

    def test_can_interface_multiple_reconnections(self, mock_can_bus):
        """Test multiple connect-disconnect-reconnect cycles."""
        mock_bus_class, mock_bus_instance = mock_can_bus

        can_interface = LNetCan(
            bustype="pcan_usb",
            channel=1,
            baud_rate=500000,
        )

        # Perform 3 connect-disconnect cycles
        for i in range(3):
            # Start
            can_interface.start()
            assert can_interface.bus is not None
            assert mock_bus_class.call_count == i + 1

            # Stop
            can_interface.stop()
            assert can_interface.bus is None
            assert mock_bus_instance.shutdown.call_count == i + 1

        # Verify we can start again after all cycles
        can_interface.start()
        assert can_interface.bus is not None
        assert mock_bus_class.call_count == EXPECTED_BUS_CALLS_AFTER_CYCLES

    def test_can_interface_stop_handles_shutdown_error(self, mock_can_bus):
        """Test that stop() handles errors during bus shutdown gracefully."""
        mock_bus_class, mock_bus_instance = mock_can_bus

        # Make shutdown raise an exception
        mock_bus_instance.shutdown.side_effect = Exception("Shutdown error")

        can_interface = LNetCan(
            bustype="pcan_usb",
            channel=1,
            baud_rate=500000,
        )

        can_interface.start()
        assert can_interface.bus is not None

        # Stop should not raise exception even if shutdown fails
        can_interface.stop()

        # Bus should still be set to None
        assert can_interface.bus is None

    def test_x2cscope_disconnect_calls_interface_stop(self, mock_can_bus):
        """Test that X2CScope.disconnect() properly calls interface.stop()."""
        mock_bus_class, mock_bus_instance = mock_can_bus

        # Mock the read/write methods to avoid actual CAN communication
        with patch('mchplnet.interfaces.can.LNetCan.read') as mock_read, \
             patch('mchplnet.interfaces.can.LNetCan.write'):

            # Mock read to return valid LNet DeviceInfo frame
            # Frame structure (49+ bytes):
            # SYN(0x55), SIZE, NODE, SERVICE_ID, STATUS,
            # MONITOR_VER(2), APP_VER(2), PROCESSOR_ID(2),
            # MONITOR_DATE(9), MONITOR_TIME(4), APP_DATE(9), APP_TIME(4),
            # DSP_STATE(1), EVENT_TYPE(2), EVENT_ID(4), TABLE_STRUCT_ADD(4)
            device_info_frame = bytearray(
                b'\x55\x2E\x01\x11\x00'  # SYN, SIZE(46 data bytes), NODE, SERVICE_ID, STATUS
                b'\x01\x00'              # Monitor version (little-endian)
                b'\x01\x00'              # App version (little-endian)
                b'\x10\x82'              # Processor ID 0x8210 (16-bit generic dsPIC)
                b'01/01/2024'            # Monitor date (9 bytes)
                b'1200'                  # Monitor time (4 bytes)
                b'01/01/2024'            # App date (9 bytes)
                b'1200'                  # App time (4 bytes)
                b'\x01'                  # DSP state (0x01 = Application runs on target)
                b'\x00\x00'              # Event type (2 bytes)
                b'\x00\x00\x00\x00'      # Event ID (4 bytes)
                b'\x00\x00\x00\x00'      # Table struct address (4 bytes)
                b'\x00'                  # CRC
            )
            # Mock LoadParameters frame (simpler, just status response)
            load_param_frame = bytearray(b'\x55\x00\x01\x12\x00\x00')
            # Mock LoadScopeData frame
            load_scope_frame = bytearray(b'\x55\x08\x01\x13\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

            # Return different frames for each call
            mock_read.side_effect = [device_info_frame, load_param_frame, load_scope_frame]

            # Create X2CScope with CAN interface
            x2cscope = X2CScope(
                elf_file=self.elf_file,
                bustype="pcan_usb",
                channel=1,
                baud_rate=500000,
            )

            # Verify interface was started
            assert mock_bus_class.called

            # Disconnect
            x2cscope.disconnect()

            # Verify shutdown was called
            assert mock_bus_instance.shutdown.called



class TestCANInterfaceStartupCleanup:
    """Test CAN interface cleanup on startup."""

    def test_start_with_none_bus_creates_new_bus(self, mock_can_bus):
        """Test that start() creates a bus when bus is None."""
        mock_bus_class, _ = mock_can_bus

        can_interface = LNetCan(bustype="pcan_usb", channel=1)
        assert can_interface.bus is None

        can_interface.start()

        assert can_interface.bus is not None
        assert mock_bus_class.call_count == 1

    def test_start_with_existing_bus_stops_first(self, mock_can_bus):
        """Test that start() stops existing bus before creating new one."""
        mock_bus_class, mock_bus_instance = mock_can_bus

        can_interface = LNetCan(bustype="pcan_usb", channel=1)

        # First start
        can_interface.start()
        first_bus = can_interface.bus
        assert first_bus is not None

        # Second start without stopping
        can_interface.start()

        # Verify old bus was shut down
        assert mock_bus_instance.shutdown.called
        # Verify new bus was created
        assert mock_bus_class.call_count == EXPECTED_BUS_CALLS_AFTER_RECONNECT

    def test_is_open_returns_false_when_bus_is_none(self):
        """Test that is_open() returns False when bus is None."""
        can_interface = LNetCan(bustype="pcan_usb", channel=1)
        assert can_interface.bus is None
        assert can_interface.is_open() is False

    def test_is_open_returns_true_when_bus_is_active(self, mock_can_bus):
        """Test that is_open() returns True when bus is active."""
        mock_bus_class, mock_bus_instance = mock_can_bus

        can_interface = LNetCan(bustype="pcan_usb", channel=1)
        can_interface.start()

        assert can_interface.is_open() is True

    def test_is_open_returns_false_when_bus_is_shutdown(self, mock_can_bus):
        """Test that is_open() returns False when bus is shutdown."""
        mock_bus_class, mock_bus_instance = mock_can_bus

        can_interface = LNetCan(bustype="pcan_usb", channel=1)
        can_interface.start()

        # Simulate bus shutdown
        mock_bus_instance._is_shutdown = True

        assert can_interface.is_open() is False
