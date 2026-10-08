#!/usr/bin/env python3
"""Turn Docling output into a note draft, a reference draft and review-only page images."""
import argparse
import json
import re
from pathlib import Path

REF_HEADING = re.compile(r"^#{1,6}\s+(?:\d+\.?\s+)?(references|bibliography|works cited)\s*$", re.I | re.M)
REF_ITEM = re.compile(r"^\s*(?:[-*]\s+)?(?:\[(\d+)\]|(\d+)\.)\s+(.+)$")
IMAGE_LINK = re.compile(r"(!\[[^\]]*\]\()([^)\s]+)(\))")
YEAR = re.compile(r"\b(19\d{2}|20\d{2})[a-z]?\b")
DOI = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+", re.I)


def split_references(markdown: str) -> tuple[str, str]:
    """Return the draft without its reference section, and that section."""
    match = REF_HEADING.search(markdown)
    if not match:
        return markdown, ""
    level = len(markdown[match.start():].split(" ", 1)[0])
    rest = markdown[match.end():]
    # The section ends at the next heading of the same or higher level.
    end = re.search(rf"^#{{1,{level}}}\s", rest, re.M)
    section = rest[:end.start()] if end else rest
    tail = rest[end.start():] if end else ""
    return markdown[:match.start()].rstrip() + "\n\n" + tail, section


def guess_title(raw: str) -> str:
    quoted = re.search(r"[\"“]([^\"”]{8,})[\"”]", raw)
    if quoted:
        return quoted[1].strip().rstrip(",.")
    apa = re.search(r"\(\d{4}[a-z]?\)\.\s+(.+?)\.(?:\s|$)", raw)
    if apa:
        return apa[1].strip()
    # ACM/Springer: "Surname, A. B., and Other, C. Title. In Proc." — the title starts
    # after the last initial that is not followed by another author or initial.
    for initial in re.finditer(r"\b(?:[A-Z]\.\s?)+(?:et al\.)?[,:]?\s+", raw):
        rest = raw[initial.end():]
        if re.match(r"(?:and\b|&|[A-Z]\.|[A-Z][\w'’-]+,\s*[A-Z]\.|et al\.)", rest):
            continue
        rest = re.sub(r"^\(\d{4}[a-z]?\)\.?\s*", "", rest)
        end = re.search(r"[.,]\s+In\b|\.\s|\.$", rest)
        return (rest[:end.start()] if end else rest).strip()
    return raw


def parse_references(section: str) -> list[dict]:
    refs, current = [], None
    for line in section.splitlines():
        item = REF_ITEM.match(line)
        if item:
            current = {"number": int(item[1] or item[2]), "raw": item[3].strip()}
            refs.append(current)
        elif current and line.strip():
            current["raw"] += " " + line.strip()
    for ref in refs:
        raw = ref["raw"]
        ref["kind"] = "paper"
        ref["title"] = guess_title(raw)
        if doi := DOI.search(raw):
            ref["doi"] = doi[0].rstrip(".,;")
        if years := YEAR.findall(raw):
            ref["year"] = int(years[0])
        author = re.match(r"\s*([^,.]+)", raw)
        if author:
            ref["first_author"] = author[1].strip()
    return refs


def review_items(doc: dict) -> list[dict]:
    sizes = {int(k): v["size"] for k, v in doc.get("pages", {}).items()}
    texts = {t["self_ref"]: t for t in doc.get("texts", [])}

    def where(item):
        prov = item["prov"][0]
        box, height = prov["bbox"], sizes[prov["page_no"]]["height"]
        if box.get("coord_origin") == "BOTTOMLEFT":
            bbox = [box["l"], height - box["t"], box["r"], height - box["b"]]
        else:
            bbox = [box["l"], box["t"], box["r"], box["b"]]
        return prov["page_no"], [round(v, 1) for v in bbox]

    items = []
    for kind in ("pictures", "tables"):
        for item in doc.get(kind, []):
            if not item.get("prov"):
                continue
            page, bbox = where(item)
            captions = [texts[c["$ref"]]["text"] for c in item.get("captions", []) if c["$ref"] in texts]
            items.append({"kind": kind[:-1], "page": page, "bbox": bbox, "caption": " ".join(captions) or None})
    for text in doc.get("texts", []):
        if text.get("label") == "formula" and text.get("prov"):
            page, bbox = where(text)
            items.append({"kind": "formula", "page": page, "bbox": bbox, "decoded": bool(text.get("text"))})
    return sorted(items, key=lambda i: (i["page"], i["bbox"][1]))


def render(pdf: Path, pages: set[int], output: Path, scale: float) -> None:
    import pypdfium2 as pdfium
    document = pdfium.PdfDocument(str(pdf))
    for number in sorted(pages):
        document[number - 1].render(scale=scale).to_pil().save(output / f"page-{number:03d}.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True, type=Path, help="Docling Markdown")
    parser.add_argument("--json", required=True, type=Path, help="Docling JSON")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scale", type=float, default=1.5, help="Page image scale (1.0 = 72 dpi)")
    args = parser.parse_args()

    markdown = args.markdown.read_text(encoding="utf-8")
    # Absolute image paths keep the draft valid outside Docling's output directory.
    base = args.markdown.parent
    markdown = IMAGE_LINK.sub(
        lambda m: m[1] + (str((base / m[2]).resolve()) if not Path(m[2]).is_absolute() and (base / m[2]).is_file() else m[2]) + m[3],
        markdown)
    draft, section = split_references(markdown)
    refs = parse_references(section)
    doc = json.loads(args.json.read_text(encoding="utf-8"))
    items = review_items(doc)
    titles = [t["text"] for t in doc.get("texts", []) if t.get("label") == "title"]

    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "pages").mkdir()
    (args.output / "note-draft.md").write_text(draft, encoding="utf-8")
    (args.output / "references.draft.json").write_text(json.dumps(refs, ensure_ascii=False, indent=1), encoding="utf-8")
    render(args.pdf, {1} | {i["page"] for i in items}, args.output / "pages", args.scale)
    summary = {
        "page_count": len(doc.get("pages", {})),
        "title_candidates": titles,
        "references": len(refs),
        "references_found": bool(section),
        "undecoded_formulas": markdown.count("<!-- formula-not-decoded -->"),
        "review": items,
    }
    (args.output / "triage.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "review"} | {"review_items": len(items)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
