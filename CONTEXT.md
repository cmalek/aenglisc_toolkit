# Ænglisc Toolkit

Domain language for a local-first desktop tool that helps a human translator
organize Old English text, morphological annotation, notes, and Modern English
translation. The translator makes every linguistic decision; the app does not
auto-translate or auto-annotate.

## Language

### Core work

**Translator**:
The human reader who creates projects, chooses translations, and assigns
annotations. The app never acts as the translator.
_Avoid_: User (when you mean the linguistic role), annotator-as-bot, AI

**Project**:
A named body of work: one Old English source text plus the translator's
structure, annotations, notes, and Modern English translation.
_Avoid_: Document, file, corpus, workspace

**Source**:
The bibliographic origin of the Old English text in a project (edition,
manuscript, anthology, etc.).
_Avoid_: Origin (unscoped), provenance (unless you mean cataloguing metadata)

**Project Notes**:
Free-form project-level metadata about the work or text as a whole — not a
Note attached to tokens or a sentence.
_Avoid_: Notes (unscoped — see Note), description, comments

### Text hierarchy

**Chapter**:
A top-level division of a project's text, ordered within the project and often
titled.
_Avoid_: Book, part (unless you truly mean a larger unit above chapter)

**Section**:
A division within a chapter, ordered within that chapter and often titled.
_Avoid_: Subsection (unless nested further), heading

**Paragraph**:
A prose block within a section that groups one or more sentences.
_Avoid_: Block, stanza (use Verse when poetry is meant)

**Sentence**:
The primary unit of parallel Old English and Modern English text: ordered OE
wording, optional Modern English translation, and ownership of its tokens,
idioms, and notes.
_Avoid_: Line (unscoped), unit, card (UI only)

**Verse Line**:
A poetic line number (or inclusive range) associated with a sentence when the
source is verse rather than continuous prose.
_Avoid_: Line number (unscoped), stanza line (unless you mean a stanza block)

### Words and spans

**Token**:
A single Old English word occurrence in a sentence, in reading order, with an
exact surface spelling.
_Avoid_: Word (when you mean the domain object), form, item

**Surface**:
The exact Old English spelling of a token as it appears in the text, including
case and diacritics.
_Avoid_: Text, spelling (unscoped), form (unscoped), lemma

**Root**:
The dictionary headword or root form the translator assigns on an annotation
(e.g. `sumor` for an attested surface). Canonical term for dictionary form;
do not say lemma.
_Avoid_: Lemma, stem (unless discussing morphology theory), base form

**Normalized Form**:
A derived comparison key for a surface or root used for grouping and search:
lowercased, diacritics stripped, hyphens removed, `ð` folded to `þ`, with OE
letters such as `æ` and `þ` kept.
_Avoid_: Normalized surface (when you mean the general rule), slug, key,
partially normalized spelling

**Partially Normalized Spelling**:
A Normalized Form that keeps length marks. Lowercased, hyphens removed, eth
folded to thorn, and diacritics other than macrons removed, including the dots
on `ċ` and `ġ`. `gē` and `ge` differ; `Hē` and `hē` do not, nor do `ðæt` and
`þæt`, nor `ġe-wāt` and `gewāt`.
_Avoid_: Normalized form, normalized spelling, slug

**Idiom**:
A contiguous multi-token span the translator treats as one annotation unit
because meaning or grammatical role belongs to the phrase as a whole — not
limited to fixed idiomatic expressions.
_Avoid_: Phrase, MWE, multiword expression, collocation (unless speaking
linguistics outside this app)

**Span**:
A contiguous token range inside a sentence used as the target of a note or
idiom.
_Avoid_: Range (UI gesture only), selection (UI only)

### Annotation

**Annotation**:
The translator's morphological and grammatical analysis of exactly one token
or one idiom, including POS, features, and lexical metadata.
_Avoid_: Tag (alone), label, parse, analysis (unscoped)

**Part of Speech (POS)**:
The primary word-class (or phrase-class, for an idiom) chosen for an
annotation: noun, verb, adjective, pronoun, determiner/article, adverb,
conjunction, preposition, or interjection.
_Avoid_: Category, word class (unless teaching linguistics), tagset entry

**Meaning**:
The Modern English gloss of the root or word in general (dictionary-style),
shown as ModE in the token table.
_Avoid_: Translation (that's sentence-level Modern English), definition
(prefer this term only in UI copy that already says "definition of root"),
sense

**Sense**:
The contextual meaning of this attested use in this place — distinct from the
general Meaning of the root.
_Avoid_: Meaning (unscoped), gloss (unscoped), instance meaning

**Confidence**:
The translator's certainty that an annotation is correct, expressed as a
percentage from 0 to 100.
_Avoid_: Score, probability, quality

**TODO Marker**:
A flag on an annotation that it still needs review or completion.
_Avoid_: Incomplete flag, review flag, FIXME

**Incremental Annotation**:
The practice of filling annotation fields over time — starting with POS and
refining features later — rather than requiring a complete analysis at once.
_Avoid_: Partial save (mechanism), draft mode

**Annotation Preset**:
A named, reusable bundle of annotation field values for a given POS, applied
manually when filling the annotation form.
_Avoid_: Template (unscoped), remembered annotation, default

**Copied Annotation**:
The field values of one token's annotation, held by the app for the current
session so they can be pasted onto another token. Excludes timestamps.
Independent of the system clipboard.
_Avoid_: Clipboard annotation (conflates with the system clipboard), remembered
annotation, preset

**POS Field Catalog**:
The single definition, per part of speech, of which annotation fields exist,
their canonical labels, and their order. The annotation form, the preset form,
and the token details view all present the same catalog.
_Avoid_: Field list, form schema, field specs (per-surface copies)

**Remembered Annotation**:
A token-only annotation template for one Partially Normalized Spelling, scoped
globally or to one project and batch-applied to every token with that
spelling. A scope holds only one entry for that spelling, so `hē` and `Hē`
are the same entry, as are `ðæt` and `þæt`, and `ġe-wāt` and `gewāt`. `gē`
and `ge` are different entries. Remembering a spelling that matches the one
existing entry updates that entry. Remembering does not choose when that
spelling is already an Ambiguous Remembered Annotation. An entry that is
part of an Ambiguous Remembered Annotation is not applied.
_Avoid_: Annotation preset, cached annotation, autocomplete, memory, normalized
form

**Annotation Propagation**:
Copying one token's annotation onto the other tokens in the project that
share its Partially Normalized Spelling. It does not consult a Remembered
Annotation.
_Avoid_: Apply remembered annotations, meaning propagation

**Meaning Propagation**:
Giving one annotation's Meaning to every other annotation in the project
whose Root has the same Partially Normalized Spelling.
_Avoid_: Annotation propagation, remembered annotation, normalized form

**Ambiguous Remembered Annotation**:
Two remembered annotations in one scope whose Partially Normalized Spellings
are identical, whether or not the rest of the annotation agrees. Neither is
applied: choosing between them would mean translating. A project entry and a
global entry for the same Partially Normalized Spelling are not ambiguous; the
project entry wins.
_Avoid_: Conflict, duplicate, case variant, normalized form

**Global Scope**:
Availability of a remembered annotation across all projects.
_Avoid_: System-wide, app-wide (unless talking about settings)

**Project Scope**:
Availability of a remembered annotation only inside one project; wins over a
global entry for the same Partially Normalized Spelling.
_Avoid_: Local scope (ambiguous), private

**Requires Infinitive**:
A verb annotation flag marking that the verb governs an infinitive complement
(e.g. modal and preterite-present verbs).
_Avoid_: Modal flag, auxiliary flag

**Impersonal**:
A verb annotation flag marking that the verb is used with no overt
grammatical subject performing the action.
_Avoid_: Subjectless flag, no-subject flag

**Transitivity**:
A verb annotation field recording whether the verb is transitive or
intransitive in this attested use.
_Avoid_: Valency (unless discussing linguistic theory generally)

### Notes and translation

**Note**:
Explanatory commentary attached to a token, a span of tokens, or a whole
sentence, numbered by position within that sentence.
_Avoid_: Project Notes, annotation, comment, footnote (export presentation
only)

**Old English Text**:
The source-language wording of a sentence (or the concatenated project text).
_Avoid_: OE string, original, source text (prefer Source for bibliography)

**Modern English Translation**:
The translator's target-language rendering of a sentence (or the concatenated
project translation).
_Avoid_: Meaning (token/annotation level), gloss, ModE (UI abbreviation only)

### Reading and export concepts

**Glossary**:
The inventory of annotated forms and roots, grouped for reading, scoped to one
project or to all projects. It is viewed live in a window or exported (especially
in PDF); it is not the annotation store itself.
_Avoid_: Dictionary, lexicon, vocabulary list (unless marketing copy)

**Meaning Conflict**:
Two or more annotations of the same Root, part of speech, and (for nouns)
gender whose Meaning text differs. The whole Meaning field is compared, so
"war" and "war; battle" conflict. Inflectional differences (case, number,
person, tense) are never a Meaning Conflict, and same-spelling words of
different part of speech or gender are different entries, not conflicts.
_Avoid_: Inconsistency (unscoped), duplicate, mismatch

**Full Translation**:
The side-by-side reading of an entire project's Old English text and Modern
English translation, with notes and annotation details available in context.
_Avoid_: Parallel text view (mechanism), reader mode (generic)

**Old English Text Export**:
A plain-text reading copy of a project's Old English Text for sharing outside
the app: official titles, verse indent, a verse number every five lines,
without notes, annotations, or auto-generated titles.
_Avoid_: Combined, source dump, OE column dump

**Translation Export**:
A plain-text reading copy of a project's Modern English Translation for
sharing outside the app, with the same title and verse-number conventions as
Old English Text Export, without notes, annotation markup, or empty-sentence
placeholders.
_Avoid_: Combined, ModE dump, meaning export

### Highlighting

**Highlighting Mode**:
The single choice, made from a drop-down on the sentence card, of what to
colour across the whole sentence: nothing, part of speech, case, number, or
Idiom. Exactly one is active at a time.
_Avoid_: Highlighter type, filter

**Highlight Layer**:
One independent kind of colouring shown over a sentence's Old English Text.
Each layer is set and cleared on its own and never disturbs the others.
_Avoid_: Highlight channel, selection group

**Mode Layer**:
The Highlight Layer that shows the sentence's current Highlighting Mode,
colouring every Token that mode cares about.
_Avoid_: Whole-sentence highlight, combo highlight

**Span Layer**:
The Highlight Layer marking the single Token or Span the translator has
selected.
_Avoid_: Selection highlight, single-instance highlight

**Search Layer**:
The Highlight Layer marking matches for the current search. It always shows
above the other layers, because a search match is the most important signal.
_Avoid_: Find highlight, match highlight

### Backup and transfer

**Backup**:
A timestamped, automatic or on-demand copy of the project database kept for
recovery. Distinct from a Project Export: a Backup covers every project in
the database, is not meant for sharing, and is restored rather than
imported.
_Avoid_: Snapshot, save point, project export (see Project Export)

**Pre-migration Backup**:
The Backup taken immediately before a Pending Migration runs, so a failed
migration can be rolled back. It is an ordinary Backup made by the same
service: it appears in the Restore dialog and counts toward retention. It is
never taken for a Fresh Database.
_Avoid_: `.pre-migration` file, migration snapshot, rollback copy

**Pending Migration**:
The state where the database's Alembic revision differs from the Alembic head
the code expects. This comparison is the only test for whether to migrate; the
application-version catalog (`migration_versions.json`) plays no part in it.
_Avoid_: Needs upgrade, version mismatch

**Unknown Database Revision**:
A database whose Alembic revision is not among the revisions the running code
knows, usually because a newer build migrated it or a Backup from a newer build
was restored. Startup stops with a dialog naming the application version to
install, or saying it cannot be determined; the Restore dialog refuses such a
Backup.
_Avoid_: Newer database, version mismatch

**Fresh Database**:
A database with no `alembic_version` table. It is built from the current
models and stamped at head rather than replaying revisions, because the
revision chain cannot be replayed from an empty database. Every released
database has `alembic_version`, so unversioned databases are out of scope.
_Avoid_: New DB, empty DB

**Project Export**:
A JSON (optionally gzip-compressed) serialization of one project's complete
data — sentences, tokens, annotations, and notes — used for sharing a single
project between Toolkit installations, or archiving that project. Distinct
from a reading-text export (Old English Text Export, Translation Export).
_Avoid_: Backup (see Backup), dump, save file, Combined

**Project Import**:
Loading a Project Export file into the application, creating a new project
from it.
_Avoid_: Restore (reserved for restoring from a Backup), load
