# F4: Finish SentenceCard Controller Split; Stop Widget ORM Writes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish moving `SentenceCard`'s remaining direct ORM writes and hierarchy-command execution into the command layer / `SentenceCardController`, so the widget only builds UI and finalizes/highlights after a command runs.

**Architecture:** `SentenceCard` (`oeapp/ui/sentence_card.py`) currently bypasses the `Command`/`CommandManager` pattern in three places: an ORM-direct annotation-save fallback (`_save_annotation`), an unconditional `idiom.save()` before annotating a brand-new idiom, and six hierarchy commands (split/merge paragraph/section/chapter) constructed and executed directly in the widget instead of via `SentenceCardController` (`oeapp/ui/sentence_card_controller.py`). This plan (1) folds idiom creation into the existing `AnnotateTokenCommand` so "create idiom + annotate it" is one undoable action (see ADR 0002), (2) makes `command_manager` a required constructor argument so there is no ORM-direct fallback path at all, (3) moves hierarchy-command dispatch and the hierarchy-position query into `SentenceCardController`, (4) replaces the `sentence_added` signal misuse for hierarchy refreshes with a new dedicated `structure_changed` signal, and (5) removes `SessionMixin`/`self.session` from `SentenceCard` entirely, since nothing in the widget needs a raw session once the above lands.

**Tech Stack:** Python, PySide6 (Qt Widgets), SQLAlchemy ORM, pytest + pytest-qt.

**Spec:** Trello card "Audit F4: Finish SentenceCard controller split; stop widget ORM writes" (`https://trello.com/c/TSlJin6B`); design decisions recorded in `docs/adr/0002-idiom-creation-undo-deletes-rows.md`.

## Global Constraints

- `SentenceCard.__init__`'s `command_manager` parameter becomes required (`command_manager: CommandManager`, no default) — there is no code path where `SentenceCard` performs a direct ORM write when a command manager is absent, because it is no longer possible to construct a `SentenceCard` without one.
- No direct `Annotation.save()`, `Annotation.from_annotation()`, or `Idiom.save()` calls remain anywhere in `oeapp/ui/sentence_card.py` — all persistence goes through `Command` subclasses.
- `SentenceCard` no longer inherits `SessionMixin` and has no `self.session` attribute.
- Hierarchy command construction/execution (`SplitParagraphCommand`, `MergeParagraphCommand`, `SplitSectionCommand`, `MergeSectionCommand`, `SplitChapterCommand`, `MergeChapterCommand`) lives in `SentenceCardController`, not `SentenceCard`.
- A new `structure_changed = Signal(int)` on `SentenceCard` replaces `sentence_added` for hierarchy refreshes; `sentence_added` keeps its original meaning (a brand-new sentence was created via `AddSentenceCommand`).
- Idiom-creation undo/redo semantics follow ADR 0002: undo deletes the created `Idiom` row (its `Annotation` cascade-deletes via `Idiom.annotation`'s `cascade="all, delete-orphan"`); redo must not attempt to re-insert with a stale primary key.

---

## Task 1: Fold idiom creation into `AnnotateTokenCommand`

**Files:**
- Modify: `oeapp/commands/annotation.py:12-89` (`AnnotateTokenCommand`)
- Test: `tests/test_commands.py`

**Interfaces:**
- Consumes: `oeapp.models.idiom.Idiom` (existing: `sentence_id`, `start_token_id`, `end_token_id`, `id`, `.annotation` relationship with `cascade="all, delete-orphan"`); `oeapp.models.sentence.Sentence.get(sentence_id) -> Sentence | None` (existing classmethod).
- Produces: `AnnotateTokenCommand` gains two new optional dataclass fields — `new_idiom: Idiom | None = None` and `sentence_id: int | None = None` — appended after the existing `idiom_id` field (so existing positional-arg call sites like `AnnotateTokenCommand(token_id, before, after)` in `tests/test_commands.py:219` keep working unchanged). Later tasks (Task 3) construct `AnnotateTokenCommand` passing `new_idiom=` and `sentence_id=` when annotating a not-yet-persisted idiom.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_commands.py` (place near the other `AnnotateTokenCommand` tests, e.g. after the existing `test_execute_and_undo_new_annotation`):

```python
    def test_execute_creates_new_idiom_and_annotation(self, command_setup):
        """A new_idiom is persisted, linked, and refreshes the sentence collections."""
        from oeapp.models.idiom import Idiom
        from oeapp.models.sentence import Sentence
        from oeapp.models.token import Token

        setup = command_setup
        command_manager = setup["command_manager"]
        session = setup["session"]
        sentence_id = setup["sentence_id"]

        tokens = Token.list(sentence_id)
        assert len(tokens) >= 2
        start_token, end_token = tokens[0], tokens[1]

        new_idiom = Idiom(
            sentence_id=sentence_id,
            start_token_id=start_token.id,
            end_token_id=end_token.id,
        )

        before = {"pos": None, "confidence": None}
        after = {"pos": "N", "confidence": 90}

        command = AnnotateTokenCommand(
            before=before,
            after=after,
            new_idiom=new_idiom,
            sentence_id=sentence_id,
        )

        assert command_manager.execute(command)

        # The idiom was persisted and given a real id.
        assert new_idiom.id is not None
        assert command.idiom_id == new_idiom.id

        # The annotation was created and linked to the new idiom.
        annotation = Annotation.get_by_idiom(new_idiom.id)
        assert annotation is not None
        assert annotation.pos == "N"
        assert annotation.confidence == 90

        # The sentence's idiom/token collections were refreshed in-session.
        sentence = Sentence.get(sentence_id)
        assert any(i.id == new_idiom.id for i in sentence.idioms)

    def test_undo_new_idiom_deletes_idiom_and_annotation(self, command_setup):
        """Undoing a new-idiom annotation deletes the idiom (annotation cascades)."""
        from oeapp.models.idiom import Idiom
        from oeapp.models.token import Token

        setup = command_setup
        command_manager = setup["command_manager"]
        sentence_id = setup["sentence_id"]

        tokens = Token.list(sentence_id)
        start_token, end_token = tokens[0], tokens[1]

        new_idiom = Idiom(
            sentence_id=sentence_id,
            start_token_id=start_token.id,
            end_token_id=end_token.id,
        )

        command = AnnotateTokenCommand(
            before={"pos": None},
            after={"pos": "N"},
            new_idiom=new_idiom,
            sentence_id=sentence_id,
        )

        assert command_manager.execute(command)
        created_idiom_id = command.idiom_id

        assert command_manager.undo()

        assert Idiom.get(created_idiom_id) is None
        assert Annotation.get_by_idiom(created_idiom_id) is None

    def test_redo_new_idiom_recreates_idiom_and_annotation(self, command_setup):
        """Redo after undo must recreate the idiom, not reuse the deleted row's id."""
        from oeapp.models.idiom import Idiom
        from oeapp.models.token import Token

        setup = command_setup
        command_manager = setup["command_manager"]
        sentence_id = setup["sentence_id"]

        tokens = Token.list(sentence_id)
        start_token, end_token = tokens[0], tokens[1]

        new_idiom = Idiom(
            sentence_id=sentence_id,
            start_token_id=start_token.id,
            end_token_id=end_token.id,
        )

        command = AnnotateTokenCommand(
            before={"pos": None},
            after={"pos": "N"},
            new_idiom=new_idiom,
            sentence_id=sentence_id,
        )

        assert command_manager.execute(command)
        first_idiom_id = command.idiom_id

        assert command_manager.undo()
        assert Idiom.get(first_idiom_id) is None

        assert command_manager.redo()

        # Redo must have created a *new* idiom row (old id is gone for good).
        assert command.idiom_id is not None
        recreated = Idiom.get(command.idiom_id)
        assert recreated is not None
        annotation = Annotation.get_by_idiom(command.idiom_id)
        assert annotation is not None
        assert annotation.pos == "N"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_commands.py -k "new_idiom" -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'new_idiom'` (the field doesn't exist yet).

- [ ] **Step 3: Implement the new fields and updated execute/undo**

In `oeapp/commands/annotation.py`, add the import and the two new fields, then replace `execute`/`undo`:

```python
from oeapp.models.annotation import Annotation
from oeapp.models.idiom import Idiom
from oeapp.models.mixins import SessionMixin
from oeapp.models.sentence import Sentence

from .abstract import Command


@dataclass
class AnnotateTokenCommand(SessionMixin, Command):
    """Command for annotating a token or idiom, optionally creating the idiom first."""

    #: The token ID.
    token_id: int | None = None
    #: The before state of the annotation.
    before: dict[str, Any] = field(default_factory=dict)
    #: The after state of the annotation.
    after: dict[str, Any] = field(default_factory=dict)
    #: The idiom ID.
    idiom_id: int | None = None
    #: A not-yet-persisted Idiom to create before annotating it. When set,
    #: undo deletes this idiom (its annotation cascade-deletes with it)
    #: instead of just blanking the annotation's fields. See ADR 0002.
    new_idiom: Idiom | None = None
    #: Sentence the annotated token/idiom belongs to, used to refresh the
    #: sentence's ``tokens``/``idioms`` relationship collections after a new
    #: idiom is linked in. Required whenever ``new_idiom`` is set.
    sentence_id: int | None = None

    @property
    def annotation(self) -> Annotation | None:
        """
        Get the current annotation.

        IF :attr:`token_id` is not None, get the annotation by token ID.
        IF :attr:`idiom_id` is not None, get the annotation by idiom ID.
        If both are None, return None.

        Returns:
            Annotation or None if not found

        """
        if self.token_id:
            return Annotation.get_by_token(self.token_id)
        if self.idiom_id:
            return Annotation.get_by_idiom(self.idiom_id)
        return None

    def execute(self) -> bool:
        """
        Execute annotation update, creating the idiom first if needed.

        If :attr:`new_idiom` is set, persist it first and use its id as
        :attr:`idiom_id`. The id is reset to ``None`` before every insert so
        a redo after a prior undo (which deleted the row) gets a fresh
        primary key rather than reusing the deleted one.

        If the annotation does not exist, create a new one with the given
        token or idiom ID, and update the annotation with the new data.

        Returns:
            True if the annotation was updated, False otherwise

        """
        session = self._get_session()

        if self.new_idiom is not None:
            self.new_idiom.id = None
            session.add(self.new_idiom)
            session.flush()
            self.idiom_id = self.new_idiom.id

        annotation = self.annotation
        if annotation is None:
            annotation = Annotation(token_id=self.token_id, idiom_id=self.idiom_id)
            session.add(annotation)
            session.flush()
        annotation.from_json(annotation.token_id, self.after, annotation.idiom_id)

        if self.idiom_id is not None and self.sentence_id is not None:
            sentence = Sentence.get(self.sentence_id)
            if sentence is not None:
                session.refresh(sentence, ["tokens", "idioms"])

        return True

    def undo(self) -> bool:
        """
        Undo annotation update.

        When :attr:`new_idiom` is set, deletes the created idiom (its
        annotation cascade-deletes with it) rather than blanking fields,
        per ADR 0002.

        Returns:
            True if there was an annotation/idiom to restore, False otherwise

        """
        if self.new_idiom is not None:
            if self.idiom_id is not None:
                idiom = Idiom.get(self.idiom_id)
                if idiom is not None:
                    session = self._get_session()
                    session.delete(idiom)
                    session.flush()
            return True

        annotation = self.annotation
        if annotation is None:
            return False
        annotation.from_json(annotation.token_id, self.before, annotation.idiom_id)
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            The computed value.

        """
        target = f"token {self.token_id}" if self.token_id else f"idiom {self.idiom_id}"
        return f"Annotate {target}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_commands.py -v`
Expected: PASS (all existing `AnnotateTokenCommand`/`CommandManager` tests plus the three new ones).

- [ ] **Step 5: Commit**

```bash
git add oeapp/commands/annotation.py tests/test_commands.py
git commit -m "feat: fold idiom creation into AnnotateTokenCommand (ADR 0002)"
```

---

## Task 2: Move hierarchy dispatch and position query into `SentenceCardController`

**Files:**
- Modify: `oeapp/ui/sentence_card_controller.py`
- Test: `tests/test_sentence_card_hierarchy.py`

**Interfaces:**
- Consumes: `oeapp.commands.paragraph.{SplitParagraphCommand, MergeParagraphCommand}`, `oeapp.commands.hierarchy.{SplitSectionCommand, MergeSectionCommand, SplitChapterCommand, MergeChapterCommand}` (existing, constructed with `sentence_id=` or `paragraph_id=`/`section_id=` as shown in `oeapp/ui/sentence_card.py:1078-1116`); `card.command_manager.execute(command) -> bool` (existing).
- Produces: `SentenceCardController.get_hierarchy_position(sentence: Sentence) -> HierarchyPosition` (new dataclass, also defined in this file) with boolean attributes `is_paragraph_start`, `is_section_start`, `is_chapter_start`. Six new controller methods — `on_split_paragraph_clicked`, `on_merge_paragraph_clicked`, `on_split_section_clicked`, `on_merge_section_clicked`, `on_split_chapter_clicked`, `on_merge_chapter_clicked` — each taking no arguments (they read `self.card.sentence`) and returning `bool` (whether the command executed successfully). Task 3 calls both of these from `SentenceCard`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_sentence_card_hierarchy.py` (after the existing dropdown-state tests):

```python
from oeapp.ui.sentence_card_controller import HierarchyPosition


def test_get_hierarchy_position_middle_of_paragraph(db_session, hierarchy_project):
    project, s1, s2, s3 = hierarchy_project
    s1.display_order = 1
    s2.display_order = 2
    s3.display_order = 3
    db_session.commit()

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager)

    position = card.controller.get_hierarchy_position(s2)

    assert position == HierarchyPosition(
        is_paragraph_start=False, is_section_start=False, is_chapter_start=False
    )


def test_get_hierarchy_position_chapter_start(db_session, hierarchy_project):
    project, s1, s2, s3 = hierarchy_project

    ch2 = Chapter(project_id=project.id, number=2)
    db_session.add(ch2)
    db_session.flush()
    sec2 = Section(chapter_id=ch2.id, number=1)
    db_session.add(sec2)
    db_session.flush()
    p2 = Paragraph(section_id=sec2.id, order=1)
    db_session.add(p2)
    db_session.flush()
    s2.paragraph_id = p2.id
    db_session.commit()

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager)

    position = card.controller.get_hierarchy_position(s2)

    assert position == HierarchyPosition(
        is_paragraph_start=True, is_section_start=True, is_chapter_start=True
    )


def test_on_split_paragraph_clicked_executes_command_via_controller(
    db_session, hierarchy_project
):
    project, s1, s2, s3 = hierarchy_project

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager)

    assert card.controller.on_split_paragraph_clicked() is True
    db_session.refresh(s2)
    assert s2.paragraph_id != s1.paragraph_id


def test_on_merge_paragraph_clicked_returns_false_when_command_manager_missing(
    db_session, hierarchy_project, monkeypatch
):
    project, s1, s2, s3 = hierarchy_project

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager)
    monkeypatch.setattr(card, "command_manager", None)

    assert card.controller.on_merge_paragraph_clicked() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sentence_card_hierarchy.py -v`
Expected: FAIL — `ImportError: cannot import name 'HierarchyPosition'` (doesn't exist yet), and `AttributeError: 'SentenceCardController' object has no attribute 'get_hierarchy_position'`.

- [ ] **Step 3: Implement `HierarchyPosition` and the controller methods**

Add to `oeapp/ui/sentence_card_controller.py` — new imports, the dataclass, and the seven new methods:

```python
from dataclasses import dataclass

from oeapp.commands import (
    AddSentenceCommand,
    DeleteSentenceCommand,
    EditSentenceCommand,
    MergeSentenceCommand,
)
from oeapp.commands.hierarchy import (
    MergeChapterCommand,
    MergeSectionCommand,
    SplitChapterCommand,
    SplitSectionCommand,
)
from oeapp.commands.paragraph import MergeParagraphCommand, SplitParagraphCommand
```

(Add these two new imports alongside the existing `from oeapp.commands import (...)` block; leave the rest of the file's imports as-is.)

```python
@dataclass(frozen=True)
class HierarchyPosition:
    """Where a sentence sits in the paragraph/section/chapter hierarchy."""

    #: Whether the sentence is the first in its paragraph.
    is_paragraph_start: bool
    #: Whether the sentence's paragraph is the first in its section.
    is_section_start: bool
    #: Whether the sentence's paragraph's section is the first in its chapter.
    is_chapter_start: bool
```

Add these methods to `SentenceCardController` (place after `on_delete_clicked`, before `open_annotation_modal`):

```python
    def get_hierarchy_position(self, sentence: Sentence) -> HierarchyPosition:
        """
        Classify where a sentence sits in the paragraph/section/chapter hierarchy.

        Args:
            sentence: Sentence to classify.

        Returns:
            The sentence's hierarchy position.

        """
        if not sentence.paragraph:
            return HierarchyPosition(
                is_paragraph_start=False,
                is_section_start=False,
                is_chapter_start=False,
            )

        sentences = sorted(
            sentence.paragraph.sentences, key=lambda s: s.display_order
        )
        is_paragraph_start = bool(sentences) and sentences[0].id == sentence.id

        is_section_start = False
        if is_paragraph_start:
            paragraphs = sorted(
                sentence.paragraph.section.paragraphs, key=lambda p: p.order
            )
            is_section_start = (
                bool(paragraphs) and paragraphs[0].id == sentence.paragraph.id
            )

        is_chapter_start = False
        if is_section_start:
            sections = sorted(
                sentence.paragraph.section.chapter.sections, key=lambda s: s.number
            )
            is_chapter_start = (
                bool(sections)
                and sections[0].id == sentence.paragraph.section.id
            )

        return HierarchyPosition(
            is_paragraph_start=is_paragraph_start,
            is_section_start=is_section_start,
            is_chapter_start=is_chapter_start,
        )

    def on_split_paragraph_clicked(self) -> bool:
        """
        Execute a split-paragraph command for the current sentence.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if not card.command_manager or not card.sentence.id:
            return False
        return card.command_manager.execute(
            SplitParagraphCommand(sentence_id=card.sentence.id)
        )

    def on_merge_paragraph_clicked(self) -> bool:
        """
        Execute a merge-paragraph command for the current sentence.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if not card.command_manager or not card.sentence.id:
            return False
        return card.command_manager.execute(
            MergeParagraphCommand(sentence_id=card.sentence.id)
        )

    def on_split_section_clicked(self) -> bool:
        """
        Execute a split-section command for the current sentence's paragraph.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if not card.command_manager or not card.sentence.paragraph:
            return False
        return card.command_manager.execute(
            SplitSectionCommand(paragraph_id=card.sentence.paragraph.id)
        )

    def on_merge_section_clicked(self) -> bool:
        """
        Execute a merge-section command for the current sentence's paragraph.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if not card.command_manager or not card.sentence.paragraph:
            return False
        return card.command_manager.execute(
            MergeSectionCommand(paragraph_id=card.sentence.paragraph.id)
        )

    def on_split_chapter_clicked(self) -> bool:
        """
        Execute a split-chapter command for the current sentence's section.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if (
            not card.command_manager
            or not card.sentence.paragraph
            or not card.sentence.paragraph.section
        ):
            return False
        return card.command_manager.execute(
            SplitChapterCommand(section_id=card.sentence.paragraph.section.id)
        )

    def on_merge_chapter_clicked(self) -> bool:
        """
        Execute a merge-chapter command for the current sentence's section.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if (
            not card.command_manager
            or not card.sentence.paragraph
            or not card.sentence.paragraph.section
        ):
            return False
        return card.command_manager.execute(
            MergeChapterCommand(section_id=card.sentence.paragraph.section.id)
        )
```

Also add, near the top of `tests/test_sentence_card_hierarchy.py`, the missing import used by the new tests (the file already imports `Chapter`, `Section`, `Paragraph`, `CommandManager`):

```python
from oeapp.ui.sentence_card_controller import HierarchyPosition
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sentence_card_hierarchy.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add oeapp/ui/sentence_card_controller.py tests/test_sentence_card_hierarchy.py
git commit -m "feat: move hierarchy command dispatch and position query into SentenceCardController"
```

---

## Task 3: Rewire `SentenceCard` — require `command_manager`, delete ORM-direct writes, add `structure_changed`

**Files:**
- Modify: `oeapp/ui/sentence_card.py`
- Test: `tests/test_sentence_card.py`

**Interfaces:**
- Consumes: `SentenceCardController.get_hierarchy_position` and the six `on_*_clicked` methods from Task 2; `AnnotateTokenCommand(new_idiom=, sentence_id=)` from Task 1.
- Produces: `SentenceCard.__init__(sentence, command_manager, main_window=None, parent=None)` — `command_manager` is now positional-or-keyword and required (no default, no `| None`). `SentenceCard.structure_changed = Signal(int)` — new signal, emits the current sentence's id. `_save_annotation` is deleted. `SentenceCard` no longer inherits `SessionMixin` and has no `self.session`.

- [ ] **Step 1: Write the failing tests**

Replace the two existing tests that call the private `_save_annotation` directly in `tests/test_sentence_card.py` (`test_save_annotation_updates_existing` and `test_save_annotation_updates_existing_idiom`, currently at lines 455-510) with versions that go through the public annotation-applied path and a real `CommandManager`:

```python
    def test_annotation_applied_updates_existing_token_annotation(
        self, db_session, qapp, mock_main_window
    ):
        """Applying a token annotation updates the existing row via the command."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        token = sentence.tokens[0]

        existing = Annotation.get_by_token(token.id)
        if not existing:
            existing = Annotation(token_id=token.id, pos="V")
            existing.save()
        else:
            existing.pos = "V"
            existing.save()

        card = SentenceCard(
            sentence,
            command_manager=CommandManager(db_session),
            main_window=mock_main_window,
            parent=None,
        )

        new_ann = Annotation(token_id=token.id, pos="N")
        card._on_annotation_applied(new_ann)

        updated = Annotation.get_by_token(token.id)
        assert updated.pos == "N"

    def test_annotation_applied_updates_existing_idiom_annotation(
        self, db_session, qapp, mock_main_window
    ):
        """Applying an idiom annotation updates the existing row via the command."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        token1 = sentence.tokens[0]
        token2 = sentence.tokens[1]

        idiom = Idiom(
            sentence_id=sentence.id, start_token_id=token1.id, end_token_id=token2.id
        )
        idiom.save()

        existing = Annotation(idiom_id=idiom.id, pos="V")
        existing.save()

        card = SentenceCard(
            sentence,
            command_manager=CommandManager(db_session),
            main_window=mock_main_window,
            parent=None,
        )

        new_ann = Annotation(idiom_id=idiom.id, pos="N")
        card._on_annotation_applied(new_ann)

        updated = Annotation.get_by_idiom(idiom.id)
        assert updated.pos == "N"

    def test_idiom_annotation_applied_creates_idiom_via_command(
        self, db_session, qapp, mock_main_window
    ):
        """A brand-new idiom is created through the command, not idiom.save()."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        token1 = sentence.tokens[0]
        token2 = sentence.tokens[1]

        card = SentenceCard(
            sentence,
            command_manager=CommandManager(db_session),
            main_window=mock_main_window,
            parent=None,
        )

        new_idiom = Idiom(
            sentence_id=sentence.id,
            start_token_id=token1.id,
            end_token_id=token2.id,
        )
        annotation = Annotation(pos="N")
        annotation.idiom = new_idiom

        card._on_idiom_annotation_applied(annotation)

        assert new_idiom.id is not None
        saved = Annotation.get_by_idiom(new_idiom.id)
        assert saved is not None
        assert saved.pos == "N"

    def test_sentence_card_requires_command_manager(
        self, db_session, qapp, mock_main_window
    ):
        """SentenceCard cannot be constructed without a command_manager."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]

        with pytest.raises(TypeError):
            SentenceCard(sentence, main_window=mock_main_window, parent=None)

    def test_sentence_card_has_no_session_attribute(
        self, db_session, qapp, mock_main_window
    ):
        """SentenceCard no longer carries a raw session (SessionMixin removed)."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        card = SentenceCard(
            sentence,
            command_manager=CommandManager(db_session),
            main_window=mock_main_window,
            parent=None,
        )
        assert not hasattr(card, "session")

    def test_hierarchy_action_emits_structure_changed_not_sentence_added(
        self, db_session, qapp, mock_main_window
    ):
        """A hierarchy toggle emits structure_changed, never sentence_added."""
        project = create_test_project(db_session, name="Test", text="Se cyning fēoll")
        sentence = project.sentences[0]
        # This project has one paragraph and one sentence, so display_order == 1
        # and the paragraph button would be hidden; force it into a splittable
        # position by adding a second sentence to the same paragraph.
        from oeapp.commands import AddSentenceCommand

        command_manager = CommandManager(db_session)
        add_command = AddSentenceCommand(
            project_id=project.id, reference_sentence_id=sentence.id, position="after"
        )
        command_manager.execute(add_command)
        db_session.refresh(sentence)
        second = sentence.paragraph.sentences[-1]

        card = SentenceCard(
            second,
            command_manager=command_manager,
            main_window=mock_main_window,
            parent=None,
        )

        structure_changed_ids = []
        sentence_added_ids = []
        card.structure_changed.connect(structure_changed_ids.append)
        card.sentence_added.connect(sentence_added_ids.append)

        card._on_split_paragraph_clicked()

        assert structure_changed_ids == [second.id]
        assert sentence_added_ids == []
```

Also add, near the top of `tests/test_sentence_card.py`, any missing imports (the file already imports `Annotation`, `Idiom`, `SentenceCard`; confirm `CommandManager` is imported — it already is, per `tests/test_sentence_card.py:334`; add `import pytest` if not already present).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sentence_card.py -k "annotation_applied or requires_command_manager or no_session_attribute or structure_changed" -v`
Expected: FAIL — old `_save_annotation`-based tests are gone so those specific failures won't appear, but the new tests fail because `SentenceCard` still accepts `command_manager=None`, still has `self.session`, and `_execute_hierarchy_command` still emits `sentence_added`.

- [ ] **Step 3: Implement the widget changes**

In `oeapp/ui/sentence_card.py`:

3a. Update imports — remove the now-unused hierarchy-command imports and `SessionMixin` (they move to/are no longer needed):

```python
from oeapp.commands import (
    AnnotateTokenCommand,
    CommandManager,
)
from oeapp.mixins import TokenOccurrenceMixin
from oeapp.models import Annotation, Idiom
from oeapp.models.sentence import Sentence
from oeapp.ui.dialogs import NoteDialog
from oeapp.ui.highlighting import SearchHighlighter, WholeSentenceHighlighter
from oeapp.ui.mixins import AnnotationLookupsMixin
from oeapp.ui.notes_panel import NotesPanel
from oeapp.ui.oe_text_edit import OldEnglishTextEdit
from oeapp.ui.sentence_card_controller import HierarchyPosition, SentenceCardController
from oeapp.ui.token_table import TokenTable
```

(Remove the `from oeapp.commands.hierarchy import (...)`, `from oeapp.commands.paragraph import (...)`, and `from oeapp.models.mixins import SessionMixin` import lines entirely.)

3b. Update the class declaration and add the new signal (near `sentence_added`):

```python
class SentenceCard(AnnotationLookupsMixin, TokenOccurrenceMixin, QWidget):
```

```python
    #: Signal emitted when a sentence is added
    sentence_added = Signal(int)  # Emits new sentence ID
    #: Signal emitted when the paragraph/section/chapter hierarchy changes
    #: around this sentence (split/merge). Distinct from sentence_added:
    #: no new sentence exists, so listeners must not enter edit mode or
    #: flash the card.
    structure_changed = Signal(int)  # Emits current sentence ID
```

3c. Update `__init__` — require `command_manager`, drop `self.session`:

```python
    def __init__(
        self,
        sentence: Sentence,
        command_manager: CommandManager,
        main_window: "MainWindow | None" = None,
        parent: QWidget | None = None,
    ):
        """
        Initialize the instance.

        Args:
            sentence: Sentence.
            command_manager: Command manager. Required — SentenceCard has no
                ORM-direct fallback for persistence.
            main_window: Main window.
            parent: Parent.

        """
        super().__init__(parent)
        #: The sentence this card represents
        self.sentence = sentence
        #: The command manager for this card
        self.command_manager = command_manager
        #: The main window this card belongs to
        self.main_window = main_window
```

(Remove the `self.session = self._get_session()` line entirely; leave the rest of `__init__` — `token_table`, `sentence_highlighter`, etc. — unchanged.)

3d. Replace `_finalize_annotation_update` (the refresh now happens inside `AnnotateTokenCommand.execute`, so the widget just reads the already-refreshed collections):

```python
    def _finalize_annotation_update(self, annotation: Annotation) -> None:
        """
        Update local caches and UI after annotation is applied.

        Args:
            annotation: Annotation that was applied

        """
        if annotation.token_id:
            self.oe_text_edit.annotations[annotation.token_id] = annotation
            self.token_table.update_annotation(annotation)
        elif annotation.idiom_id:
            self.oe_text_edit.set_tokens()
            self.oe_text_edit.render_readonly_text()

        self.annotation_applied.emit(annotation)
        self.sentence_highlighter.highlight()
```

3e. Delete `_save_annotation` entirely (the whole method, `oeapp/ui/sentence_card.py:844-863` in the pre-change file).

3f. Replace `_on_idiom_annotation_applied` and `_on_annotation_applied`:

```python
    def _on_idiom_annotation_applied(self, annotation: Annotation) -> None:
        """
        Handle annotation applied for a new idiom (needs creation).

        The idiom is created by the same command that applies the
        annotation — see :meth:`_execute_annotate_command` and ADR 0002.

        Args:
            annotation: Annotation applied for the new idiom

        """
        self._on_annotation_applied(annotation)

    def _on_annotation_applied(self, annotation: Annotation) -> None:
        """
        Handle annotation applied signal.

        Args:
            annotation: Annotation applied

        """
        before_state = self._get_annotation_state(annotation)
        after_state = self._extract_annotation_state(annotation)

        self._execute_annotate_command(annotation, before_state, after_state)
        self._finalize_annotation_update(annotation)
```

3g. Replace `_execute_annotate_command` to detect and pass the not-yet-persisted idiom:

```python
    def _execute_annotate_command(
        self, annotation: Annotation, before: dict, after: dict
    ) -> None:
        """
        Execute the annotate command via command manager.  This will handle the
        actual save or update of the annotation and also handle the undo/redo
        operations, creating the idiom first if this annotation is for a
        brand-new (not-yet-persisted) idiom.

        Args:
            annotation: Annotation to execute the command for
            before: Before state of the annotation
            after: After state of the annotation

        """
        new_idiom = None
        if annotation.idiom_id is None and annotation.idiom is not None:
            new_idiom = annotation.idiom

        command = AnnotateTokenCommand(
            token_id=annotation.token_id,
            idiom_id=annotation.idiom_id,
            before=before,
            after=after,
            new_idiom=new_idiom,
            sentence_id=self.sentence.id,
        )
        if self.command_manager.execute(command):
            if new_idiom is not None:
                annotation.idiom_id = command.idiom_id
```

3h. Replace `_update_paragraph_button_state`, splitting the menu-building into its own method and delegating hierarchy classification to the controller:

```python
    def _update_paragraph_button_state(self) -> None:
        """
        Update the toggle paragraph button text and visibility based on current state.
        """
        if not self.sentence.paragraph:
            self.toggle_paragraph_button.setVisible(False)
            return

        # Hide button for first sentence of project
        if self.sentence.display_order == 1:
            self.toggle_paragraph_button.setVisible(False)
            return

        self.paragraph_menu.clear()
        position = self.controller.get_hierarchy_position(self.sentence)
        self.toggle_paragraph_button.setVisible(True)
        self._build_paragraph_menu(position)

    def _build_paragraph_menu(self, position: HierarchyPosition) -> None:
        """
        Populate the paragraph dropdown menu for a given hierarchy position.

        Args:
            position: Hierarchy position of the current sentence.

        """
        if not position.is_paragraph_start:
            # Case A: Middle of paragraph
            action = self.paragraph_menu.addAction("Paragraph Start")
            action.triggered.connect(self._on_split_paragraph_clicked)
        elif not position.is_section_start:
            # Case B: Paragraph start, but not section start
            action_not_p = self.paragraph_menu.addAction("Not Paragraph Start")
            action_not_p.triggered.connect(self._on_merge_paragraph_clicked)
            action_section = self.paragraph_menu.addAction("Section Start")
            action_section.triggered.connect(self._on_split_section_clicked)
        elif not position.is_chapter_start:
            # Case C: Section start, but not chapter start
            action_not_p = self.paragraph_menu.addAction("Not Paragraph Start")
            action_not_p.triggered.connect(self._on_merge_paragraph_clicked)
            action_not_s = self.paragraph_menu.addAction("Not Section Start")
            action_not_s.triggered.connect(self._on_merge_section_clicked)
            action_chapter = self.paragraph_menu.addAction("Chapter Start")
            action_chapter.triggered.connect(self._on_split_chapter_clicked)
        else:
            # Case D: Chapter start
            action_not_p = self.paragraph_menu.addAction("Not Paragraph Start")
            action_not_p.triggered.connect(self._on_merge_paragraph_clicked)
            action_not_s = self.paragraph_menu.addAction("Not Section Start")
            action_not_s.triggered.connect(self._on_merge_section_clicked)
            action_not_c = self.paragraph_menu.addAction("Not Chapter Start")
            action_not_c.triggered.connect(self._on_merge_chapter_clicked)
```

3i. Replace the six `_on_*_clicked` hierarchy handlers and `_execute_hierarchy_command`:

```python
    def _on_split_paragraph_clicked(self) -> None:
        """Handle Split Paragraph action."""
        self._finish_hierarchy_action(self.controller.on_split_paragraph_clicked())

    def _on_merge_paragraph_clicked(self) -> None:
        """Handle Merge Paragraph action."""
        self._finish_hierarchy_action(self.controller.on_merge_paragraph_clicked())

    def _on_split_section_clicked(self) -> None:
        """Handle Split Section action."""
        self._finish_hierarchy_action(self.controller.on_split_section_clicked())

    def _on_merge_section_clicked(self) -> None:
        """Handle Merge Section action."""
        self._finish_hierarchy_action(self.controller.on_merge_section_clicked())

    def _on_split_chapter_clicked(self) -> None:
        """Handle Split Chapter action."""
        self._finish_hierarchy_action(self.controller.on_split_chapter_clicked())

    def _on_merge_chapter_clicked(self) -> None:
        """Handle Merge Chapter action."""
        self._finish_hierarchy_action(self.controller.on_merge_chapter_clicked())

    def _finish_hierarchy_action(self, executed: bool) -> None:
        """
        Update UI after a hierarchy command dispatched via the controller.

        Args:
            executed: Whether the controller reported successful execution.

        """
        if executed:
            self._update_paragraph_button_state()
            self.sentence_number_label.setText(self._line_reference_text())
            if self.sentence.id:
                self.structure_changed.emit(self.sentence.id)
        else:
            QMessageBox.warning(
                self,
                "Action Failed",
                "Failed to perform hierarchy action. Please try again.",
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sentence_card.py tests/test_sentence_card_hierarchy.py -v`
Expected: PASS. (This will also surface `TypeError: missing 1 required positional argument: 'command_manager'` failures in every other `SentenceCard(...)` call site across the test suite that omits it — those are fixed in Task 5, not this task. Confirm the failures you see here are all inside `tests/test_sentence_card.py`/`tests/test_sentence_card_hierarchy.py` and pass; ignore failures reported from other test files for now.)

- [ ] **Step 5: Commit**

```bash
git add oeapp/ui/sentence_card.py tests/test_sentence_card.py
git commit -m "refactor: require command_manager on SentenceCard, remove ORM-direct writes, add structure_changed signal"
```

---

## Task 4: Wire `structure_changed` in `ProjectWorkspace`

**Files:**
- Modify: `oeapp/ui/project_workspace.py`
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `SentenceCard.structure_changed` signal (Task 3); `ProjectWorkspace._reload_after_structure_change(*, clear_search: bool, message: str | None = None) -> bool` (existing); `ProjectWorkspace.find_sentence_card(sentence_id) -> SentenceCard | None` (existing); `MainWindow.ensure_visible(card) -> None` (existing).
- Produces: `ProjectWorkspace._on_structure_changed(sentence_id: int) -> None`, connected to `card.structure_changed` in `_connect_card_signals`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_main_window.py`, right after `test_on_sentence_added_defers_focus_to_new_card` (mirrors its structure, but asserts no edit-mode/flash side effects):

```python
    def test_on_structure_changed_scrolls_without_edit_mode_or_flash(
        self, main_window
    ):
        """A hierarchy change should scroll to the card but not edit/flash it."""
        project_ui = main_window.project_ui
        main_window.app_context.current_project_id = 1

        project = MagicMock()
        target_card = MagicMock()
        target_card.sentence.id = 42

        with (
            patch("oeapp.ui.project_workspace.Project.get", return_value=project),
            patch.object(
                project_ui,
                "_reload_after_structure_change",
                return_value=True,
            ),
            patch.object(project_ui, "find_sentence_card", return_value=target_card),
            patch.object(main_window, "reload_main_window"),
            patch.object(main_window, "ensure_visible") as mock_ensure_visible,
            patch("oeapp.ui.project_workspace.QTimer.singleShot") as mock_single_shot,
        ):
            project_ui._on_structure_changed(42)

            mock_single_shot.assert_called_once()
            scheduled_delay, scheduled_callback = mock_single_shot.call_args.args
            assert scheduled_delay == 0

            scheduled_callback()
            mock_ensure_visible.assert_called_once_with(target_card)
            target_card.enter_edit_mode.assert_not_called()
            target_card.flash_added.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main_window.py -k test_on_structure_changed_scrolls_without_edit_mode_or_flash -v`
Expected: FAIL — `AttributeError: 'ProjectWorkspace' object has no attribute '_on_structure_changed'`.

- [ ] **Step 3: Implement `_on_structure_changed` and wire the signal**

In `oeapp/ui/project_workspace.py`, add the connection in `_connect_card_signals` (right after `card.sentence_deleted.connect(self._on_sentence_deleted)`):

```python
        card.structure_changed.connect(self._on_structure_changed)
```

Add the handler right after `_on_sentence_added` (before `_on_sentence_deleted`):

```python
    def _on_structure_changed(self, sentence_id: int) -> None:
        """
        Handle hierarchy structure changed signal.

        Reloads the project from the database to refresh all sentence cards
        after a paragraph/section/chapter split or merge, then scrolls back
        to the same sentence card — but does not enter edit mode or flash it,
        since nothing was "added".

        Args:
            sentence_id: ID of the sentence whose hierarchy context changed

        """
        if not self._reload_after_structure_change(clear_search=True):
            return

        card = self.find_sentence_card(sentence_id)

        if card:
            _card = cast("SentenceCard", card)

            def _scroll_to_card(card: SentenceCard = _card) -> None:
                self.main_window.ensure_visible(card)

            QTimer.singleShot(0, _scroll_to_card)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main_window.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add oeapp/ui/project_workspace.py tests/test_main_window.py
git commit -m "feat: reload and rescroll on structure_changed without treating it as sentence_added"
```

---

## Task 5: Add `command_manager` to every remaining bare `SentenceCard(...)` test call site

**Files:**
- Modify (as needed, discovered per Step 1's grep — expected candidates based on current repo state): `tests/test_annotation_copy_paste.py`, `tests/test_annotation_integration.py`, `tests/test_annotation_propagation.py`, `tests/test_highlighting.py`, `tests/test_idioms.py`, `tests/test_notes_panel.py`, `tests/test_oe_text_edit.py`, `tests/test_selection_edges.py`, `tests/test_sentence_card.py` (remaining call sites not already touched in Task 3), `tests/test_token_selection_robustness.py`, `tests/test_user_repro_clicks.py`

**Interfaces:**
- Consumes: `SentenceCard.__init__`'s now-required `command_manager` parameter (Task 3); `CommandManager(db_session)` (existing, already used this way in `tests/test_sentence_card.py:334` and `tests/test_oe_text_edit.py:176`).
- Produces: nothing new — this task only removes `TypeError`s at construction time. No new public interface.

This task is mechanical and self-verifying: making `command_manager` required means every remaining bad call site fails loudly at collection/run time with an unambiguous error, so there is no need to hand-enumerate every line up front — find them by running the suite and fixing what breaks.

- [ ] **Step 1: Run the full suite to enumerate every failure**

Run: `pytest --tb=line 2>&1 | grep -B5 "missing 1 required positional argument: 'command_manager'" | grep "tests/" `

This prints the file:line of every remaining `SentenceCard(...)` call missing `command_manager`. (If your pytest version's `--tb=line` output doesn't show the call-site file:line directly, run `pytest --tb=short` instead and read the traceback's last `tests/...py:LINE` frame for each failure.)

- [ ] **Step 2: Fix each call site**

For each file surfaced in Step 1:

1. If the file does not already `from oeapp.commands import CommandManager` (check with `grep -n "CommandManager" <file>`), add that import near the file's other `oeapp` imports.
2. At each bare `SentenceCard(sentence, main_window=mock_main_window, ...)` (or equivalent keyword ordering) call, add `command_manager=CommandManager(db_session),` as a keyword argument. Use whichever `db_session`-named fixture is already in scope at that call site (it is a standard fixture available in every test function in this suite per `tests/conftest.py`).

Example transformation (the shape repeats across every affected file — apply the same edit pattern each time):

```python
# Before
card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

# After
card = SentenceCard(
    sentence,
    command_manager=CommandManager(db_session),
    main_window=mock_main_window,
    parent=None,
)
```

For fixture-style constructions like `tests/test_oe_text_edit.py`'s `card` fixture (`def card(self, db_session, qapp, mock_main_window): ... card = SentenceCard(sentence, main_window=mock_main_window) ...`), `db_session` is already a fixture parameter — just add the keyword argument, no signature change needed.

For `tests/test_idioms.py:165` and `:192`, check the enclosing test function's parameter list for `db_session`; if it isn't already a parameter, add it (pytest fixtures are available by adding the fixture name to the test function's signature).

- [ ] **Step 3: Run the full suite again**

Run: `pytest -v`
Expected: PASS, zero occurrences of `missing 1 required positional argument: 'command_manager'` in the output. If any remain, repeat Step 2 for the newly surfaced file:lines.

- [ ] **Step 4: Grep-verify no bare instantiations remain**

Run: `grep -rn "SentenceCard(" tests/*.py`

Manually confirm every match either passes `command_manager=` on the same statement, or is a fixture/variable whose construction (visible a few lines above) already does. (`tests/test_sentence_card_selection.py`'s `MockSentenceCard` is unrelated — it is a different, hand-rolled test double, not `oeapp.ui.sentence_card.SentenceCard`, and needs no change.)

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "test: pass command_manager to every SentenceCard construction now that it is required"
```

---

## Self-Review Notes

- **Spec coverage:** "Persist only via commands" → Tasks 1, 3 (annotation + idiom), Task 2/3 (hierarchy). "hierarchy lives next to sentence commands" → Task 2. "widget only finalizes/highlights" → Task 3 (refresh moved into the command, session removed). "dedicated structure-changed signal" → Tasks 3, 4. The `idiom.save()` bypass found during research (not named in the original card) → Task 1/3. `command_manager` required-arg blast radius found during research → Task 5.
- **Placeholder scan:** no TBDs; every code block is complete, runnable code with exact names matching across tasks (`HierarchyPosition`, `get_hierarchy_position`, `on_split_paragraph_clicked` etc., `structure_changed`, `_finish_hierarchy_action`, `AnnotateTokenCommand.new_idiom`/`sentence_id`).
- **Type consistency:** `AnnotateTokenCommand.new_idiom`/`sentence_id` (Task 1) are consumed with the same keyword names in Task 3's `_execute_annotate_command`. `SentenceCardController.get_hierarchy_position` (Task 2) returns the exact `HierarchyPosition` shape consumed by `SentenceCard._build_paragraph_menu` (Task 3). The six `on_*_clicked` controller methods (Task 2) return `bool`, consumed by `SentenceCard._finish_hierarchy_action` (Task 3) which takes a `bool`.
