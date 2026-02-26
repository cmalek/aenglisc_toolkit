# Full Translation Window

## Overview

The Full Translation Window is a focused reading and export view for a single project. It presents the entire Old English text and Modern English translation side by side, with project notes and token details available while you read.

## How to Open It

1. Open a project.
2. Use **Window → Full Translation**.

The window title is `Full Translation - <project name>`.

## What You Can Do in This Window

### Read the Full Text Side by Side

- Left pane: full Old English text.
- Right pane: full Modern English translation.
- Scrolling is synchronized.

### Search Across the Full Project

- Use the toolbar search field to highlight matches in:
  - Old English text
  - Modern English text
  - Note list

### Inspect Notes in Context

- Notes are listed under the text panes.
- Click a note to highlight the corresponding token span in the Old English pane.
- Click again to clear the note highlight.

### Use Token/Idiom Details

- Click a token in the Old English pane to open the details sidebar.
- The sidebar shows annotation information for the selected token/idiom.

### Navigate Back to Main Editor Context

- Double-clicking OE text can navigate to the corresponding sentence in the main window.

## Exporting PDF from Full Translation Window

Use the **Export PDF** button in the toolbar.

1. Click **Export PDF**.
2. Choose a file location and name.
3. Save as `.pdf`.

The PDF is generated using a LaTeX-based layout pipeline for high-quality print output.

## PDF Structure

The exported PDF includes these sections in this order:

1. **Title**: `Translation: <project title>`
2. **Source** line (if set)
3. **Translator** line (if set)
4. **Full-width horizontal rule**
5. **Two side-by-side columns**
   - Left: Old English
   - Right: Translation
   - Notes appear as real footnotes in the Old English flow
6. **Full-width horizontal rule**
7. **About this text** (only if project-level notes exist)
8. **Full-width horizontal rule**
9. **Glossary**
   - Alphabetized entries
   - Two-column glossary layout

## Notes About Footnotes and Glossary

- Footnote markers are placed from note spans and rendered as real PDF footnotes.
- The glossary is built from token annotations (normalized root + part of speech groupings).
- Root display preserves original diacritics/dashes and can show alternate variants.
- Verb entries can include `#666` metadata markers such as `[impers]`, `[intrans]`, and `(+ inf)`.

## Back to Start Here

- [Start Here](start-here.html)
