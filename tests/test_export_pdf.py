"""Unit tests for FullTranslationPDFExporter."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from oeapp.models.note import Note
from oeapp.services.export_pdf import FullTranslationPDFExporter
from oeapp.services.import_export import ProjectImporter

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "texts"


def _import_fixture_project(
    filename: str,
    *,
    tmp_path: Path | None = None,
    normalize_empty_annotation_strings: bool = False,
):
    """Import a project fixture from ``texts/`` and return the created project."""
    importer = ProjectImporter()
    fixture_path = FIXTURES_DIR / filename
    import_path = fixture_path

    if normalize_empty_annotation_strings:
        if tmp_path is None:
            msg = "tmp_path is required when normalize_empty_annotation_strings is enabled"
            raise ValueError(msg)

        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        for sentence in data.get("sentences", []):
            for token in sentence.get("tokens", []):
                annotation = token.get("annotation")
                if not isinstance(annotation, dict):
                    continue
                coded_fields = {
                    "pos",
                    "gender",
                    "number",
                    "case",
                    "declension",
                    "article_type",
                    "pronoun_type",
                    "pronoun_number",
                    "verb_class",
                    "verb_tense",
                    "verb_person",
                    "verb_mood",
                    "verb_aspect",
                    "verb_form",
                    "verb_direct_object_case",
                    "prep_case",
                    "adjective_inflection",
                    "adjective_degree",
                    "conjunction_type",
                    "adverb_degree",
                }
                for key, value in list(annotation.items()):
                    if value == "":
                        annotation[key] = None
                        continue
                    if key not in coded_fields or not isinstance(value, str):
                        continue
                    match = re.search(r"\(([^()]+)\)\s*$", value.strip())
                    if match:
                        annotation[key] = match.group(1)

        import_path = tmp_path / filename
        import_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    project, _was_renamed = importer.import_project_json(str(import_path))
    return project


class TestFullTranslationPDFExporter:
    """Test cases for FullTranslationPDFExporter."""

    def test_export_returns_false_when_project_not_found(self, db_session, tmp_path):
        """Exporter should return False when project ID does not exist."""
        exporter = FullTranslationPDFExporter()
        output_path = tmp_path / "missing.pdf"
        assert exporter.export_side_by_side_pdf(999999, output_path) is False

    def test_build_document_tex_contains_required_structure(self, db_session):
        """Generated LaTeX should include required sections and structures."""
        from tests.conftest import create_test_project

        project = create_test_project(
            db_session,
            name="PDF Project",
            text="Se cyning.",
            source="A Source",
            translator="A Translator",
            notes="Project-level notes.",
        )
        sentence = project.sentences[0]
        sentence.text_modern = "The   king."

        token = sentence.tokens[0]
        token.annotation.pos = "N"
        token.annotation.root = "cyning"
        token.annotation.gender = "m"
        token.annotation.declension = "w"
        token.annotation.case = "n"
        token.annotation.number = "s"
        token.annotation.modern_english_meaning = "king; ruler"
        token.annotation.save()

        note = Note(
            sentence_id=sentence.id,
            start_token=token.id,
            end_token=token.id,
            note_text_md="A note here.",
        )
        note.save()

        exporter = FullTranslationPDFExporter()
        latex = exporter._build_document_tex(project)

        assert r"\usepackage{paracol}" in latex
        assert r"\usepackage[hidelinks]{hyperref}" in latex
        assert r"\usepackage{xcolor}" in latex
        assert r"\@ifundefined{footnoteplacement}{}{\footnoteplacement{m}}" in latex
        assert r"\@ifundefined{footnotelayout}{}{\footnotelayout{p}}" in latex
        assert (
            r"\renewcommand{\footnoterule}{\kern-3pt\noindent\rule{\dimexpr\textwidth\relax}{0.4pt}\kern2.6pt}"
            in latex
        )
        assert r"\section*{Translation: PDF Project}" in latex
        assert r"\begin{paracol}{2}" in latex
        assert r"\footnote{" in latex
        assert r"\section*{About this text}" in latex
        assert r"\clearpage" in latex
        assert r"\section*{Glossary}" in latex
        assert r"\begin{multicols}{3}" in latex
        assert r"\begin{multicols}{5}" in latex
        assert "How to Decode Annotations" in latex
        assert "A note here." in latex
        assert r"The \hspace*{5.40em}king." in latex
        assert "m weak" in latex
        assert r"\textcolor[HTML]{666666}{[" in latex
        assert r"\switchcolumn[1]" in latex
        assert r"\switchcolumn[0]*" in latex
        assert latex.index(r"\clearpage") < latex.index(r"\section*{Glossary}")

    def test_glossary_entries_use_compact_db_codes(self, db_session):
        """Attested forms should use short DB-code annotations."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Glossary Project", text="Ic singe.")
        sentence = project.sentences[0]

        noun = sentence.tokens[0]
        noun.annotation.pos = "N"
        noun.annotation.root = "ic"
        noun.annotation.case = "n"
        noun.annotation.number = "s"
        noun.annotation.gender = "m"
        noun.annotation.declension = "w"
        noun.annotation.modern_english_meaning = "I, self"
        noun.annotation.save()

        verb = sentence.tokens[1]
        verb.annotation.pos = "V"
        verb.annotation.root = "singan"
        verb.annotation.verb_tense = "n"
        verb.annotation.verb_mood = "i"
        verb.annotation.verb_person = "1"
        verb.annotation.number = "s"
        verb.annotation.verb_class = "s3"
        verb.annotation.modern_english_meaning = "sing"
        verb.annotation.save()

        exporter = FullTranslationPDFExporter()
        entries = exporter._build_glossary_entries(project)

        noun_entry = next(entry for entry in entries if entry.root == "ic")
        verb_entry = next(entry for entry in entries if entry.root == "singan")

        assert ("ic", "ns") in noun_entry.examples
        assert ("singe", "pri1s") in verb_entry.examples

    def test_verb_glossary_renders_impers_intrans_infinitive_metadata(self, db_session):
        """Verb glossary should render impers/intrans markers and (+ inf)."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Verb Meta", text="Mæg.")
        token = project.sentences[0].tokens[0]
        token.annotation.pos = "V"
        token.annotation.root = "magan"
        token.annotation.verb_class = "pp"
        token.annotation.verb_direct_object_case = "d"
        token.annotation.verb_impersonal = True
        token.annotation.verb_transitivity = "intransitive"
        token.annotation.verb_requires_infinitive = True
        token.annotation.modern_english_meaning = "may"
        token.annotation.save()

        exporter = FullTranslationPDFExporter()
        latex = exporter._build_document_tex(project)
        expected = (
            r"\textbf{magan} v: \textit{pret-pres} "
            r"\textcolor[HTML]{666666}{[impers]} "
            r"\textcolor[HTML]{666666}{[intrans]} (+ dat) (+ inf) may"
        )
        assert expected in latex

    def test_glossary_examples_keep_unique_code_combinations_for_same_form(self, db_session):
        """Same lowercase form should keep distinct morphology codes for N/A/R."""
        from tests.conftest import create_test_project

        project = create_test_project(
            db_session,
            name="Combo Project",
            text="Word WORD Swift SWIFT Him HIM.",
        )
        sentence = project.sentences[0]
        word_tokens = [token for token in sentence.tokens if token.surface.isalpha()]
        token_noun, token_noun_2, token_adj, token_adj_2, token_pro, token_pro_2 = word_tokens[:6]

        # Duplicate noun form with different case/number.
        token_noun.annotation.pos = "N"
        token_noun.annotation.root = "word"
        token_noun.annotation.case = "n"
        token_noun.annotation.number = "s"
        token_noun.annotation.modern_english_meaning = "word"
        token_noun.annotation.save()

        token_noun_2.annotation.pos = "N"
        token_noun_2.annotation.root = "word"
        token_noun_2.annotation.case = "d"
        token_noun_2.annotation.number = "p"
        token_noun_2.annotation.modern_english_meaning = "word"
        token_noun_2.annotation.save()

        # Duplicate adjective form with different degree/inflection/gender/case/number.
        token_adj.annotation.pos = "A"
        token_adj.annotation.root = "swift"
        token_adj.annotation.adjective_degree = "p"
        token_adj.annotation.adjective_inflection = "s"
        token_adj.annotation.gender = "m"
        token_adj.annotation.case = "n"
        token_adj.annotation.number = "s"
        token_adj.annotation.modern_english_meaning = "swift"
        token_adj.annotation.save()

        token_adj_2.annotation.pos = "A"
        token_adj_2.annotation.root = "swift"
        token_adj_2.annotation.adjective_degree = "c"
        token_adj_2.annotation.adjective_inflection = "w"
        token_adj_2.annotation.gender = "f"
        token_adj_2.annotation.case = "a"
        token_adj_2.annotation.number = "p"
        token_adj_2.annotation.modern_english_meaning = "swift"
        token_adj_2.annotation.save()

        # Duplicate pronoun form with different pronoun type/number/case.
        token_pro.annotation.pos = "R"
        token_pro.annotation.root = "he"
        token_pro.annotation.pronoun_type = "p"
        token_pro.annotation.pronoun_number = "s"
        token_pro.annotation.case = "d"
        token_pro.annotation.modern_english_meaning = "him"
        token_pro.annotation.save()

        token_pro_2.annotation.pos = "R"
        token_pro_2.annotation.root = "he"
        token_pro_2.annotation.pronoun_type = "rx"
        token_pro_2.annotation.pronoun_number = "pl"
        token_pro_2.annotation.case = "a"
        token_pro_2.annotation.modern_english_meaning = "him"
        token_pro_2.annotation.save()

        exporter = FullTranslationPDFExporter()
        entries = exporter._build_glossary_entries(project)

        noun_entry = next(entry for entry in entries if entry.root == "word" and entry.pos == "N")
        adj_entry = next(entry for entry in entries if entry.root == "swift" and entry.pos == "A")
        pro_entry = next(entry for entry in entries if entry.root == "he" and entry.pos == "R")

        assert ("word", "ns") in noun_entry.examples
        assert ("word", "dp") in noun_entry.examples
        assert ("swift", "psmns") in adj_entry.examples
        assert ("swift", "cwfap") in adj_entry.examples
        assert ("him", "psd") in pro_entry.examples
        assert ("him", "rxpla") in pro_entry.examples

    def test_conjunction_has_no_classification_or_bracketed_attested_code(self, db_session):
        """Conjunction entries omit classification and bracketed attested-form codes."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Conj Project", text="And.")
        token = project.sentences[0].tokens[0]
        token.annotation.pos = "C"
        token.annotation.root = "and"
        token.annotation.conjunction_type = "c"
        token.annotation.modern_english_meaning = "and, also"
        token.annotation.save()

        exporter = FullTranslationPDFExporter()
        latex = exporter._build_document_tex(project)

        assert r"\textbf{and} conj: and; also; \textbf{and}" in latex
        assert r"\textbf{and} conj \textit{" not in latex
        assert r"\textcolor[HTML]{666666}{[c]}" not in latex

    def test_oe_segment_preserves_spacing_and_aligns_left_edge(self):
        """OE rendering should preserve interior spacing and leading indentation."""
        exporter = FullTranslationPDFExporter()
        rendered, at_line_start = exporter._render_oe_text_segment(
            "   Hwæt    we\n   Gar-Dena",
            at_line_start=True,
        )

        assert rendered.startswith(r"\hspace*{1.80em}Hwæt")
        assert r"\hspace*{5.40em}" in rendered
        assert r"\newline \hspace*{1.80em}Gar-Dena" in rendered
        assert at_line_start is False

    def test_render_two_columns_joins_sentences_within_paragraph(self, db_session):
        """Sentences in the same paragraph should be rendered as one line-block per column."""
        from tests.conftest import create_test_project

        project = create_test_project(
            db_session,
            name="Paragraph Join",
            text="First sentence. Second sentence.",
        )
        first, second = project.sentences[:2]
        first.text_modern = "First modern."
        second.text_modern = "Second modern."
        first.save()
        second.save()

        exporter = FullTranslationPDFExporter()
        latex = exporter._render_two_columns(project)

        assert latex.count(r"\switchcolumn[1]") == 1
        assert "First sentence. Second sentence." in latex
        assert "First modern. Second modern." in latex

    def test_render_two_columns_keeps_paragraph_boundaries_separate(self, db_session):
        """Sentences from different paragraphs must not be merged together."""
        from oeapp.models.paragraph import Paragraph
        from tests.conftest import create_test_project

        project = create_test_project(
            db_session,
            name="Paragraph Split",
            text="First sentence. Second sentence.",
        )
        first, second = project.sentences[:2]
        section = project.chapters[0].sections[0]
        new_paragraph = Paragraph(section_id=section.id, order=2)
        db_session.add(new_paragraph)
        db_session.flush()

        second.paragraph_id = new_paragraph.id
        second.text_modern = "Second modern."
        first.text_modern = "First modern."
        first.save()
        second.save()

        exporter = FullTranslationPDFExporter()
        latex = exporter._render_two_columns(project)

        assert latex.count(r"\switchcolumn[1]") == 2
        assert "First modern. Second modern." not in latex

    def test_long_internal_space_runs_normalize_to_ten_spaces(self):
        """3+ internal spaces should normalize to a fixed 10-space gap."""
        exporter = FullTranslationPDFExporter()

        rendered_three = exporter._latex_escape_preserving_space_runs("Hwæt   we")
        rendered_many = exporter._latex_escape_preserving_space_runs("Hwæt        we")
        assert rendered_three == rendered_many
        assert r"\hspace*{5.40em}" in rendered_three

    def test_modern_spacing_normalizes_three_plus_spaces(self, db_session):
        """ModE column should use the same fixed wide-gap normalization."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Spacing Project", text="Se cyning.")
        sentence = project.sentences[0]
        sentence.text_modern = "The   king."

        exporter = FullTranslationPDFExporter()
        latex = exporter._build_document_tex(project)
        assert r"The \hspace*{5.40em}king." in latex

    def test_latex_escape_maps_old_english_diacritics(self):
        """Unicode OE diacritics should be emitted as explicit LaTeX accents."""
        exporter = FullTranslationPDFExporter()

        escaped = exporter._latex_escape("ā ē ī ō ū ȳ ǣ ġ ċ")
        assert r"\={a}" in escaped
        assert r"\={e}" in escaped
        assert r"\={\i}" in escaped
        assert r"\={o}" in escaped
        assert r"\={u}" in escaped
        assert r"\={y}" in escaped
        assert r"\={\ae}" in escaped
        assert r"\.{g}" in escaped
        assert r"\.{c}" in escaped

    def test_glossary_prepositions_split_by_governed_case(self, db_session):
        """Prepositions should be split by ``prep_case`` in glossary entries."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Prep Split", text="In in.")
        first, second = [token for token in project.sentences[0].tokens if token.surface.isalpha()][:2]

        first.annotation.pos = "E"
        first.annotation.root = "in"
        first.annotation.prep_case = "d"
        first.annotation.modern_english_meaning = "in"
        first.annotation.save()

        second.annotation.pos = "E"
        second.annotation.root = "in"
        second.annotation.prep_case = "a"
        second.annotation.modern_english_meaning = "into"
        second.annotation.save()

        exporter = FullTranslationPDFExporter()
        entries = exporter._build_glossary_entries(project)
        in_entries = [entry for entry in entries if entry.root == "in" and entry.pos == "E"]

        assert len(in_entries) == 2
        assert {entry.prep_case for entry in in_entries} == {"a", "d"}
        assert {entry.classification for entry in in_entries} == {"(+acc)", "(+dat)"}

    def test_glossary_groups_by_normalized_root_and_tracks_variants(self, db_session):
        """Roots that normalize the same should be deduped and variant-listed."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Norm Roots", text="Hæðen Hæþen.")
        first, second = [token for token in project.sentences[0].tokens if token.surface.isalpha()][:2]

        first.annotation.pos = "N"
        first.annotation.root = "Hæð-en"
        first.annotation.gender = "m"
        first.annotation.case = "n"
        first.annotation.number = "s"
        first.annotation.modern_english_meaning = "heathen"
        first.annotation.save()

        second.annotation.pos = "N"
        second.annotation.root = "Hæþen"
        second.annotation.gender = "m"
        second.annotation.case = "n"
        second.annotation.number = "s"
        second.annotation.modern_english_meaning = "heathen"
        second.annotation.save()

        exporter = FullTranslationPDFExporter()
        entries = exporter._build_glossary_entries(project)
        noun_entries = [entry for entry in entries if entry.pos == "N"]

        assert len(noun_entries) == 1
        assert noun_entries[0].root == "Hæð-en"
        assert "Hæþen" in noun_entries[0].root_variants

    def test_glossary_preposition_classifier_and_dash_attestation_behavior(self, db_session):
        """Prepositions show case classifier and omit bracketed ``[-]`` attestations."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Prep Display", text="Be in.")
        first, second = [token for token in project.sentences[0].tokens if token.surface.isalpha()][:2]

        first.annotation.pos = "E"
        first.annotation.root = "be"
        first.annotation.prep_case = None
        first.annotation.modern_english_meaning = "by"
        first.annotation.save()

        second.annotation.pos = "E"
        second.annotation.root = "in"
        second.annotation.prep_case = "d"
        second.annotation.modern_english_meaning = "in"
        second.annotation.save()

        exporter = FullTranslationPDFExporter()
        latex = exporter._build_document_tex(project)

        assert r"\textcolor[HTML]{666666}{(+dat)}" in latex
        assert r"\textbf{be} prep:" in latex
        assert r"\textcolor[HTML]{666666}{[-]}" not in latex

    def test_oe_sort_key_handles_special_letters_and_dotted_ge_prefix(self):
        """OE sort key should intermix ċ/c, ġ/g, ð/þ and ignore dotted-ġe for N/V."""
        exporter = FullTranslationPDFExporter()

        assert exporter._oe_glossary_sort_key("ċild", "N") == exporter._oe_glossary_sort_key(
            "cild", "N"
        )
        assert exporter._oe_glossary_sort_key("ðorn", "N") == exporter._oe_glossary_sort_key(
            "þorn", "N"
        )
        assert exporter._oe_glossary_sort_key("ġeard", "N") < exporter._oe_glossary_sort_key(
            "geard", "N"
        )

        roots = ["b", "æ", "a"]
        sorted_roots = sorted(roots, key=lambda root: exporter._oe_glossary_sort_key(root, "N"))
        assert sorted_roots == ["a", "æ", "b"]

    def test_glossary_legend_shows_only_used_codes(self, db_session):
        """Legend should include full glossary codebooks in five columns."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Legend Used Only", text="Cyning.")
        token = project.sentences[0].tokens[0]
        token.annotation.pos = "N"
        token.annotation.root = "cyning"
        token.annotation.gender = "m"
        token.annotation.case = "n"
        token.annotation.number = "s"
        token.annotation.declension = "w"
        token.annotation.modern_english_meaning = "king"
        token.annotation.save()

        exporter = FullTranslationPDFExporter()
        latex = exporter._build_document_tex(project)

        assert r"\begin{multicols}{5}" in latex
        assert r"\noindent n: noun\par" in latex
        assert r"\noindent v: verb\par" in latex
        assert r"\noindent m: masculine\par" in latex
        assert r"\noindent n: nominative\par" in latex
        assert r"\noindent f: feminine\par" in latex
        assert r"\noindent p: pos\par" in latex
        assert r"\noindent s: strong\par" in latex
        assert r"\noindent f: finite\par" in latex

    def test_decode_block_is_rendered_below_legend(self, db_session):
        """Decode help text should be positioned below the legend columns."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Legend Decode", text="Cyning.")
        token = project.sentences[0].tokens[0]
        token.annotation.pos = "N"
        token.annotation.root = "cyning"
        token.annotation.case = "n"
        token.annotation.number = "s"
        token.annotation.modern_english_meaning = "king"
        token.annotation.save()

        exporter = FullTranslationPDFExporter()
        latex = exporter._build_document_tex(project)

        assert latex.index(r"\end{multicols}") < latex.index("How to Decode Annotations")

    def test_fixture_seafarer_tex_contains_new_layout_and_long_ash(self, db_session):
        """Seafarer fixture output should include new layout and preserve long ash."""
        project = _import_fixture_project("The_Seafarer.json")
        exporter = FullTranslationPDFExporter()

        latex = exporter._build_document_tex(project)

        assert r"\@ifundefined{footnoteplacement}{}{\footnoteplacement{m}}" in latex
        assert r"\@ifundefined{footnotelayout}{}{\footnotelayout{p}}" in latex
        assert (
            r"\renewcommand{\footnoterule}{\kern-3pt\noindent\rule{\dimexpr\textwidth\relax}{0.4pt}\kern2.6pt}"
            in latex
        )
        assert r"\begin{multicols}{3}" in latex
        assert r"\begin{multicols}{5}" in latex
        assert "How to Decode Annotations" in latex
        assert r"\={\ae}" in latex

    def test_adj_and_adv_entries_omit_classification_blocks(self, db_session):
        """Adjective and adverb glossary entries should not render classification text."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Adj Adv", text="Swift quickly.")
        tokens = [token for token in project.sentences[0].tokens if token.surface.isalpha()]
        adj_token, adv_token = tokens[:2]

        adj_token.annotation.pos = "A"
        adj_token.annotation.root = "swift"
        adj_token.annotation.adjective_degree = "p"
        adj_token.annotation.adjective_inflection = "s"
        adj_token.annotation.gender = "m"
        adj_token.annotation.case = "n"
        adj_token.annotation.number = "s"
        adj_token.annotation.modern_english_meaning = "swift"
        adj_token.annotation.save()

        adv_token.annotation.pos = "B"
        adv_token.annotation.root = "swiftlice"
        adv_token.annotation.adverb_degree = "p"
        adv_token.annotation.modern_english_meaning = "swiftly"
        adv_token.annotation.save()

        exporter = FullTranslationPDFExporter()
        latex = exporter._build_document_tex(project)

        assert r"\textbf{swift} adj:" in latex
        assert r"\textbf{swift} adj: \textit{" not in latex
        assert r"\textbf{swiftlice} adv:" in latex
        assert r"\textbf{swiftlice} adv: \textit{" not in latex

    def test_fixture_caedmon_splits_in_by_case_and_legend_is_used_only(self, db_session, tmp_path):
        """Cædmon fixture should split ``in`` prepositions by case and build used-only legend."""
        project = _import_fixture_project(
            "The_Story_of_Cædmon.json",
            tmp_path=tmp_path,
            normalize_empty_annotation_strings=True,
        )
        exporter = FullTranslationPDFExporter()

        entries = exporter._build_glossary_entries(project)
        in_entries = [entry for entry in entries if entry.root == "in" and entry.pos == "E"]
        assert {entry.prep_case for entry in in_entries} >= {"a", "d"}

        latex = exporter._build_document_tex(project)
        assert r"\textcolor[HTML]{666666}{(+acc)}" in latex
        assert r"\textcolor[HTML]{666666}{(+dat)}" in latex
        assert r"\noindent v: verb\par" in latex
        assert r"\noindent f: feminine\par" in latex

    def test_export_side_by_side_pdf_success(self, db_session, tmp_path, monkeypatch):
        """Successful compile should produce a PDF at destination path."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Compile Project", text="Se cyning.")
        output_path = tmp_path / "compiled.pdf"
        exporter = FullTranslationPDFExporter()

        def fake_compile(tex_path: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
            (output_dir / "full_translation.pdf").write_bytes(b"%PDF-1.4\n%fake\n")
            return subprocess.CompletedProcess(
                args=[str(tex_path)],
                returncode=0,
                stdout="ok",
                stderr="",
            )

        monkeypatch.setattr("oeapp.services.export_pdf.compile_latex_with_tectonic", fake_compile)

        assert exporter.export_side_by_side_pdf(project.id, output_path) is True
        assert output_path.exists()

    def test_export_failure_copies_debug_artifacts(self, db_session, tmp_path, monkeypatch):
        """Failed compile should preserve .tex/.log artifacts near output path."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Fail Project", text="Se cyning.")
        output_path = tmp_path / "failed.pdf"
        exporter = FullTranslationPDFExporter()

        def fake_compile(tex_path: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
            (output_dir / "full_translation.log").write_text("compile failed", encoding="utf-8")
            return subprocess.CompletedProcess(
                args=[str(tex_path)],
                returncode=1,
                stdout="",
                stderr="bad compile",
            )

        monkeypatch.setattr("oeapp.services.export_pdf.compile_latex_with_tectonic", fake_compile)

        assert exporter.export_side_by_side_pdf(project.id, output_path) is False
        assert output_path.with_suffix(".tex").exists()
        assert output_path.with_suffix(".log").exists()
        assert output_path.with_suffix(".stderr.txt").exists()

    def test_export_failure_handles_engine_invocation_exception(
        self, db_session, tmp_path, monkeypatch
    ):
        """Unexpected engine invocation errors should fail gracefully."""
        from tests.conftest import create_test_project

        project = create_test_project(db_session, name="Engine Error", text="Se cyning.")
        output_path = tmp_path / "engine-error.pdf"
        exporter = FullTranslationPDFExporter()

        def failing_compile(tex_path: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
            msg = "permission denied"
            raise OSError(msg)

        monkeypatch.setattr(
            "oeapp.services.export_pdf.compile_latex_with_tectonic",
            failing_compile,
        )

        assert exporter.export_side_by_side_pdf(project.id, output_path) is False
        assert "Failed to run PDF engine" in (exporter.last_error or "")
