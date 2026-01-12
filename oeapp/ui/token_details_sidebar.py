"""Token details sidebar widget."""

from typing import TYPE_CHECKING, Any, Final, cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from oeapp.exc import NoAnnotationAvailable
from oeapp.ui.mixins import AnnotationLookupsMixin
from oeapp.utils import clear_layout, open_bosworth_toller, render_svg

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.models.idiom import Idiom
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token


class FieldRenderer(AnnotationLookupsMixin):
    #: Style for label text (e.g. Part of Speech:)
    LABEL_STYLE: Final[str] = "color: #666; font-family: Helvetica; font-weight: bold;"
    #: Style for unset value text (e.g. ?)
    UNSET_VALUE_STYLE: Final[str] = "color: #999; font-style: italic;"
    #: Style for set value text (e.g. Dog)
    SET_VALUE_STYLE: Final[str] = "color: #333; font-family: Helvetica; "

    @classmethod
    def format_field(
        cls,
        label: str,
        value: Any,
        parent_layout: QVBoxLayout | QHBoxLayout,
        spacing: int = 25,
    ) -> None:
        """
        Format a field label based on whether value is set.

        Args:
            label: Label to format
            value: Field value (None or empty means unset)
            parent_layout: Parent layout to add the label widget to

        Keyword Args:
            spacing: Spacing between the label and the value

        """
        parent_widget = parent_layout.parentWidget()
        container = QHBoxLayout()
        container.setContentsMargins(0, 0, 0, 0)
        label_widget = QLabel(f"{label}: ", parent_widget)
        label_widget.setStyleSheet(cls.LABEL_STYLE)
        container.addWidget(label_widget)
        container.addSpacing(spacing)
        if isinstance(value, QWidget):
            container.addWidget(value)
        else:
            if value is None:
                value = "?"
            value_widget = QLabel(str(value), parent_widget)
            value_widget.setStyleSheet(cls.SET_VALUE_STYLE)
            container.addWidget(value_widget)
        parent_layout.addLayout(container)


class AbstractPartOfSpeechRenderer(AnnotationLookupsMixin):
    #: Font for part of speech label text (e.g. Part of Speech:)
    POS_LABEL_STYLE: Final[str] = (
        "color: #999; font-family: Helvetica; font-size: 18px;"
    )

    def __init__(self, annotation: Annotation | None) -> None:
        """
        Initialize the part of speech renderer.

        Args:
            annotation: Annotation to render

        """
        super().__init__()
        self.annotation: Annotation | None = annotation
        self.field_renderer = FieldRenderer

    def render(self, parent_layout: QVBoxLayout) -> None:
        """
        Render the part of speech.  This renders the part of speech label and
        the fields for the part of speech.  It also raises an error if no
        annotation is available.

        Args:
            parent_layout: Parent layout to add the fields to

        Raises:
            NoAnnotationAvailable: If no annotation is available

        """
        parent_widget = parent_layout.parentWidget()
        if not self.annotation or not self.annotation.pos:
            # No annotation or POS set
            no_pos_label = QLabel("No annotation available", parent_widget)
            no_pos_label.setStyleSheet("color: #999; font-style: italic;")
            parent_layout.addWidget(no_pos_label)
            raise NoAnnotationAvailable
        pos_text = self.PART_OF_SPEECH_MAP[self.annotation.pos]
        if self.annotation.idiom_id:
            pos_text += " (idiom)"
        if pos_text:
            pos_label = QLabel(pos_text, parent_widget)
            pos_label.setStyleSheet(self.POS_LABEL_STYLE)
            parent_layout.addWidget(pos_label)
            parent_layout.addSpacing(23)


class NounRenderer(AbstractPartOfSpeechRenderer):
    def render(self, parent_layout: QVBoxLayout) -> None:
        """
        Render the noun.  This renders these fields:

        - Gender
        - Number
        - Case
        - Declension

        Args:
            parent_layout: Parent layout to add the fields to

        """
        super().render(parent_layout)
        annotation = cast("Annotation", self.annotation)
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        self.field_renderer.format_field("Gender", gender_value, parent_layout)
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        self.field_renderer.format_field("Number", number_value, parent_layout)
        case_value = self.CASE_MAP.get(annotation.case, "?")
        self.field_renderer.format_field("Case", case_value, parent_layout)
        declension_value = (
            self.DECLENSION_MAP.get(annotation.declension, "?")
            if annotation.declension is not None
            else "?"
        )
        self.field_renderer.format_field("Declension", declension_value, parent_layout)


class VerbRenderer(AbstractPartOfSpeechRenderer):
    def render(self, parent_layout: QVBoxLayout) -> None:
        """
        Render the verb.  This renders these fields:

        - Verb Class
        - Verb Tense
        - Verb Mood
        - Verb Person
        - Number
        - Verb Aspect
        - Verb Form

        Args:
            parent_layout: Parent layout to add the fields to

        """
        super().render(parent_layout)
        annotation = cast("Annotation", self.annotation)
        verb_class_value = self.VERB_CLASS_MAP.get(annotation.verb_class, "?")
        self.field_renderer.format_field("Verb Class", verb_class_value, parent_layout)
        tense_value = self.VERB_TENSE_MAP.get(annotation.verb_tense, "?")
        self.field_renderer.format_field("Tense", tense_value, parent_layout)
        mood_value = self.VERB_MOOD_MAP.get(annotation.verb_mood, "?")
        self.field_renderer.format_field("Mood", mood_value, parent_layout)
        person_value = self.VERB_PERSON_MAP.get(annotation.verb_person, "?")
        self.field_renderer.format_field("Person", person_value, parent_layout)
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        self.field_renderer.format_field("Number", number_value, parent_layout)
        aspect_value = self.VERB_ASPECT_MAP.get(annotation.verb_aspect, "?")
        self.field_renderer.format_field("Aspect", aspect_value, parent_layout)
        form_value = self.VERB_FORM_MAP.get(annotation.verb_form, "?")
        self.field_renderer.format_field("Form", form_value, parent_layout)


class AdjectiveRenderer(AbstractPartOfSpeechRenderer):
    def render(self, parent_layout: QVBoxLayout) -> None:
        """
        Render the adjective.  This renders these fields:

        - Degree
        - Inflection
        - Gender
        - Number
        - Case

        Args:
            parent_layout: Parent layout to add the fields to

        """
        super().render(parent_layout)
        annotation = cast("Annotation", self.annotation)
        adjective_degree_value = self.ADJECTIVE_DEGREE_MAP.get(
            annotation.adjective_degree, "?"
        )
        self.field_renderer.format_field(
            "Degree", adjective_degree_value, parent_layout
        )
        adjective_inflection_value = self.ADJECTIVE_INFLECTION_MAP.get(
            annotation.adjective_inflection, "?"
        )
        self.field_renderer.format_field(
            "Inflection", adjective_inflection_value, parent_layout
        )
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        self.field_renderer.format_field("Gender", gender_value, parent_layout)
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        self.field_renderer.format_field("Number", number_value, parent_layout)
        case_value = self.CASE_MAP.get(annotation.case, "?")
        self.field_renderer.format_field("Case", case_value, parent_layout)


class PronounRenderer(AbstractPartOfSpeechRenderer):
    def render(self, parent_layout: QVBoxLayout) -> None:
        """
        Render the pronoun.  This renders these fields:

        - Pronoun Type
        - Gender
        - Number
        - Case

        Args:
            parent_layout: Parent layout to add the fields to

        """
        super().render(parent_layout)
        annotation = cast("Annotation", self.annotation)
        pronoun_type_value = self.PRONOUN_TYPE_MAP.get(annotation.pronoun_type, "?")
        self.field_renderer.format_field(
            "Pronoun Type", pronoun_type_value, parent_layout
        )
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        self.field_renderer.format_field("Gender", gender_value, parent_layout)
        number_value = self.PRONOUN_NUMBER_MAP.get(annotation.pronoun_number, "?")
        self.field_renderer.format_field("Number", number_value, parent_layout)
        case_value = self.CASE_MAP.get(annotation.case, "?")
        self.field_renderer.format_field("Case", case_value, parent_layout)


class ArticleRenderer(AbstractPartOfSpeechRenderer):
    def render(self, parent_layout: QVBoxLayout) -> None:
        """
        Render the article.  This renders these fields:

        - Article Type
        - Gender
        - Number
        - Case

        Args:
            parent_layout: Parent layout to add the fields to

        """
        super().render(parent_layout)
        annotation = cast("Annotation", self.annotation)
        article_type_value = self.ARTICLE_TYPE_MAP.get(annotation.article_type, "?")
        self.field_renderer.format_field(
            "Article Type", article_type_value, parent_layout
        )
        gender_value = self.GENDER_MAP.get(annotation.gender, "?")
        self.field_renderer.format_field("Gender", gender_value, parent_layout)
        number_value = self.NUMBER_MAP.get(annotation.number, "?")
        self.field_renderer.format_field("Number", number_value, parent_layout)
        case_value = self.CASE_MAP.get(annotation.case, "?")
        self.field_renderer.format_field("Case", case_value, parent_layout)


class PrepositionRenderer(AbstractPartOfSpeechRenderer):
    def render(self, parent_layout: QVBoxLayout) -> None:
        """
        Render the preposition.  This renders these fields:

        - Governed Case

        Args:
            parent_layout: Parent layout to add the fields to

        """
        super().render(parent_layout)
        annotation = cast("Annotation", self.annotation)
        preposition_case_value = self.PREPOSITION_CASE_MAP.get(
            annotation.prep_case, "?"
        )
        self.field_renderer.format_field(
            "Governed Case", preposition_case_value, parent_layout
        )


class AdverbRenderer(AbstractPartOfSpeechRenderer):
    def render(self, parent_layout: QVBoxLayout) -> None:
        """
        Render the adverb.  This renders these fields:

        - Adverb Degree

        Args:
            parent_layout: Parent layout to add the fields to

        """
        super().render(parent_layout)
        annotation = cast("Annotation", self.annotation)
        adverb_degree_value = self.ADVERB_DEGREE_MAP.get(annotation.adverb_degree, "?")
        self.field_renderer.format_field(
            "Adverb Degree", adverb_degree_value, parent_layout
        )


class ConjunctionRenderer(AbstractPartOfSpeechRenderer):
    def render(self, parent_layout: QVBoxLayout) -> None:
        """
        Render the conjunction.  This renders these fields:

        - Conjunction Type

        Args:
            parent_layout: Parent layout to add the fields to

        """
        super().render(parent_layout)
        annotation = cast("Annotation", self.annotation)
        conjunction_type_value = self.CONJUNCTION_TYPE_MAP.get(
            annotation.conjunction_type, "?"
        )
        self.field_renderer.format_field(
            "Conjunction Type", conjunction_type_value, parent_layout
        )


class InterjectionRenderer(AbstractPartOfSpeechRenderer):
    pass


class NumberRenderer(AbstractPartOfSpeechRenderer):
    pass


class NoneRenderer(AbstractPartOfSpeechRenderer):
    pass


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

    #: A lookup map for POS codes to their render method.  The key is the POS
    #: code, and the value is the name of the method to call to render the fields.
    POS_RENDER_MAP: Final[dict[str | None, type[AbstractPartOfSpeechRenderer]]] = {
        "N": NounRenderer,
        "V": VerbRenderer,
        "A": AdjectiveRenderer,
        "R": PronounRenderer,
        "D": ArticleRenderer,
        "E": PrepositionRenderer,
        "B": AdverbRenderer,
        "C": ConjunctionRenderer,
        "I": InterjectionRenderer,
        "L": NumberRenderer,
        "": NoneRenderer,
        None: NoneRenderer,
    }

    #: Font for line labels (e.g. [1] ¶:1 S:1)
    LINE_LABEL_FONT: Final[QFont] = QFont("Helvetica", 12, QFont.Weight.Bold)
    #: Style for line labels (e.g. [1] ¶:1 S:1)
    LINE_LABEL_STYLE: Final[str] = "color: #333;"

    #: Font for label text (e.g. Part of Speech: Noun)
    LABEL_FONT: Final[QFont] = QFont("Helvetica", 12, QFont.Weight.Bold)

    #: Style for superscript text (e.g. N) for the surface form
    SUP_STYLE: Final[str] = "color: #666; font-family: Helvetica; font-weight: normal;"
    #: Style for subscript text (e.g. M) for the surface form
    SUB_STYLE: Final[str] = SUP_STYLE
    #: Style for the token text (e.g. Dog) for the surface form
    TOKEN_STYLE: Final[str] = (
        "color: #000; font-family: Helvetica; font-weight: normal;"  # noqa: S105
    )
    TOKEN_FONT: Final[QFont] = QFont("Anvers", 18, QFont.Weight.Bold)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the token details sidebar."""
        super().__init__(parent)
        self._current_token: Token | None = None
        self._current_idiom: Idiom | None = None
        self._current_sentence: Sentence | None = None
        self.field_renderer = FieldRenderer
        self.build()

    def build(self) -> None:
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
        self.show_empty()

    def show_empty(self) -> None:
        """Show empty state with centered 'Word details' text."""
        self.clear_sidebar()
        self._current_token = None
        self._current_idiom = None
        self._current_sentence = None

        empty_label = QLabel("Word details", self.content_widget)
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setFont(QFont("Arial", 16))
        empty_label.setStyleSheet("color: #666;")

        self.content_layout.addStretch()
        self.content_layout.addWidget(empty_label)
        self.content_layout.addStretch()

    def clear_sidebar(self, layout: QVBoxLayout | QHBoxLayout | None = None) -> None:
        """
        Clear all content from the sidebar and reset the current token and
        sentence.
        """
        if not layout:
            layout = self.content_layout
        clear_layout(cast("QLayout", layout))

    def part_of_speech(self, annotation: Annotation) -> None:
        """
        Display the part of speech field and its associated fields.

        If the annotation has no part of speech, display a label indicating that
        no part of speech is available.

        Args:
            annotation: Annotation to display

        """
        if annotation is None:
            renderer = NoneRenderer(annotation)
            renderer.render(self.content_layout)
            return
        renderer = self.POS_RENDER_MAP[annotation.pos](annotation)
        renderer.render(self.content_layout)

    def rule(self) -> None:
        """Display a horizontal rule."""
        separator = QLabel("─" * 24, self.content_widget)
        separator.setStyleSheet(
            "color: #ccc; font-family: Helvetica; font-weight: normal;"
        )
        self.content_layout.addWidget(separator)
        self.content_layout.addSpacing(10)

    def surface_form(self, token: Token) -> None:
        """
        Display the surface form of the token.  This is the word plus
        annotations as superscript and subscript.

        Args:
            token: Token to display

        """
        annotation = cast("Annotation", token.annotation)
        if annotation is None:
            return
        gender_str = ""
        context_str = ""
        if annotation is not None:
            pos_str = annotation.format_pos(annotation)
            gender_str = annotation.format_gender(annotation)
            context_str = annotation.format_context(annotation)
        token_text = ""
        if pos_str:
            token_text += f"<sup style='{self.SUP_STYLE}'>{pos_str}</sup>"
        if gender_str:
            token_text += f"<sub style='{self.SUB_STYLE}'>{gender_str}</sub>"
        token_text += f"{token.surface}"
        if context_str:
            token_text += f"<sub style='{self.SUB_STYLE}'>{context_str}</sub>"
        token_label = QLabel(token_text, self.content_widget)
        token_label.setFont(self.TOKEN_FONT)
        token_label.setWordWrap(True)
        self.content_layout.addWidget(token_label)
        self.content_layout.addSpacing(10)

    def line_label(self, sentence: Sentence) -> None:
        """
        Display the line label for the given sentence.  The line label is
        displayed on its own line, and is used to identify the paragraph and
        sentence line of text in the source text.

        Example: [1] ¶:1 S:1

        Args:
            sentence: Sentence to display

        """
        number_label = QLabel(
            f"[{sentence.display_order}] ¶:{sentence.paragraph_number} S:{sentence.sentence_number_in_paragraph}",  # noqa: E501
            self.content_widget,
        )
        number_label.setFont(self.LINE_LABEL_FONT)
        number_label.setStyleSheet(self.LINE_LABEL_STYLE)
        self.content_layout.addWidget(number_label)

    def root(self, annotation: Annotation) -> None:
        """
        Display the root field and its associated dictionary icon button.

        Args:
            annotation: Annotation to display

        """
        # Root
        root_value = annotation.root if annotation.root else "?"
        if root_value == "?":
            self.field_renderer.format_field(
                "Root", root_value, parent_layout=self.content_layout
            )
        else:
            root_layout = QHBoxLayout()
            root_layout.setContentsMargins(0, 0, 0, 0)
            value_widget = QLabel(str(root_value), self.content_widget)
            value_widget.setStyleSheet(self.field_renderer.SET_VALUE_STYLE)
            root_layout.addWidget(value_widget)
            dict_button = QPushButton(self.content_widget)
            dict_button.setIcon(render_svg(self.BOOK_ICON_SVG, self.BOOK_ICON_SIZE))
            dict_button.setMaximumWidth(25)
            dict_button.setToolTip("Open in Bosworth-Toller dictionary")
            dict_button.setStyleSheet(
                "QPushButton { padding: 2px; } "
                "QPushButton:hover { background-color: #f0f0f0; border-radius: 3px; }"
            )
            dict_button.clicked.connect(
                lambda _checked=False, rv=annotation.root: open_bosworth_toller(rv)
            )
            root_layout.addWidget(dict_button)
            root_widget = QWidget(self.content_widget)
            root_widget.setLayout(root_layout)
            self.field_renderer.format_field(
                "Root", root_widget, parent_layout=self.content_layout
            )

    def modern_english_meaning(self, annotation: Annotation) -> None:
        """
        Display the modern English meaning field.

        Args:
            annotation: Annotation to display

        """
        # Modern English Meaning
        # Modern English Meaning Label
        mod_e_label = QLabel("Modern English Meaning:", self.content_widget)
        mod_e_label.setWordWrap(True)
        mod_e_label.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        if not annotation.modern_english_meaning:
            mod_e_label.setStyleSheet("color: #999; font-style: bold;")
            container = QHBoxLayout()
            container.setContentsMargins(0, 0, 0, 0)
            container.addWidget(mod_e_label)
            container.addSpacing(30)
            mod_e_value_label = QLabel("?", self.content_widget)
            container.addWidget(mod_e_value_label)
            self.content_layout.addLayout(container)
            return
        mod_e_label.setStyleSheet(
            "color: #000; font-family: Helvetica; font-weight: bold;"
        )
        self.content_layout.addWidget(mod_e_label)

        # Modern English Meaning Value
        mod_e_value_text = (
            annotation.modern_english_meaning
            if annotation.modern_english_meaning
            else "?"
        )
        mod_e_value_label = QLabel(mod_e_value_text, self.content_widget)
        mod_e_value_label.setWordWrap(True)
        self.content_layout.addWidget(mod_e_value_label)
        if not annotation.modern_english_meaning:
            mod_e_value_label.setStyleSheet("color: #999; font-style: italic;")
        else:
            mod_e_value_label.setStyleSheet(
                "background-color: #888; color: #fff; font-family: Helvetica; "
                "font-weight: normal; padding: 5px; border-radius: 3px;"
            )
            mod_e_value_label.setSizePolicy(
                mod_e_value_label.sizePolicy().horizontalPolicy(),
                mod_e_value_label.sizePolicy().verticalPolicy(),
            )
            mod_e_value_label.setMaximumWidth(
                int(mod_e_value_label.parentWidget().width() * 0.8)  # type: ignore[union-attr]
                if mod_e_value_label.parentWidget()
                else 16777215
            )
            mod_e_value_label.setMinimumWidth(0)
            mod_e_value_label.setMaximumHeight(16777215)

    def confidence(self, annotation: Annotation) -> None:
        """
        Display the confidence field.

        Args:
            annotation: Annotation to display

        """
        # Confidence
        confidence_value = (
            f"{annotation.confidence}%" if annotation.confidence is not None else "?"
        )
        self.field_renderer.format_field(
            "Confidence", confidence_value, parent_layout=self.content_layout
        )

    def render_token(self, token: Token, sentence: Sentence) -> None:
        """
        Update the sidebar with token details.

        Args:
            token: Token to display
            sentence: Sentence containing the token

        """
        self._current_token = token
        self._current_idiom = None
        self._current_sentence = sentence
        self.clear_sidebar()

        annotation = cast("Annotation", token.annotation)

        # Line label, e.g. [1] ¶:1 S:1
        self.line_label(sentence)
        # Horizontal rule
        self.rule()
        # Token surface form
        self.surface_form(token)
        self.rule()
        self.content_layout.addSpacing(10)
        try:
            self.part_of_speech(annotation)
        except NoAnnotationAvailable:
            return
        self.root(annotation)
        self.confidence(annotation)
        self.modern_english_meaning(annotation)
        self.content_layout.addStretch()

    def render_idiom(self, idiom: Idiom, sentence: Sentence) -> None:
        """
        Update the sidebar with idiom details.

        Args:
            idiom: Idiom to display
            sentence: Sentence containing the idiom

        """
        self._current_token = None
        self._current_idiom = idiom
        self._current_sentence = sentence
        self.clear_sidebar()

        annotation = cast("Annotation", idiom.annotation)

        # Line label, e.g. [1] ¶:1 S:1
        self.line_label(sentence)
        # Horizontal rule
        self.rule()

        # Idiom surface forms (all tokens joined)
        tokens, _ = sentence.sorted_tokens
        idiom_tokens = [
            t
            for t in tokens
            if idiom.start_token.order_index
            <= t.order_index
            <= idiom.end_token.order_index
        ]
        surface = " ".join(t.surface for t in idiom_tokens)

        # Similar to surface_form but for idiom
        pos_str = ""
        gender_str = ""
        context_str = ""
        if annotation is not None:
            pos_str = annotation.format_pos(annotation)
            gender_str = annotation.format_gender(annotation)
            context_str = annotation.format_context(annotation)

        text = ""
        if pos_str:
            text += f"<sup style='{self.SUP_STYLE}'>{pos_str}</sup>"
        if gender_str:
            text += f"<sub style='{self.SUB_STYLE}'>{gender_str}</sub>"
        text += f"{surface}"
        if context_str:
            text += f"<sub style='{self.SUB_STYLE}'>{context_str}</sub>"

        label = QLabel(text, self.content_widget)
        label.setFont(self.TOKEN_FONT)
        label.setWordWrap(True)
        self.content_layout.addWidget(label)

        self.rule()
        self.content_layout.addSpacing(10)

        if annotation:
            try:
                self.part_of_speech(annotation)
            except NoAnnotationAvailable:
                return
            self.root(annotation)
            self.confidence(annotation)
            self.modern_english_meaning(annotation)
        else:
            no_ann_label = QLabel(
                "No annotation available for this idiom.", self.content_widget
            )
            no_ann_label.setStyleSheet("color: #999; font-style: italic;")
            self.content_layout.addWidget(no_ann_label)

        self.content_layout.addStretch()

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    def _on_token_deselected(self) -> None:
        """
        Handle token deselection.
        """
        self.show_empty()

    def _on_token_selected(self, token: Token) -> None:
        """
        Handle token selection.
        """
        self.render_token(token, token.sentence)

    def _on_idiom_selected(self, idiom: Idiom) -> None:
        """
        Handle idiom selection.
        """
        self.render_idiom(idiom, idiom.sentence)
