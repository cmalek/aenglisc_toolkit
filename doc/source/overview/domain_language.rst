===============
Domain Language
===============

``Ænglisc Toolkit`` uses a handful of terms consistently, in the
application, in error messages, and in the in-app help documentation.

The application, in one sentence
=================================

``Ænglisc Toolkit`` is a local-first desktop tool that helps a translator
organize Old English text, morphological annotation, notes, and Modern
English translation — the translator makes every linguistic decision; the
app never auto-translates or auto-annotates.

Glossary
========

Your work
---------

**Project**
   A named body of work: one Old English source text plus its structure,
   annotations, notes, and Modern English translation.

**Source**
   The bibliographic origin of a project's Old English text (edition,
   manuscript, anthology, etc.).

**Chapter / Section / Paragraph / Sentence**
   The text hierarchy, in order from largest to smallest. A **Sentence**
   is the primary unit you work with — it pairs Old English wording with an
   optional Modern English translation, and owns its tokens, idioms, and
   notes.

**Verse Line**
   A poetic line number (or range) attached to a sentence, when the source
   is verse rather than prose.

Words and annotation
---------------------

**Token**
   A single Old English word occurrence in a sentence, in reading order.

**Idiom**
   A multi-token span you treat as one annotation unit, because meaning or
   grammatical role belongs to the phrase as a whole.

**Annotation**
   Your morphological and grammatical analysis of one token or one idiom:
   part of speech, grammatical features, and lexical metadata.

**Root**
   The dictionary headword you assign a word to (e.g. ``sumor``) — not
   "lemma."

**Meaning** and **Sense**
   **Meaning** is the general, dictionary-style gloss of a root. **Sense**
   is the contextual meaning of this specific attested use — narrower, and
   distinct from Meaning.

**Confidence**
   Your certainty that an annotation is correct, 0–100%.

**Incremental Annotation**
   Filling in annotation fields over time — start with just the part of
   speech, add grammatical detail later — rather than all at once.

**Remembered Annotation**
   A saved annotation template keyed to an exact Old English spelling, so
   you don't have to re-enter the same analysis every time a word recurs.

Notes and translation
-----------------------

**Note**
   Explanatory commentary attached to a token, a span of tokens, or a whole
   sentence.

**Old English Text** / **Modern English Translation**
   The source-language wording and your target-language rendering of a
   sentence (or a whole project, concatenated).

Reading and export
--------------------

**Full Translation**
   The side-by-side reading view of an entire project's Old English text
   and Modern English translation, with notes and annotation details
   available in context.

**Glossary** (exported)
   An inventory of annotated forms and roots generated for reading,
   especially in PDF export — not the same as this page.

Backup and transfer
---------------------

**Backup**
   An automatic or on-demand copy of your whole project database, kept for
   recovery.

**Project Export** / **Project Import**
   A single project's complete data as a JSON file, used to share, archive,
   or move that one project between installations — distinct from a
   Backup, which covers everything and is restored rather than imported.
