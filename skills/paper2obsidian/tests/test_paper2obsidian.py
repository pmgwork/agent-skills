import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from link_references import build_note, link_citations, render_references
from paper_common import PaperSaveError, sanitize_title
from save_paper import save_paper
from triage import parse_references, split_references


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

    def test_existing_doi_uses_actual_filename_and_future_link_uses_saving_name(self):
        self.note("Old-name 2", title="An earlier title", doi="https://doi.org/10.1234/paper")
        refs = [{"number": 53, "kind": "paper", "title": "New title", "doi": "10.1234/PAPER"},
                {"number": 7, "kind": "paper", "title": "Future: Craft-Aligned Work"}]
        out, report = build_note("A claim [53, 7].\n\n## PDF\nOriginal\n", refs, self.root)
        self.assertIn("[[papers/Old-name 2|New title]] ^ref-53", out)
        self.assertIn("[[#^ref-53|53]]", out)
        self.assertIn("papers/" + sanitize_title(refs[1]["title"]), out)
        self.assertLess(out.index("## References"), out.index("## PDF"))
        self.assertTrue(report["references"][0]["exists"])
        self.assertFalse(report["references"][1]["exists"])
        self.assertEqual(len(list((self.root / "papers").glob("*.md"))), 1)

    def test_title_matching_tolerates_punctuation_without_fuzzy_match(self):
        self.note("Actual", title="Tandem: Craft-Aligned Work")
        rendered, _ = render_references([{"number": 1, "kind": "paper", "title": "tandem craft aligned work"}], self.root)
        self.assertIn("[[papers/Actual|", rendered)
        rendered, report = render_references([{"number": 1, "kind": "paper", "title": "Tandem"}], self.root)
        self.assertFalse(report[0]["exists"])

    def test_ambiguous_notes_require_reviewed_target(self):
        self.note("One", title="Shared title", doi="10.1/one")
        self.note("Two", title="Shared title", doi="10.1/two")
        ref = {"number": 1, "kind": "paper", "title": "Shared title"}
        with self.assertRaises(PaperSaveError): render_references([ref], self.root)
        ref["target"] = "papers/Two"
        rendered, _ = render_references([ref], self.root)
        self.assertIn("[[papers/Two|", rendered)

    def test_different_doi_cannot_link_to_same_title(self):
        self.note("Shared title", title="Shared title", doi="10.1/old")
        with self.assertRaises(PaperSaveError):
            render_references([{"number": 1, "kind": "paper", "title": "Shared title", "doi": "10.1/new"}], self.root)

    def test_colliding_future_filenames_stop(self):
        refs = [{"number": 1, "kind": "paper", "title": "A-B", "doi": "10.1/a"},
                {"number": 2, "kind": "paper", "title": "A: B", "doi": "10.1/b"}]
        with self.assertRaises(PaperSaveError): render_references(refs, self.root)

    def test_non_papers_stay_external_and_list_item_has_block_id(self):
        refs = [{"number": 1, "kind": "artwork", "title": "Work [A]", "url": "https://example.org/work_(1)"}]
        out, _ = build_note("The work [1].", refs, self.root)
        self.assertIn("^ref-1", out)
        self.assertNotIn("[[papers/", out)
        self.assertIn("https://example.org/work_%281%29", out)

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

    def test_book_without_url_keeps_original_bibliography(self):
        citation = 'David F. Noble. 2011. Forces of production. Transaction Publishers.'
        refs = [{"number": 36, "kind": "other", "title": "Forces of production", "citation": citation}]
        out, report = build_note('Previous work [36].', refs, self.root)
        self.assertIn('36. ' + citation + ' ^ref-36', out)
        self.assertTrue(report['references'][0]['unlinked'])
        self.assertNotIn('[[papers/', out)

    def test_same_doi_can_have_two_reference_title_variants(self):
        refs = [{"number": 1, "kind": "paper", "title": "A: B", "doi": "10.1/same"},
                {"number": 2, "kind": "paper", "title": "A-B", "doi": "10.1/same"}]
        rendered, _ = render_references(refs, self.root)
        self.assertIn('1. [[papers/A B|', rendered)
        self.assertIn('2. [[papers/A B|', rendered)

    def test_missing_reference_and_duplicate_number_stop(self):
        with self.assertRaises(PaperSaveError): link_citations("Claim [1–3]", {1, 3})
        ref = {"number": 1, "kind": "paper", "title": "One"}
        with self.assertRaises(PaperSaveError): render_references([ref, ref], self.root)

    def test_code_headings_do_not_split_or_reject_the_draft(self):
        text = '```md\n## References\n## PDF\nexample ^ref-53\n```\nClaim [53].\n## BibTeX\nTail\n'
        out, _ = build_note(text, [{"number": 53, "kind": "paper", "title": "Example"}], self.root)
        self.assertIn('```md\n## References\n## PDF\nexample ^ref-53\n```', out)
        self.assertLess(out.index('Claim \\['), out.index('53. [[papers/Example'))
        self.assertLess(out.index('53. [[papers/Example'), out.index('## BibTeX'))

    def test_link_delimiters_are_removed_from_new_filenames(self):
        title = 'An Artist’s #Work: A–B | [Case] ^2 %'
        sanitized = sanitize_title(title)
        self.assertEqual(sanitized, 'An Artists Work A B Case 2')
        self.assertEqual(sanitize_title('WORM: Craft-Aligned Fabrication'), 'WORM Craft Aligned Fabrication')

    def test_save_keeps_reference_blocks_images_thumbnail_pdf_and_prevents_overwrite(self):
        image = self.root / "figure.png"; image.write_bytes(b"figure")
        pdf = self.root / "original.pdf"; pdf.write_bytes(b"pdf")
        title = 'Example: Paper'
        draft = '---\ntitle: "Example: Paper"\nfigure: "figure.png"\n---\nClaim [53].\n![Figure](figure.png)\n'
        linked, _ = build_note(draft, [{"number": 53, "kind": "paper", "title": "Future paper"}], self.root)
        md = self.root / "input.md"; md.write_text(linked, encoding="utf-8")
        note, saved_pdf, count = save_paper(self.root, title, pdf, md, None)
        text = note.read_text()
        self.assertEqual(count, 1)
        self.assertEqual(saved_pdf.read_bytes(), b"pdf")
        self.assertIn('![[assets/Example Paper/artifacts/image_001.png]]', text)
        self.assertIn('figure: "assets/Example Paper/artifacts/image_001.png"', text)
        self.assertIn('[[#^ref-53|53]]', text)
        self.assertIn('^ref-53', text)
        self.assertIn('[[papers/Future paper|Future paper]]', text)
        with self.assertRaises(PaperSaveError): save_paper(self.root, title, pdf, md, None)
        self.assertEqual(note.read_text(), text)

    def test_triage_splits_references_and_drafts_titles(self):
        md = ("# Paper\n\nBody [1].\n\n## REFERENCES\n\n"
              "1. Cao, X. and Balakrishnan, R., Interacting with Information Spaces. In Proc. UIST 2006 , 225-234.\n"
              "2. Manresa, C. and Perales, F. (2005) Hand tracking for HCI. Electronic Letters, 5 (3).\n"
              "3. Tang, A., Greenberg, S.: Videoarms: embodiments in groupware. In Proc. BCS-HCI , 2006.\n"
              "4. A. Author, \"Quoted IEEE Style Title,\" in Proc. X, 2020, doi: 10.1145/123.456.\n"
              "\n## Appendix\n\nKept.\n")
        draft, section = split_references(md)
        self.assertNotIn("REFERENCES", draft)
        self.assertIn("## Appendix", draft)
        refs = parse_references(section)
        self.assertEqual([r["title"] for r in refs], [
            "Interacting with Information Spaces", "Hand tracking for HCI",
            "Videoarms: embodiments in groupware", "Quoted IEEE Style Title"])
        self.assertEqual(refs[0]["year"], 2006)
        self.assertEqual(refs[0]["first_author"], "Cao")
        self.assertEqual(refs[3]["doi"], "10.1145/123.456")
        self.assertTrue(all(r["kind"] == "paper" for r in refs))


if __name__ == '__main__':
    unittest.main()
