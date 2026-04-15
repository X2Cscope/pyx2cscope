"""Centralized application state management.

This module provides thread-safe state management for the generic GUI,
inspired by the WebScope pattern from the web GUI.
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QMutex, QObject, pyqtSignal

from pyx2cscope.x2cscope import TriggerConfig, X2CScope


@dataclass
class WatchVariable:
    """Represents a watch variable configuration."""

    name: str = ""
    value: float = 0.0
    scaling: float = 1.0
    offset: float = 0.0
    unit: str = ""
    live: bool = False
    plot_enabled: bool = False
    sfr: bool = False  # True when the variable is a Special Function Register
    _var_ref: Any = field(default=None, repr=False)  # Cached x2cscope variable reference

    @property
    def scaled_value(self) -> float:
        """Calculate the scaled value."""
        return (self.value * self.scaling) + self.offset

    @property
    def var_ref(self):
        """Get the cached x2cscope variable reference."""
        return self._var_ref

    @var_ref.setter
    def var_ref(self, value):
        """Set the cached x2cscope variable reference."""
        self._var_ref = value


@dataclass
class ScopeChannel:
    """Represents a scope channel configuration."""

    name: str = ""
    trigger: bool = False
    gain: float = 1.0
    visible: bool = True
    sfr: bool = False  # True when the variable is a Special Function Register


@dataclass
class TriggerSettings:
    """Trigger configuration settings."""

    mode: str = "Auto"  # "Auto" or "Triggered"
    edge: str = "Rising"  # "Rising" or "Falling"
    level: float = 0.0
    delay: int = 0
    variable: Optional[str] = None


@dataclass
class DeviceInfo:
    """Device information."""

    processor_id: str = ""
    uc_width: str = ""
    date: str = ""
    time: str = ""
    app_ver: str = ""
    dsp_state: str = ""


class AppState(QObject):
    """Centralized application state management.

    Provides thread-safe access to all application state including:
    - Connection status and device info
    - Watch variables (Tab1 and Tab3)
    - Scope channels and trigger settings (Tab2)
    - Plot data accumulation

    Similar to WebScope in the web GUI, this class uses a mutex
    to ensure thread-safe operations.
    """

    # Signals for state changes
    connection_changed = pyqtSignal(bool)
    device_info_updated = pyqtSignal(dict)
    variable_list_updated = pyqtSignal(list)

    MAX_WATCH_VARS = 5
    MAX_SCOPE_CHANNELS = 8
    PLOT_DATA_MAXLEN = 250

    def __init__(self, parent=None):
        """Initialize the application state."""
        super().__init__(parent)
        self._mutex = QMutex()
        self._x2cscope: Optional[X2CScope] = None

        # Connection state
        self._port: str = ""
        self._baud_rate: int = 115200
        self._elf_file: str = ""
        self._connected: bool = False

        # Device info
        self._device_info = DeviceInfo()

        # Variable list cache
        self._variable_list: List[str] = []

        # Watch variables (Tab1 - WatchPlot)
        self._watch_vars: List[WatchVariable] = [
            WatchVariable() for _ in range(self.MAX_WATCH_VARS)
        ]

        # Scope channels (Tab2 - ScopeView)
        self._scope_channels: List[ScopeChannel] = [
            ScopeChannel() for _ in range(self.MAX_SCOPE_CHANNELS)
        ]

        # Trigger settings
        self._trigger_settings = TriggerSettings()

        # Scope state
        self._scope_active: bool = False
        self._scope_single_shot: bool = False
        self._sample_time_factor: int = 1
        self._scope_sample_time_us: int = 50
        self._real_sample_time: float = 0.0

        # Dynamic watch variables (Tab3 - WatchView)
        self._live_watch_vars: List[WatchVariable] = []

        # Plot data accumulator
        self._plot_data: deque = deque(maxlen=self.PLOT_DATA_MAXLEN)

        # Timing configuration
        self._watch_poll_interval_ms: int = 500

    # ============= Connection Management =============

    @property
    def x2cscope(self) -> Optional[X2CScope]:
        """Get X2CScope instance (not thread-safe, use with caution)."""
        return self._x2cscope

    def set_x2cscope(self, x2cscope: Optional[X2CScope]):
        """Set the X2CScope instance (thread-safe)."""
        self._mutex.lock()
        try:
            self._x2cscope = x2cscope
            if x2cscope:
                self._variable_list = x2cscope.list_variables() or []
                if self._variable_list:
                    self._variable_list.insert(0, "None")
                self._connected = True
            else:
                self._variable_list = []
                self._connected = False
        finally:
            self._mutex.unlock()
        self.connection_changed.emit(self._connected)
        self.variable_list_updated.emit(self._variable_list)

    def is_connected(self) -> bool:
        """Check if connected to device (thread-safe)."""
        self._mutex.lock()
        try:
            return self._connected and self._x2cscope is not None
        finally:
            self._mutex.unlock()

    def get_variable_list(self) -> List[str]:
        """Get cached variable list (thread-safe)."""
        self._mutex.lock()
        try:
            return self._variable_list.copy()
        finally:
            self._mutex.unlock()

    def get_sfr_list(self) -> List[str]:
        """Get the list of SFR (Special Function Register) names (thread-safe)."""
        self._mutex.lock()
        try:
            if self._x2cscope:
                return self._x2cscope.list_sfr()
            return []
        finally:
            self._mutex.unlock()

    def update_device_info(self) -> Optional[DeviceInfo]:
        """Fetch and update device info (thread-safe)."""
        self._mutex.lock()
        try:
            if not self._x2cscope:
                return None
            info = self._x2cscope.get_device_info()
            self._device_info = DeviceInfo(
                processor_id=str(info.get("processor_id", "")),
                uc_width=str(info.get("uc_width", "")),
                date=str(info.get("date", "")),
                time=str(info.get("time", "")),
                app_ver=str(info.get("AppVer", "")),
                dsp_state=str(info.get("dsp_state", "")),
            )
            return self._device_info
        except Exception as e:
            logging.error(f"Error fetching device info: {e}")
            return None
        finally:
            self._mutex.unlock()

    def get_device_info(self) -> DeviceInfo:
        """Get cached device info (thread-safe)."""
        self._mutex.lock()
        try:
            return self._device_info
        finally:
            self._mutex.unlock()

    # ============= Connection Properties =============

    @property
    def port(self) -> str:
        """Get the current port."""
        return self._port

    @port.setter
    def port(self, value: str):
        self._mutex.lock()
        self._port = value
        self._mutex.unlock()

    @property
    def baud_rate(self) -> int:
        """Get the current baud rate."""
        return self._baud_rate

    @baud_rate.setter
    def baud_rate(self, value: int):
        self._mutex.lock()
        self._baud_rate = value
        self._mutex.unlock()

    @property
    def elf_file(self) -> str:
        """Get the current ELF file path."""
        return self._elf_file

    @elf_file.setter
    def elf_file(self, value: str):
        self._mutex.lock()
        self._elf_file = value
        self._mutex.unlock()

    # ============= Variable Read/Write =============

    def read_variable(self, name: str, sfr: bool = False) -> Optional[float]:
        """Read a variable value from the device (thread-safe).

        Args:
            name: The variable name to read.
            sfr: When True, look up the name in the SFR register map.
        """
        if not name or name == "None":
            return None
        self._mutex.lock()
        try:
            if self._x2cscope:
                var = self._x2cscope.get_variable(name, sfr=sfr)
                if var is not None:
                    return var.get_value()
        except Exception as e:
            logging.error(f"Error reading variable {name}: {e}")
        finally:
            self._mutex.unlock()
        return None

    def read_watch_var_value(self, index: int) -> Optional[float]:
        """Read a watch variable value using cached var_ref (thread-safe)."""
        self._mutex.lock()
        try:
            if 0 <= index < len(self._watch_vars):
                watch_var = self._watch_vars[index]
                if watch_var.var_ref is not None:
                    return watch_var.var_ref.get_value()
                elif watch_var.name and watch_var.name != "None" and self._x2cscope:
                    # Fallback: get and cache the variable
                    var_ref = self._x2cscope.get_variable(watch_var.name)
                    if var_ref is not None:
                        watch_var.var_ref = var_ref
                        return var_ref.get_value()
        except Exception as e:
            logging.error(f"Error reading watch var {index}: {e}")
        finally:
            self._mutex.unlock()
        return None

    def read_live_watch_var_value(self, index: int) -> Optional[float]:
        """Read a live watch variable value using cached var_ref (thread-safe)."""
        self._mutex.lock()
        try:
            if 0 <= index < len(self._live_watch_vars):
                live_var = self._live_watch_vars[index]
                if live_var.var_ref is not None:
                    return live_var.var_ref.get_value()
                elif live_var.name and live_var.name != "None" and self._x2cscope:
                    # Fallback: get and cache the variable
                    var_ref = self._x2cscope.get_variable(live_var.name)
                    if var_ref is not None:
                        live_var.var_ref = var_ref
                        return var_ref.get_value()
        except Exception as e:
            logging.error(f"Error reading live watch var {index}: {e}")
        finally:
            self._mutex.unlock()
        return None

    def write_variable(self, name: str, value: float, sfr: bool = False) -> bool:
        """Write a variable value to the device (thread-safe).

        Args:
            name: The variable name to write.
            value: The value to write.
            sfr: When True, look up the name in the SFR register map.
        """
        if not name or name == "None":
            return False
        self._mutex.lock()
        try:
            if self._x2cscope:
                var = self._x2cscope.get_variable(name, sfr=sfr)
                if var is not None:
                    var.set_value(value)
                    return True
        except Exception as e:
            logging.error(f"Error writing variable {name}: {e}")
        finally:
            self._mutex.unlock()
        return False

    # ============= Watch Variables (Tab1) =============

    def get_watch_var(self, index: int) -> WatchVariable:
        """Get watch variable at index (thread-safe)."""
        self._mutex.lock()
        try:
            if 0 <= index < len(self._watch_vars):
                return self._watch_vars[index]
            return WatchVariable()
        finally:
            self._mutex.unlock()

    def set_watch_var(self, index: int, var: WatchVariable):
        """Set watch variable at index (thread-safe)."""
        self._mutex.lock()
        try:
            if 0 <= index < len(self._watch_vars):
                self._watch_vars[index] = var
        finally:
            self._mutex.unlock()

    def update_watch_var_field(self, index: int, field: str, value: Any):
        """Update a specific field of a watch variable (thread-safe)."""
        self._mutex.lock()
        try:
            if 0 <= index < len(self._watch_vars):
                setattr(self._watch_vars[index], field, value)
                # Cache the x2cscope variable reference when name is set
                if field == "name" and value and value != "None" and self._x2cscope:
                    sfr = self._watch_vars[index].sfr
                    var_ref = self._x2cscope.get_variable(value, sfr=sfr)
                    if var_ref is not None:
                        self._watch_vars[index].var_ref = var_ref
        finally:
            self._mutex.unlock()

    def get_active_watch_vars(self) -> List[Dict[str, Any]]:
        """Get all watch variables with live=True (thread-safe)."""
        self._mutex.lock()
        try:
            return [
                {"index": i, "name": v.name, "live": v.live}
                for i, v in enumerate(self._watch_vars)
                if v.live and v.name and v.name != "None"
            ]
        finally:
            self._mutex.unlock()

    def get_all_watch_vars(self) -> List[WatchVariable]:
        """Get all watch variables (thread-safe copy)."""
        self._mutex.lock()
        try:
            return [
                WatchVariable(
                    name=v.name,
                    value=v.value,
                    scaling=v.scaling,
                    offset=v.offset,
                    unit=v.unit,
                    live=v.live,
                    plot_enabled=v.plot_enabled,
                )
                for v in self._watch_vars
            ]
        finally:
            self._mutex.unlock()

    # ============= Scope Channels (Tab2) =============

    def get_scope_channel(self, index: int) -> ScopeChannel:
        """Get scope channel at index (thread-safe)."""
        self._mutex.lock()
        try:
            if 0 <= index < len(self._scope_channels):
                return self._scope_channels[index]
            return ScopeChannel()
        finally:
            self._mutex.unlock()

    def set_scope_channel(self, index: int, channel: ScopeChannel):
        """Set scope channel at index (thread-safe)."""
        self._mutex.lock()
        try:
            if 0 <= index < len(self._scope_channels):
                self._scope_channels[index] = channel
        finally:
            self._mutex.unlock()

    def update_scope_channel_field(self, index: int, field: str, value: Any):
        """Update a specific field of a scope channel (thread-safe)."""
        self._mutex.lock()
        try:
            if 0 <= index < len(self._scope_channels):
                setattr(self._scope_channels[index], field, value)
        finally:
            self._mutex.unlock()

    def get_all_scope_channels(self) -> List[ScopeChannel]:
        """Get all scope channels (thread-safe copy)."""
        self._mutex.lock()
        try:
            return [
                ScopeChannel(
                    name=c.name, trigger=c.trigger, gain=c.gain, visible=c.visible
                )
                for c in self._scope_channels
            ]
        finally:
            self._mutex.unlock()

    def get_trigger_variable(self) -> Optional[str]:
        """Get the currently selected trigger variable (thread-safe)."""
        self._mutex.lock()
        try:
            for channel in self._scope_channels:
                if channel.trigger and channel.name:
                    return channel.name
            return None
        finally:
            self._mutex.unlock()

    # ============= Trigger Settings =============

    def get_trigger_settings(self) -> TriggerSettings:
        """Get trigger settings (thread-safe)."""
        self._mutex.lock()
        try:
            return TriggerSettings(
                mode=self._trigger_settings.mode,
                edge=self._trigger_settings.edge,
                level=self._trigger_settings.level,
                delay=self._trigger_settings.delay,
                variable=self._trigger_settings.variable,
            )
        finally:
            self._mutex.unlock()

    def set_trigger_settings(self, settings: TriggerSettings):
        """Set trigger settings (thread-safe)."""
        self._mutex.lock()
        try:
            self._trigger_settings = settings
        finally:
            self._mutex.unlock()

    # ============= Scope Operations =============

    def start_scope(self) -> bool:
        """Start scope sampling (thread-safe)."""
        self._mutex.lock()
        try:
            if not self._x2cscope:
                return False

            # Clear existing channels
            self._x2cscope.clear_all_scope_channel()

            # Add configured channels
            for channel in self._scope_channels:
                if channel.name and channel.name != "None":
                    variable = self._x2cscope.get_variable(channel.name, sfr=channel.sfr)
                    if variable is not None:
                        self._x2cscope.add_scope_channel(variable)

            # Set sample time
            self._x2cscope.set_sample_time(self._sample_time_factor)
            self._real_sample_time = self._x2cscope.get_scope_sample_time(
                self._scope_sample_time_us
            )

            self._scope_active = True
            return True
        except Exception as e:
            logging.error(f"Error starting scope: {e}")
            return False
        finally:
            self._mutex.unlock()

    def configure_scope_trigger(self) -> bool:
        """Configure scope trigger (thread-safe)."""
        self._mutex.lock()
        try:
            if not self._x2cscope:
                return False

            trigger_var_name = self.get_trigger_variable()
            if self._trigger_settings.mode == "Auto":
                self._x2cscope.reset_scope_trigger()
                return True

            if trigger_var_name:
                # Find sfr flag for the trigger channel
                trigger_sfr = next(
                    (ch.sfr for ch in self._scope_channels if ch.trigger and ch.name == trigger_var_name),
                    False,
                )
                variable = self._x2cscope.get_variable(trigger_var_name, sfr=trigger_sfr)
                if variable is not None:
                    trigger_edge = (
                        0 if self._trigger_settings.edge == "Rising" else 1
                    )
                    trigger_mode = 1  # Triggered mode

                    trigger_config = TriggerConfig(
                        variable=variable,
                        trigger_level=self._trigger_settings.level,
                        trigger_mode=trigger_mode,
                        trigger_delay=self._trigger_settings.delay,
                        trigger_edge=trigger_edge,
                    )
                    self._x2cscope.set_scope_trigger(trigger_config)
                    return True
            else:
                self._x2cscope.reset_scope_trigger()
            return True
        except Exception as e:
            logging.error(f"Error configuring trigger: {e}")
            return False
        finally:
            self._mutex.unlock()

    def request_scope_data(self):
        """Request scope data (thread-safe)."""
        self._mutex.lock()
        try:
            if self._x2cscope:
                self._x2cscope.request_scope_data()
        finally:
            self._mutex.unlock()

    def stop_scope(self):
        """Stop scope sampling (thread-safe)."""
        self._mutex.lock()
        try:
            self._scope_active = False
            if self._x2cscope:
                self._x2cscope.clear_all_scope_channel()
        finally:
            self._mutex.unlock()

    def is_scope_active(self) -> bool:
        """Check if scope is actively sampling (thread-safe)."""
        self._mutex.lock()
        try:
            return self._scope_active
        finally:
            self._mutex.unlock()

    def is_scope_data_ready(self) -> bool:
        """Check if scope data is ready (thread-safe)."""
        self._mutex.lock()
        try:
            if self._x2cscope:
                return self._x2cscope.is_scope_data_ready()
        except Exception as e:
            logging.error(f"Error checking scope data ready: {e}")
        finally:
            self._mutex.unlock()
        return False

    def get_scope_channel_data(self) -> Dict[str, List[float]]:
        """Get scope channel data (thread-safe)."""
        self._mutex.lock()
        try:
            if self._x2cscope:
                return self._x2cscope.get_scope_channel_data()
        except Exception as e:
            logging.error(f"Error getting scope data: {e}")
        finally:
            self._mutex.unlock()
        return {}

    # ============= Scope Settings Properties =============

    @property
    def scope_single_shot(self) -> bool:
        """Get the scope single shot mode setting."""
        return self._scope_single_shot

    @scope_single_shot.setter
    def scope_single_shot(self, value: bool):
        self._mutex.lock()
        self._scope_single_shot = value
        self._mutex.unlock()

    @property
    def sample_time_factor(self) -> int:
        """Get the sample time factor."""
        return self._sample_time_factor

    @sample_time_factor.setter
    def sample_time_factor(self, value: int):
        self._mutex.lock()
        self._sample_time_factor = 1 if value < 1 else value
        self._mutex.unlock()

    @property
    def scope_sample_time_us(self) -> int:
        """Get the scope sample time in microseconds."""
        return self._scope_sample_time_us

    @scope_sample_time_us.setter
    def scope_sample_time_us(self, value: int):
        self._mutex.lock()
        self._scope_sample_time_us = value
        self._mutex.unlock()

    @property
    def real_sample_time(self) -> float:
        """Get the real sample time."""
        return self._real_sample_time

    # ============= Tab3 Live Variables =============

    def add_live_watch_var(self) -> int:
        """Add a new live watch variable row (thread-safe)."""
        self._mutex.lock()
        try:
            self._live_watch_vars.append(WatchVariable())
            return len(self._live_watch_vars) - 1
        finally:
            self._mutex.unlock()

    def remove_live_watch_var(self, index: int):
        """Remove a live watch variable row (thread-safe)."""
        self._mutex.lock()
        try:
            if 0 <= index < len(self._live_watch_vars):
                self._live_watch_vars.pop(index)
        finally:
            self._mutex.unlock()

    def get_live_watch_var(self, index: int) -> WatchVariable:
        """Get live watch variable at index (thread-safe)."""
        self._mutex.lock()
        try:
            if 0 <= index < len(self._live_watch_vars):
                return self._live_watch_vars[index]
            return WatchVariable()
        finally:
            self._mutex.unlock()

    def update_live_watch_var_field(self, index: int, field: str, value: Any):
        """Update a specific field of a live watch variable (thread-safe)."""
        self._mutex.lock()
        try:
            if 0 <= index < len(self._live_watch_vars):
                setattr(self._live_watch_vars[index], field, value)
                # Cache the x2cscope variable reference when name is set
                if field == "name" and value and value != "None" and self._x2cscope:
                    sfr = self._live_watch_vars[index].sfr
                    var_ref = self._x2cscope.get_variable(value, sfr=sfr)
                    if var_ref is not None:
                        self._live_watch_vars[index].var_ref = var_ref
        finally:
            self._mutex.unlock()

    def get_active_live_watch_vars(self) -> List[Dict[str, Any]]:
        """Get all live watch variables with live=True (thread-safe)."""
        self._mutex.lock()
        try:
            return [
                {"index": i, "name": v.name, "live": v.live}
                for i, v in enumerate(self._live_watch_vars)
                if v.live and v.name and v.name != "None"
            ]
        finally:
            self._mutex.unlock()

    def get_all_live_watch_vars(self) -> List[WatchVariable]:
        """Get all live watch variables (thread-safe copy)."""
        self._mutex.lock()
        try:
            return [
                WatchVariable(
                    name=v.name,
                    value=v.value,
                    scaling=v.scaling,
                    offset=v.offset,
                    unit=v.unit,
                    live=v.live,
                    plot_enabled=v.plot_enabled,
                )
                for v in self._live_watch_vars
            ]
        finally:
            self._mutex.unlock()

    def get_live_watch_var_count(self) -> int:
        """Get count of live watch variables (thread-safe)."""
        self._mutex.lock()
        try:
            return len(self._live_watch_vars)
        finally:
            self._mutex.unlock()

    def clear_live_watch_vars(self):
        """Clear all live watch variables (thread-safe)."""
        self._mutex.lock()
        try:
            self._live_watch_vars.clear()
        finally:
            self._mutex.unlock()

    # ============= Plot Data =============

    def append_plot_data(self, data: tuple):
        """Append data to plot buffer (thread-safe)."""
        self._mutex.lock()
        try:
            self._plot_data.append(data)
        finally:
            self._mutex.unlock()

    def get_plot_data(self) -> List[tuple]:
        """Get plot data (thread-safe copy)."""
        self._mutex.lock()
        try:
            return list(self._plot_data)
        finally:
            self._mutex.unlock()

    def clear_plot_data(self):
        """Clear plot data buffer (thread-safe)."""
        self._mutex.lock()
        try:
            self._plot_data.clear()
        finally:
            self._mutex.unlock()

    # ============= Timing Configuration =============

    @property
    def watch_poll_interval_ms(self) -> int:
        """Get the watch poll interval in milliseconds."""
        return self._watch_poll_interval_ms

    @watch_poll_interval_ms.setter
    def watch_poll_interval_ms(self, value: int):
        self._mutex.lock()
        self._watch_poll_interval_ms = max(50, value)
        self._mutex.unlock()
