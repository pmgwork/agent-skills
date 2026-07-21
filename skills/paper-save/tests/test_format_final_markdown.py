from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "format_final_markdown.py"


class FormatFinalMarkdownTest(unittest.TestCase):
    def test_adds_blank_lines_around_headings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "note.md"
            output = root / "formatted.md"
            source.write_text(
                "---\n"
                'title: "Paper"\n'
                "---\n"
                "## Abstract\n"
                "Text.\n"
                "## References\n"
                "- [[Paper A]]\n"
                "- [[Paper B]]\n"
                "## PDF\n"
                "![[paper.pdf]]\n"
                "## BibTeX\n"
                "```bibtex\n"
                "# This is not a Markdown heading\n"
                "```\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(source), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "---\n"
                'title: "Paper"\n'
                "---\n"
                "## Abstract\n\n"
                "Text.\n\n"
                "## References\n\n"
                "- [[Paper A]]\n"
                "- [[Paper B]]\n\n"
                "## PDF\n\n"
                "![[paper.pdf]]\n\n"
                "## BibTeX\n\n"
                "```bibtex\n"
                "# This is not a Markdown heading\n"
                "```\n",
            )

    def test_rejects_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "note.md"
            output = root / "formatted.md"
            source.write_text("## Abstract\nText.\n", encoding="utf-8")
            output.write_text("existing\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(source), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("既に存在します", result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "existing\n")

    def test_normalizes_numbered_heading_levels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "note.md"
            output = root / "formatted.md"
            source.write_text(
                "## 2 Method\n"
                "Text.\n"
                "## 2.1 Participants\n"
                "Text.\n"
                "## 2.1.1 Recruitment\n"
                "Text.\n"
                "#### 3. Results\n"
                "Text.\n"
                "```markdown\n"
                "## 4.1 This heading is inside a fence\n"
                "```\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(source), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "## 2 Method\n\n"
                "Text.\n\n"
                "### 2.1 Participants\n\n"
                "Text.\n\n"
                "#### 2.1.1 Recruitment\n\n"
                "Text.\n\n"
                "## 3. Results\n\n"
                "Text.\n"
                "```markdown\n"
                "## 4.1 This heading is inside a fence\n"
                "```\n",
            )


if __name__ == "__main__":
    unittest.main()
