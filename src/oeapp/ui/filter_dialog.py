"""Filter dialog for finding annotations."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGroupBox,
    QFormLayout,
    QDialogButtonBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.oeapp.services.filter import FilterService, FilterCriteria
from src.oeapp.models.token import Token


class FilterDialog(QDialog):
    """Dialog for filtering and finding annotations."""

    token_selected = Signal(int)  # Emits token_id when user selects a token

    def __init__(self, filter_service: FilterService, project_id: int, parent=None):
        """Initialize filter dialog.

        Args:
            filter_service: Filter service instance
            project_id: Current project ID
            parent: Parent widget
        """
        super().__init__(parent)
        self.filter_service = filter_service
        self.project_id = project_id
        self.current_results: list[dict] = []
        self._setup_ui()
        self._load_statistics()

    def _setup_ui(self):
        """Set up the UI layout."""
        self.setWindowTitle("Filter Annotations")
        self.setGeometry(100, 100, 900, 700)
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Filter and Find Annotations")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        # Statistics section
        stats_label = QLabel("Project Statistics")
        stats_font = QFont()
        stats_font.setBold(True)
        stats_label.setFont(stats_font)
        layout.addWidget(stats_label)
        self.stats_text = QLabel()
        self.stats_text.setWordWrap(True)
        layout.addWidget(self.stats_text)

        # Filter criteria section
        filter_group = QGroupBox("Filter Criteria")
        filter_layout = QFormLayout()

        # POS filter
        self.pos_combo = QComboBox()
        self.pos_combo.addItems([
            "Any POS",
            "Noun (N)",
            "Verb (V)",
            "Adjective (A)",
            "Pronoun (R)",
            "Determiner (D)",
            "Adverb (B)",
            "Conjunction (C)",
            "Preposition (E)",
            "Interjection (I)",
        ])
        filter_layout.addRow("Part of Speech:", self.pos_combo)

        # Incomplete filter
        self.incomplete_check = QCheckBox("Show only incomplete annotations")
        self.incomplete_check.setToolTip(
            "Find annotations missing required fields (e.g., verbs missing tense, nouns missing case)"
        )
        filter_layout.addRow("", self.incomplete_check)

        # Missing field filter
        self.missing_field_combo = QComboBox()
        self.missing_field_combo.addItems([
            "None",
            "Gender",
            "Number",
            "Case",
            "Verb Tense",
            "Verb Mood",
            "Verb Person",
            "Verb Class",
            "Pronoun Type",
            "Preposition Case",
        ])
        filter_layout.addRow("Missing Field:", self.missing_field_combo)

        # Uncertainty filter
        self.uncertain_combo = QComboBox()
        self.uncertain_combo.addItems([
            "All",
            "Uncertain only",
            "Certain only",
        ])
        filter_layout.addRow("Uncertainty:", self.uncertain_combo)

        # Confidence range
        confidence_layout = QHBoxLayout()
        self.min_confidence_spin = QSpinBox()
        self.min_confidence_spin.setRange(0, 100)
        self.min_confidence_spin.setSpecialValueText("Any")
        self.min_confidence_spin.setValue(0)
        confidence_layout.addWidget(QLabel("Min:"))
        confidence_layout.addWidget(self.min_confidence_spin)
        confidence_layout.addWidget(QLabel("Max:"))
        self.max_confidence_spin = QSpinBox()
        self.max_confidence_spin.setRange(0, 100)
        self.max_confidence_spin.setSpecialValueText("Any")
        self.max_confidence_spin.setValue(100)
        confidence_layout.addWidget(self.max_confidence_spin)
        confidence_layout.addStretch()
        filter_layout.addRow("Confidence:", confidence_layout)

        # Has alternatives
        self.has_alternatives_combo = QComboBox()
        self.has_alternatives_combo.addItems([
            "All",
            "With alternatives",
            "Without alternatives",
        ])
        filter_layout.addRow("Alternatives:", self.has_alternatives_combo)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Buttons
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply Filter")
        self.apply_button.clicked.connect(self._apply_filter)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear_filters)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Results table
        results_label = QLabel("Results")
        results_font = QFont()
        results_font.setBold(True)
        results_label.setFont(results_font)
        layout.addWidget(results_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Sentence",
            "Token",
            "POS",
            "Issues",
            "Uncertain",
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.doubleClicked.connect(self._on_result_double_clicked)
        layout.addWidget(self.results_table)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_statistics(self):
        """Load and display project statistics."""
        stats = self.filter_service.get_statistics(self.project_id)
        stats_text = (
            f"Total tokens: {stats['total_tokens']} | "
            f"Annotated: {stats['annotated_tokens']} | "
            f"Unannotated: {stats['unannotated_tokens']} | "
            f"Uncertain: {stats['uncertain_count']} | "
            f"Incomplete: {stats['incomplete_count']}"
        )
        if stats['pos_distribution']:
            pos_text = ", ".join([f"{pos}: {count}" for pos, count in stats['pos_distribution'].items()])
            stats_text += f"\nPOS distribution: {pos_text}"
        self.stats_text.setText(stats_text)

    def _apply_filter(self):
        """Apply filter criteria and show results."""
        criteria = FilterCriteria()

        # POS filter
        pos_text = self.pos_combo.currentText()
        if pos_text != "Any POS":
            pos_map = {
                "Noun (N)": "N",
                "Verb (V)": "V",
                "Adjective (A)": "A",
                "Pronoun (R)": "R",
                "Determiner (D)": "D",
                "Adverb (B)": "B",
                "Conjunction (C)": "C",
                "Preposition (E)": "E",
                "Interjection (I)": "I",
            }
            criteria.pos = pos_map.get(pos_text)

        # Incomplete filter
        criteria.incomplete = self.incomplete_check.isChecked()

        # Missing field filter
        missing_field_text = self.missing_field_combo.currentText()
        if missing_field_text != "None":
            field_map = {
                "Gender": "gender",
                "Number": "number",
                "Case": "case",
                "Verb Tense": "verb_tense",
                "Verb Mood": "verb_mood",
                "Verb Person": "verb_person",
                "Verb Class": "verb_class",
                "Pronoun Type": "pronoun_type",
                "Preposition Case": "prep_case",
            }
            criteria.missing_field = field_map.get(missing_field_text)

        # Uncertainty filter
        uncertain_text = self.uncertain_combo.currentText()
        if uncertain_text == "Uncertain only":
            criteria.uncertain = True
        elif uncertain_text == "Certain only":
            criteria.uncertain = False

        # Confidence range
        if self.min_confidence_spin.value() > 0:
            criteria.min_confidence = self.min_confidence_spin.value()
        if self.max_confidence_spin.value() < 100:
            criteria.max_confidence = self.max_confidence_spin.value()

        # Alternatives filter
        alternatives_text = self.has_alternatives_combo.currentText()
        if alternatives_text == "With alternatives":
            criteria.has_alternatives = True
        elif alternatives_text == "Without alternatives":
            criteria.has_alternatives = False

        # Execute filter
        try:
            self.current_results = self.filter_service.find_tokens(self.project_id, criteria)
            self._display_results()
        except Exception as e:
            QMessageBox.warning(self, "Filter Error", f"An error occurred while filtering:\n{str(e)}")

    def _display_results(self):
        """Display filter results in the table."""
        self.results_table.setRowCount(len(self.current_results))

        for row_idx, result in enumerate(self.current_results):
            # Sentence number
            sentence_item = QTableWidgetItem(f"[{result['sentence_order']}]")
            self.results_table.setItem(row_idx, 0, sentence_item)

            # Token
            token_item = QTableWidgetItem(result['surface'])
            self.results_table.setItem(row_idx, 1, token_item)

            # POS
            pos_item = QTableWidgetItem(result['pos'] or "—")
            self.results_table.setItem(row_idx, 2, pos_item)

            # Issues (missing fields)
            issues = []
            if result['pos'] == 'N':
                if not result['gender']:
                    issues.append("no gender")
                if not result['number']:
                    issues.append("no number")
                if not result['case']:
                    issues.append("no case")
            elif result['pos'] == 'V':
                if not result['verb_tense']:
                    issues.append("no tense")
                if not result['verb_mood']:
                    issues.append("no mood")
                if not result['verb_person']:
                    issues.append("no person")
                if not result['number']:
                    issues.append("no number")
            elif result['pos'] == 'A':
                if not result['gender']:
                    issues.append("no gender")
                if not result['number']:
                    issues.append("no number")
                if not result['case']:
                    issues.append("no case")
            elif result['pos'] == 'R':
                if not result['pronoun_type']:
                    issues.append("no type")
                if not result['gender']:
                    issues.append("no gender")
                if not result['number']:
                    issues.append("no number")
                if not result['case']:
                    issues.append("no case")
            elif result['pos'] == 'E':
                if not result['prep_case']:
                    issues.append("no case")

            issues_text = ", ".join(issues) if issues else "—"
            issues_item = QTableWidgetItem(issues_text)
            self.results_table.setItem(row_idx, 3, issues_item)

            # Uncertain
            uncertain_item = QTableWidgetItem("Yes" if result['uncertain'] else "No")
            self.results_table.setItem(row_idx, 4, uncertain_item)

        # Resize columns
        self.results_table.resizeColumnsToContents()

        # Show count
        if len(self.current_results) == 0:
            QMessageBox.information(self, "No Results", "No tokens match the filter criteria.")

    def _clear_filters(self):
        """Clear all filter criteria."""
        self.pos_combo.setCurrentIndex(0)
        self.incomplete_check.setChecked(False)
        self.missing_field_combo.setCurrentIndex(0)
        self.uncertain_combo.setCurrentIndex(0)
        self.min_confidence_spin.setValue(0)
        self.max_confidence_spin.setValue(100)
        self.has_alternatives_combo.setCurrentIndex(0)
        self.results_table.setRowCount(0)
        self.current_results = []

    def _on_result_double_clicked(self, index):
        """Handle double-click on result row."""
        if index.row() < len(self.current_results):
            token_id = self.current_results[index.row()]["token_id"]
            self.token_selected.emit(token_id)
            self.accept()

