"""Scripting tab - Execute Python scripts with access to x2cscope."""

import io
import os
import subprocess
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from typing import TYPE_CHECKING

from PyQt5.QtCore import QSettings, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QStyle,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from pyx2cscope.gui.resources import get_resource_path

if TYPE_CHECKING:
    from pyx2cscope.gui.qt.models.app_state import AppState

# Item data role holding the full path of a script in the script list model
SCRIPT_PATH_ROLE = Qt.UserRole + 1

SCRIPT_COMBO_MIN_WIDTH = 180
NO_FOLDER_TEXT = "No script folder selected"
NO_SCRIPTS_TEXT = "No scripts in folder"
SELECT_SCRIPT_TEXT = "Select a script..."


def same_path(path_a: str, path_b: str) -> bool:
    """Return True if both paths point to the same location.

    Args:
        path_a: First path.
        path_b: Second path.

    Returns:
        True when the normalized absolute paths are equal. Empty paths are never equal.
    """
    if not path_a or not path_b:
        return False
    return os.path.normcase(os.path.abspath(path_a)) == os.path.normcase(os.path.abspath(path_b))


def list_scripts(folder: str) -> list:
    """Return the Python scripts directly inside a folder.

    Sub-folders are not searched. Files whose name starts with a double underscore
    (e.g. ``__init__.py``) are skipped because they are not meant to be run.

    Args:
        folder: The folder to scan.

    Returns:
        Full paths of the ``.py`` files, sorted by file name (case-insensitive).
        An empty list if the folder is empty or does not exist.
    """
    if not folder or not os.path.isdir(folder):
        return []
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    scripts = [
        os.path.join(folder, name)
        for name in names
        if name.lower().endswith(".py")
        and not name.startswith("__")
        and os.path.isfile(os.path.join(folder, name))
    ]
    return sorted(scripts, key=lambda path: os.path.basename(path).lower())


class ScriptComboBox(QComboBox):
    """Combo box for the scripts of the script folder.

    Emits ``popup_about_to_show`` before the list opens, so the folder can be rescanned
    and scripts created or deleted in the meantime are shown.
    """

    popup_about_to_show = pyqtSignal()

    def showPopup(self):  # noqa: N802 (Qt override)
        """Emit popup_about_to_show, then open the list."""
        self.popup_about_to_show.emit()
        super().showPopup()


class ScriptHelpDialog(QDialog):
    """Dialog showing help for writing scripts."""

    def __init__(self, parent=None):
        """Initialize the script help dialog."""
        super().__init__(parent)
        self.setWindowTitle("Script Help")
        self.setMinimumSize(700, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        help_browser = QTextBrowser()
        help_browser.setOpenExternalLinks(True)
        help_browser.setStyleSheet(
            "QTextBrowser { font-family: Segoe UI, Arial, sans-serif; font-size: 10pt; }"
        )
        help_browser.setMarkdown(self._load_help_content())
        layout.addWidget(help_browser)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _load_help_content(self) -> str:
        """Load help content from external markdown file."""
        try:
            help_path = get_resource_path("script_help.md")
            with open(help_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"# Error\n\nCould not load help file: {e}\n\nPlease check that `script_help.md` exists in the resources folder."


class ScriptWorker(QThread):
    """Worker thread for executing Python scripts."""

    output_ready = pyqtSignal(str)
    finished_with_code = pyqtSignal(int)

    def __init__(self, script_path: str, x2cscope, parent=None):
        """Initialize the script worker.

        Args:
            script_path: Path to the Python script to execute.
            x2cscope: The x2cscope instance to inject into script namespace.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._script_path = script_path
        self._x2cscope = x2cscope
        self._stop_requested = False

    def is_stop_requested(self) -> bool:
        """Check if stop has been requested. Scripts should call this in loops."""
        return self._stop_requested

    def run(self):
        """Execute the script in this thread."""
        exit_code = 0

        # Create a custom stdout/stderr that emits signals
        class OutputCapture(io.StringIO):
            def __init__(self, signal):
                super().__init__()
                self._signal = signal

            def write(self, text):
                if text:
                    self._signal.emit(text)
                return len(text) if text else 0

            def flush(self):
                pass

        stdout_capture = OutputCapture(self.output_ready)
        stderr_capture = OutputCapture(self.output_ready)

        try:
            with open(self._script_path, "r", encoding="utf-8") as f:
                script_code = f.read()

            # Create namespace with x2cscope and stop_requested function
            namespace = {
                "__name__": "__main__",
                "__file__": self._script_path,
                "x2cscope": self._x2cscope,
                "stop_requested": self.is_stop_requested,
            }

            # Execute with captured output
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(compile(script_code, self._script_path, "exec"), namespace)

        except SystemExit as e:
            # Handle sys.exit() calls in scripts
            exit_code = e.code if isinstance(e.code, int) else 1
        except StopIteration:
            # Script was stopped via stop_requested
            exit_code = 0
        except Exception as e:
            self.output_ready.emit(f"\nScript error: {e}\n")
            self.output_ready.emit(traceback.format_exc())
            exit_code = 1

        self.finished_with_code.emit(exit_code)

    def request_stop(self):
        """Request the script to stop. Scripts should check stop_requested() in loops."""
        self._stop_requested = True


class ScriptingTab(QWidget):
    """Tab for executing Python scripts with x2cscope access.

    Features:
    - Select a script folder and pick one of its scripts from a dropdown
    - Select and execute Python scripts
    - View script output in real-time (separate tab)
    - Log messages with timestamps (separate tab)
    - Option to log output to file with custom location
    - Edit scripts with IDLE
    - Scripts can access the x2cscope instance from the main app
    """

    # Signals
    script_selected = pyqtSignal(str)  # path of the loaded script
    script_started = pyqtSignal()
    script_finished = pyqtSignal(int)  # exit code
    script_folder_changed = pyqtSignal(str)  # path of the script folder
    scripts_changed = pyqtSignal()  # the list of scripts in the folder changed

    def __init__(self, app_state: "AppState", parent=None):
        """Initialize the Scripting tab.

        Args:
            app_state: The centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._script_path = ""
        self._script_folder = ""
        # One model for the scripts of the folder, shared by every script dropdown
        self._script_model = QStandardItemModel(self)
        self._settings = QSettings("Microchip", "pyX2Cscope")
        self._worker = None
        self._log_file = None
        self._log_file_path = ""

        self._setup_ui()

        # Restore the last script folder chosen by the user
        saved_folder = self._settings.value("script_folder", "", type=str)
        if saved_folder and os.path.isdir(saved_folder):
            self.set_script_folder(saved_folder)

    def _setup_ui(self):  # noqa: PLR0915
        """Set up the user interface."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)

        # === Script Selection Group ===
        script_group = QGroupBox("Script Selection")
        script_group_layout = QVBoxLayout()
        script_group_layout.setSpacing(8)
        script_group_layout.setContentsMargins(10, 15, 10, 10)
        script_group.setLayout(script_group_layout)

        label_width = 45

        # First row: script folder
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(8)
        folder_label = QLabel("Folder:")
        folder_label.setFixedWidth(label_width)
        folder_layout.addWidget(folder_label)

        self._folder_edit = QLineEdit()
        self._folder_edit.setReadOnly(True)
        self._folder_edit.setPlaceholderText(NO_FOLDER_TEXT)
        folder_layout.addWidget(self._folder_edit, 1)

        self._folder_btn = QPushButton("Folder...")
        self._folder_btn.setFixedWidth(80)
        self._folder_btn.setToolTip("Select a folder; its scripts are listed in the Script dropdown")
        self._folder_btn.clicked.connect(self._on_folder_clicked)
        folder_layout.addWidget(self._folder_btn)
        script_group_layout.addLayout(folder_layout)

        # Second row: script of the folder and script actions
        script_layout = QHBoxLayout()
        script_layout.setSpacing(8)
        script_label = QLabel("Script:")
        script_label.setFixedWidth(label_width)
        script_layout.addWidget(script_label)

        self._script_combo = ScriptComboBox()
        self._script_combo.setModel(self._script_model)
        self._script_combo.setMinimumWidth(SCRIPT_COMBO_MIN_WIDTH)
        self._script_combo.activated.connect(self._on_combo_activated)
        self._script_combo.popup_about_to_show.connect(self.refresh_scripts)
        script_layout.addWidget(self._script_combo, 1)
        self.scripts_changed.connect(self._update_combo)

        # Browse button
        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.setFixedWidth(80)
        self._browse_btn.setToolTip("Select a script file; its folder becomes the script folder")
        self._browse_btn.clicked.connect(self._on_browse_clicked)
        script_layout.addWidget(self._browse_btn)

        # Edit button
        self._edit_btn = QPushButton("Edit Script")
        self._edit_btn.setFixedWidth(90)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        self._edit_btn.setEnabled(False)
        self._edit_btn.setToolTip("Open script in text editor")
        script_layout.addWidget(self._edit_btn)

        # New script button
        self._new_btn = QPushButton("New Script")
        self._new_btn.setFixedWidth(90)
        self._new_btn.clicked.connect(self._on_new_clicked)
        self._new_btn.setToolTip("Create a new script from the built-in template")
        script_layout.addWidget(self._new_btn)

        # Help button
        self._help_btn = QPushButton("Help")
        self._help_btn.setFixedWidth(60)
        self._help_btn.clicked.connect(self._on_help_clicked)
        script_layout.addWidget(self._help_btn)
        script_group_layout.addLayout(script_layout)

        main_layout.addWidget(script_group)

        # === Execution Controls Group ===
        controls_group = QGroupBox("Execution Controls")
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(8)
        controls_layout.setContentsMargins(10, 15, 10, 10)
        controls_group.setLayout(controls_layout)

        # First row: Execute, Stop, Status
        row1_layout = QHBoxLayout()

        # Execute button
        self._execute_btn = QPushButton("Execute")
        self._execute_btn.setFixedSize(100, 30)
        self._execute_btn.clicked.connect(self._on_execute_clicked)
        self._execute_btn.setEnabled(False)
        row1_layout.addWidget(self._execute_btn)

        # Stop button
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setFixedSize(100, 30)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setToolTip("Request script to stop (may not work for blocking operations)")
        row1_layout.addWidget(self._stop_btn)

        # Status label
        row1_layout.addStretch()
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("color: #666;")
        row1_layout.addWidget(self._status_label)

        controls_layout.addLayout(row1_layout)

        # Second row: Log to file checkbox and path
        row2_layout = QHBoxLayout()

        # Log to file checkbox
        self._log_checkbox = QCheckBox("Log output to file:")
        self._log_checkbox.setChecked(False)
        self._log_checkbox.stateChanged.connect(self._on_log_checkbox_changed)
        row2_layout.addWidget(self._log_checkbox)

        # Log file path display
        self._log_path_edit = QLineEdit()
        self._log_path_edit.setReadOnly(True)
        self._log_path_edit.setPlaceholderText("Select log file location...")
        self._log_path_edit.setEnabled(False)
        row2_layout.addWidget(self._log_path_edit, 1)

        # Browse log location button
        self._log_browse_btn = QPushButton("Browse...")
        self._log_browse_btn.setFixedWidth(80)
        self._log_browse_btn.clicked.connect(self._on_log_browse_clicked)
        self._log_browse_btn.setEnabled(False)
        row2_layout.addWidget(self._log_browse_btn)

        controls_layout.addLayout(row2_layout)

        main_layout.addWidget(controls_group)

        # === Output Tabs ===
        self._output_tabs = QTabWidget()

        # Script Output tab
        script_output_widget = QWidget()
        script_output_layout = QVBoxLayout(script_output_widget)
        script_output_layout.setContentsMargins(5, 5, 5, 5)

        self._script_output_text = QPlainTextEdit()
        self._script_output_text.setReadOnly(True)
        self._script_output_text.setStyleSheet(
            "QPlainTextEdit { font-family: Consolas, monospace; font-size: 10pt; }"
        )
        script_output_layout.addWidget(self._script_output_text)

        # Clear button for script output
        script_clear_layout = QHBoxLayout()
        script_clear_layout.addStretch()
        script_clear_btn = QPushButton("Clear")
        script_clear_btn.setFixedWidth(80)
        script_clear_btn.clicked.connect(self._script_output_text.clear)
        script_clear_layout.addWidget(script_clear_btn)
        script_output_layout.addLayout(script_clear_layout)

        self._output_tabs.addTab(script_output_widget, "Script Output")

        # Log Output tab
        log_output_widget = QWidget()
        log_output_layout = QVBoxLayout(log_output_widget)
        log_output_layout.setContentsMargins(5, 5, 5, 5)

        self._log_output_text = QPlainTextEdit()
        self._log_output_text.setReadOnly(True)
        self._log_output_text.setStyleSheet(
            "QPlainTextEdit { font-family: Consolas, monospace; font-size: 10pt; "
            "color: #555; }"
        )
        log_output_layout.addWidget(self._log_output_text)

        # Clear button for log output
        log_clear_layout = QHBoxLayout()
        log_clear_layout.addStretch()
        log_clear_btn = QPushButton("Clear")
        log_clear_btn.setFixedWidth(80)
        log_clear_btn.clicked.connect(self._log_output_text.clear)
        log_clear_layout.addWidget(log_clear_btn)
        log_output_layout.addLayout(log_clear_layout)

        self._output_tabs.addTab(log_output_widget, "Log")

        main_layout.addWidget(self._output_tabs, 1)  # Stretch factor 1

        # === Info Label ===
        info_label = QLabel(
            "Scripts have access to 'x2cscope' variable when connected. "
            "Click Help for examples and documentation."
        )
        info_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        # Initial state of the dropdown and the Execute button
        self._update_combo()

    def _on_log_checkbox_changed(self, state):
        """Handle log checkbox state change."""
        enabled = state == Qt.Checked
        self._log_path_edit.setEnabled(enabled)
        self._log_browse_btn.setEnabled(enabled)

        if enabled and not self._log_file_path:
            # Suggest a default path based on script location
            if self._script_path:
                script_dir = os.path.dirname(self._script_path)
                script_name = os.path.splitext(os.path.basename(self._script_path))[0]
                self._log_file_path = os.path.join(script_dir, f"{script_name}_log.txt")
                self._log_path_edit.setText(self._log_file_path)

    def _on_log_browse_clicked(self):
        """Handle log file browse button click."""
        # Get initial directory
        if self._log_file_path:
            initial_dir = os.path.dirname(self._log_file_path)
        elif self._script_path:
            initial_dir = os.path.dirname(self._script_path)
        else:
            initial_dir = self._settings.value("log_file_dir", "", type=str)

        # Generate default filename with timestamp
        if self._script_path:
            script_name = os.path.splitext(os.path.basename(self._script_path))[0]
            default_name = f"{script_name}_log.txt"
        else:
            default_name = "script_log.txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Log File Location",
            os.path.join(initial_dir, default_name),
            "Text Files (*.txt);;Log Files (*.log);;All Files (*.*)",
        )
        if file_path:
            self._log_file_path = file_path
            self._log_path_edit.setText(file_path)
            self._settings.setValue("log_file_dir", os.path.dirname(file_path))

    def _on_help_clicked(self):
        """Show help dialog."""
        dialog = ScriptHelpDialog(self)
        dialog.exec_()

    def _open_with_system_editor(self, script_path):
        """Open script with the system's default editor or associated application.

        Uses OS-specific methods to open the file with the default application
        associated with .py files.

        Args:
            script_path: Path to the script file to open.
        """
        if sys.platform == "win32":
            # Windows: Use os.startfile to open with associated application
            os.startfile(script_path)
        elif sys.platform == "darwin":
            # macOS: Use 'open' command
            subprocess.Popen(['open', script_path])
        else:
            # Linux: Use xdg-open to respect file associations
            subprocess.Popen(['xdg-open', script_path])

    def _on_new_clicked(self):
        """Create a new script from the built-in template.

        Asks the user where to save the new file, copies the template there,
        loads it into the tab, and opens it in the system editor.
        """
        import shutil

        from pyx2cscope.gui.resources import get_resource_path

        last_dir = self._script_folder or self._settings.value("script_file_dir", "", type=str)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save New Script",
            os.path.join(last_dir, "my_script.py"),
            "Python Files (*.py);;All Files (*.*)",
        )
        if not file_path:
            return

        template_path = get_resource_path("script_template.py")
        try:
            shutil.copy(template_path, file_path)
        except Exception as e:
            self._log_message(f"Error creating script: {e}")
            return

        # Load the new file into the tab; its folder becomes the script folder
        self._remember_folder(os.path.dirname(file_path))
        self.set_script(file_path)
        self._log_message(f"New script created: {file_path}")

        # Open immediately in the system editor so the user can start writing
        try:
            self._open_with_system_editor(file_path)
        except Exception as e:
            self._log_message(f"Could not open editor: {e}")

    def _on_browse_clicked(self):
        """Handle browse button click."""
        # Start in the script folder, otherwise in the last used directory
        last_dir = self._script_folder or self._settings.value("script_file_dir", "", type=str)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Python Script",
            last_dir,
            "Python Files (*.py);;All Files (*.*)",
        )
        if file_path:
            self._remember_folder(os.path.dirname(file_path))
            self.set_script(file_path)
            self._log_message(f"Selected script: {file_path}")

    def _on_folder_clicked(self):
        """Select the script folder whose scripts are listed in the dropdowns."""
        start_dir = self._script_folder or self._settings.value("script_file_dir", "", type=str)
        folder = QFileDialog.getExistingDirectory(self, "Select Script Folder", start_dir)
        if not folder:
            return
        self._remember_folder(folder)
        self.set_script_folder(folder)
        count = self._script_model.rowCount()
        self._log_message(f"Script folder: {self._script_folder} ({count} script(s))")

    def _on_combo_activated(self, index: int):
        """Load the script picked in the dropdown of this tab."""
        path = self.script_at(index)
        if path and not same_path(path, self._script_path):
            self.set_script(path)
            self._log_message(f"Selected script: {path}")

    def _remember_folder(self, folder: str):
        """Store a folder chosen by the user, so it is restored at the next start."""
        self._settings.setValue("script_file_dir", folder)
        self._settings.setValue("script_folder", folder)

    def _update_combo(self):
        """Select the loaded script in this tab's dropdown and update the dropdown and Execute button."""
        running = self.is_running()
        self.sync_combo(self._script_combo)
        self._script_combo.setEnabled(self._script_model.rowCount() > 0 and not running)
        self._execute_btn.setEnabled(self.has_valid_script() and not running)

    # Public API, also used by the Run Script control on the Data Views tab

    @property
    def script_path(self) -> str:
        """Path of the loaded script, or an empty string if none is loaded."""
        return self._script_path

    @property
    def script_folder(self) -> str:
        """Path of the script folder, or an empty string if none is selected."""
        return self._script_folder

    @property
    def script_model(self) -> QStandardItemModel:
        """Model with the scripts of the script folder, to share with other dropdowns.

        Each item shows the file name and holds the full path in ``SCRIPT_PATH_ROLE``.
        """
        return self._script_model

    def is_running(self) -> bool:
        """Return True while a script is running."""
        return self._worker is not None and self._worker.isRunning()

    def has_valid_script(self) -> bool:
        """Return True if the loaded script can be run.

        The script must exist and be one of the scripts listed in the dropdowns. If the
        script folder has no valid script, or the loaded script is not in it, nothing runs.
        """
        return (
            bool(self._script_path)
            and os.path.isfile(self._script_path)
            and self.script_index(self._script_path) >= 0
        )

    def script_at(self, index: int) -> str:
        """Return the full path of a script in the script list.

        Args:
            index: Row in the script model.

        Returns:
            The script path, or an empty string if the row does not exist.
        """
        item = self._script_model.item(index) if index >= 0 else None
        return item.data(SCRIPT_PATH_ROLE) if item is not None else ""

    def script_index(self, file_path: str) -> int:
        """Return the row of a script in the script list.

        Args:
            file_path: Path of the script.

        Returns:
            The row, or -1 if the script is not in the script folder.
        """
        for row in range(self._script_model.rowCount()):
            if same_path(self.script_at(row), file_path):
                return row
        return -1

    def sync_combo(self, combo: QComboBox):
        """Show the loaded script in a dropdown that uses script_model.

        Args:
            combo: The dropdown to update. Its signals are blocked while the index changes.
        """
        if not self._script_folder:
            combo.setPlaceholderText(NO_FOLDER_TEXT)
        elif self._script_model.rowCount() == 0:
            combo.setPlaceholderText(NO_SCRIPTS_TEXT)
        else:
            combo.setPlaceholderText(SELECT_SCRIPT_TEXT)
        combo.blockSignals(True)
        combo.setCurrentIndex(self.script_index(self._script_path))
        combo.blockSignals(False)
        combo.setToolTip(self._script_path or self._script_folder or NO_FOLDER_TEXT)

    def set_script_folder(self, folder: str):
        """Set the script folder and list its scripts.

        The loaded script is kept, even when it is not in the new folder.

        Args:
            folder: The folder to list, or an empty string to clear the list.
        """
        self._script_folder = os.path.abspath(folder) if folder else ""
        self._folder_edit.setText(self._script_folder)
        self._fill_model(list_scripts(self._script_folder))
        self.script_folder_changed.emit(self._script_folder)

    def refresh_scripts(self):
        """Rescan the script folder; emit scripts_changed only if the list changed."""
        scripts = list_scripts(self._script_folder)
        current = [self.script_at(row) for row in range(self._script_model.rowCount())]
        if scripts != current:
            self._fill_model(scripts)

    def _fill_model(self, scripts: list):
        """Replace the content of the script model and emit scripts_changed."""
        self._script_model.clear()
        for path in scripts:
            item = QStandardItem(os.path.basename(path))
            item.setData(path, SCRIPT_PATH_ROLE)
            item.setToolTip(path)
            self._script_model.appendRow(item)
        self.scripts_changed.emit()

    def set_script(self, file_path: str):
        """Load a script into the tab and emit script_selected.

        The folder of the script becomes the script folder, so the dropdowns list the
        scripts next to it.

        Args:
            file_path: Path of the Python script.
        """
        self._script_path = file_path
        script_dir = os.path.dirname(os.path.abspath(file_path))
        if same_path(script_dir, self._script_folder):
            self.refresh_scripts()
        else:
            self.set_script_folder(script_dir)
        self._update_combo()
        self._edit_btn.setEnabled(True)

        # Update suggested log path if logging is enabled
        if self._log_checkbox.isChecked():
            script_dir = os.path.dirname(file_path)
            script_name = os.path.splitext(os.path.basename(file_path))[0]
            self._log_file_path = os.path.join(script_dir, f"{script_name}_log.txt")
            self._log_path_edit.setText(self._log_file_path)

        self.script_selected.emit(file_path)

    def run_script(self):
        """Run the loaded script, as the Execute button does."""
        self._on_execute_clicked()

    def stop_script(self):
        """Request the running script to stop, as the Stop button does."""
        self._on_stop_clicked()

    def _on_edit_clicked(self):
        """Open the script in the system's default editor."""
        if not self._script_path:
            return

        try:
            # Open with system default application for .py files
            self._open_with_system_editor(self._script_path)
            self._log_message(f"Opened {os.path.basename(self._script_path)} in default editor")
        except Exception as e:
            self._log_message(f"Error opening editor: {e}")

    def _on_execute_clicked(self):
        """Execute the selected script."""
        if not self._script_path:
            return

        if not os.path.exists(self._script_path):
            self._log_message(f"Error: Script file not found: {self._script_path}")
            return

        if self.is_running():
            self._log_message("A script is already running.")
            return

        if not self.has_valid_script():
            self._log_message(f"Error: {os.path.basename(self._script_path)} is not a script of the script folder")
            return

        # Clear script output only
        self._script_output_text.clear()

        # Setup logging if enabled
        if self._log_checkbox.isChecked():
            self._setup_log_file()

        # Update UI state
        self._execute_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status_label.setText("Running...")
        self._status_label.setStyleSheet("color: #0078d4;")

        # Log messages go to Log tab
        self._log_message(f"Script started: {os.path.basename(self._script_path)}")

        # Check if x2cscope is available
        x2cscope = self._app_state.x2cscope
        if x2cscope:
            self._log_message("x2cscope instance available")
        else:
            self._log_message("x2cscope not connected (variable will be None)")

        # Create and start worker thread
        self._worker = ScriptWorker(self._script_path, x2cscope, self)
        self._worker.output_ready.connect(self._on_script_output)
        self._worker.finished_with_code.connect(self._on_script_finished)
        self._worker.start()

        # The script cannot be changed while it runs
        self._script_combo.setEnabled(False)
        self.script_started.emit()

    def _on_script_output(self, text: str):
        """Handle output from the script worker - goes to Script Output tab."""
        self._append_script_output(text)

    def _on_script_finished(self, exit_code: int):
        """Handle script completion."""
        self._log_message(f"Script finished with exit code {exit_code}")

        # Close log file if open
        if self._log_file:
            self._log_file.close()
            self._log_file = None

        # Update UI state (Execute and the dropdown follow in _update_combo below)
        self._stop_btn.setEnabled(False)

        if exit_code == 0:
            self._status_label.setText("Completed")
            self._status_label.setStyleSheet("color: green;")
        else:
            self._status_label.setText(f"Finished (code {exit_code})")
            self._status_label.setStyleSheet("color: orange;")

        self._worker = None
        self._update_combo()
        self.script_finished.emit(exit_code)

    def _on_stop_clicked(self):
        """Stop the running script."""
        if self.is_running():
            self._worker.request_stop()
            self._log_message("Stop requested (may not work for blocking operations)")
            self._status_label.setText("Stop requested...")
            self._status_label.setStyleSheet("color: orange;")

    def _log_message(self, message: str):
        """Add a timestamped message to the Log tab."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"

        cursor = self._log_output_text.textCursor()
        cursor.movePosition(cursor.End)
        if not self._log_output_text.toPlainText().endswith("\n") and self._log_output_text.toPlainText():
            cursor.insertText("\n")
        cursor.insertText(formatted)
        self._log_output_text.setTextCursor(cursor)
        self._log_output_text.ensureCursorVisible()

        # Also write to log file if enabled
        if self._log_file:
            try:
                self._log_file.write(f"{formatted}\n")
                self._log_file.flush()
            except Exception:
                pass

    def _append_script_output(self, text: str):
        """Append text to the Script Output tab."""
        cursor = self._script_output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self._script_output_text.setTextCursor(cursor)
        self._script_output_text.ensureCursorVisible()

        # Write to log file if enabled
        if self._log_file:
            try:
                self._log_file.write(text)
                self._log_file.flush()
            except Exception:
                pass

    def _setup_log_file(self):
        """Setup log file for script output."""
        if not self._log_file_path:
            self._log_message("Warning: No log file path specified")
            return

        try:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(self._log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            self._log_file = open(self._log_file_path, "a", encoding="utf-8")

            # Write header
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log_file.write(f"\n{'='*60}\n")
            self._log_file.write(f"Script execution started: {timestamp}\n")
            self._log_file.write(f"Script: {self._script_path}\n")
            self._log_file.write(f"{'='*60}\n\n")
            self._log_file.flush()

            self._log_message(f"Logging to: {self._log_file_path}")
        except Exception as e:
            self._log_message(f"Warning: Could not create log file: {e}")
            self._log_file = None

    def on_connection_changed(self, connected: bool):
        """Handle connection state change."""
        # Update info about x2cscope availability
        if connected:
            self._status_label.setText("Ready (x2cscope available)")
            self._log_message("Connection established - x2cscope now available")
        else:
            self._status_label.setText("Ready (x2cscope not connected)")
            self._log_message("Disconnected - x2cscope not available")


class ScriptRunControl(QWidget):
    """Script dropdown, Run/Stop button and status for the script of the Scripting tab.

    Placed on the Data Views tab, so a script can be picked, started and its effect watched
    in WatchView and ScopeView without switching tabs. The dropdown lists the scripts of the
    script folder of the Scripting tab and shares its model. The button is disabled until a
    script is loaded.
    """

    RUN_TEXT = "Run Script"
    STOP_TEXT = "Stop Script"
    NO_SCRIPT_TIP = "Load a script in the Scripting tab to run it from here."
    NO_FOLDER_TIP = "Select a script folder in the Scripting tab to list its scripts here."
    NO_VALID_SCRIPT_TIP = "No valid script selected: pick a script of the script folder in the dropdown."

    def __init__(self, scripting_tab: ScriptingTab, parent=None):
        """Initialize the control and follow the state of the Scripting tab.

        Args:
            scripting_tab: The Scripting tab that holds and runs the script.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._scripting_tab = scripting_tab

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._combo = ScriptComboBox()
        self._combo.setModel(scripting_tab.script_model)
        self._combo.setMinimumWidth(SCRIPT_COMBO_MIN_WIDTH)
        self._combo.activated.connect(self._on_combo_activated)
        self._combo.popup_about_to_show.connect(scripting_tab.refresh_scripts)
        layout.addWidget(self._combo)

        self._button = QPushButton(self.RUN_TEXT)
        self._button.setFixedSize(110, 28)
        self._button.clicked.connect(self._on_clicked)
        layout.addWidget(self._button)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #666;")
        layout.addWidget(self._status_label)

        scripting_tab.script_selected.connect(self._update)
        scripting_tab.script_started.connect(self._on_started)
        scripting_tab.script_finished.connect(self._on_finished)
        scripting_tab.scripts_changed.connect(self._update)
        self._update()

    @property
    def button(self) -> QPushButton:
        """The Run/Stop button."""
        return self._button

    @property
    def combo(self) -> QComboBox:
        """The dropdown with the scripts of the script folder."""
        return self._combo

    def _on_combo_activated(self, index: int):
        """Load the script picked in the dropdown into the Scripting tab."""
        path = self._scripting_tab.script_at(index)
        if path and not same_path(path, self._scripting_tab.script_path):
            self._scripting_tab.set_script(path)
            self._status_label.setText("")

    @property
    def status_text(self) -> str:
        """The status shown beside the button."""
        return self._status_label.text()

    def _on_clicked(self):
        """Start the script, or request it to stop when it is running."""
        if self._scripting_tab.is_running():
            self._scripting_tab.stop_script()
            self._status_label.setText("Stop requested...")
        else:
            self._scripting_tab.run_script()

    def _on_started(self):
        """Show the running state."""
        self._status_label.setText("Running...")
        self._status_label.setStyleSheet("color: #0078d4;")
        self._update()

    def _on_finished(self, exit_code: int):
        """Show the result of the last run; details are in the Scripting tab output."""
        if exit_code == 0:
            self._status_label.setText("Completed")
            self._status_label.setStyleSheet("color: green;")
        else:
            self._status_label.setText(f"Finished (code {exit_code}), see Scripting tab")
            self._status_label.setStyleSheet("color: orange;")
        self._update()

    def _update(self, *_args):
        """Update the dropdown and the button text, icon, tooltip and enabled state."""
        script_path = self._scripting_tab.script_path
        running = self._scripting_tab.is_running()

        has_scripts = self._scripting_tab.script_model.rowCount() > 0
        self._scripting_tab.sync_combo(self._combo)
        self._combo.setEnabled(has_scripts and not running)
        if not self._scripting_tab.script_folder:
            self._combo.setToolTip(self.NO_FOLDER_TIP)

        icon = QStyle.SP_MediaStop if running else QStyle.SP_MediaPlay
        self._button.setIcon(self.style().standardIcon(icon))
        self._button.setText(self.STOP_TEXT if running else self.RUN_TEXT)
        # While running, the button must stay enabled to stop the script
        self._button.setEnabled(running or self._scripting_tab.has_valid_script())
        if not script_path:
            self._button.setToolTip(self.NO_SCRIPT_TIP)
        elif not running and not self._scripting_tab.has_valid_script():
            self._button.setToolTip(self.NO_VALID_SCRIPT_TIP)
        else:
            action = "Stop" if running else "Run"
            self._button.setToolTip(f"{action} {os.path.basename(script_path)}")
