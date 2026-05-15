# Remembered Annotations

Remembered annotations let you save a token annotation as a reusable template and then apply it to matching tokens later.

This is useful when the same Old English word appears many times with the same analysis and you do not want to re-enter the same annotation repeatedly.

## What Gets Remembered

Remembered annotations are **token-only**. They save the grammatical fields and shared metadata you would normally set on a token annotation, such as:

- part of speech
- inflectional details
- Modern English meaning
- root

They do **not** remember idiom annotations, and they do not store per-instance sense information.

## Exact Matching

Remembered annotations match by the token's exact Old English surface text.

- Matching is case-sensitive and diacritic-sensitive.
- A remembered entry for `sæ` matches `sæ`.
- It does **not** match `sae` or a different token spelling.

Use the exact token text you want to reuse.

## Scopes

There are two remembered-annotation scopes:

- **Global**: available across all projects
- **Project**: available only inside the current project

If both a global and project remembered annotation exist for the same exact token text, the **project** one wins inside that project.

## Remembering an Annotation From Text

To save a token's current annotation as a remembered annotation:

1. In the Old English text area, right-click a token that already has an annotation.
2. Choose **Remember globally** to save it as a global remembered annotation.
3. Choose **Remember for project** to save it only for the current project.

These actions are only available when the token already has an annotation to copy from.

## Managing Remembered Annotations

Use the **Tools** menu to manage remembered annotations directly:

- **Tools -> Global Remembered Annotations...**
- **Tools -> Project Remembered Annotations...**

In the management dialog you can:

- create a new remembered annotation for an exact token text
- edit an existing remembered annotation
- delete a remembered annotation you no longer want

When creating a new entry manually, you must enter the exact token text it should match.

## Applying Remembered Annotations

To apply remembered annotations across the current project:

1. Open **Tools -> Apply Remembered Annotations**
2. The app finds tokens whose exact surface text matches remembered entries visible to the project
3. Matching tokens that are safe to auto-fill are updated in one batch

The app does not blindly overwrite existing filled-in annotations. Tokens that already contain meaningful annotation data are skipped.

## Undo Support

Applying remembered annotations is undoable as a single batch operation:

- use **Ctrl+Z** to undo the batch apply
- use redo if you want to restore it again

This makes it safe to try remembered annotations and roll back if the result is not what you wanted.

## Good Uses

Remembered annotations work best when:

- the same exact token spelling repeats often
- you want a project-specific override for one text
- you have established a stable annotation for a common form

They are less useful when the same spelling can legitimately take different analyses in different contexts. In those cases, review matches carefully before relying on batch application.

## Related Topics

- [Start Here](start-here.html)
- [Annotation Guide](annotation-guide.html)
- [Idioms Guide](idioms-guide.html)
