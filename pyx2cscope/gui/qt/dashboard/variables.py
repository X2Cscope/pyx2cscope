"""Connect dashboard widgets to variables of the connected target.

A widget data source ``$name`` (or ``$sfr:name`` for a peripheral register) reads the variable ``name`` from
the target. The reads happen in a background thread, so the dashboard timer in the GUI thread never waits for
the serial line.
"""

import logging
import threading
import time
from typing import Callable, Dict, Iterable, Optional, Set, Tuple

VARIABLE_PREFIX = "$"
SFR_PREFIX = "sfr:"
POLL_PAUSE_S = 0.005  # pause between two sweeps over the variables
IDLE_PAUSE_S = 0.1  # pause while there is nothing to read


def make_source(name: str, sfr: bool = False) -> str:
    """Return the data source string for a variable.

    Args:
        name: The variable name.
        sfr: True for a Special Function Register.

    Returns:
        str: ``$name`` or ``$sfr:name``.
    """
    return f"{VARIABLE_PREFIX}{SFR_PREFIX if sfr else ''}{name}"


def parse_source(source: str) -> Optional[Tuple[str, bool]]:
    """Split a data source string into variable name and SFR flag.

    Args:
        source: A data source such as ``sine``, ``@slider``, ``$motor.speed`` or ``$sfr:PORTA``.

    Returns:
        tuple: ``(name, sfr)``, or None when the source is not a variable.
    """
    if not isinstance(source, str) or not source.startswith(VARIABLE_PREFIX):
        return None
    name = source[len(VARIABLE_PREFIX):]
    if name.startswith(SFR_PREFIX):
        return name[len(SFR_PREFIX):], True
    return name, False


class VariableBridge:
    """Reads the variables used by a running dashboard in a background thread."""

    def __init__(self, reader: Callable[[str, bool], Optional[float]], writer: Optional[Callable] = None):
        """Initialize the bridge.

        Args:
            reader: ``reader(name, sfr)`` returns the variable value, or None when it cannot be read.
            writer: ``writer(name, value, sfr)`` writes a value to the target; None for read-only.
        """
        self._reader = reader
        self._writer = writer
        self._pending: Dict[Tuple[str, bool], float] = {}
        self._wanted: Set[Tuple[str, bool]] = set()
        self._values: Dict[Tuple[str, bool], float] = {}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self, sources: Iterable[str]):
        """Start reading the variables found in the given data sources.

        Args:
            sources: Data source strings; the ones that are not variables are ignored.
        """
        self.stop()
        wanted = {parsed for parsed in map(parse_source, sources) if parsed and parsed[0]}
        with self._lock:
            self._wanted = wanted
            self._values = {}
        if not wanted:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="DashboardVariables", daemon=True)
        self._thread.start()

    def stop(self):
        """Stop reading."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def value(self, source: str) -> float:
        """Return the last value read for a variable data source.

        Args:
            source: A ``$name`` or ``$sfr:name`` data source.

        Returns:
            float: The value, or 0.0 when nothing was read yet or the variable cannot be read.
        """
        parsed = parse_source(source)
        with self._lock:
            return self._values.get(parsed, 0.0) if parsed else 0.0

    def write(self, source: str, value: float):
        """Queue a value for a variable data source; the thread writes the latest value per variable.

        Args:
            source: A ``$name`` or ``$sfr:name`` data source.
            value: The value to write.
        """
        parsed = parse_source(source)
        if parsed and parsed[0] and self._writer is not None:
            with self._lock:
                self._pending[parsed] = value
                self._values[parsed] = value  # shown at once, until the next read

    def _flush_writes(self):
        """Write the queued values."""
        with self._lock:
            pending, self._pending = self._pending, {}
        for (name, sfr), value in pending.items():
            try:
                self._writer(name, value, sfr)
            except Exception as e:
                logging.warning("Dashboard: writing %s failed: %s", name, e)

    def _run(self):
        """Thread body: read every wanted variable again and again."""
        while not self._stop.is_set():
            with self._lock:
                wanted = list(self._wanted)
            self._flush_writes()
            got_any = False
            for key in wanted:
                if self._stop.is_set():
                    return
                try:
                    value = self._reader(*key)
                except Exception as e:  # keep the thread alive, e.g. on a connection loss
                    logging.warning("Dashboard: reading %s failed: %s", key[0], e)
                    value = None
                if value is not None:
                    got_any = True
                    with self._lock:
                        self._values[key] = value
            time.sleep(POLL_PAUSE_S if got_any else IDLE_PAUSE_S)
