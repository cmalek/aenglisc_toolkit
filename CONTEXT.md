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
_Avoid_: Normalized surface (when you mean the general rule), slug, key

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

**Remembered Annotation**:
A token-only annotation template keyed by exact surface text, scoped globally
or to one project, used to batch-apply the same analysis to matching tokens.
_Avoid_: Annotation preset, cached annotation, autocomplete, memory

**Global Scope**:
Availability of a remembered annotation across all projects.
_Avoid_: System-wide, app-wide (unless talking about settings)

**Project Scope**:
Availability of a remembered annotation only inside one project; wins over a
global entry for the same exact surface.
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
An exported inventory of annotated forms and roots (especially in PDF),
grouped for reading — not the live annotation store itself.
_Avoid_: Dictionary, lexicon, vocabulary list (unless marketing copy)

**Full Translation**:
The side-by-side reading of an entire project's Old English text and Modern
English translation, with notes and annotation details available in context.
_Avoid_: Parallel text view (mechanism), reader mode (generic)

### Backup and transfer

**Backup**:
A timestamped, automatic or on-demand copy of the project database kept for
recovery. Distinct from a Project Export: a Backup covers every project in
the database, is not meant for sharing, and is restored rather than
imported.
_Avoid_: Snapshot, save point, project export (see Project Export)

**Project Export**:
A JSON (optionally gzip-compressed) serialization of one project's complete
data — sentences, tokens, annotations, and notes — used for sharing a single
project, archiving it, or moving it between installations.
_Avoid_: Backup (see Backup), dump, save file

**Project Import**:
Loading a Project Export file into the application, creating a new project
from it.
_Avoid_: Restore (reserved for restoring from a Backup), load
