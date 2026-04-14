"""Help tab for the Qt GUI application."""

import platform
import sys

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import pyx2cscope


class HelpTab(QWidget):
    """Help tab containing links to GitHub, release notes, and version info."""

    def __init__(self, parent=None):
        """Initialize the help tab."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        layout.addWidget(self._create_release_group())
        layout.addWidget(self._create_github_group())
        layout.addWidget(self._create_version_group())
        layout.addWidget(self._create_resources_group())
        layout.addStretch()

    def _create_release_group(self):
        """Create the Release Notes and Documentation group box."""
        group = QGroupBox("Release Notes and Documentation")
        group_layout = QVBoxLayout(group)

        info = QLabel("View the latest release notes, changelog, and documentation.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; margin-bottom: 10px;")
        group_layout.addWidget(info)

        button_layout = QHBoxLayout()

        self.release_notes_btn = QPushButton("View Release Notes")
        self.release_notes_btn.clicked.connect(self._open_release_notes)
        button_layout.addWidget(self.release_notes_btn)

        self.documentation_btn = QPushButton("Documentation")
        self.documentation_btn.clicked.connect(self._open_documentation)
        button_layout.addWidget(self.documentation_btn)
        button_layout.addStretch()

        group_layout.addLayout(button_layout)
        return group

    def _create_github_group(self):
        """Create the Report Issues and Request Features group box."""
        group = QGroupBox("Report Issues and Request Features")
        group_layout = QVBoxLayout(group)

        info = QLabel(
            "If you encounter bugs, have feature requests, or need help, "
            "please open an issue on our GitHub repository."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; margin-bottom: 10px;")
        group_layout.addWidget(info)

        button_layout = QHBoxLayout()

        self.github_issues_btn = QPushButton("Open GitHub Issues")
        self.github_issues_btn.clicked.connect(self._open_github_issues)
        button_layout.addWidget(self.github_issues_btn)

        self.github_repo_btn = QPushButton("Visit Repository")
        self.github_repo_btn.clicked.connect(self._open_github_repo)
        button_layout.addWidget(self.github_repo_btn)
        button_layout.addStretch()

        group_layout.addLayout(button_layout)
        return group

    def _create_version_group(self):
        """Create the Software Versions group box."""
        group = QGroupBox("Software Versions")
        group_layout = QVBoxLayout(group)

        info = QLabel("Current software and dependency versions:")
        info.setStyleSheet("color: #666; margin-bottom: 10px;")
        group_layout.addWidget(info)

        self.version_text = QTextEdit()
        self.version_text.setReadOnly(True)
        self.version_text.setMaximumHeight(250)
        self.version_text.setStyleSheet(
            "QTextEdit { "
            "background-color: #f8f9fa; "
            "border: 1px solid #dee2e6; "
            "border-radius: 4px; "
            "padding: 10px; "
            "font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 10pt; "
            "}"
        )
        self._populate_version_info()
        group_layout.addWidget(self.version_text)
        return group

    def _create_resources_group(self):
        """Create the Additional Resources group box."""
        group = QGroupBox("Additional Resources")
        group_layout = QVBoxLayout(group)

        text = QLabel(
            "For additional support and resources:\n"
            "• Check the examples directory for usage examples\n"
            "• Review the README file for installation instructions\n"
            "• Join our community discussions on GitHub\n"
            "• Visit the documentation for detailed guides"
        )
        text.setWordWrap(True)
        text.setStyleSheet("color: #666; line-height: 1.8; padding: 5px;")
        group_layout.addWidget(text)
        return group

    def _open_github_issues(self):
        """Open GitHub issues page in default browser."""
        QDesktopServices.openUrl(QUrl("https://github.com/X2Cscope/pyx2cscope/issues"))

    def _open_github_repo(self):
        """Open GitHub repository page in default browser."""
        QDesktopServices.openUrl(QUrl("https://github.com/X2Cscope/pyx2cscope"))

    def _open_release_notes(self):
        """Open GitHub releases page in default browser."""
        QDesktopServices.openUrl(QUrl("https://github.com/X2Cscope/pyx2cscope/releases"))

    def _open_documentation(self):
        """Open documentation in default browser."""
        QDesktopServices.openUrl(QUrl("https://x2cscope.github.io/pyx2cscope/"))

    @staticmethod
    def _get_module_version(import_name, version_attr="__version__"):
        """Return the version string for a module, or 'Not installed' on failure."""
        try:
            module = __import__(import_name)
            return getattr(module, version_attr, "Unknown")
        except ImportError:
            return "Not installed"

    def _populate_version_info(self):
        """Populate the version information text area."""
        lines = []

        lines.append("=== Application ===")
        lines.append(f"pyX2Cscope: {pyx2cscope.__version__}")

        lines.append("\n=== Core Dependencies ===")
        lines.append(f"mchplnet: {self._get_module_version('mchplnet')}")
        lines.append(f"python-can: {self._get_module_version('can')}")
        lines.append(f"numpy: {self._get_module_version('numpy')}")
        lines.append(f"matplotlib: {self._get_module_version('matplotlib')}")
        lines.append(f"pyserial: {self._get_module_version('serial', 'VERSION')}")
        lines.append(f"pyelftools: {self._get_module_version('elftools')}")

        lines.append("\n=== GUI Framework ===")
        try:
            from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
            lines.append(f"Qt: {QT_VERSION_STR}")
            lines.append(f"PyQt5: {PYQT_VERSION_STR}")
        except ImportError:
            lines.append("PyQt5: Not available")

        lines.append("\n=== System Information ===")
        lines.append(f"Python: {sys.version.split()[0]}")
        lines.append(f"Platform: {platform.platform()}")
        lines.append(f"Architecture: {platform.architecture()[0]}")

        processor = platform.processor()
        if processor:
            lines.append(f"Processor: {processor}")

        self.version_text.setPlainText("\n".join(lines))
