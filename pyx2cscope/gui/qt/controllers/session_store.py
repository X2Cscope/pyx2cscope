"""Recent sessions of the Qt GUI.

A session is the configuration of one project: the ELF/YML/PKL file, the connection settings,
the WatchView and ScopeView variables with trigger and sample settings, the view mode and the
script and script folder of the Scripting tab. It uses the same JSON format as **Save Config**, so a
session can also be saved to and loaded from a file.

The recent sessions are kept in ``recent_sessions.json`` in the user configuration folder,
one entry per ELF/YML/PKL file, most recent first.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QStandardPaths

from pyx2cscope.utils import get_project_name

MAX_RECENT_SESSIONS = 10
SESSIONS_FILE_NAME = "recent_sessions.json"
SESSIONS_FILE_VERSION = 1
# Keys of a session that describe the views; they are kept when only the connection is updated
VIEW_KEYS = ("watch_view", "scope_view", "view_mode", "sample_control", "trigger_control")
DATE_FORMAT = "%d.%m.%Y %H:%M"


def default_sessions_file() -> str:
    """Return the default location of the recent sessions file.

    Returns:
        str: e.g. ``C:/Users/<user>/AppData/Local/Microchip/pyX2Cscope/recent_sessions.json`` on Windows.
    """
    base = QStandardPaths.writableLocation(QStandardPaths.GenericConfigLocation) or os.path.expanduser("~")
    return os.path.join(base, "Microchip", "pyX2Cscope", SESSIONS_FILE_NAME)


def _key(elf_file: str) -> str:
    """Return the comparison key of a file path (absolute, case-insensitive on Windows)."""
    return os.path.normcase(os.path.abspath(elf_file))


class RecentSessions:
    """Store of the most recently used sessions.

    Each entry is a dict with ``saved_at`` (ISO time) and ``config`` (the session configuration,
    which always contains ``elf_file``).
    """

    def __init__(self, file_path: Optional[str] = None, max_entries: int = MAX_RECENT_SESSIONS):
        """Load the recent sessions.

        Args:
            file_path: The JSON file. Defaults to :func:`default_sessions_file`.
            max_entries: Maximum number of sessions kept.
        """
        self._file_path = file_path or default_sessions_file()
        self._max_entries = max_entries
        self._entries: List[Dict[str, Any]] = self._read()

    @property
    def file_path(self) -> str:
        """The JSON file of the recent sessions."""
        return self._file_path

    def entries(self) -> List[Dict[str, Any]]:
        """Return the sessions, most recent first."""
        return list(self._entries)

    def get(self, elf_file: str) -> Optional[Dict[str, Any]]:
        """Return the session configuration of a file, or None.

        Args:
            elf_file: The ELF/YML/PKL file of the session.
        """
        entry = self._find(elf_file)
        return dict(entry["config"]) if entry else None

    def save_session(self, config: Dict[str, Any], keep_views: bool = False):
        """Add or update the session of ``config["elf_file"]`` and move it to the top.

        Args:
            config: The session configuration. Ignored if it has no ``elf_file``.
            keep_views: Keep the WatchView/ScopeView settings already stored for this file and
                only update the other keys (used when connecting, before the views show the project).
        """
        elf_file = config.get("elf_file")
        if not elf_file:
            return
        existing = self._find(elf_file)
        new_config = dict(config)
        if keep_views:
            # Take the views from the stored session only; a new session starts without views
            stored = existing["config"] if existing else {}
            for key in VIEW_KEYS:
                if key in stored:
                    new_config[key] = stored[key]
                else:
                    new_config.pop(key, None)
        if existing:
            self._entries.remove(existing)
        self._entries.insert(0, {"saved_at": datetime.now().isoformat(timespec="seconds"), "config": new_config})
        del self._entries[self._max_entries:]
        self._write()

    def remove(self, elf_file: str):
        """Remove the session of a file.

        Args:
            elf_file: The ELF/YML/PKL file of the session.
        """
        entry = self._find(elf_file)
        if entry:
            self._entries.remove(entry)
            self._write()

    @staticmethod
    def describe(entry: Dict[str, Any]) -> str:
        """Return the text shown in the Recent sessions list, e.g. ``LAB1_HALL - 01.11.2026 21:30``.

        Args:
            entry: A session entry from :meth:`entries`.
        """
        elf_file = entry["config"].get("elf_file", "")
        text = get_project_name(elf_file) or elf_file
        try:
            text += " - " + datetime.fromisoformat(entry.get("saved_at", "")).strftime(DATE_FORMAT)
        except ValueError:
            pass
        if not os.path.exists(elf_file):
            text += " (file not found)"
        return text

    def _find(self, elf_file: str) -> Optional[Dict[str, Any]]:
        key = _key(elf_file)
        return next((e for e in self._entries if _key(e["config"]["elf_file"]) == key), None)

    def _read(self) -> List[Dict[str, Any]]:
        """Read the sessions file; a missing or damaged file gives an empty list."""
        if not os.path.exists(self._file_path):
            return []
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            entries = [
                e for e in data.get("sessions", [])
                if isinstance(e, dict) and isinstance(e.get("config"), dict) and e["config"].get("elf_file")
            ]
            return entries[: self._max_entries]
        except (OSError, ValueError, AttributeError) as e:
            logging.warning(f"Could not read recent sessions from {self._file_path}: {e}")
            return []

    def _write(self):
        """Write the sessions file; errors are logged, the GUI keeps working."""
        try:
            os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
            tmp_path = self._file_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump({"version": SESSIONS_FILE_VERSION, "sessions": self._entries}, f, indent=4)
            os.replace(tmp_path, self._file_path)
        except OSError as e:
            logging.warning(f"Could not save recent sessions to {self._file_path}: {e}")
