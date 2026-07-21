from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "save_paper.py"


class SavePaperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.papers = self.root / "vault" / "papers"
        self.source = self.root / "source"
        self.artifacts = self.source / "artifacts"
        self.papers.mkdir(parents=True)
        self.artifacts.mkdir(parents=True)

    def command(self, *extra: str) -> list[str]:
        return [
            sys.executable,
            str(SCRIPT),
            "--papers-dir",
            str(self.papers),
            "--sanitized-title",
            "Paper Title",
            "--citekey",
            "author2026paper",
            "--doi",
            "https://doi.org/10.1/paper",
            *extra,
        ]

    def run_command(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            self.command(*extra), check=False, capture_output=True, text=True
        )

    def note(self, image: str = "") -> str:
        return (
            "---\n"
            'title: "Paper Title"\n'
            'doi: "https://doi.org/10.1/paper"\n'
            "citekey: author2026paper\n"
            "---\n"
            "## 2 Method\n"
            "Text.\n"
            f"{image}"
            "## PDF\n"
            "![[assets/Paper Title/Paper Title.pdf]]\n"
            "## BibTeX\n"
            "```bibtex\n@article{author2026paper,}\n```\n"
        )

    def prepare(self, note: str | None = None) -> None:
        (self.source / "note.md").write_text(note or self.note(), encoding="utf-8")
        (self.source / "paper.pdf").write_bytes(b"pdf")

    def save_args(self) -> tuple[str, ...]:
        return (
            "--markdown",
            str(self.source / "note.md"),
            "--paper-pdf",
            str(self.source / "paper.pdf"),
            "--artifacts-dir",
            str(self.artifacts),
        )

    def test_check_only_accepts_unique_registration(self) -> None:
        result = self.run_command("--check-only")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_check_only_rejects_path_citekey_and_doi_conflicts(self) -> None:
        (self.papers / "Paper Title.md").write_text("existing\n", encoding="utf-8")
        result = self.run_command("--check-only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("登録先が既に存在", result.stderr)
        (self.papers / "Paper Title.md").unlink()

        (self.papers / "Existing.md").write_text(
            '---\ndoi: ""\ncitekey: author2026paper\n---\n', encoding="utf-8"
        )
        result = self.run_command("--check-only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("citekey", result.stderr)
        (self.papers / "Existing.md").write_text(
            '---\ndoi: "https://doi.org/10.1/PAPER"\ncitekey: other\n---\n',
            encoding="utf-8",
        )
        result = self.run_command("--check-only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DOI", result.stderr)

    def test_formats_and_saves_outputs(self) -> None:
        note = self.note("![[assets/Paper Title/artifacts/image_001.png]]\n").replace(
            "Text.\n",
            "Text.\n## 2.1 Sample\nText.\n```markdown\n"
            "## 9.1 Example\n![example](sample.png)\n```\n",
        )
        note = note.replace(
            "citekey: author2026paper\n",
            "citekey: author2026paper\n"
            'figure: "assets/Paper Title/artifacts/image_001.png"\n',
        )
        self.prepare(note)
        (self.artifacts / "image_001.png").write_bytes(b"image")
        (self.artifacts / "image_002.png").write_bytes(b"unused")
        result = self.run_command(*self.save_args())
        self.assertEqual(result.returncode, 0, result.stderr)

        note = (self.papers / "Paper Title.md").read_text(encoding="utf-8")
        self.assertIn("## 2 Method\n\nText.", note)
        self.assertIn("### 2.1 Sample\n\nText.", note)
        self.assertIn(
            "```markdown\n## 9.1 Example\n![example](sample.png)\n```", note
        )
        self.assertIn(
            'figure: "assets/Paper Title/artifacts/image_001.png"', note
        )
        self.assertTrue(
            (self.papers / "assets" / "Paper Title" / "Paper Title.pdf").is_file()
        )
        saved = self.papers / "assets" / "Paper Title" / "artifacts"
        self.assertEqual(len(list(saved.glob("*.png"))), 2)

    def test_rejects_empty_pdf_or_artifact_and_non_png(self) -> None:
        self.prepare()
        (self.source / "paper.pdf").write_bytes(b"")
        result = self.run_command(*self.save_args())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("原本PDF", result.stderr)

        (self.source / "paper.pdf").write_bytes(b"pdf")
        (self.artifacts / "image_001.png").write_bytes(b"")
        result = self.run_command(*self.save_args())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("空のartifact", result.stderr)

        (self.artifacts / "image_001.png").unlink()
        (self.artifacts / "image.jpg").write_bytes(b"image")
        result = self.run_command(*self.save_args())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PNG以外", result.stderr)

    def test_rejects_missing_image_and_wrong_pdf_embedding(self) -> None:
        self.prepare(self.note("![[assets/Paper Title/artifacts/image_001.png]]\n"))
        result = self.run_command(*self.save_args())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("画像リンク先", result.stderr)

        self.prepare(self.note("![[assets/Other/artifacts/image_001.png]]\n"))
        (self.artifacts / "image_001.png").write_bytes(b"image")
        result = self.run_command(*self.save_args())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("画像埋め込み先", result.stderr)

        self.prepare(self.note().replace("assets/Paper Title/Paper Title.pdf", "other.pdf"))
        result = self.run_command(*self.save_args())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PDF埋め込み先", result.stderr)

    def test_rejects_missing_or_misdirected_thumbnail(self) -> None:
        note = self.note().replace(
            "citekey: author2026paper\n",
            "citekey: author2026paper\n"
            'figure: "assets/Paper Title/artifacts/image_001.png"\n',
        )
        self.prepare(note)
        result = self.run_command(*self.save_args())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("figureの参照先がartifactsにありません", result.stderr)

        (self.artifacts / "image_001.png").write_bytes(b"image")
        self.prepare(note.replace("assets/Paper Title", "assets/Other", 1))
        result = self.run_command(*self.save_args())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("figureの参照先が命名規則と一致しません", result.stderr)


if __name__ == "__main__":
    unittest.main()
