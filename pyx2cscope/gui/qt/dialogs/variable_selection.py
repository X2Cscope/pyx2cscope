"""Variable selection dialog for searching and selecting variables."""

from typing import List, Optional

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QVBoxLayout,
)


class VariableSelectionDialog(QDialog):
    """Dialog for searching and selecting a variable from a list.

    Provides a search bar, an SFR toggle to switch between firmware variables
    and Special Function Registers, and a list to select from.
    Double-clicking or pressing OK selects the highlighted variable.
    """

    def __init__(self, variables: List[str], parent=None, sfr_variables: Optional[List[str]] = None):
        """Initialize the variable selection dialog.

        Args:
            variables: A list of firmware variable names to select from.
            parent: The parent widget.
            sfr_variables: An optional list of SFR names. When provided the SFR
                toggle checkbox is enabled and the user can switch between the two
                namespaces.
        """
        super().__init__(parent)
        self._variables = variables
        self._sfr_variables: List[str] = sfr_variables or []
        self._active_list = self._variables

        self.selected_variable: Optional[str] = None
        self.sfr_selected: bool = False  # True when the selected name is an SFR

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface components."""
        self.setWindowTitle("Search Variable")
        self.setMinimumSize(300, 400)

        layout = QVBoxLayout()

        # --- Search bar + SFR toggle row ---
        search_row = QHBoxLayout()

        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self._filter_variables)
        search_row.addWidget(self.search_bar)

        self.sfr_checkbox = QCheckBox("SFR", self)
        self.sfr_checkbox.setEnabled(bool(self._sfr_variables))
        self.sfr_checkbox.setToolTip(
            "Search Special Function Registers instead of firmware variables"
        )
        self.sfr_checkbox.stateChanged.connect(self._on_sfr_toggled)
        search_row.addWidget(self.sfr_checkbox)

        layout.addLayout(search_row)

        # Variable list
        self.variable_list = QListWidget(self)
        self.variable_list.addItems(self._active_list)
        self.variable_list.itemDoubleClicked.connect(self._accept_selection)
        layout.addWidget(self.variable_list)

        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.button_box.accepted.connect(self._accept_selection)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def _on_sfr_toggled(self, state: int):
        """Switch the active variable list when the SFR checkbox changes.

        Args:
            state: Qt checkbox state (Qt.Checked or Qt.Unchecked).
        """
        from PyQt5.QtCore import Qt

        self._active_list = (
            self._sfr_variables if state == Qt.Checked else self._variables
        )
        self.search_bar.clear()
        self._filter_variables("")

    def _filter_variables(self, text: str):
        """Filter the variables based on user input in the search bar.

        Args:
            text: The input text to filter variables.
        """
        self.variable_list.clear()
        filtered = [var for var in self._active_list if text.lower() in var.lower()]
        self.variable_list.addItems(filtered)

    def _accept_selection(self):
        """Accept the selection when a variable is chosen from the list."""
        selected_items = self.variable_list.selectedItems()
        if selected_items:
            self.selected_variable = selected_items[0].text()
            self.sfr_selected = self.sfr_checkbox.isChecked()
            self.accept()
