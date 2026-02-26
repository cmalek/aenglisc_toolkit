# Search Guide

Use the search bar at the top of the main window to find Old English terms, modern English translations, and note text.

## Search Modes

Use the scope dropdown to choose what is searched:

- **OE Text**: Searches normalized Old English token surface forms and normalized annotation roots.
- **ModE text**: Searches only the Modern English translation text (no OE normalization).
- **Notes**: Combines normalized OE matching with note-text matching.
- **All**: Combines normalized OE matching, ModE text matching, and note-text matching.

## OE Normalization Rules

For OE-aware scopes, your query is normalized before matching:

- lowercase
- remove combining-mark diacritics
- remove internal hyphens/dashes
- normalize `ð` to `þ`
- preserve OE letters like `æ` and `þ`

Matching is partial (substring), so a query like `cyn` can match `cyning`.

## Navigating Matches

- Press **Enter** (or **Ctrl+G**) to focus the first result.
- Press **N** for next match.
- Press **Shift+N** for previous match.
- The counter shows your current position as `current / total`.

When a match is in another chapter or section, the app loads that location and moves focus to the matched context:

- OE token/root match: focuses the matched token
- ModE match: focuses the sentence's ModE textbox
- Notes match: focuses the sentence card

## Exiting Search Mode

You can exit search mode by:

- Clicking **Clear**
- Pressing **Esc** while search is active

After exit, focus returns to the Modern English textbox of the sentence you were in when search began.

## Related Topics

- [Start Here](start-here.html)
- [Notes Guide](notes-guide.html)
- [Keybindings](keybindings.html)
