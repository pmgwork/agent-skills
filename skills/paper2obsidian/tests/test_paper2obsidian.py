import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from link_references import build_note, link_citations
from paper_common import PaperSaveError, sanitize_title
from save_paper import save_paper
import convert
import crossref
import run
from run import parse_references, split_references


class Paper2ObsidianTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "papers").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def note(self, filename, **metadata):
        p = self.root / "papers" / (filename + ".md")
        p.write_text("---\n" + "\n".join(f"{k}: {json.dumps(v)}" for k, v in metadata.items()) + "\n---\n", encoding="utf-8")
        return p

    def build(self, entries, refs, body="A claim [1].\n"):
        text = body + "\n## References\n\n" + "".join(f"{n}. {e}\n" for n, e in entries) + "\n## PDF\nOriginal\n"
        return build_note(text, refs, self.root)

    def test_existing_doi_uses_actual_filename_and_future_link_uses_printed_title(self):
        self.note("Old-name 2", title="An earlier title", doi="https://doi.org/10.1234/paper")
        out, report = self.build(
            [(53, "A. Author. 2020. New Title. In Proc."), (7, "B. Author. 2021. Future: Craft-Aligned Work. In Proc.")],
            [{"number": 53, "doi": "10.1234/PAPER", "title": "New title"},
             {"number": 7, "doi": "10.1/future", "title": "Future: craft-aligned work"}], body="A claim [53, 7].\n")
        self.assertIn("2020. [[papers/Old-name 2|New Title]]. In Proc. ^ref-53", out)
        self.assertIn("[[papers/Future Craft Aligned Work|Future: Craft-Aligned Work]]", out)
        self.assertIn("[[#^ref-53|53]]", out)
        self.assertLess(out.index("^ref-53"), out.index("## PDF"))
        self.assertEqual([r["exists"] for r in report["references"]], [True, False])
        self.assertEqual(len(list((self.root / "papers").glob("*.md"))), 1)

    def test_entries_without_doi_keep_docling_text_with_block_id(self):
        entry = "David F. Noble. 2011. Forces of production. Transaction Publishers."
        out, report = self.build([(1, entry)], [])
        self.assertIn(f"1. {entry} ^ref-1", out)
        self.assertNotIn("[[papers/", out)
        self.assertTrue(report["references"][0]["unlinked"])

    def test_registered_title_missing_from_entry_is_not_linked(self):
        out, report = self.build([(1, "A. Author. 2019. Target-Guided Open-Domain Conversation. ArXiv.")],
                                 [{"number": 1, "doi": "10.48550/wrong", "title": "Sparse Causal Discovery"}])
        self.assertNotIn("[[papers/", out)
        self.assertIn("DOI title not in entry", report["references"][0]["reason"])

    def test_non_ascii_words_in_registered_title_may_be_absent_from_print(self):
        out, _ = self.build([(1, "C. Li. 2025. Satori: Towards Proactive AR Assistant. In CHI.")],
                            [{"number": 1, "doi": "10.1/satori", "title": "Satori 悟り: Towards Proactive AR Assistant"}])
        self.assertIn("[[papers/Satori Towards Proactive AR Assistant|Satori: Towards Proactive AR Assistant]]", out)

    def test_stray_fragments_in_another_style_are_not_entries(self):
        text = ("Claim [16].\n\n## References\n\n- [15] A. 2007. Fifteen Title Here. In Proc.\n"
                "- [16] B. 2007. Input technologies and techniques. In Handbook.\n\n"
                "16. Computing Systems (CHI '12). ACM, 2981-2990.\n")
        out, report = build_note(text, [], self.root)
        self.assertEqual(report["stray_fragments"], ["16. Computing Systems (CHI '12). ACM, 2981-2990."])
        self.assertEqual(report["duplicate_numbers"], [])
        self.assertIn("In Handbook. ^ref-16\n", out)
        self.assertIn("\n16. Computing Systems (CHI '12). ACM, 2981-2990.\n", out)

    def test_unnumbered_bullets_link_by_doi_without_block_ids(self):
        text = ("Author (2015) said so.\n\n## References\n\n"
                "- H. Agrawal. 2015. Protopiper: Physically Sketching Room-Sized Objects. In UIST. https://doi.org/10.1145/2807442\n"
                "- B. Other. 2016. Something Else Entirely. Journal.\n")
        out, report = build_note(text, [{"number": 1, "doi": "10.1145/2807442", "title": "Protopiper: Physically Sketching Room-Sized Objects"}], self.root)
        self.assertIn("[[papers/Protopiper Physically Sketching Room Sized Objects|Protopiper: Physically Sketching Room-Sized Objects]]", out)
        self.assertNotIn("^ref-", out)
        self.assertEqual(len(report["references"]), 2)

    def test_bracketed_docling_list_items_and_wrapped_lines(self):
        text = ("Claim [2].\n\n## REFERENCES\n\n- [1] One. 2020. First Title Here. In Proc.\n"
                "- [2] Two. 2021. Second Title\nwrapped here. In Proc.\n")
        out, report = build_note(text, [{"number": 2, "doi": "10.1/two", "title": "Second Title wrapped here"}], self.root)
        self.assertIn("- [1] One. 2020. First Title Here. In Proc. ^ref-1\n", out)
        self.assertIn("- [2] Two. 2021. [[papers/Second Title wrapped here|Second Title wrapped here]]. In Proc. ^ref-2", out)
        self.assertIn("[[#^ref-2|2]]", out)
        self.assertNotIn("[[#^ref-1|1]]", out[out.index("## REFERENCES"):])

    def test_ambiguous_notes_stay_unlinked_until_target_is_given(self):
        self.note("One", title="Shared title")
        self.note("Two", title="Shared title")
        ref = {"number": 1, "doi": "10.1/three", "title": "Shared title"}
        out, report = self.build([(1, "X. 2020. Shared title. In Proc.")], [ref])
        self.assertNotIn("[[papers/", out)
        self.assertIn("Ambiguous", report["references"][0]["reason"])
        out, _ = self.build([(1, "X. 2020. Shared title. In Proc.")], [ref | {"target": "papers/Two"}])
        self.assertIn("[[papers/Two|", out)

    def test_colliding_future_filenames_stop(self):
        refs = [{"number": 1, "doi": "10.1/a", "title": "A-B"}, {"number": 2, "doi": "10.1/b", "title": "A: B"}]
        out, report = self.build([(1, "X. A-B. Proc."), (2, "Y. A: B. Proc.")], refs)
        self.assertIn("[[papers/A B|A-B]]", out)
        self.assertIn("same note name as reference 1", report["references"][1]["reason"])

    def test_group_and_range_citations_preserve_code_links_math_and_yaml(self):
        source = ('---\ntitle: "[53]"\n---\n'
                  '[53, 7] and [3–5]. `array[53]` $a[53]$ \\(b[53]\\)\n'
                  '[53](https://example.org) [[Note|[53]]] ![53](image.png) \\[53]\n'
                  '````python\n```\nvalue[53]\n````\n')
        out, cited = link_citations(source, {53, 7, 3, 4, 5})
        self.assertEqual(cited, {53, 7, 3, 4, 5})
        self.assertIn('title: "[53]"', out)
        self.assertIn('[[#^ref-3|3]]–[[#^ref-5|5]]', out)
        self.assertIn('\\[ [[#^ref-53|53]], [[#^ref-7|7]] \\]', out)
        for protected in ['`array[53]`', '$a[53]$', '\\(b[53]\\)', '[53](https://example.org)',
                          '[[Note|[53]]]', '![53](image.png)', '\\[53]', 'value[53]']:
            self.assertIn(protected, out)

    def test_missing_reference_and_duplicate_number_stop(self):
        unmatched = []
        out, cited = link_citations("Claim [1–3] in [0, 1] and [1].", {1, 3}, unmatched)
        self.assertEqual((cited, unmatched), ({1}, ["[1–3]", "[0, 1]"]))
        self.assertIn("Claim [1–3] in [0, 1] and \\[ [[#^ref-1|1]] \\]", out)
        out, report = self.build([(1, "One."), (1, "Again.")], [])
        self.assertEqual(report["duplicate_numbers"], [1])
        self.assertIn("1. Again.\n", out)
        with self.assertRaises(PaperSaveError): build_note("Claim [1].\n", [{"number": 1, "doi": "10.1/a", "title": "T"}], self.root)

    def test_link_delimiters_are_removed_from_new_filenames(self):
        title = 'An Artist’s #Work: A–B | [Case] ^2 %'
        sanitized = sanitize_title(title)
        self.assertEqual(sanitized, 'An Artists Work A B Case 2')
        self.assertEqual(sanitize_title('WORM: Craft-Aligned Fabrication'), 'WORM Craft Aligned Fabrication')

    def test_save_keeps_reference_blocks_images_thumbnail_pdf_and_prevents_overwrite(self):
        image = self.root / "figure.png"; image.write_bytes(b"figure")
        pdf = self.root / "original.pdf"; pdf.write_bytes(b"pdf")
        title = 'Example: Paper'
        draft = ('---\ntitle: "Example: Paper"\nfigure: "figure.png"\n---\nClaim [53].\n![Figure](figure.png)\n'
                 '\n## References\n\n53. A. 2020. Future paper. In Proc.\n')
        linked, _ = build_note(draft, [{"number": 53, "doi": "10.1/f", "title": "Future paper"}], self.root)
        md = self.root / "input.md"; md.write_text(linked, encoding="utf-8")
        note, saved_pdf, count = save_paper(self.root, title, pdf, md)
        text = note.read_text()
        self.assertEqual(count, 1)
        self.assertEqual(saved_pdf.read_bytes(), b"pdf")
        self.assertIn('![[assets/Example Paper/artifacts/image_001.png]]', text)
        self.assertIn('figure: "assets/Example Paper/artifacts/image_001.png"', text)
        self.assertIn('[[#^ref-53|53]]', text)
        self.assertIn('^ref-53', text)
        self.assertIn('[[papers/Future paper|Future paper]]', text)
        with self.assertRaises(PaperSaveError): save_paper(self.root, title, pdf, md)
        self.assertEqual(note.read_text(), text)

    def test_reference_section_and_printed_dois_are_found(self):
        md = ("# Paper\n\nBody [1].\n\n## 参考文献\n\n"
              "1. A. Author, \"Quoted Title,\" in Proc. X, 2020, doi: 10.1145/123.456.\n"
              "2. Zixuan Li. 2024. Learning to Ask. ArXiv (2024). doi:10. 48550/arXiv. 2403.02754\n"
              "\n## Appendix\n\nKept.\n")
        refs = parse_references(split_references(md)[1])
        self.assertEqual([r.get("doi") for r in refs], ["10.1145/123.456", "10.48550/arXiv.2403.02754"])

    def test_crossref_list_maps_dois_only_when_order_agrees(self):
        pdf = parse_references("1. A. Smith. 2020. First Paper Title Text. In Proc.\n"
                               "2. B. Jones. 2021. Second Paper Title Text. In Proc.\n"
                               "3. C. Lee. 2022. Third Paper Title Text. In Proc.\n")
        message = {"reference": [
            {"unstructured": "A. Smith. 2020. First Paper Title Text. In Proc.", "DOI": "10.1/a"},
            {"unstructured": "B. Jones. 2021. Second Paper Title Text. In Proc.", "DOI": "10.1/b"},
            {"DOI": "10.1/c"}]}
        dois, info = crossref.reference_dois(pdf, message)
        self.assertEqual(dois, {1: "10.1/a", 2: "10.1/b", 3: "10.1/c"})
        self.assertEqual(info["crossref"], "aligned")
        self.assertEqual(crossref.reference_dois(pdf[:1], message)[0], {})
        other = {"reference": [{"unstructured": "Z. Other. 1999. Unrelated Work Entirely. Journal."}] * 3}
        self.assertEqual(crossref.reference_dois(pdf, other)[0], {})

    def test_crossref_metadata_builds_citekey_frontmatter_and_bibtex(self):
        message = {"title": ["ShadowPuppets"], "subtitle": ["supporting collocated interaction"],
                   "author": [{"given": "Lisa G.", "family": "Cowan"}, {"given": "Kevin A.", "family": "Li"}],
                   "issued": {"date-parts": [[2011, 5]]}, "DOI": "10.1145/1978942.1979340",
                   "container-title": ["Proceedings of CHI"]}
        meta = crossref.metadata(message, "@inproceedings{Cowan_2011, title={ShadowPuppets}}")
        self.assertEqual(meta["title"], "ShadowPuppets: supporting collocated interaction")
        self.assertEqual(meta["citekey"], "cowan2011shadowpuppets")
        self.assertTrue(meta["bibtex"].startswith("@inproceedings{cowan2011shadowpuppets,"))
        header = crossref.frontmatter(meta)
        self.assertIn('doi: "https://doi.org/10.1145/1978942.1979340"', header)
        self.assertIn('  - "Kevin A. Li"', header)

    def test_marker_cleanup_unlinks_internal_citation_anchors(self):
        md = ('<span id="page-1-0"></span>Users [\\[41,](#page-17-1) [72\\]](#page-18-28) said.\n'
              'See [\\(Figure](#page-10-0) 5).')
        self.assertEqual(convert.clean_markdown(md), "Users [41, 72] said.\nSee (Figure 5).")

    def test_marker_references_are_split_one_entry_per_line(self):
        md = ("Body [1].\n\n## References\n\n"
              "[1] A. 2020. First [0, 1] range. [doi:10.1/x](https://doi.org/10.1/x) [2] B. 2021.\n"
              "Second wrapped. [3] C. 2022. Third.\n\n## A Appendix\n\nKept.\n")
        out = convert.split_references(md)
        self.assertIn("- [1] A. 2020. First [0, 1] range. doi:10.1/x\n- [2] B. 2021. Second wrapped.\n- [3] C. 2022. Third.\n", out)
        self.assertIn("## A Appendix\n\nKept.", out)
        refs = parse_references(split_references(out)[1])
        self.assertEqual([r["number"] for r in refs], [1, 2, 3])
        self.assertEqual(refs[0]["doi"], "10.1/x")

    def test_marker_reference_headings_are_normalized(self):
        bold = convert.split_references("Body.\n\n#### **6. REFERENCES**\n\n[1] A. One. [2] B. Two.\n")
        self.assertIn("## References\n\n- [1] A. One.\n- [2] B. Two.\n", bold)
        inline = convert.split_references("- Acknowledgments Thanks to X. References [1] A. One. [2] B. Two.\n")
        self.assertIn("- Acknowledgments Thanks to X.\n\n## References\n\n- [1] A. One.\n- [2] B. Two.\n", inline)
        dotted = convert.split_references("## References\n\n1.Lewis, J. Text. In Proc. 1999, pp. 131-140. 2.McDirmid, S. Live. 2007.\n")
        self.assertIn("- [1] Lewis, J. Text. In Proc. 1999, pp. 131-140.\n- [2] McDirmid, S. Live. 2007.\n", dotted)
        # Unnumbered styles are left as Marker wrote them.
        keys = "## References\n\n[BLP10] BARAN I.: Clothoids. 2010. [Zit13] ZITNICK C. L.: Tokens. 2013.\n"
        self.assertIn("[BLP10] BARAN I.: Clothoids. 2010. [Zit13]", convert.split_references(keys))
        bold = convert.split_references("## References\n\n- 1. A <sup>M</sup> B. One.\n- **2.** C. Two.\n")
        self.assertIn("- [1] A M B. One.\n- [2] C. Two.\n", bold)

    def test_first_sizeable_image_becomes_the_thumbnail(self):
        from PIL import Image
        logo, figure = self.root / "logo.png", self.root / "figure.png"
        Image.new("RGB", (80, 30)).save(logo)
        Image.new("RGB", (400, 300)).save(figure)
        note = f'---\ntitle: "T"\n---\n\n![]({logo})\n\n![]({figure})\n'
        out = run.set_thumbnail(note)
        self.assertIn(f'figure: "{figure}"\n---\n', out)
        self.assertEqual(run.set_thumbnail(out), out)
        self.assertEqual(run.frontmatter_title(out), "T")

    def verify_cli(self, note):
        return subprocess.run(
            [sys.executable, run.__file__, "--work", str(self.root / "work"), "--verify-only", str(note)],
            capture_output=True, text=True,
            env={**os.environ, "PAPER_SAVE_VAULT_ROOT": str(self.root / "nonexistent-vault")},
        )

    def saved_note_for_verification(self):
        image = self.root / "figure.png"
        image.write_bytes(b"image")
        pdf = self.root / "original.pdf"
        pdf.write_bytes(b"pdf")
        draft = self.root / "draft.md"
        draft.write_text('---\ntitle: "Example"\nfigure: "figure.png"\n---\n'
                         '\n# Example\n\n## Abstract\nText.\n\n![Figure](figure.png)\n', encoding="utf-8")
        return save_paper(self.root, "Example", pdf, draft)[:2]

    def test_verify_only_checks_edited_note_without_writing_or_requiring_vault(self):
        note, _ = self.saved_note_for_verification()
        note.write_text(note.read_text(encoding="utf-8").replace("# Example\n\n", ""), encoding="utf-8")
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = self.verify_cli(note)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"status": "verified", "note": str(note.resolve()), "problems": []})
        self.assertFalse((self.root / "work").exists())
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_verify_only_reports_missing_assets_and_temporary_paths_after_edit(self):
        note, pdf = self.saved_note_for_verification()
        image = note.parent / "assets/Example/artifacts/image_001.png"
        image.unlink()
        pdf.unlink()
        with note.open("a", encoding="utf-8") as stream:
            stream.write(f'\n![Temporary]({self.root / "work" / "image.png"})\n')
        result = self.verify_cli(note)
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "invalid")
        self.assertEqual(report["problems"], [
            "note still points at temporary files",
            "missing embed: assets/Example/artifacts/image_001.png",
            "missing thumbnail: assets/Example/artifacts/image_001.png",
            "PDF was not saved",
        ])

    def test_verify_only_missing_note_fails_without_creating_files(self):
        result = self.verify_cli(self.root / "papers/missing.md")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("paper2obsidian error:", result.stderr)
        self.assertFalse((self.root / "work").exists())


if __name__ == '__main__':
    unittest.main()
