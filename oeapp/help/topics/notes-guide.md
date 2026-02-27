# Notes Guide

## Overview

The Notes system allows you to attach explanatory notes to ranges of words in your Old English text. Notes are displayed with superscript numbers in the text and listed in the Notes section of each sentence card.

## Adding a Note

### Selecting Word Ranges

- Click on the first word you want to include
- Hold down **Shift** and click on the last word (if you simply want a note for one word, Shift-Click twice on the same word)
- All words between the two points will be selected and highlighted

### Creating the Note

1. After selecting your word range, click the **Add Note** button (located to the left of the "Edit OE" button)
2. A note dialog opens with:

   - The selected words (shown in italics and quoted)
   - A text area where you type the note body

3. Enter your note text in the text area
4. Click **Save** to add the note, or **Cancel** to discard it

### Note Numbering

- For each sentence, notes are automatically numbered starting from 1
- Numbers increase sequentially based on the note's position in the sentence
- Notes that appear earlier in the sentence have lower numbers
- After saving, the note number appears as a superscript after the last word in the selected range

## Viewing Notes

### In the Text Area

- Note numbers appear as superscripts after the last word in each note's range
- Example: `Hwæt<sup>1</sup> we<sup>2</sup> Gar-Dena`
- Superscripts are only visible when not in edit mode

### In the Notes Section

- All notes for a sentence are displayed in the Notes section below the translation field
- Each note is prefixed with its number
- The highlighted words appear in italics and quoted at the start of the note
- Example: `1. "Hwæt" - This is an interjection meaning "Lo!" or "Listen!"`
- Notes are displayed in 10 point Helvetica font

## Editing Notes

1. **Double-click** on a note in the Notes section
2. The note dialog will open with the current note text
3. Modify the text as needed
4. Click **Save** to update the note, or **Cancel** to discard changes

## Deleting Notes

1. **Double-click** on a note in the Notes section
2. In the note dialog, click the **Delete** button
3. The note will be removed and remaining notes will be automatically renumbered

## Highlighting Word Ranges

- **Click** on a note in the Notes section to highlight its associated words in the Old English text area
- This helps you quickly locate which words a note refers to

## Editing Mode Behavior

### When Editing Old English Text

- Note superscripts are **not** displayed in the editable text area
- This keeps the text clean and easy to edit
- When you save or cancel editing, superscripts are restored

### Word Changes During Editing

The system automatically handles note associations when words change:

- **Adding words**: If you add words within a note's words range, they are automatically included in the note
- **Removing words**: If you remove words from a note's range, they are automatically removed from the note
- **Empty ranges**: If a note's words range becomes empty (all words deleted), the note is automatically deleted

## Best Practices

1. **Be specific**: Select the exact words range that your note refers to
2. **Use clear language**: Write notes that will be helpful when reviewing the text later
3. **Organize by position**: Notes are numbered by their position in the sentence, making it easy to follow along
4. **Review regularly**: Click on notes to highlight their words and verify they still refer to the correct text

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Select words range | Click first words, then **Shift+Click** last words |
| Add note | Click **Add Note** button (after selecting words) |
| Edit note | **Double-click** note in Notes section |
| Highlight note words | **Click** note in Notes section |

## Workflow Tips

1. Read through a sentence first to identify areas that need notes
2. Select words ranges carefully - you can always edit the note later if needed
3. Use notes to explain:

   - Unusual grammatical constructions
   - Historical or cultural context
   - Translation choices
   - Ambiguous interpretations
   - Cross-references to other parts of the text

4. Click on notes while reading to quickly see which words they refer to
5. Notes persist across sessions and are included in project exports

## Undo Support

> **Undo support:** Many in-editor operations are undoable with `Ctrl+Z` (and redo with `Ctrl+R` / `Ctrl+Shift+R`), but project-level destructive actions are not always undoable. When in doubt, create a backup or JSON export first.

## Back to Start Here

- [Start Here](start-here.html)
