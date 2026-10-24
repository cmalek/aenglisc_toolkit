# Annotation Guide

## Overview

The Ænglisc Toolkit allows you to add detailed morphological annotations
to tokens in your text. Annotations include Part of Speech (POS), grammatical
features, and metadata.

For multi-token phrase annotation, see [Idioms Guide](idioms-guide.html).

## Starting an Annotation

1. Select a word in the Old English Text box.
2. Press **Enter** or double-click on the word to open the annotation modal
3. Select the Part of Speech from the dropdown or use keyboard shortcuts:

   - **N** - Noun
   - **V** - Verb
   - **A** - Adjective
   - **R** - Pronoun
   - **D** - Determiner/Article
   - **B** - Adverb
   - **C** - Conjunction
   - **E** - Preposition
   - **I** - Interjection

## Multi-token Idioms

When a phrase should be treated as one unit, annotate it as an idiom instead of only as separate token annotations. For the full idiom workflow, see [Idioms Guide](idioms-guide.html).

## Annotation Fields by POS

### Nouns

- **Gender**: Masculine (m), Feminine (f), Neuter (n)
- **Number**: Singular (s), Plural (p)
- **Case**: Nominative (n), Accusative (a), Genitive (g), Dative (d), Instrumental (i)
- **Declension**: Strong (s), Weak (w), Other (o), i-stem (i), u-stem (u), ja-stem (ja), jo-stem (jo), wa-stem (wa), wo-stem (wo), -pu/po

### Verbs

- **Class**: Anomolous (a), Weak Class I (w1), Weak Class II (w2), Weak Class III (w3), Strong Class I-VII (s1-s7)
- **Tense**: Past (p), Present (n)
- **Mood**: Indicative (i), Subjunctive (s), Imperative (imp)
- **Person**: First (1), Second (2), Third (3)
- **Number**: Singular (s), Plural (p)
- **Aspect**: Perfect (p), Progressive (prg), Gnomic (gn)
- **Form**: Finite (f), Infinitive (i), Participle (p)
- **Requires Infinitive**: Marks verbs that govern an infinitive complement, e.g. modal/preterite-present verbs
- **Impersonal**: Marks impersonal verbs
- **Transitivity**: Transitive or intransitive

> **Preterite-present shortcut:** Selecting verb class `preterite-present` auto-enables **Requires Infinitive**. You can manually change it afterward.

### Adjectives

- **Gender**: Masculine (m), Feminine (f), Neuter (n)
- **Number**: Singular (s), Plural (p)
- **Case**: Nominative (n), Accusative (a), Genitive (g), Dative (d), Instrumental (i)
- **Degree**: Positive (p), Comparative (c), Superlative (s)
- **Inflection**: Strong (s), Weak (w)

### Pronouns

- **Type**: Personal (p), Relative (r), Demonstrative (d), Interrogative (i)
- **Gender**: Masculine (m), Feminine (f), Neuter (n)
- **Number**: Singular (s), Plural (p)
- **Case**: Nominative (n), Accusative (a), Genitive (g), Dative (d), Instrumental (i)

### Determiners/Articles

- **Type**: Definite (d), Indefinite (i), Possessive (p), Demonstrative (D)
- **Gender**: Masculine (m), Feminine (f), Neuter (n)
- **Number**: Singular (s), Plural (p)
- **Case**: Nominative (n), Accusative (a), Genitive (g), Dative (d), Instrumental (i)

### Prepositions

- **Governed Case**: Accusative (a), Dative (d), Genitive (g), Instrumental (i)

### Conjunctions

- **Type**: Coordinating (c), Subordinating (s)

### Adverbs

- **Degree**: Positive (p), Comparative (c), Superlative (s)

## Metadata Fields

The following fields are available for all POS types in the Metadata section:

- **Confidence**: Set confidence level from 0-100% using the slider
- **TODO**: Mark annotation as needing review
- **Definition of root word**: Enter the dictionary definition for the root word (e.g., "time, season")
- **Meaning/Sense in this instance**: Enter the contextual sense for this attested use (e.g., "season in this line")
- **Root**: Enter the root form of the word (e.g., "sumor")

`Root` and word surface forms are also stored in normalized internal forms for grouping/search:

- lowercase
- no combining-mark diacritics
- internal hyphens removed
- `ð` normalized to `þ`
- OE letters like `æ` and `þ` preserved

These metadata fields are displayed in the token table as "ModE" and "Root" columns.

## Applying Annotations

- Click **Apply** or press **Enter** to save your annotation
- Click **Clear** to remove all fields and start over
- Click **Cancel** or press **Escape** to discard changes

## Incremental Annotation

You don't need to fill in all fields at once! You can:

1. Start with just the Part of Speech
2. Add grammatical features later
3. Refine annotations as you work through the text

The system remembers your last-used values for each POS type, making it faster to annotate similar tokens.

## Copying an Annotation to Matching Words

Right-click a word that already has an annotation:

- **Propagate annotation** copies that annotation onto other words in the project with the same partially normalized spelling, when those words do not already have an annotation.
- **Force propagate meaning** copies only the Modern English meaning onto other annotations whose root has the same partially normalized spelling.

Partially normalized spelling ignores case, eth and thorn, hyphens, and the dots on `ċ` and `ġ`. Length marks still count, so `gē` does not match `ge`, and `gōd` does not match `god`.

The confirmation is a count. It includes the one source spelling, with its length marks kept, as in `3 words updated to match gōd`. **Force propagate meaning** puts the root's spelling in that same sentence. The dialog does not list the words that changed.

See [Remembered Annotations](remembered-annotations.html) to save a spelling and apply it later.

## Undo Support

> **Undo support:** Many in-editor operations are undoable with `Ctrl+Z` (and redo with `Ctrl+R` / `Ctrl+Shift+R`), but project-level destructive actions are not always undoable. When in doubt, create a backup or JSON export first.

## Back to Start Here

- [Start Here](start-here.html)
- [Remembered Annotations](remembered-annotations.html)
