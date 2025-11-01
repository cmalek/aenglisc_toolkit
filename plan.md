# Old English Annotator — Comprehensive Development Plan

This plan defines the full architecture and workflow for a **Python desktop application** that assists with translating and annotating Old English texts (e.g. your *Story of Cædmon 1–10* document).
It is ready to feed directly into **Cursor**, **Warp**, or **Claude Code** for implementation.

---

## 🧭 Overview

**Goal:**
Create a robust, keyboard-driven tool that helps linguists translate Old English (OE) into Modern English (ModE) while tagging each word with grammatical, morphological, and syntactic annotations.

**Core tasks supported:**
- Input OE text → automatically split into sentences.
- Annotate each word with POS, gender, case, number, declension, etc.
- Add translations under each OE sentence.
- Add anchored notes to individual words, spans, or sentences.
- Autosave progress and export to **DOCX** for use in Word or Apple Pages.
- Support **incremental refinement** — annotate partially now, update later.
- Fully keyboard-driven annotation with mnemonic multi-key chords.
- Include a built-in **Help system** (F1) documenting all shortcuts and categories.

---

## 🧩 Application Structure

### 1. Sentence Cards (Main Editing UI)
Each OE sentence becomes a vertically stacked “card” with:
1. **Header:** Sentence number + quick actions (Split, Merge, Delete, Move).
2. **Old English line:** Large serif text, editable inline.
3. **Token Annotation Grid:**
   - Columns: `Word | POS | Gender | Number | Case | Declension | PronounType | VerbClass | VerbForm | PrepObjCase | Notes`
   - Inline HUD shows filled vs missing annotations.
4. **Modern English translation** (text area immediately *beneath* OE sentence).
5. **Notes Section:**
   - Sentence-level notes.
   - Anchored word/span notes (e.g., “brōðer, masculine r-stem, acc sg”).
   - Notes support Markdown formatting.

---

## 🧮 Data Model (SQLite + JSON)

| Table | Purpose | Key Fields |
|--------|----------|------------|
| `projects` | Project metadata | id, name, created_at, updated_at |
| `sentences` | Sentence text & translations | id, project_id, index, text_oe, text_modern |
| `tokens` | Tokenized OE words | id, sentence_id, order_index, surface, lemma |
| `annotations` | Morphology & grammar | token_id, pos, gender, number, case, declension, pronoun_type, verb_class, verb_tense, verb_person, verb_mood, verb_aspect, prep_case, uncertain, alternatives_json, confidence_json, last_inferred_json |
| `notes` | Anchored commentary | id, sentence_id, start_token, end_token, note_text_md, note_type ("token","span","sentence") |
| `audit_log` | Revision tracking | id, ts, entity, entity_id, action, diff_json |

---

## 🖥️ UX Flow

### Creating a Project
- Paste or import OE text.
- Automatic sentence segmentation (regex split, manual corrections allowed).
- Numbered cards appear instantly.

### Annotating
- Navigate tokens with arrows (`→`, `←`).
- Press `A` to enter **Annotate Mode**.
- Use **multi-key chords** to assign grammar tags (see below).
- Press **Enter** to commit, **Space** to continue, **Esc** to cancel.
- You can **add annotations incrementally** over time (start vague, refine later).

### Notes
- `N` → add a note (opens note editor dialog).
- Anchors can be per-token, span (multiple tokens), or sentence.
- Notes are for **clarifying information only** (context, explanations, commentary).
- Grammatical annotations appear directly on words as superscripts/subscripts (see Export section).
- Inline marker `[n1]`, `[n2]`, etc. appears near annotated word(s) in token grid (optional, for notes only).
- Notes appear in collapsible right-hand panel (toggle with `Ctrl+/`).
- Clicking note marker scrolls to note in panel; hovering highlights anchor.
- Notes support Markdown formatting (rendered in panel, plain text in editor).
- Notes can be edited inline or via dialog.

### Export
- DOCX has these aspects, per sentence
  -  Old English sentence (italic) with annotations as superscripts and subscripts
  -  Modern English translation
  -  Notes list
- PDF/RTF optional.
- Missing fields display “—” or are hidden.
- Uncertain annotations show `?`; alternatives as `/`.

---

## 🎹 Keyboard Shortcuts

### Navigation & Editing
| Action | Shortcut |
|---------|-----------|
| Next/Prev Token | → / ← |
| Next/Prev Sentence | J / K |
| Split Sentence | Ctrl+Enter |
| Merge Sentence | Ctrl+M |
| Edit OE Line | Enter |
| Focus Translation | T |
| Add Note | N |
| Toggle Notes | Ctrl+/ |
| Save | Ctrl+S |
| Export | Ctrl+E |
| Undo / Redo | Ctrl+Z / Ctrl+Y |
| Show Help | F1 |

---

## ✍️ Annotate Mode — Multi-Key Chords

Begin with **A**, then type subcommands.
You can enter one attribute at a time and refine later.

### POS
| Command | Meaning |
|----------|----------|
| `A P N` | Noun |
| `A P V` | Verb |
| `A P A` | Adjective |
| `A P R` | Pronoun |
| `A P D` | Determiner/Article |
| `A P B` | Adverb |
| `A P C` | Conjunction |
| `A P E` | Preposition |
| `A P I` | Interjection |

### Nouns / Articles
| Command | Meaning |
|----------|----------|
| `A N g m/f/n` | Gender |
| `A N n s/p` | Number |
| `A N c n/a/g/d/i` | Case |
| `A N d s/w/o/i/u/ja/jo/wa/wo` | Declension type |
| Example: `A N g m n s c a` → Masc Sg Acc strong declension |

### Pronouns
| Command | Meaning |
|----------|----------|
| `A R p` | Personal |
| `A R r` | Relative |
| `A R d` | Demonstrative |
| `A R i` | Interrogative |

### Verbs
| Command | Meaning |
|----------|----------|
| `A V c w1/w2/w3/s1–s7` | Verb class (weak/strong) |
| `A V t p/n` | Tense (past/present) |
| `A V m i/s/imp` | Mood (indicative/subjunctive/imperative) |
| `A V p 1/2/3` | Person |
| `A V n s/p` | Number |
| `A V a p/f/prg/gn` | Aspect (perfect/progressive/gnomic) |
| `A V f f/i/p` | Finite/Infinitive/Participle |
| Example: `A V c w2 t p m i p 3 n s` → Weak II, past, indicative, 3rd sg |

### Prepositions
| Command | Meaning |
|----------|----------|
| `A E o a/d/g` | Governs accusative/dative/genitive |

### Adjectives
| Command | Meaning |
|----------|----------|
| `A A d p/c/s` | Degree (positive/comparative/superlative) |
| `A A s s/w` | Strong/Weak inflection |
| Reuse noun chords for gender/number/case. |

---

## 🔁 Incremental Refinement

You can annotate progressively:
1. `A P V` → mark as Verb.
2. Later `A V c w2` → specify Weak Class II.
3. Later `A V t p m i p 3 n p` → add full verb details.

System supports:
- Partial data (null fields allowed).
- Uncertain tags: `A ?` → mark as uncertain.
- Alternatives: `A =` → add alt (`w2 / s3`).
- Confidence: `A % 80` → 80% certainty.
- TODO marker: `A !` → add task note.

Filters help you find incomplete annotations (“verbs missing tense,” etc.).

---

## 📚 In-App Help System

**Access:** F1 or Help → Open Help.
**Features:**
- Markdown-based documentation.
- Searchable topics:
- Keybindings
- Annotation Guide
- Incremental Annotation
- Export Formatting
- Morphological Tag Reference
- Troubleshooting
- Editable Markdown files in `/help/`.
- Contextual F1 opens relevant topic.

---

## 🏗️ Technical Stack

| Component | Technology |
|------------|-------------|
| UI | PySide6 (Qt for Python) |
| DB | SQLite (via `sqlite3`) |
| Export | `python-docx` |
| PDF | `reportlab` or Pages automation |
| Markdown | `markdown` Python package |
| Packaging | PyInstaller |
| Version control | Git |
| Autosave | Threaded debounce writer (WAL mode) |

---

## ⚙️ Architecture Layout

oe_annotator/
│  README.md
│  pyproject.toml
├─ src/oeapp/
│  ├─ main.py
│  ├─ ui/
│  │  ├─ main_window.py
│  │  ├─ sentence_card.py
│  │  ├─ token_table.py
│  │  ├─ help_dialog.py
│  │  └─ notes_panel.py
│  ├─ services/
│  │  ├─ splitter.py
│  │  ├─ db.py
│  │  ├─ autosave.py
│  │  ├─ export_docx.py
│  │  └─ keymap.py
│  ├─ models/
│  │  ├─ sentence.py
│  │  ├─ token.py
│  │  ├─ annotation.py
│  │  └─ note.py
│  └─ themes/default.qss
├─ assets/styles.docx
├─ help/*.md
└─ tests/

---

## 🧠 Intelligent Assist (Optional v1.1)
- Suggest case for prepositions (e.g., *mid* → dative).
- Suggest verb person/number by endings.
- Highlight inconsistencies but don’t block export.

---

## 🧾 Export Behavior (DOCX)

### Format Specification
Export format matches `story-of-caedmon-1-10.docx` sentences [7]-[13] style:

**Per Sentence:**
1. **Old English sentence** (italic font, "Default" paragraph style)
   - Grammatical annotations appear **directly on words** as superscripts and subscripts
   - Format: `[word][superscript][subscript]` where:
     - **Superscripts** show: Case (n/a/g/d/i), Number (s/p), Gender (m/f/n), POS abbreviations (pron:rel, n:, v:, prep:, etc.)
     - **Subscripts** show: Declension/class details (e.g., "weak", "strong7", "dat1", "acc1", "gen1")
     - Example: `sumre^dat1_` or `þæt^acc1_` or `pron:rel^þāragenpl_`
   - Annotations are compact abbreviations (e.g., "dat1" = dative singular, "acc1" = accusative singular, "genpl" = genitive plural)
   - Only annotated tokens get annotations; unannotated tokens appear normally
   - Annotation markers use smaller font size with vertical alignment (superscript/subscript)

2. **Modern English translation** (normal font, "Body" paragraph style)
   - Plain text paragraph
   - Empty if translation not provided

3. **Blank line** (empty paragraph)

4. **Notes list** (numbered list, "Body" paragraph style, **only for clarifying information**)
   - Notes are separate from grammatical annotations
   - Used for explanations, context, or additional commentary
   - Format: `[token], [clarifying explanation]`
   - Example: `sumre, dative singular "time, season" — object of preposition`
   - Notes are optional and only included when user adds clarifying notes

### Annotation Formatting Rules
- **Superscripts:** Case, Number, Gender, POS type (pron:rel, n:, v:, prep:, etc.)
- **Subscripts:** Detailed morphological info (declension class, verb class, case/number combinations like "dat1", "acc1")
- **Compact format:** Use abbreviations to keep annotations readable
  - "dat1" = dative singular
  - "acc1" = accusative singular
  - "genpl" = genitive plural
  - "pron:rel" = relative pronoun
  - "v:strong7" = strong verb class VII
  - "n:weak" = weak noun declension
- **Missing annotations:** Omitted (no placeholder)
- **Uncertain annotations:** Show `?` after value (e.g., `dat1?`)
- **Alternatives:** Show with `/` separator (e.g., `w2/s3`)

### Export Implementation
- Use `python-docx` library (or `docx` package).
- Create document with proper styles (Title, Body, Default).
- Iterate through sentences in `display_order`.
- For each sentence, extract tokens and annotations.
- Build Old English paragraph with:
  - Word text (italic)
  - Superscript runs for case/number/gender/POS
  - Subscript runs for detailed morphological info
- Add translation paragraph.
- Generate notes list from `notes` table entries (only clarifying notes, not grammatical annotations).
- Handle missing data gracefully (omit missing annotations, skip empty translations).
- Export dialog allows file selection and format options (DOCX only initially).

---

## ✅ Acceptance Criteria

- Paste OE text → app splits into sentences automatically.
- Sentences display with translation areas beneath.
- Tokens editable; annotations saved incrementally.
- Inline HUD shows annotation completeness.
- Notes attach to tokens, spans, or sentences.
- Autosave prevents data loss (<1s lag).
- DOCX export matches target layout.
- Help (F1) lists all shortcuts.
- Filters find incomplete annotations.

---

## 🚀 Next Steps for Implementation

1. Scaffold PySide6 app and database schema.
2. Implement sentence tokenizer + editor layout.
3. Add token HUD + annotation keymap logic.
4. Build autosave and undo system.
5. Implement DOCX export template.
6. Create `/help/` Markdown docs and Help dialog.
7. Add filtering and refinement utilities.
8. Package for macOS and Windows (PyInstaller).

---

**End of Plan — ready to paste into Cursor, Warp, or Claude Code.**
