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

    def test_docling_paths_with_spaces_and_parentheses_survive_save(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "3746059.3747616 (1)_artifacts"
            artifacts.mkdir()
            image = artifacts / "image_000000.png"
            image.write_bytes(b"figure")
            pdf = root / "paper.pdf"
            pdf.write_bytes(b"pdf")
            markdown = root / "note.md"
            markdown.write_text(f"![Image]({image})\n", encoding="utf-8")
            note, _, count = save_paper.save_paper(root, "WORM", pdf, markdown, artifacts)
            self.assertEqual(note.read_text(), "![[assets/WORM/artifacts/image_001.png]]\n")
            self.assertEqual(count, 1)
            self.assertEqual((root / "papers/assets/WORM/artifacts/image_001.png").read_bytes(), b"figure")

    def test_image_link_variants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "figure (draft (1)).png"
            image.write_bytes(b"figure")
            references = [
                str(image),
                image.name,
                image.as_uri(),
                f'<{image}> "Caption"',
                f'{image} "Caption"',
                image.name.replace("(", r"\(").replace(")", r"\)"),
            ]
            for reference in references:
                with self.subTest(reference=reference):
                    text, images = save_paper.transform_and_collect_images(
                        f"Before ![Image]({reference}) after ![Image]({reference})\n",
                        root, None, "Title",
                    )
                    link = "![[assets/Title/artifacts/image_001.png]]"
                    self.assertEqual(text, f"Before {link} after {link}\n")
                    self.assertEqual(len(images), 1)

    def test_invalid_image_inputs_do_not_publish_note(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "paper.pdf"
            pdf.write_bytes(b"pdf")
            markdown = root / "note.md"
            for text, artifacts in [
                ("![Image](missing (1)/image.png)", None),
                ("![Image](unclosed (path.png)", None),
                ("note", root / "missing_artifacts"),
            ]:
                with self.subTest(text=text, artifacts=artifacts):
                    markdown.write_text(text, encoding="utf-8")
                    with self.assertRaises(save_paper.PaperSaveError):
                        save_paper.save_paper(root, "Title", pdf, markdown, artifacts)
                    self.assertFalse((root / "papers").exists())

    def test_explicit_image_is_not_replaced_by_same_basename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts"
            artifacts.mkdir()
            (root / "image.png").write_bytes(b"correct")
            (artifacts / "image.png").write_bytes(b"other")
            _, images = save_paper.transform_and_collect_images(
                "![Image](image.png)", root, artifacts, "Title"
            )
            self.assertEqual(images[0][0].read_bytes(), b"correct")
            with self.assertRaises(save_paper.PaperSaveError):
                save_paper.transform_and_collect_images(
                    "![Image](missing/image.png)", root, artifacts, "Title"
                )

    def test_remote_images_cannot_resolve_to_local_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "image.png").write_bytes(b"local")
            for ref in ["https://example.com/image.png", "//example.com/image.png", "file://example.com/image.png", "data:image/png;base64,AAA"]:
                with self.subTest(ref=ref), self.assertRaises(save_paper.PaperSaveError):
                    save_paper.transform_and_collect_images(f"![Image]({ref})", root, root, "Title")

    def test_raw_special_characters_and_encoded_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["figure#1.png", "figure%20name.png", "figure name.png"]:
                image = root / name
                image.write_bytes(name.encode())
                for ref in [str(image), image.as_uri()]:
                    with self.subTest(ref=ref):
                        _, images = save_paper.transform_and_collect_images(f"![Image]({ref})", root, None, "Title")
                        self.assertEqual(images[0][0], image.resolve())
            (root / "figure%20name.png").unlink()
            _, images = save_paper.transform_and_collect_images("![Image](figure%20name.png)", root, None, "Title")
            self.assertEqual(images[0][0].name, "figure name.png")

    def test_inline_code_is_preserved_including_multiline_spans(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "image.png").write_bytes(b"image")
            code = '`![Example](missing.png)` and ``code ` ![Example](missing.png)``\n`multiline\n![Example](missing.png)`\n'
            text, images = save_paper.transform_and_collect_images(code + "![Image](image.png)", root, None, "Title")
            self.assertEqual(text, code + "![[assets/Title/artifacts/image_001.png]]")
            self.assertEqual(len(images), 1)

    def test_image_titles_with_unbalanced_parentheses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "image.png").write_bytes(b"image")
            for title in ['"view (left"', "'view right)'", r'"view \" (left"']:
                with self.subTest(title=title):
                    text, _ = save_paper.transform_and_collect_images(f"![Image](image.png {title})", root, None, "Title")
                    self.assertEqual(text, "![[assets/Title/artifacts/image_001.png]]")

    def test_thumbnail_tracks_source_and_numbered_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "first.png").write_bytes(b"first")
            (root / "figure.jpg").write_bytes(b"figure")
            for ref in ["figure.jpg", "assets/Title/artifacts/image_002.png"]:
                with self.subTest(ref=ref):
                    text, images = save_paper.transform_and_collect_images(
                        f'---\nfigure: "{ref}"\n---\n![First](first.png)\n![Figure 1](figure.jpg)', root, None, "Title"
                    )
                    self.assertIn('figure: "assets/Title/artifacts/image_002.jpg"', text)
                    self.assertEqual(images[1][0].read_bytes(), b"figure")

    def test_missing_thumbnail_aborts_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "paper.pdf"
            pdf.write_bytes(b"pdf")
            note = root / "note.md"
            note.write_text('---\nfigure: "assets/Title/artifacts/image_001.png"\n---\nBody')
            with self.assertRaises(save_paper.PaperSaveError):
                save_paper.save_paper(root, "Title", pdf, note, None)
            self.assertFalse((root / "papers").exists())

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
