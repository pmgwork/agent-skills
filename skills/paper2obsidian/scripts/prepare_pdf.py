#!/usr/bin/env python3
"""Render selected PDF pages, or crop agent-selected figure regions (PDF pt, top-left origin)."""
import argparse
import json
from pathlib import Path


def render_pages(pdf_path: Path, pages: list[int], output: Path, scale: float) -> int:
    import pypdfium2 as pdfium
    document = pdfium.PdfDocument(str(pdf_path))
    if any(not 1 <= p <= len(document) for p in pages):
        raise ValueError("Page out of range")
    output.mkdir(parents=True, exist_ok=True)
    for number in pages:
        document[number - 1].render(scale=scale).to_pil().save(output / f"page-{number:03d}.png")
    return len(pages)


def crop(pdf_path: Path, manifest: Path, output: Path, scale: float) -> int:
    import pypdfium2 as pdfium
    regions = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(regions, list) or not regions:
        raise ValueError("Figure manifest must be a non-empty array")
    names = [r["file"] for r in regions]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate figure filename")
    if any(Path(n).name != n or not n.lower().endswith(".png") or n in {".png", "..png"} for n in names):
        raise ValueError("Figure filenames must be plain .png filenames")
    document = pdfium.PdfDocument(str(pdf_path))
    # Validate every region before creating any output.
    for r in regions:
        if type(r["page"]) is not int or not 1 <= r["page"] <= len(document):
            raise ValueError("Figure page out of range")
        width, height = document[r["page"] - 1].get_size()
        x0, top, x1, bottom = r["bbox"]
        if not (0 <= x0 < x1 <= width and 0 <= top < bottom <= height):
            raise ValueError("Figure box outside page")
    output.mkdir(parents=True, exist_ok=False)
    for r in regions:
        image = document[r["page"] - 1].render(scale=scale).to_pil()
        image.crop(tuple(round(v * scale) for v in r["bbox"])).save(output / r["file"])
    return len(regions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pages", help="Comma-separated page numbers to render, e.g. 2,5")
    mode.add_argument("--figures", type=Path, help="JSON manifest of figure regions to crop")
    parser.add_argument("--scale", type=float, help="1.0 = 72 dpi (default: pages 1.5, figures 2.5)")
    args = parser.parse_args()
    if not args.pdf.is_file(): parser.error("PDF does not exist")
    if args.scale is not None and not 0.5 <= args.scale <= 8: parser.error("scale must be 0.5..8")
    if args.figures:
        print(f"Cropped figures: {crop(args.pdf, args.figures, args.output, args.scale or 2.5)}")
    else:
        pages = [int(p) for p in args.pages.split(",") if p.strip()]
        print(f"Rendered pages: {render_pages(args.pdf, pages, args.output, args.scale or 1.5)}")


if __name__ == "__main__":
    main()
