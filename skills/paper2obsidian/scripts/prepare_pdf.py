#!/usr/bin/env python3
"""Render PDF pages and expose native text; crop agent-selected figure regions."""
import argparse
import json
from pathlib import Path


def prepare(pdf_path: Path, output: Path, dpi: int = 120) -> dict:
    import pdfplumber
    output.mkdir(parents=True, exist_ok=False)
    (output / "pages").mkdir()
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            page.to_image(resolution=dpi).save(str(output / "pages" / f"page-{number:03d}.png"))
            pages.append({
                "page": number, "width": float(page.width), "height": float(page.height),
                "text": page.extract_text(x_tolerance=1) or "",
                "words": page.extract_words(x_tolerance=1),
                "images": [{key: image[key] for key in ("x0", "top", "x1", "bottom")} for image in page.images],
            })
    result = {"pdf": str(pdf_path.resolve()), "pages": pages}
    (output / "pdf-text.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def crop(pdf_path: Path, manifest: Path, output: Path, dpi: int = 180) -> int:
    import pdfplumber
    regions = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(regions, list) or not regions:
        raise ValueError("Figure manifest must be a non-empty array")
    names = [r["file"] for r in regions]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate figure filename")
    if any(Path(n).name != n or not n.lower().endswith(".png") or n in {".png", "..png"} for n in names):
        raise ValueError("Figure filenames must be plain .png filenames")
    with pdfplumber.open(pdf_path) as pdf:
        # Validate every region before creating any output.
        for r in regions:
            if type(r["page"]) is not int or not 1 <= r["page"] <= len(pdf.pages):
                raise ValueError("Figure page out of range")
            page = pdf.pages[r["page"] - 1]
            x0, top, x1, bottom = r["bbox"]
            if not (0 <= x0 < x1 <= page.width and 0 <= top < bottom <= page.height):
                raise ValueError("Figure box outside page")
        output.mkdir(parents=True, exist_ok=False)
        for r in regions:
            pdf.pages[r["page"] - 1].crop(tuple(r["bbox"])).to_image(resolution=dpi).save(str(output / r["file"]))
    return len(regions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--figures", type=Path, help="JSON manifest; crop figures instead of preparing pages")
    parser.add_argument("--dpi", type=int)
    args = parser.parse_args()
    if not args.pdf.is_file(): parser.error("PDF does not exist")
    if args.dpi is not None and not 36 <= args.dpi <= 600: parser.error("dpi must be 36..600")
    if args.figures:
        print(f"Cropped figures: {crop(args.pdf, args.figures, args.output, args.dpi or 180)}")
    else:
        print(f"Prepared pages: {len(prepare(args.pdf, args.output, args.dpi or 120)['pages'])}")


if __name__ == "__main__":
    main()
