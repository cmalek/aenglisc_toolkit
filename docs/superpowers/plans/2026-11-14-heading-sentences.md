# Heading Sentences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Print chapter, section, and subsection headings from the sentence itself, once, in Full Translation, the PDF, the DOCX, and the plain-text exports.

**Architecture:** `oeapp/models/headings.py` owns the slot rules, generated names, and the official-title promotion. `Sentence.heading_role` is the persisted role. Mark, clear, delete, and refused moves are undoable commands. Renderers stop calling `visible_titles` for a separate title line and style the heading sentence in place. The PDF starts a later chapter by closing `paracol`, emitting `\clearpage`, and opening `paracol` again so both columns share the break.

**Tech Stack:** Python 3.13, PySide6, SQLAlchemy, Alembic via `bin/create_migration.py`, pytest. No new packages.

**Spec:** `doc/source/architecture/adr_0014_heading_sentences.rst` (binding). Glossary: `CONTEXT.md` (Heading Sentence, Chapter Heading, Section Heading, Subsection Heading, Verse Section).

## Global Constraints

- Role values, stored as nullable `String(16)`: `"chapter"`, `"section"`, `"subsection"`. Absent means no heading.
- Menu labels, exact: `Chapter heading`, `Section heading`, `Subsection heading`, `Not a heading`.
- Generated names, exact: `Chapter {number}` and `Section {number}`, written with `title_auto=True`. A marked heading stores `sentence.text_oe` with `title_auto=False`.
- Official-title match is `chapter.title == first_sentence.text_oe`. No case fold, no strip.
- A section is verse when it has at least one sentence and every sentence has `is_verse` true.
- Section index is 1-based display order among that section's sentences. The opening section is the one with the lowest `Section.number` in the chapter.
- Opening section: index 1 may be `chapter`. Index 2 may be `section` only while index 1 is `chapter` and the section is not verse. Index 2 allows nothing when the section is verse, and nothing when index 1 is not `chapter`. Index >= 3 may be `subsection`.
- Any other section: index 1 may be `section` only when the section is not verse. A verse section's index 1 allows nothing. Index >= 2 may be `subsection`. Never `chapter`.
- Verse sections never allow `section`. They allow `subsection` only in the slots above, and `chapter` on index 1 of the opening section. Marking or clearing a chapter heading does not rewrite a verse section's `Lines N-M` title.
- Untranslated heading (`text_modern` is `None` or `strip()` is empty): Full Translation, PDF, and DOCX show `text_oe` on the Modern English side. Translation `.txt` stays empty. Other sentences still show `[...]` in Full Translation, PDF, and DOCX.
- Do not mutate stored `text_oe` to capitals. Capitals are a render flag. Full Translation uses `QFont.Capitalization.AllUppercase` on both columns. DOCX uses the run's all-caps property. PDF uppercases with Python `str.upper()` and then LaTeX-escapes that string. Do not use `\MakeUppercase`. pdfLaTeX with T1 does not capitalize ð, þ, or æ.
- PDF and DOCX chapter heading at the top of its page: 4pt above, 16pt below. Full Translation, a chapter heading that is the first sentence of the project: 4pt above, 16pt below. Full Translation, any other chapter heading: 22pt above, 16pt below. Section heading: 12pt above and below. Subsection heading: 6pt above and below. PDF emits one `\vspace{<above>}` before the heading text and one `\vspace{<below>}` after it. `\vspace` takes one length.
- Chapter heading: bold + all capitals. Section heading: bold, own case. Subsection heading: italic, own case, not bold.
- PDF heading text is the escaped sentence text, not `_render_oe_sentence`. No verse indent, no verse line-number marker, and no footnote command inside the bold or italic wrapper. Notes for that sentence, if any, follow the heading.
- DOCX `export` writes two paragraphs for a heading sentence: the styled heading text, then the translation. The translation is `text_modern` when its strip is non-empty, otherwise `text_oe`. No `¶[n]` sentence number and no annotation superscripts or subscripts. `export_side_by_side` is not on the File menu. Do not change it in this plan.
- A later chapter heading starts a new PDF page for both columns and a new DOCX page. The first sentence of the project does not.
- Dialog when a clear also drops the section heading: `The section heading on "{text_oe}" was also cleared. That section is now named Section {number}.`
- Dialog when a delete clears one or more headings, lines in display order: `These headings no longer sit in a legal place, so they were cleared:` then one line `- {Chapter heading|Section heading|Subsection heading} on "{text_oe}"`. No dialog when nothing else was cleared.
- Refused-move warning, exact: `Clear the heading with Not a heading before changing the structure around it.`
- Help and the user-guide page already describe this. Do not rewrite them in this plan.
- Use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy`. `/usr/bin/cd` to change directories.
- Napoleon docstrings and `#:` on new attributes. `Sentence` defines `list()`, so annotations inside that class use `builtins.list`.
- Methods stay at or under 60 lines. No new package.

## Review Focus

- Importing a project whose chapter title is `Chapter 2` and `title_auto` is true must not insert a sentence. A person would expect the generated menu name to stay a menu name.
- Deleting a chapter heading when sentence 2 is a section heading and sentence 3 is a subsection heading clears both, and the next chapter's chapter heading stays. A person would expect only the broken slots in that section to change.
- `Beowulf.` as the official title with first-sentence `Beowulf` inserts a new first sentence. `Beowulf` equal to the first sentence only marks it. A person would expect a punctuation difference to count.
- The Translation `.txt` of an untranslated chapter heading does not contain that heading's Old English. A person sharing the English file would expect no Old English in it.
- The PDF source for a second chapter contains `\end{paracol}`, then `\clearpage`, then `\begin{paracol}{2}` before that chapter heading, and the heading text appears in both column streams after the break. A person would expect the translation to start on the same page as the Old English heading.

## File map

| File | Role |
|------|------|
| Create `oeapp/models/headings.py` | Role enum, slot rules, title writes, official-title promotion |
| Modify `oeapp/models/sentence.py` | `heading_role` column; JSON in/out |
| Modify `oeapp/services/import_export_schema.py` | `SentenceJson.heading_role` |
| Modify `oeapp/models/alembic/versions/<generated>.py` | Column plus data backfill call |
| Create `oeapp/commands/heading.py` | Set and clear commands |
| Modify `oeapp/commands/sentence.py` | OE edit syncs the title; delete rechecks; merge refuses |
| Modify `oeapp/commands/__init__.py` | Export the new commands |
| Modify `oeapp/ui/sentence_card.py` | Menu labels; show the menu on sentence 1; dialogs |
| Modify `oeapp/ui/sentence_card_controller.py` | Dispatch mark, clear, and the refusal check |
| Modify `oeapp/ui/full_translation_window.py` | Style the heading sentence; no `visible_titles` line |
| Modify `oeapp/services/export_pdf.py` | Styles, OE fallback, synchronized page break |
| Modify `oeapp/services/export_docx.py` | Heading run without number or glosses; page break |
| Modify `oeapp/services/export_reading_text.py` | No title line; translation stays empty |
| Modify `oeapp/services/wyrdcraeft_ingest.py` | Promote official chapter titles after the hierarchy exists |
| Modify `oeapp/services/import_export.py` | Restore `heading_role`; promote only when the file has no roles |
| Test `tests/test_headings.py` | Rules, titles, promotion, commands |
| Test `tests/test_text_flow.py` | Existing title tests stay; renderers are tested elsewhere |
| Test `tests/test_export_reading_text.py` | No title line; empty translation |
| Test `tests/test_export_pdf.py` | LaTeX break and styles |
| Test `tests/test_export_docx.py` | Heading paragraph shape |
| Test `tests/test_full_translation_window.py` | Block format and fallback |
| Test `tests/test_import_export.py` | Round trip and `Chapter N` |
| Test `tests/test_sentence_card_hierarchy.py` | Menu labels and sentence 1 |

---

### Task 1: Persist `heading_role`

**Files:**
- Modify: `oeapp/models/sentence.py`
- Modify: `oeapp/services/import_export_schema.py` (`SentenceJson`)
- Test: `tests/test_headings.py`

**Interfaces:**
- Consumes: nothing earlier.
- Produces: `Sentence.heading_role: Mapped[str | None]`. JSON key `heading_role`, omitted from the required set so old files still parse. `to_json` always writes it (`None` when unset). `from_json` reads `sentence_data.get("heading_role")`.

- [ ] **Step 1: Write the failing test**

Use `create_test_sentence` from `tests.conftest`. The old-file case copies `to_json()`, removes `heading_role`, deletes that source sentence, and only then calls `Sentence.from_json`. Leaving the source row in place hits `uq_sentences_project_order`.

```python
def test_sentence_json_round_trips_heading_role(db_session) -> None:
    sentence = create_test_sentence(db_session, text="Beowulf")
    sentence.heading_role = "chapter"
    sentence.save()
    assert sentence.to_json()["heading_role"] == "chapter"

def test_old_sentence_json_without_heading_role_imports(db_session) -> None:
    sentence = create_test_sentence(db_session, text="Hwæt")
    payload = sentence.to_json()
    payload.pop("heading_role", None)
    lookup = {
        (
            sentence.paragraph.section.chapter.number,
            sentence.paragraph.section.number,
            sentence.paragraph.order,
        ): sentence.paragraph_id
    }
    project_id = sentence.project_id
    sentence.delete()
    imported = Sentence.from_json(
        project_id, payload, lookup, session=db_session
    )
    assert imported.heading_role is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_headings.py::test_sentence_json_round_trips_heading_role tests/test_headings.py::test_old_sentence_json_without_heading_role_imports -v`

Expected: FAIL with `heading_role` missing.

- [ ] **Step 3: Add the column and the JSON field**

`heading_role: Mapped[str | None]` nullable `String(16)`, no server default. Check constraint name `ck_sentences_heading_role` allowing NULL, `chapter`, `section`, `subsection`. Create the revision with `bin/create_migration.py "Add sentence heading role"`. Do not put the data backfill in this revision; Task 9 adds it.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_headings.py::test_sentence_json_round_trips_heading_role tests/test_headings.py::test_old_sentence_json_without_heading_role_imports -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add oeapp/models/sentence.py oeapp/services/import_export_schema.py oeapp/models/alembic/versions tests/test_headings.py
git commit -m "feat: store a heading role on the sentence"
```

---

### Task 2: Slot rules and title writes

**Files:**
- Create: `oeapp/models/headings.py`
- Test: `tests/test_headings.py`

**Interfaces:**
- Consumes: `Sentence.heading_role`, `Sentence.is_verse`, `Chapter.title`, `Chapter.title_auto`, `Section.title`, `Section.title_auto`.
- Produces:

```python
class HeadingRole(StrEnum):
    CHAPTER = "chapter"
    SECTION = "section"
    SUBSECTION = "subsection"

def section_index(sentence: Sentence) -> int: ...
def is_opening_section(sentence: Sentence) -> bool: ...
def is_verse_section(section: Section) -> bool: ...
def allowed_role(sentence: Sentence) -> HeadingRole | None: ...
def apply_heading_title(sentence: Sentence) -> None: ...
def apply_generated_title(sentence: Sentence) -> None: ...
def heading_is_legal(sentence: Sentence) -> bool: ...
```

`allowed_role` follows the Global Constraints and ignores the sentence's current role. `heading_is_legal` is true when `heading_role` is None or equals `allowed_role`. `apply_heading_title` writes `text_oe` onto the chapter for `chapter` and onto the section for `section`, with `title_auto=False`. It does nothing for `subsection` and for `None`. `apply_generated_title` writes `Chapter {n}` or `Section {n}` with `title_auto=True` for a sentence whose role is `chapter` or `section`, using the division it currently belongs to. It does nothing for `subsection`.

- [ ] **Step 1: Write the failing tests**

Assert, with a two-sentence opening section:

- index 1 allows `HeadingRole.CHAPTER`
- index 2 allows `HeadingRole.SECTION` only after index 1's `heading_role` is `chapter`
- index 2 of a non-verse opening section allows nothing while index 1 has no chapter heading: `allowed_role` is None
- index 3 allows `HeadingRole.SUBSECTION`
- a verse opening section: index 1 allows `chapter`. Index 2 allows nothing, including after index 1's role is `chapter`. Index 3 allows `subsection`. A non-opening verse section: index 1 allows nothing, index 2 allows `subsection`
- a non-verse later section: index 1 allows `section`, never `chapter`
- `apply_generated_title` on a chapter heading sets `title == "Chapter 2"` and `title_auto is True` when `chapter.number == 2`
- `apply_heading_title` sets `title == text_oe` and `title_auto is False`

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_headings.py -v -k "allowed or generated or heading_title"`

Expected: FAIL with import error for `oeapp.models.headings`.

- [ ] **Step 3: Implement the functions in `oeapp/models/headings.py`**

Index is the 1-based position in `sorted(section.sentences, key=lambda s: s.display_order)`. Opening section is `min(chapter.sections, key=lambda s: s.number)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_headings.py -v -k "allowed or generated or heading_title"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add oeapp/models/headings.py tests/test_headings.py
git commit -m "feat: decide which heading a sentence slot allows"
```

---

### Task 3: Mark, clear, and the menu

**Files:**
- Create: `oeapp/commands/heading.py`
- Modify: `oeapp/commands/__init__.py`
- Modify: `oeapp/commands/sentence.py` (`EditSentenceCommand.execute` / `undo` for `text_oe`)
- Modify: `oeapp/ui/sentence_card.py` (`_build_paragraph_menu`, `_update_paragraph_button_state`)
- Modify: `oeapp/ui/sentence_card_controller.py`
- Test: `tests/test_headings.py`
- Test: `tests/test_sentence_card_hierarchy.py`

**Interfaces:**
- Consumes: Task 2 functions. `Command` in `oeapp/commands/abstract.py`.
- Produces:

```python
@dataclass
class SetHeadingCommand(SessionMixin, Command):
    sentence_id: int
    role: str
    def execute(self) -> bool: ...
    def undo(self) -> bool: ...
    def menu_text(self) -> str: ...  # "Mark heading"

@dataclass
class ClearHeadingCommand(SessionMixin, Command):
    sentence_id: int
    cleared_section_heading_id: int | None = None
    def execute(self) -> bool: ...
    def undo(self) -> bool: ...
    def menu_text(self) -> str: ...  # "Clear heading"
```

`SetHeadingCommand` sets `heading_role` to `allowed_role(sentence).value` and calls `apply_heading_title`. It returns False when `allowed_role` is None. Undo restores the previous role and the previous title and `title_auto`.

`ClearHeadingCommand` always restores the generated name before it clears a `chapter` or `section` role. Call `apply_generated_title` while the sentence still has that role, then set `heading_role` to None. A `subsection` clear only sets the role to None and does not write a title. When the cleared role was `chapter` and index 2 of the same section has role `section`, clear that sentence the same way, store its id, and have the card show the cascade dialog. A verse opening section has no section heading, so this cascade does not run there and the section title stays `Lines N-M`. Undo restores both roles and both previous titles.

`EditSentenceCommand` for `text_oe`: after the text write, if `heading_role` is `chapter` or `section`, call `apply_heading_title`. Undo of the text restores the previous title the same way.

`_update_paragraph_button_state` shows the button on `display_order == 1` when `allowed_role` is not None or `heading_role` is set. The first sentence of the project still has no earlier boundary, so Paragraph Start, Section Start, Chapter Start, and the Not … Start actions stay off that menu. The heading actions are the legal role, when `allowed_role` is not None and the sentence does not already have that role, and **Not a heading** when `heading_role` is set. **Not a heading** pushes `ClearHeadingCommand`.

- [ ] **Step 1: Write the failing tests**

`test_set_heading_copies_oe_and_clears_auto` and `test_clear_chapter_heading_also_clears_section_heading`:

- After set chapter, `chapter.title == "Be ðēodwitan"` and `title_auto is False`.
- Sentence 2 role `section`, then clear sentence 1: both roles are None, `chapter.title == "Chapter 1"`, `chapter.title_auto is True`, `section.title == "Section 1"`, `section.title_auto is True`.
- `test_clear_section_heading_restores_section_n`: a section heading cleared on its own sets `section.title == "Section 2"` and `title_auto is True` when `section.number == 2`. The chapter title is unchanged.
- `test_edit_oe_updates_chapter_title`: changing `text_oe` to `Beowulf` updates `chapter.title` to `Beowulf`.
- `test_first_sentence_menu_offers_chapter_heading`: the button is visible and an action is titled `Chapter heading`.
- `test_marked_heading_menu_offers_not_a_heading`: a sentence whose role is `chapter` has an action titled `Not a heading` and does not also offer `Chapter heading`. Triggering it runs `ClearHeadingCommand`.

- [ ] **Step 2: Run test to verify it fails**

Run the two files separately. A second `-k` on one pytest command replaces the first.

```bash
.venv/bin/pytest tests/test_headings.py -v -k "set_heading or clear_chapter or clear_section_heading or edit_oe"
.venv/bin/pytest tests/test_sentence_card_hierarchy.py -v -k "first_sentence or not_a_heading"
```

Expected: FAIL

- [ ] **Step 3: Implement the commands and the menu**

The card calls `QMessageBox.information` with the cascade string from Global Constraints only when `cleared_section_heading_id` is not None. Capture `text_oe` before the role is cleared.

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_headings.py -v -k "set_heading or clear_chapter or clear_section_heading or edit_oe"
.venv/bin/pytest tests/test_sentence_card_hierarchy.py -v -k "first_sentence or not_a_heading"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add oeapp/commands/heading.py oeapp/commands/__init__.py oeapp/commands/sentence.py oeapp/ui/sentence_card.py oeapp/ui/sentence_card_controller.py tests/test_headings.py tests/test_sentence_card_hierarchy.py
git commit -m "feat: mark and clear heading sentences from the card"
```

---

### Task 4: Refuse illegal moves and recheck after delete

**Files:**
- Modify: `oeapp/commands/sentence.py` (`AddSentenceCommand`, `DeleteSentenceCommand`, `MergeSentenceCommand`)
- Modify: `oeapp/commands/hierarchy.py` (split/merge chapter and section)
- Modify: `oeapp/ui/sentence_card_controller.py`
- Test: `tests/test_headings.py`

**Interfaces:**
- Consumes: `heading_is_legal`, `allowed_role`, `apply_generated_title` from Task 2. Clear behavior from Task 3.
- Produces:

```python
def headings_illegal_after(section: Section) -> list[Sentence]: ...
```

in `oeapp/models/headings.py`. Returns sentences in that section whose `heading_role` is set and not `heading_is_legal`, in display order. `headings.py` does not define `list()`, so the annotation is the builtin.

Refuse before any write when the move would leave a heading outside its legal slot. Predict the new index without writing. An insert in a section shifts every later sentence in that section up by one. A heading whose new index is not `allowed_role` for that index is a refusal. The commands are `AddSentenceCommand` (before or after), `MergeSentenceCommand`, `MergeChapterCommand` (menu **Not Chapter Start**), `MergeSectionCommand` (menu **Not Section Start**), `SplitChapterCommand`, and `SplitSectionCommand`. `MergeSentenceCommand` also returns False when either sentence has a role, even if the merged sentence would still sit in a legal slot, because the stored title would become the joined Old English. Paragraph split and merge do not change a section index, so they are not guarded. On refusal the command returns False, nothing is unmarked, and the card shows the refused-move warning without pushing the command.

`DeleteSentenceCommand.execute` reverts the deleted sentence first. If its role is `chapter` or `section`, call `apply_generated_title` while it still belongs to that division, and remember the previous title and `title_auto` for undo. Then delete and renumber. Then call `headings_illegal_after` on that section only. For each result, call `apply_generated_title` when the role is `chapter` or `section`, then set `heading_role` to None. The deleted sentence is already gone, so it is not in that list. Record the cleared ids and roles for undo. The card shows the delete dialog only when that list is non-empty. Undo restores the deleted sentence, the division title, and every cleared role.

- [ ] **Step 1: Write the failing tests**

`test_delete_chapter_heading_clears_shifted_section_and_subsection`: sentences with roles chapter, section, subsection. Delete the first. The surviving two have `heading_role is None`. The chapter title is `Chapter 1` with `title_auto` true. A second chapter whose first sentence is `chapter` still has that role and keeps its own title.

`test_add_sentence_before_heading_is_refused`: `AddSentenceCommand` with `position="before"` returns False and the heading sentence's `display_order` is unchanged.

`test_add_sentence_after_chapter_heading_refuses_when_it_shifts_a_section_heading`: sentence 1 is `chapter`, sentence 2 is `section`. `AddSentenceCommand` with `position="after"` on sentence 1 returns False. Both roles and both titles stay as they were.

`test_merge_heading_with_neighbor_is_refused`: `MergeSentenceCommand` returns False and `chapter.title` is still the heading's `text_oe`.

`test_not_chapter_start_refuses_when_the_chapter_heading_would_move`: `MergeChapterCommand` returns False and the next chapter's first sentence keeps `heading_role == "chapter"`.

`test_merge_section_refuses_when_a_section_heading_would_leave_index_1`: section 2's first sentence is `section`. `MergeSectionCommand` on that section returns False. The role and `section.title` stay.

`test_split_section_refuses_when_a_subsection_would_become_first`: a subsection heading is the split point. `SplitSectionCommand` returns False and the role stays.

`test_split_chapter_refuses_when_a_section_heading_would_become_chapter_slot`: a later section's first sentence is `section`, and that section would become the opening section of a new chapter. `SplitChapterCommand` returns False and the role stays `section`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_headings.py -v -k "delete_chapter_heading or add_sentence_before or add_sentence_after or merge_heading or not_chapter_start or merge_section or split_section or split_chapter"`

Expected: FAIL

- [ ] **Step 3: Implement the guards and the section-bounded recheck**

Do not walk into the next section. Undo of the delete restores the cleared roles and titles.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_headings.py -v -k "delete_chapter_heading or add_sentence_before or add_sentence_after or merge_heading or not_chapter_start or merge_section or split_section or split_chapter"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add oeapp/models/headings.py oeapp/commands/sentence.py oeapp/commands/hierarchy.py oeapp/ui/sentence_card_controller.py tests/test_headings.py
git commit -m "feat: keep headings inside their legal slots"
```

---

### Task 5: Full Translation rendering

**Files:**
- Modify: `oeapp/ui/full_translation_window.py` (`render_readonly_text`, `render_text`)
- Test: `tests/test_full_translation_window.py`

**Interfaces:**
- Consumes: `Sentence.heading_role`. Do not call `visible_titles`.
- Produces: block format on the heading's characters in both editors. `QFont.Capitalization.AllUppercase` and bold for `chapter` on both columns. Bold for `section`. Italic for `subsection`. Top and bottom margins from Global Constraints. A chapter heading uses 4pt above only when it is the project's first sentence. Every other chapter heading uses 22pt above, including one that is still in chapter 1. Modern English body is `text_modern` when its strip is non-empty, else `text_oe` when `heading_role` is set, else `[...]`.

- [ ] **Step 1: Write the failing test**

Build a project whose first sentence is a chapter heading `Beowulf` with empty `text_modern`, then a body sentence, then a second chapter whose first sentence is a chapter heading. Assert the OE document contains `Beowulf` once, the block format for that range is all-caps and bold on both the Old English and Modern English documents, top margin is 4, and the second chapter heading's block top margin is 22. Assert the Modern English document's first heading text is `Beowulf`, not `[...]`. A second case, one chapter whose heading is sentence 2, also has top margin 22.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_full_translation_window.py -v -k heading`

Expected: FAIL

- [ ] **Step 3: Render headings in place**

Skip the `visible_titles` insert in both editors. Apply the block format to the heading sentence's inserted range. Body sentences stay on the existing separator path with `has_titles=False`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_full_translation_window.py -v -k heading`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add oeapp/ui/full_translation_window.py tests/test_full_translation_window.py
git commit -m "feat: style heading sentences in the full translation"
```

---

### Task 6: PDF page break and styles

**Files:**
- Modify: `oeapp/services/export_pdf.py` (`_render_two_columns`)
- Test: `tests/test_export_pdf.py`

**Interfaces:**
- Consumes: `Sentence.heading_role`, `Sentence.display_order`.
- Produces: LaTeX. A chapter heading that is not the project's first sentence ends the current `paracol`, emits `\clearpage`, and starts `\begin{paracol}{2}` before that heading is written into either column. Heading text is the Python string, uppercased with `str.upper()` for `chapter`, then `_latex_escape`. Wrap chapter in `\textbf{...}`, section in `\textbf{...}`, subsection in `\textit{...}`. Before the wrapper emit `\vspace{<above>}`. After it emit `\vspace{<below>}`. Use the Global Constraint points. Do not call `_render_oe_sentence` for a heading, and do not append the verse line-number marker or the verse indent. A heading's notes, if rendered, come after that pair of vspaces. Empty `text_modern` on a heading uses the same plain text as the Old English side, escaped, and uppercased on a chapter heading.

- [ ] **Step 1: Write the failing test**

`test_second_chapter_heading_breaks_both_columns`: two chapters. Assert on `_render_two_columns`, not the full document. The full document already emits `\clearpage` before the glossary, so a global count is the wrong check. The column string contains the sequence `\end{paracol}`, then `\clearpage`, then `\begin{paracol}{2}` once. The chapter-2 Old English heading occurs after that second `\begin{paracol}{2}` and, after the following `\switchcolumn`, on the Modern English side. `\newpage` does not appear in the column string. The first chapter's heading is not preceded by `\clearpage`. The chapter heading `ðæt` is emitted as `\textbf{ÐÆT}`, with `\vspace{4pt}` before it and `\vspace{16pt}` after it. `'ðæt'.upper()` is `'ÐÆT'`. The column string contains neither `\MakeUppercase` nor `\vspace*{`.

`test_verse_chapter_heading_has_no_line_number`: a chapter heading whose sentence `is_verse` is true. The column string contains the uppercased heading and does not contain that sentence's `verse_line_end` as a bold marker after the heading.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_export_pdf.py -v -k "second_chapter_heading or verse_chapter_heading"`

Expected: FAIL

- [ ] **Step 3: Split `paracol` at later chapter headings**

Build a list of segments. Each segment is the OE parts and ModE parts up to but not including the next chapter heading that needs a page. Join segments with `\end{paracol}\n\\clearpage\n\\begin{paracol}{2}`. Do not call `visible_titles`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_export_pdf.py -v -k "second_chapter_heading or verse_chapter_heading"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add oeapp/services/export_pdf.py tests/test_export_pdf.py
git commit -m "feat: break both PDF columns on a later chapter heading"
```

---

### Task 7: DOCX headings

**Files:**
- Modify: `oeapp/services/export_docx.py` (`export`)
- Test: `tests/test_export_docx.py`

**Interfaces:**
- Consumes: `Sentence.heading_role`.
- Produces: for a heading sentence, two paragraphs. The first run is the heading text, bold and all-caps for chapter, bold for section, italic for subsection. The second paragraph is the translation: `text_modern` when its strip is non-empty, otherwise `text_oe`. `paragraph_format.page_break_before` is True only on the heading paragraph of a chapter heading that is not the project's first sentence. Space before and after on the heading paragraph match the PDF point values (a new page still uses 4pt before, not the scrolling 22pt). No sentence-number paragraph and no call to `_add_oe_sentence_with_annotations` for that sentence. Do not call `_visible_titles`. Do not modify `export_side_by_side`.

- [ ] **Step 1: Write the failing test**

A chapter heading `Beowulf` with empty `text_modern` and a glossed token is exported. The document has a heading paragraph whose text is `Beowulf`, that run is bold and all caps, and a following paragraph whose text is `Beowulf`. No paragraph contains `¶[`, and the gloss text is absent. A second chapter heading has `page_break_before` true on the heading paragraph. A heading whose `text_modern` is `Listen` has a second paragraph `Listen` and does not repeat the Old English there.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_export_docx.py -v -k heading`

Expected: FAIL

- [ ] **Step 3: Branch `export` on `heading_role`**

Keep the existing body path for sentences whose role is unset.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_export_docx.py -v -k heading`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add oeapp/services/export_docx.py tests/test_export_docx.py
git commit -m "feat: export heading sentences as headings in DOCX"
```

---

### Task 8: Plain-text exports

**Files:**
- Modify: `oeapp/services/export_reading_text.py` (`_render`)
- Test: `tests/test_export_reading_text.py`

**Interfaces:**
- Consumes: `Sentence.text_oe`, `Sentence.text_modern`, `Sentence.heading_role`.
- Produces: no call to `visible_titles`. Heading sentences are ordinary bodies. Translation of a heading with blank `text_modern` appends `""`.

- [ ] **Step 1: Write the failing test**

Chapter title `Her onginneð`, `title_auto=False`. The only sentence is a chapter heading `Hwæt` with `text_modern` None. `render_old_english` contains `Hwæt` and does not contain `Her onginneð`. `render_translation` contains neither `Hwæt` nor `Her onginneð`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_export_reading_text.py -v -k "title_line or untranslated_heading"`

Expected: FAIL because `visible_titles` still inserts `Beowulf`.

- [ ] **Step 3: Stop inserting titles**

Pass `has_titles=False` always. Leave `visible_titles` defined for its unit tests.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_export_reading_text.py tests/test_text_flow.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add oeapp/services/export_reading_text.py tests/test_export_reading_text.py
git commit -m "feat: drop the separate title line from plain-text export"
```

---

### Task 9: Promote official chapter titles

**Files:**
- Modify: `oeapp/models/headings.py`
- Modify: `oeapp/services/wyrdcraeft_ingest.py` (`_map_canonical_to_project`, after each chapter is filled)
- Modify: `oeapp/services/import_export.py` (`import_project_json`, after sentences exist)
- Modify: the revision created in Task 1, `upgrade()` only
- Test: `tests/test_headings.py`
- Test: `tests/test_import_export.py`
- Test: `tests/test_wyrdcraeft_ingest.py`

**Interfaces:**
- Consumes: Task 1 column, Task 2 title writers, `Sentence.renumber_sentences`.
- Produces:

```python
def promote_official_chapter_title(chapter: Chapter, *, session: Session) -> None: ...
```

Return immediately when any sentence in the chapter has `heading_role` set, or when `title_auto` is true, or when `title` is missing or `strip()` is empty. Otherwise look at the opening section.

- No sentences there: `Sentence.create(..., commit=False, session=session)` in that section's first paragraph, at the next project `display_order`, with `text_oe=chapter.title` and `text_modern=None`. Set `heading_role` to `chapter`, call `apply_heading_title`, and return.
- A first sentence whose `text_oe` equals `chapter.title`: set that sentence's role to `chapter`, call `apply_heading_title`, and return.
- Any other first sentence: renumber every sentence with `display_order >= first.display_order` up by one using `Sentence.renumber_sentences`, then `Sentence.create(..., commit=False, session=session)` in that sentence's paragraph at the old display order, with `text_oe=chapter.title` and `text_modern=None`. `Sentence.create` does not take `heading_role`. Set it on the returned sentence, then call `apply_heading_title`.

Re-read each chapter from the session after an insert. Do not cache first-sentence ids across chapters, because an insert shifts later display orders.

Ingest calls it for each chapter it just created. Import calls it only when no sentence in the raw file had a `heading_role` key. `SentenceJson` defaults the field to None, and `model_dump()` writes that default, so the check has to use the raw sentence dicts or `model_fields_set` before the dump. A file whose sentences all have an explicit null still counts as having the key, and import does not promote. The migration `upgrade()` opens `Session(bind=op.get_bind())` and calls it for every chapter after the column exists, with `commit=False` so Alembic owns the transaction. Pass that same session into `Sentence.create`. `downgrade()` drops the column and does not try to remove inserted sentences.

- [ ] **Step 1: Write the failing tests**

`test_exact_title_marks_existing_first_sentence`: title `Beowulf`, first `text_oe` `Beowulf`. One sentence, role `chapter`.

`test_title_punctuation_inserts_a_sentence`: title `Beowulf.`, first `text_oe` `Beowulf`. Two sentences; the new first is `Beowulf.` with role `chapter`; the old sentence is second.

`test_generated_chapter_name_is_not_inserted`: title `Chapter 2`, `title_auto=True`, first sentence `Hwæt`. Still one sentence, `heading_role is None`.

`test_import_with_heading_role_does_not_insert`: file has `heading_role: "section"` on sentence 2 and an official chapter title different from sentence 1. Sentence count unchanged; sentence 2 role stays `section`.

`test_import_explicit_null_heading_role_does_not_promote`: every sentence has `"heading_role": null` and the official title differs from the first sentence. Sentence count unchanged.

`test_official_title_on_an_empty_section_inserts_the_first_sentence`: `title_auto` is false, title `Beowulf`, opening section has no sentences. After promotion there is one sentence, `text_oe == "Beowulf"`, role `chapter`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_headings.py tests/test_import_export.py -v -k "exact_title or punctuation or generated_chapter or heading_role_does_not or explicit_null or empty_section"`

Expected: FAIL

- [ ] **Step 3: Implement promotion and call it from ingest, import, and `upgrade()`**

Shift display orders before insert, or the unique constraint on `(project_id, display_order)` will fail.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_headings.py tests/test_import_export.py tests/test_wyrdcraeft_ingest.py -v`

Expected: PASS

- [ ] **Step 5: Quality gate and commit**

Run: `.venv/bin/ruff check oeapp/models/headings.py oeapp/models/sentence.py oeapp/commands/heading.py oeapp/ui/sentence_card.py oeapp/ui/full_translation_window.py oeapp/services/export_pdf.py oeapp/services/export_docx.py oeapp/services/export_reading_text.py`

Run: `.venv/bin/mypy oeapp/models/headings.py oeapp/commands/heading.py`

Run: `make napoleon-gate`

Run: `graphify update .`

```bash
git add oeapp/models/headings.py oeapp/services/wyrdcraeft_ingest.py oeapp/services/import_export.py oeapp/models/alembic/versions tests/test_headings.py tests/test_import_export.py tests/test_wyrdcraeft_ingest.py
git commit -m "feat: turn official chapter titles into heading sentences"
```
