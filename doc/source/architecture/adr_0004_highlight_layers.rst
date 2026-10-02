.. _adr_0004_highlight_layers:

=====================================================================
ADR 0004: Highlight layers composed by the Old English text editor
=====================================================================

:Status: Accepted
:Date: 2026-10-01

Context
=======

Audit finding F3 (resolve order 4 of 12 in the 2026-09-13 architecture and
capability audit): several writers independently replace the whole
``QTextEdit`` ExtraSelection list on a sentence's Old English text editor.
Each one reads ``extraSelections()`` back, filters by a property tag, merges
its own selections, and writes the list again:

- ``WholeSentenceHighlighter.set_highlights`` (mode highlights) preserves
  search-tagged selections only. It therefore also drops a selected-span
  highlight whenever the mode changes.
- ``SingleInstanceHighlighter.set_existing_selections`` (the selected token,
  idiom or note span) preserves search-tagged selections with a copy of the
  same filter-and-merge code, and keeps its own ``existing_selections``
  snapshot.
- The static ``SearchHighlighter`` methods preserve everything that is not
  search-tagged.
- ``WholeSentenceHighlighter.unhighlight`` calls ``setExtraSelections([])`` and
  so wipes the other writers' selections. Entering edit mode reaches it
  through ``OldEnglishTextEdit.in_edit_mode`` and discards active search
  highlights.

Ownership of the merged list is implicit and spread over three classes tied
together only by the property tags ``1001`` and ``1002``.

An ExtraSelection also holds a ``QTextCursor`` bound to the document, and
``render_readonly_text`` rebuilds the document (inserting note superscripts,
so offsets move). Today it re-applies the span and search highlights by hand;
mode highlights are re-applied by its callers.

Colours are baked from the palette when a highlight is built.
``SentenceCard.refresh_theme`` therefore re-runs the sentence highlighter on a
live theme switch; selections built any other way go stale.

The full translation window has the same problem on its own editors, with
more writers: six ``setExtraSelections`` sites plus the static search calls.
Its Old English editor, ``FullProjectOldEnglishTextEdit``, subclasses
``OldEnglishTextEdit`` but keeps its own ``token_positions`` map keyed by
``(sentence_id, token_id)`` and never fills ``token_to_position``. That
window is out of scope here (finding F9).

Decision
========

D1 — The editor owns the merge
------------------------------

``OldEnglishTextEdit`` owns the merged ExtraSelection list. Highlighters set
or clear their own layer and never read ``extraSelections()`` back.
``SentenceCard`` remains a client.

D2 — Three layers with a fixed stacking order
---------------------------------------------

There are three highlight layers, painted bottom to top: mode, span, search.
Search is on top because a search match is the most important signal; an
opaque match therefore covers the selected span beneath it. This matches
today's visible order for search (appended last by every writer).

Mode and span become independent. Today a mode change drops the selected-span
highlight; with layers, the span survives a mode change. This is a deliberate
behaviour change.

D3 — The mode layer is a single slot
------------------------------------

Highlighting modes (none, part of speech, case, number, idiom) are mutually
exclusive: the drop-down is single-choice and ``WholeSentenceHighlighter``
holds one active command. Changing the mode replaces the mode layer wholesale;
choosing "none" clears it.

D4 — Idiom visualization contract
---------------------------------

- Idiom italics is character formatting applied in the read-only reading-text
  render. It is not an ExtraSelection and is not a layer.
- The idiom highlighting mode (all idioms, mode layer) and the selected idiom
  (one idiom, span layer) are different concepts and stay separate layers.
- They keep two distinct styles (see D6): an opaque one for the mode layer
  and a translucent one (alpha 150) for the span layer. They have been
  distinct since the first idiom commit (``617e979``). The reason for the
  alpha is not recorded; we assume it lets a selection overlay a mode layer
  without hiding it.

D5 — Scope is the sentence card's editor, selected by capability
----------------------------------------------------------------

``OldEnglishTextEdit`` declares a class attribute ``uses_highlight_layers``
(``True``). ``FullProjectOldEnglishTextEdit`` overrides it to ``False``, and
plain ``QTextEdit`` editors lack it. The static ``SearchHighlighter`` methods
keep their signatures and branch on that attribute, never on ``isinstance``:
when it is true they write the search layer, otherwise they write directly as
today. The full translation window is not folded into this design (finding
F9) and keeps its current writers and bug until then.

D6 — Layers are declarative, token-anchored and theme-resolved
--------------------------------------------------------------

A layer entry is ``(first_token_id, last_token_id, style)``. It carries no
cursor, no document offset and no concrete colour. ``style`` is a
``HighlightStyle(source, key)``: the name of an ``AnnotationLookupsMixin``
colour map plus a key (for example ``HighlightStyle("POS_COLORS", "N")``), or
the name of a single colour constant (for example
``HighlightStyle("SPAN_COLOR")``). At compose time the editor resolves:

- Offsets, through ``OldEnglishTextEdit.token_to_position``, which
  ``render_token`` fills in as it renders:
  ``start = token_to_position[first_token_id][0]`` and
  ``end = token_to_position[last_token_id][1]``.
- The character format, from the style key against the current palette,
  including the dark-theme foreground that the old ``highlight_positions`` set.

Mode entries are one per token (``first == last``). Span entries are also one per
token, as today, so note superscripts between tokens stay unhighlighted; the
``(first, last)`` shape allows a contiguous run if a future layer needs one. An entry whose token id is missing from the map, for example
after a split or delete, is skipped.

Because styles resolve at compose time, a live theme switch needs only
``recompose()``; ``SentenceCard.refresh_theme`` no longer has to rebuild the
mode highlight to recolour it.

The search layer stores token-id spans for token-based searches. A text search
stores the pattern, and the editor matches it against the rendered document
with ``document.find``, as ``highlight_text`` does now (including matches that
span superscript digits). Resolved search ranges are cached and invalidated
only when the document is rebuilt or the search layer is set or cleared, so
span and mode changes (every token click) do not rescan the document.

The editor recomposes at the end of ``render_readonly_text``, after the map is
rebuilt, which replaces the hand-written span and search re-apply code. While
the editor is editable, positions are meaningless, so composing writes no
selections.

Edit mode is modal: the search box is disabled while any card is editing, and
saving re-tokenizes the sentence, so token ids and offsets can both change.
Entering edit mode therefore clears all three layers, as it visibly does today.
On leaving edit mode, by save or cancel, the card calls a new method,
``SentenceCard.reapply_search()``. It reads the current query and scope from
the main window's search input and scope combo, derives the normalized query
with the same helper ``SearchController`` uses, and calls the existing
``highlight_search(pattern, scope, normalized_oe, None)``. Passing no token ids
makes ``highlight_search`` recompute matches against the current tokens through
``_matching_oe_token_ids``, so matches by normalized form or root are found
again. The search layer is a cache of the last query's results and is never
relied on across a token change.

D7 — Layer API and clear paths
------------------------------

``OldEnglishTextEdit`` exposes ``set_layer(layer, entries)`` and
``clear_layer(layer)``, where ``layer`` is a ``HighlightLayer`` enum
``{MODE, SPAN, SEARCH}`` declared in paint order. Each owner clears only its
own layer:

- ``WholeSentenceHighlighter.unhighlight`` clears the mode layer.
- ``SingleInstanceHighlighter.unhighlight`` clears the span layer.
- ``SearchHighlighter.clear_highlight`` clears the search layer.

Highlighter commands build entries and no longer build ``QTextCursor``
selections. The property tag ``1001``, ``existing_selections``, and the merge
code in ``set_highlights`` and ``set_existing_selections`` are removed. Tag
``1002`` (``SEARCH_HIGHLIGHT_PROPERTY``) stays, because the direct path for
editors without layers still uses it. The public ``highlight()`` and ``unhighlight()`` names are kept so
callers do not change.

Consequences
============

- No clear path can wipe another writer's selections, and the copy-pasted
  filter-and-merge code is gone. Edit mode still clears the card's highlights
  on entry, now deliberately and followed by a search re-run on exit.
- A selected span now survives a mode change, which it did not before.
- A search match found by normalized form or root now survives a re-render
  and a new card's first render; the previous pattern-only re-apply lost it.
  In the running application entering edit mode also empties the main
  window's search box (``edit_mode_started`` clears the search), so
  ``reapply_search`` finds no query on exit today; it is correct for any
  caller that keeps the query across an edit.
- Theme switching reduces to ``recompose()`` for the three layers.
- Every highlighter command's ``highlight`` body changes, because it emits
  entries instead of cursor selections, and the colour constants become
  palette-resolved style keys.
- Re-apply logic moves from ``render_readonly_text`` and the mode callers into
  one ``recompose()``. Some callers' explicit re-highlight calls become
  redundant and need to be checked individually.
- The search layer has two forms (token spans and a pattern), the one place
  the model is not purely token-anchored.
- The capability attribute is a deliberate asymmetry between the card editor
  and the full translation window, which keeps its own competing writers
  until F9.
- Follow-up tests: search-plus-mode and search-plus-span coexistence, per-layer
  clearing, mode exclusivity, stacking order, the idiom contract, edit-mode
  entry (all layers clear, nothing composed while editable) and exit
  (``reapply_search`` re-resolves at new coordinates on save, at the original
  ones on cancel), re-render with changing note superscripts, a missing token
  id, plain ``QTextEdit`` search, the full translation window still searching
  correctly, a live theme switch recolouring all layers, and a mode change
  preserving the selected span.

Open questions
==============

None. The span layer is only ever set from token order ranges (token click,
range selection, idiom, note), so the token-run entry shape is sufficient and no
whole-sentence form is needed.

Alternatives considered
=======================

- **A dedicated compositor class** that any ``QTextEdit`` could own. Cleaner
  in theory, but it widens the change into the full translation window (F9)
  for editors that have their own writers and positions.
- **Layers storing ExtraSelection lists as-is**, with ``render_readonly_text``
  clearing them and re-applying by hand. Smaller diff, but the stored cursors
  die on every rebuild and the scattered re-apply code stays.
- **Keeping per-highlighter merging with property tags** and only fixing the
  ``unhighlight`` wipe. Leaves three writers and two copies of the merge.

Related
=======

- Audit findings, tracked on their Trello cards: F3 (this decision, competing
  ExtraSelection writers); F11 (clear path on read-only editors, commit
  ``da57ad5``, a prerequisite already included in the squashed refactoring
  commit); F9 (full translation window search and highlighting, deferred).
- ``oeapp/ui/highlighting.py``, ``oeapp/ui/oe_text_edit.py``,
  ``oeapp/ui/sentence_card.py``, ``oeapp/ui/search_controller.py``.
