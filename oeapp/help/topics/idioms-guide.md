# Idioms Guide

## What Idioms Are

In Ænglisc Toolkit, an idiom is a multi-word span that you treat as one annotation unit.

- The idiom keeps its own annotation record (separate from single-word annotations).
- Idiom word are visually grouped in the Old English text.
- Idioms are useful when meaning or grammatical function is carried by the phrase as a whole, not by one word alone.

## How to Make Idioms

1. In the Old English text area (not edit mode), start idiom range selection with **Cmd/Ctrl+Click** on a word.
2. Extend the idiom range with additional **Cmd/Ctrl+Click** actions until the full span is selected.
3. Press **A** to open the annotation modal for that span.
4. Set Part of Speech and other fields for the idiom.
5. Click **Apply** (or press **Enter**) to save.

Notes:

- If the selected range already matches an existing idiom, pressing **A** opens that idiom for editing.
- Clicking a word that belongs to a saved idiom selects the whole idiom span.

## How to Access Underlying Words After an Idiom Exists

### From the Idiom Annotation Modal

At the top of the idiom modal, the idiom words are shown as clickable word labels. Click any word label to open that word's annotation modal directly.

### From the Token Table and Sidebar

- Open the token table and select a word row to inspect word-level details in the sidebar.
- This is useful for checking word morphology even when the phrase is also captured as an idiom.

## Advice for Choosing Part of Speech for an Idiom

Use POS for the role of the full phrase in context, not just the head word.

Practical approach:

1. Identify what the whole expression is doing in the sentence (noun-like, adverb-like, conjunction-like, etc.).
2. Choose the POS that best matches that phrase-level function.
3. If the expression is ambiguous, use **Alternatives**, lower **Confidence**, and mark **TODO** for later review.
4. Keep word-level annotations for internal morphology; use idiom annotation for phrase-level behavior.

## Undo Support

> **Undo support:** Many in-editor operations are undoable with `Ctrl+Z` (and redo with `Ctrl+R` / `Ctrl+Shift+R`), but project-level destructive actions are not always undoable. When in doubt, create a backup or JSON export first.

## Back to Start Here

- [Start Here](start-here.html)
