from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_heading_structure.py"


class ValidateHeadingStructureTest(unittest.TestCase):
    def run_validator(self, markdown_text: str, headings: list[dict[str, object]]) -> subprocess.CompletedProcess[str]:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        markdown = root / "note.md"
        expected = root / "heading-map.json"
        markdown.write_text(markdown_text, encoding="utf-8")
        expected.write_text(json.dumps({"headings": headings}), encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--markdown",
                str(markdown),
                "--expected",
                str(expected),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_accepts_exact_pdf_derived_structure(self) -> None:
        result = self.run_validator(
            "---\ntitle: Paper\n---\n"
            "## Abstract\nText.\n"
            "## RESULTS\nText.\n"
            "### Finding One\nText.\n"
            "```markdown\n## Not a document heading\n```\n"
            "## PDF\n![[paper.pdf]]\n"
            "## BibTeX\n```bibtex\n# Not a heading\n```\n",
            [
                {"level": 2, "title": "Abstract"},
                {"level": 2, "title": "RESULTS"},
                {"level": 3, "title": "Finding One"},
            ],
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Headings: 3", result.stdout)

    def test_rejects_flattened_unnumbered_heading(self) -> None:
        result = self.run_validator(
            "## RESULTS\nText.\n"
            "## Finding One\nText.\n"
            "## PDF\n![[paper.pdf]]\n"
            "## BibTeX\n```bibtex\nentry\n```\n",
            [
                {"level": 2, "title": "RESULTS"},
                {"level": 3, "title": "Finding One"},
            ],
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("見出し2が不一致", result.stderr)

    def test_rejects_figure_label_misclassified_as_heading(self) -> None:
        result = self.run_validator(
            "## RESULTS\nText.\n"
            "### Shadows made by Owner\n"
            "## PDF\n![[paper.pdf]]\n"
            "## BibTeX\n```bibtex\nentry\n```\n",
            [{"level": 2, "title": "RESULTS"}],
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("見出し数が不一致", result.stderr)


if __name__ == "__main__":
    unittest.main()
