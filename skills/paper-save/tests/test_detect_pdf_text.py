from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "detect_pdf_text.py"
SPEC = importlib.util.spec_from_file_location("detect_pdf_text", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DetectPdfTextTest(unittest.TestCase):
    def test_classifies_empty_text_as_ocr(self) -> None:
        self.assertEqual(MODULE.classify(0), "ocr")

    def test_classifies_text_as_no_ocr(self) -> None:
        self.assertEqual(MODULE.classify(200), "no-ocr")
        self.assertEqual(MODULE.classify(1), "no-ocr")

    def test_defaults_to_no_ocr_without_pdftotext(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf = Path(temp_dir) / "paper.pdf"
            pdf.write_bytes(b"pdf")
            output = io.StringIO()
            with patch.object(MODULE.shutil, "which", return_value=None):
                with redirect_stdout(output):
                    result = MODULE.run(Namespace(pdf=pdf))
            self.assertEqual(result, 0)
            self.assertIn("OCR mode: no-ocr", output.getvalue())


if __name__ == "__main__":
    unittest.main()
