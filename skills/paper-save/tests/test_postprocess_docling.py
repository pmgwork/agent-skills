from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "postprocess_docling.py"


class PostprocessDoclingTest(unittest.TestCase):
    def test_preserves_headings_and_transforms_all_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work = root / "work" / "docling"
            artifacts = work / "paper_artifacts"
            artifacts.mkdir(parents=True)
            (artifacts / "first.png").write_bytes(b"first")
            (artifacts / "second.png").write_bytes(b"second")
            (artifacts / "unused.png").write_bytes(b"unused")

            markdown = work / "paper.md"
            markdown.write_text(
                "# Paper title\n"
                "## Section\n"
                "##### Deep section\n"
                f"![second](<{artifacts / 'second.png'}>)\n"
                "![first](paper_artifacts/first.png)\n"
                "![second again](paper_artifacts/second.png)\n"
                "| A | B |\n| - | - |\n| 1 | $x$ |\n"
                "```markdown\n# Do not shift\n![do-not-rewrite](fake.png)\n```\n",
                encoding="utf-8",
            )

            output_markdown = root / "final" / "prepared.md"
            output_artifacts = root / "vault" / "assets" / "Title" / "artifacts"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--markdown",
                    str(markdown),
                    "--artifacts-dir",
                    str(artifacts),
                    "--output-markdown",
                    str(output_markdown),
                    "--output-artifacts-dir",
                    str(output_artifacts),
                    "--asset-link-prefix",
                    "assets/Title/artifacts",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            output = output_markdown.read_text(encoding="utf-8")
            self.assertIn("# Paper title", output)
            self.assertIn("## Section", output)
            self.assertIn("##### Deep section", output)
            self.assertEqual(output.count("![[assets/Title/artifacts/image_001.png]]"), 2)
            self.assertIn("![[assets/Title/artifacts/image_002.png]]", output)
            self.assertIn("# Do not shift", output)
            self.assertIn("![do-not-rewrite](fake.png)", output)
            self.assertNotIn(str(work), output)
            self.assertEqual(
                sorted(path.name for path in output_artifacts.iterdir()),
                ["image_001.png", "image_002.png", "image_003.png"],
            )
            self.assertEqual((output_artifacts / "image_001.png").read_bytes(), b"second")
            self.assertEqual((output_artifacts / "image_002.png").read_bytes(), b"first")
            self.assertEqual((output_artifacts / "image_003.png").read_bytes(), b"unused")

    def test_rejects_nonempty_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifacts = root / "paper_artifacts"
            artifacts.mkdir()
            markdown = root / "paper.md"
            markdown.write_text("text\n", encoding="utf-8")
            output_artifacts = root / "output"
            output_artifacts.mkdir()
            (output_artifacts / "existing.png").write_bytes(b"existing")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--markdown",
                    str(markdown),
                    "--artifacts-dir",
                    str(artifacts),
                    "--output-markdown",
                    str(root / "prepared.md"),
                    "--output-artifacts-dir",
                    str(output_artifacts),
                    "--asset-link-prefix",
                    "assets/Title/artifacts",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("空ではありません", result.stderr)
            self.assertEqual((output_artifacts / "existing.png").read_bytes(), b"existing")

    def test_accepts_document_without_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            markdown = root / "paper.md"
            markdown.write_text("# Text-only paper\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--markdown",
                    str(markdown),
                    "--artifacts-dir",
                    str(root / "missing_artifacts"),
                    "--output-markdown",
                    str(root / "final" / "prepared.md"),
                    "--output-artifacts-dir",
                    str(root / "final" / "artifacts"),
                    "--asset-link-prefix",
                    "assets/Title/artifacts",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("# Text-only paper", (root / "final" / "prepared.md").read_text(encoding="utf-8"))
            self.assertEqual(list((root / "final" / "artifacts").iterdir()), [])

    def test_accepts_preexisting_empty_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifacts = root / "paper_artifacts"
            artifacts.mkdir()
            (artifacts / "figure.png").write_bytes(b"figure")
            markdown = root / "paper.md"
            markdown.write_text("![figure](paper_artifacts/figure.png)\n", encoding="utf-8")
            output_artifacts = root / "final" / "artifacts"
            output_artifacts.mkdir(parents=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--markdown",
                    str(markdown),
                    "--artifacts-dir",
                    str(artifacts),
                    "--output-markdown",
                    str(root / "final" / "prepared.md"),
                    "--output-artifacts-dir",
                    str(output_artifacts),
                    "--asset-link-prefix",
                    "assets/Title/artifacts",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((output_artifacts / "image_001.png").read_bytes(), b"figure")


if __name__ == "__main__":
    unittest.main()
