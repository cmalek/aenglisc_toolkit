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

## Matching

Remembered annotations match by partially normalized spelling.

- Capitalization is ignored, so `Hē` matches `hē`.
- Eth and thorn match, so `ðæt` matches `þæt`.
- Hyphens are ignored, and the dots on `ċ` and `ġ` are ignored, so `ġe-wāt` matches `gewāt`.
- Length marks still count, so `gē` does not match `ge`, and `gōd` does not match `god`.

The spelling shown in the remembered-annotation list stays as it was first saved. Remembering another casing updates that entry instead of adding a second one.

If one scope already has two entries with the same partially normalized spelling, neither is applied. Remember refuses to pick one, and names both spellings so you can delete one.

## Scopes

There are two remembered-annotation scopes:

- **Global**: available across all projects
- **Project**: available only inside the current project

If both a global and project remembered annotation exist for the same partially normalized spelling, the **project** one wins inside that project. Those two are not a conflict.

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

- create a new remembered annotation for a token spelling
- edit an existing remembered annotation
- delete a remembered annotation you no longer want

When creating a new entry manually, enter the token spelling it should match. The prompt asks for that spelling, not an exact copy of one token. Capitalization, eth and thorn, hyphens, and the dots on `ċ` and `ġ` count as the same spelling. Length marks do not. If that spelling is already remembered in the scope, the existing entry opens for editing and keeps the spelling already saved. If two entries already share that spelling, the dialog names both and does not save a third.

## Applying Remembered Annotations

To apply remembered annotations across the current project:

1. Open **Tools -> Apply Remembered Annotations**
2. The app finds tokens whose partially normalized spelling matches a remembered entry visible to the project
3. Matching tokens that are safe to auto-fill are updated in one batch
4. When the run finishes, a summary dialog titled **Apply Remembered Annotations** appears. It reports how many tokens were updated. When some tokens already had an annotation, it says how many were skipped. When remembered spellings conflict, it names those saved spellings and does not apply those entries. When nothing matched, it says so. The dialog reports counts. It does not list each token.

The app does not blindly overwrite existing filled-in annotations. Tokens that already contain meaningful annotation data are skipped.

## Undo Support

Applying remembered annotations is undoable as a single batch operation:

- use **Ctrl+Z** to undo the batch apply
- use redo if you want to restore it again

This makes it safe to try remembered annotations and roll back if the result is not what you wanted.

## Good Uses

Remembered annotations work best when:

- the same token spelling repeats often, including differences of case, eth/thorn, hyphenation, or consonant dots
- you want a project-specific override for one text
- you have established a stable annotation for a common form

They are less useful when the same spelling can legitimately take different analyses in different contexts. In those cases, review matches carefully before relying on batch application.

## Related Topics

- [Start Here](start-here.html)
- [Annotation Guide](annotation-guide.html)
- [Idioms Guide](idioms-guide.html)
