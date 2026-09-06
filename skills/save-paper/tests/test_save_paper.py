from __future__ import annotations

import importlib.util
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "save_paper.py"
SPEC = importlib.util.spec_from_file_location("save_paper", SCRIPT)
assert SPEC and SPEC.loader
save_paper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(save_paper)


class SavePaperTests(unittest.TestCase):
    def test_check_conflicts_has_no_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            papers = Path(directory) / "missing" / "papers"
            save_paper.check_conflicts(papers, "Title")
            self.assertFalse(papers.exists())

    def test_empty_assets_directory_is_a_conflict_and_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "papers" / "assets" / "Title"
            assets.mkdir(parents=True)
            with self.assertRaises(save_paper.PaperSaveError):
                save_paper.check_conflicts(root / "papers", "Title")
            self.assertTrue(assets.is_dir())

            pdf = root / "paper.pdf"
            markdown = root / "note.md"
            pdf.write_bytes(b"pdf")
            markdown.write_text("note", encoding="utf-8")
            with self.assertRaises(save_paper.PaperSaveError):
                save_paper.save_paper(root, "Title", pdf, markdown, None)
            self.assertTrue(assets.is_dir())

    def test_images_keep_extensions_and_are_collected_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts"
            nested = artifacts / "nested"
            nested.mkdir(parents=True)
            (artifacts / "figure.JPG").write_bytes(b"jpeg")
            (nested / "extra.webp").write_bytes(b"webp")
            text, images = save_paper.transform_and_collect_images(
                "![figure](artifacts/figure.JPG)\n", root, artifacts, "Title"
            )
            self.assertIn("image_001.jpg", text)
            self.assertEqual([name for _, name in images], ["image_001.jpg", "image_002.webp"])

    def test_shorter_or_annotated_fence_does_not_close_code_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "image.png"
            image.write_bytes(b"png")
            markdown = "````python\n```\n![inside](image.png)\n````\n![outside](image.png)\n"
            text, images = save_paper.transform_and_collect_images(markdown, root, None, "Title")
            self.assertIn("![inside](image.png)", text)
            self.assertIn("![[assets/Title/artifacts/image_001.png]]", text)
            self.assertEqual(len(images), 1)

    def test_partial_copy_failure_removes_only_reserved_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "paper.pdf"
            markdown = root / "note.md"
            pdf.write_bytes(b"pdf")
            markdown.write_text("complete note", encoding="utf-8")

            def failing_copy(source, destination):
                Path(destination).write_bytes(b"partial")
                self.assertFalse((root / "papers" / "Title.md").exists())
                raise OSError("simulated full disk")

            with patch.object(save_paper.shutil, "copy2", side_effect=failing_copy):
                with self.assertRaises(save_paper.PaperSaveError):
                    save_paper.save_paper(root, "Title", pdf, markdown, None)
            self.assertFalse((root / "papers" / "Title.md").exists())
            self.assertFalse((root / "papers" / "assets" / "Title").exists())
            self.assertEqual(pdf.read_bytes(), b"pdf")

    def test_note_created_before_publication_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "paper.pdf"
            markdown = root / "note.md"
            pdf.write_bytes(b"pdf")
            markdown.write_text("new note", encoding="utf-8")
            original_link = save_paper.os.link

            def concurrent_link(source, destination):
                Path(destination).write_text("other writer", encoding="utf-8")
                return original_link(source, destination)

            with patch.object(save_paper.os, "link", side_effect=concurrent_link):
                with self.assertRaises(save_paper.PaperSaveError):
                    save_paper.save_paper(root, "Title", pdf, markdown, None)
            self.assertEqual((root / "papers" / "Title.md").read_text(), "other writer")
            self.assertFalse((root / "papers" / "assets" / "Title").exists())

    def test_concurrent_same_title_has_one_winner_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / "vault"
            vault.mkdir()
            pdf = root / "paper.pdf"
            markdown = root / "note.md"
            pdf.write_bytes(b"pdf")
            markdown.write_text("complete note", encoding="utf-8")
            barrier = threading.Barrier(2)
            results: list[str] = []

            def save() -> None:
                barrier.wait()
                try:
                    save_paper.save_paper(vault, "Same Title", pdf, markdown, None)
                    results.append("saved")
                except save_paper.PaperSaveError:
                    results.append("conflict")

            threads = [threading.Thread(target=save) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertCountEqual(results, ["saved", "conflict"])
            self.assertEqual((vault / "papers" / "Same Title.md").read_text(), "complete note")
            self.assertEqual((vault / "papers" / "assets" / "Same Title" / "Same Title.pdf").read_bytes(), b"pdf")


if __name__ == "__main__":
    unittest.main()
