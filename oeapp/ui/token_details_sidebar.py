"""Token details sidebar widget."""

import re
from typing import TYPE_CHECKING, Final, cast
from urllib.parse import quote

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from oeapp.ui.mixins import AnnotationLookupsMixin

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token


class TokenDetailsSidebar(AnnotationLookupsMixin, QWidget):
    """
    Sidebar widget displaying detailed token information.  The sidebar displays
    the token's surface form, its annotations, and its dictionary entry, Modern
    English Meaning, Uncertainty, Alternatives, and Confidence.

    It is displayed to the right of the text editor, and is populated when a
    token is selected in the text editor.

    Args:
        parent: Parent widget

    """

    #: URL for the Bosworth-Toller dictionary search.  The placeholder is
    #: for the root value.
    DICTIONARY_URL: Final[str] = "https://bosworthtoller.com/search?q={}"
    #: Size of the book icon in pixels.  This is used for the Bosworth-Toller
    #: dictionary icon.
    BOOK_ICON_SIZE: Final[int] = 16
    #: SVG data for the book icon.  This is used for the Bosworth-Toller
    #: dictionary icon.
    BOOK_ICON_SVG: Final[str] = """
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path stroke="none" d="M0 0h24v24H0z" fill="none"/>
<path d="M3 19a9 9 0 0 1 9 0a9 9 0 0 1 9 0" />
<path d="M3 6a9 9 0 0 1 9 0a9 9 0 0 1 9 0" />
<path d="M3 6l0 13" />
<path d="M12 6l0 13" />
<path d="M21 6l0 13" />
</svg>"""  # noqa: E501

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the token details sidebar."""
        super().__init__(parent)
        self._current_token: Token | None = None
        self._current_sentence: Sentence | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area)

        # Show empty state initially
        self._show_empty_state()

    def _show_empty_state(self) -> None:
        """Show empty state with centered 'Word details' text."""
        self._clear_content()

        empty_label = QLabel("Word details")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setFont(QFont("Arial", 16))
        empty_label.setStyleSheet("color: #666;")

        self.content_layout.addStretch()
        self.content_layout.addWidget(empty_label)
        self.content_layout.addStretch()

    def _clear_content(self) -> None:
        """Clear all content from the sidebar."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _get_book_icon(self, size: int = 16) -> QIcon:
        """
        Create a book icon from the :attr:`BOOK_ICON_SVG`.

        Args:
            size: Size of the icon in pixels (default: 16)

        Returns:
            QIcon with the book icon

        """
        renderer = QSvgRenderer()
        renderer.load(self.BOOK_ICON_SVG.encode("utf-8"))

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)

    def _open_bosworth_toller(self, root_value: str) -> None:
        """
        Open the Bosworth-Toller dictionary search page for the given root value.

        Args:
            root_value: The root value to search for

        """
        # Remove hyphens, en-dashes, and em-dashes
        cleaned_root = re.sub(r"[-–—]", "", root_value)  # noqa: RUF001

        # URL-encode the cleaned root value
        encoded_root = quote(cleaned_root)

        # Construct URL
        url = QUrl(self.DICTIONARY_URL.format(encoded_root))

        # Open in default browser
        QDesktopServices.openUrl(url)

    def update_token(self, token: Token, sentence: Sentence) -> None:  # noqa: PLR0912, PLR0915
        """
        Update the sidebar with token details.

        Args:
            token: Token to display
            sentence: Sentence containing the token

        """
        self._current_token = token
        self._current_sentence = sentence
        self._clear_content()

        annotation = cast("Annotation", token.annotation)
        pos_str = ""
        gender_str = ""
        context_str = ""
        if annotation is not None:
            pos_str = annotation.format_pos(annotation)
            gender_str = annotation.format_gender(annotation)
            context_str = annotation.format_context(annotation)

        # Paragraph/sentence number label on its own line
        paragraph_num = sentence.paragraph_number
        sentence_num = sentence.sentence_number_in_paragraph
        number_label = QLabel(
            f"[{sentence.display_order}] ¶:{paragraph_num} S:{sentence_num}"
        )
        number_label.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        number_label.setStyleSheet("color: #333;")
        self.content_layout.addWidget(number_label)

        # Horizontal rule
        separator = QLabel("─" * 30)
        separator.setStyleSheet(
            "color: #ccc; font-family: Helvetica; font-weight: normal;"
        )
        self.content_layout.addWidget(separator)

        # Token surface with annotations
        style = "color: #666; font-family: Helvetica; font-weight: normal;"
        token_text = ""
        if pos_str:
            token_text += f"<sup style='{style}'>{pos_str}</sup>"
        if gender_str:
            token_text += f"<sub style='{style}'>{gender_str}</sub>"
        token_text += f"{token.surface}"
        if context_str:
            token_text += f"<sub style='{style}'>{context_str}</sub>"
        token_label = QLabel(token_text)
        token_label.setFont(QFont("Anvers", 18, QFont.Weight.Bold))
        token_label.setWordWrap(True)
        self.content_layout.addWidget(token_label)

        self.content_layout.addSpacing(10)

        if not annotation or not annotation.pos:
            # No annotation or POS set
            no_pos_label = QLabel("No annotation available")
            no_pos_label.setStyleSheet("color: #999; font-style: italic;")
            self.content_layout.addWidget(no_pos_label)
            return

        # Display POS
        pos_text = self.PART_OF_SPEECH_MAP.get(annotation.pos, "Unknown")
        if pos_text:
            pos_label = QLabel(f"Part of Speech: {pos_text}")
            pos_label.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
            self.content_layout.addWidget(pos_label)
            self.content_layout.addSpacing(5)

        # Display POS-specific fields
        if annotation.pos == "N":
            self._display_noun_fields(annotation)
        elif annotation.pos == "V":
            self._display_verb_fields(annotation)
        elif annotation.pos == "A":
            self._display_adjective_fields(annotation)
        elif annotation.pos == "R":
            self._display_pronoun_fields(annotation)
        elif annotation.pos == "D":
            self._display_article_fields(annotation)
        elif annotation.pos == "E":
            self._display_preposition_fields(annotation)
        elif annotation.pos == "B":
            self._display_adverb_fields(annotation)
        elif annotation.pos == "C":
            self._display_conjunction_fields(annotation)
        elif annotation.pos == "I":
            self._display_interjection_fields(annotation)

        # Common fields for all POS
        self.content_layout.addSpacing(10)
        separator = QLabel("─" * 30)
        separator.setStyleSheet(
            "color: #ccc; font-family: Helvetica; font-weight: normal;"
        )
        self.content_layout.addWidget(separator)
        self.content_layout.addSpacing(10)

        self._display_common_fields(annotation)

        self.content_layout.addStretch()

    def _display_common_fields(self, annotation: Annotation) -> None:
        """
        Display fields common to all POS types.

        Args:
            annotation: Annotation to display

        """
        # Root
        root_value = annotation.root if annotation.root else "?"
        root_label = QLabel(f"Root: {root_value}")
        self._format_field_label(root_label, annotation.root)

        # Create horizontal layout for root field with optional dictionary icon
        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(root_label)

        # Add dictionary icon button if root is not empty
        if annotation.root:
            dict_button = QPushButton()
            dict_button.setIcon(self._get_book_icon(self.BOOK_ICON_SIZE))
            dict_button.setToolTip("Open in Bosworth-Toller dictionary")
            dict_button.setFlat(True)
            dict_button.setStyleSheet(
                "QPushButton { border: none; padding: 2px; } "
                "QPushButton:hover { background-color: #f0f0f0; border-radius: 3px; }"
            )
            dict_button.clicked.connect(
                lambda _checked=False, rv=annotation.root: self._open_bosworth_toller(
                    rv
                )
            )
            root_layout.addWidget(dict_button)
            root_layout.addStretch()

        # Create a widget to hold the layout
        root_widget = QWidget()
        root_widget.setLayout(root_layout)
        self.content_layout.addWidget(root_widget)

        # Modern English Meaning
        mod_e_value = (
            annotation.modern_english_meaning
            if annotation.modern_english_meaning
            else "?"
        )
        mod_e_label = QLabel(f"Modern English Meaning: {mod_e_value}")
        mod_e_label.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self._format_field_label(mod_e_label, annotation.modern_english_meaning)
        self.content_layout.addWidget(mod_e_label)

        # Confidence
        confidence_value = (
            f"{annotation.confidence}%" if annotation.confidence is not None else "?"
        )
        confidence_label = QLabel(f"Confidence: {confidence_value}")
        self._format_field_label(confidence_label, annotation.confidence)
        self.content_layout.addWidget(confidence_label)

    def _format_field_label(
        self,
        label: QLabel,
        value: str | int | bool | None,  # noqa: FBT001
    ) -> None:
        """
        Format a field label based on whether value is set.

        Args:
            label: Label to format
            value: Field value (None or empty means unset)

        """
        if value is None or value == "" or value is False:
            label.setStyleSheet("color: #999; font-style: italic;")
        else:
            label.setStyleSheet(
                "color: #000; font-family: Helvetica; font-weight: normal;"
            )

    def _display_noun_fields(self, annotation: Annotation) -> None:
        """
        Display noun-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Gender
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        gender_label = QLabel(f"Gender: {gender_value}")
        self._format_field_label(gender_label, annotation.gender)
        self.content_layout.addWidget(gender_label)

        # Number
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        number_label = QLabel(f"Number: {number_value}")
        self._format_field_label(number_label, annotation.number)
        self.content_layout.addWidget(number_label)

        # Case
        case_value = self.CASE_MAP.get(annotation.case, "?")
        case_label = QLabel(f"Case: {case_value}")
        case_label.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self._format_field_label(case_label, annotation.case)
        self.content_layout.addWidget(case_label)

        # Declension
        declension_value = (
            self.DECLENSION_MAP.get(annotation.declension, "?")
            if annotation.declension is not None
            else "?"
        )
        declension_label = QLabel(f"Declension: {declension_value}")
        self._format_field_label(declension_label, annotation.declension)
        self.content_layout.addWidget(declension_label)

    def _display_verb_fields(self, annotation: Annotation) -> None:
        """
        Display verb-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Verb Class
        verb_class_value = self.VERB_CLASS_MAP.get(annotation.verb_class, "?")
        verb_class_label = QLabel(f"Verb Class: {verb_class_value}")
        self._format_field_label(verb_class_label, annotation.verb_class)
        self.content_layout.addWidget(verb_class_label)

        # Verb Tense
        tense_value = self.VERB_TENSE_MAP.get(annotation.verb_tense, "?")
        tense_label = QLabel(f"Tense: {tense_value}")
        self._format_field_label(tense_label, annotation.verb_tense)
        self.content_layout.addWidget(tense_label)

        # Verb Mood
        mood_value = self.VERB_MOOD_MAP.get(annotation.verb_mood, "?")
        mood_label = QLabel(f"Mood: {mood_value}")
        self._format_field_label(mood_label, annotation.verb_mood)
        self.content_layout.addWidget(mood_label)

        # Verb Person
        person_value = (
            self.VERB_PERSON_MAP.get(annotation.verb_person, "?")
            if annotation.verb_person is not None
            else "?"
        )
        person_label = QLabel(f"Person: {person_value}")
        self._format_field_label(person_label, annotation.verb_person)
        self.content_layout.addWidget(person_label)

        # Number
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        number_label = QLabel(f"Number: {number_value}")
        self._format_field_label(number_label, annotation.number)
        self.content_layout.addWidget(number_label)

        # Verb Aspect
        aspect_value = self.VERB_ASPECT_MAP.get(annotation.verb_aspect, "?")
        aspect_label = QLabel(f"Aspect: {aspect_value}")
        self._format_field_label(aspect_label, annotation.verb_aspect)
        self.content_layout.addWidget(aspect_label)

        # Verb Form
        form_value = self.VERB_FORM_MAP.get(annotation.verb_form, "?")
        form_label = QLabel(f"Form: {form_value}")
        self._format_field_label(form_label, annotation.verb_form)
        self.content_layout.addWidget(form_label)

    def _display_adjective_fields(self, annotation: Annotation) -> None:
        """
        Display adjective-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Note: Degree and inflection may not be directly stored in annotation model
        # For now, we'll show what's available

        # Gender
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        gender_label = QLabel(f"Gender: {gender_value}")
        self._format_field_label(gender_label, annotation.gender)
        self.content_layout.addWidget(gender_label)

        # Number
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        number_label = QLabel(f"Number: {number_value}")
        self._format_field_label(number_label, annotation.number)
        self.content_layout.addWidget(number_label)

        # Case
        case_value = self.CASE_MAP.get(annotation.case, "?")
        case_label = QLabel(f"Case: {case_value}")
        self._format_field_label(case_label, annotation.case)
        self.content_layout.addWidget(case_label)

    def _display_pronoun_fields(self, annotation: Annotation) -> None:
        """
        Display pronoun-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Pronoun Type
        pro_type_value = self.PRONOUN_TYPE_MAP.get(annotation.pronoun_type, "?")
        pro_type_label = QLabel(f"Pronoun Type: {pro_type_value}")
        self._format_field_label(pro_type_label, annotation.pronoun_type)
        self.content_layout.addWidget(pro_type_label)

        # Gender
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        gender_label = QLabel(f"Gender: {gender_value}")
        self._format_field_label(gender_label, annotation.gender)
        self.content_layout.addWidget(gender_label)

        # Number
        number_value = self.PRONOUN_NUMBER_MAP.get(annotation.pronoun_number, "?")
        number_label = QLabel(f"Number: {number_value}")
        self._format_field_label(number_label, annotation.number)
        self.content_layout.addWidget(number_label)

        # Case
        case_value = self.CASE_MAP.get(annotation.case, "?")
        case_label = QLabel(f"Case: {case_value}")
        self._format_field_label(case_label, annotation.case)
        self.content_layout.addWidget(case_label)

    def _display_article_fields(self, annotation: Annotation) -> None:
        """
        Display article/determiner-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Article Type
        article_type_value = self.ARTICLE_TYPE_MAP.get(annotation.article_type, "?")
        article_type_label = QLabel(f"Article Type: {article_type_value}")
        self._format_field_label(article_type_label, annotation.article_type)
        self.content_layout.addWidget(article_type_label)

        # Gender
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        gender_label = QLabel(f"Gender: {gender_value}")
        self._format_field_label(gender_label, annotation.gender)
        self.content_layout.addWidget(gender_label)

        # Number
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        number_label = QLabel(f"Number: {number_value}")
        self._format_field_label(number_label, annotation.number)
        self.content_layout.addWidget(number_label)

        # Case
        case_value = self.CASE_MAP.get(annotation.case, "?")
        case_label = QLabel(f"Case: {case_value}")
        self._format_field_label(case_label, annotation.case)
        self.content_layout.addWidget(case_label)

    def _display_preposition_fields(self, annotation: Annotation) -> None:
        """
        Display preposition-specific fields.

        Args:
            annotation: Annotation to display

        """
        # Preposition Case
        prep_case_value = self.PREPOSITION_CASE_MAP.get(annotation.prep_case, "?")
        prep_case_label = QLabel(f"Governed Case: {prep_case_value}")
        self._format_field_label(prep_case_label, annotation.prep_case)
        self.content_layout.addWidget(prep_case_label)

    def _display_adverb_fields(self, annotation: Annotation) -> None:
        """Display adverb-specific fields."""
        # Adverbs have minimal fields

    def _display_conjunction_fields(self, annotation: Annotation) -> None:
        """Display conjunction-specific fields."""
        # Conjunctions have minimal fields

    def _display_interjection_fields(self, annotation: Annotation) -> None:
        """Display interjection-specific fields."""
        # Interjections have minimal fields

    def clear(self) -> None:
        """Clear the sidebar and show empty state."""
        self._current_token = None
        self._current_sentence = None
        self._show_empty_state()
