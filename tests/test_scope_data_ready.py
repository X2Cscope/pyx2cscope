"""Tests for X2CScope.is_scope_data_ready() (issue #141)."""

import os
from dataclasses import replace

from pyx2cscope.x2cscope import X2CScope
from tests import data
from tests.utils.serial_stub import fake_serial

elf_file_16 = os.path.join(os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf")

# Snapshot captured on hardware: triggered capture still busy, write pointer at the end of the
# ring buffer (3-byte datasets, 1666 samples), post-trigger samples only partly written.
SCOPE_STATE_BUSY = 7
USED_LENGTH = 4998
TRIGGER_EVENT_POSITION = 1662


def _scope(mocker):
    fake_serial(mocker, 16)
    return X2CScope(elf_file=elf_file_16, port="COM11")


def _mock_load_parameters(mocker, scope, **fields):
    scope_data = replace(scope.lnet.scope_data, **fields)
    mocker.patch.object(scope.lnet, "load_parameters", return_value=scope_data)


def test_not_ready_while_busy_and_pointer_at_end(mocker):
    """A busy scope whose pointer is at the end of the buffer must not be reported as ready."""
    scope = _scope(mocker)
    _mock_load_parameters(
        mocker, scope,
        scope_state=SCOPE_STATE_BUSY,
        data_array_pointer=USED_LENGTH,
        data_array_used_length=USED_LENGTH,
        trigger_event_position=TRIGGER_EVENT_POSITION,
    )
    assert scope.is_scope_data_ready() is False


def test_not_ready_while_busy(mocker):
    """A busy scope is not ready, wherever the pointer is."""
    scope = _scope(mocker)
    _mock_load_parameters(
        mocker, scope, scope_state=SCOPE_STATE_BUSY, data_array_pointer=3, data_array_used_length=USED_LENGTH,
    )
    assert scope.is_scope_data_ready() is False


def test_ready_when_idle(mocker):
    """An idle scope (scope_state == 0) is ready."""
    scope = _scope(mocker)
    _mock_load_parameters(
        mocker, scope, scope_state=0, data_array_pointer=USED_LENGTH, data_array_used_length=USED_LENGTH,
    )
    assert scope.is_scope_data_ready() is True
