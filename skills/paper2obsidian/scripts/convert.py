#!/usr/bin/env python3
"""Convert a paper PDF with Marker: fast text-layer mode first, OCR (balanced) only when needed.

Writes <output>/paper.md and the figure images. Run with Marker's Python:  "$(sed -n '1s/^#!//p' "$(command -v marker_single)")"
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
# OCR: a page that falls into a repetition loop would otherwise generate 12k tokens for up to 10 minutes.
# A dense two-column page needs about 3k tokens.
os.environ.setdefault("SURYA_MAX_TOKENS_FULL_PAGE", "6144")
os.environ.setdefault("SURYA_INFERENCE_TIMEOUT_SECONDS", "240")


def llama_server() -> str | None:
    """Marker's OCR needs llama.cpp's llama-server: $LLAMA_CPP_BINARY or PATH."""
    candidate = os.environ.get("LLAMA_CPP_BINARY") or shutil.which("llama-server")
    return candidate if candidate and Path(candidate).is_file() else None


def convert(pdf: Path, mode: str, ocr: bool):
    from marker.config.parser import ConfigParser
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.renderers.markdown import MarkdownRenderer

    options = {"output_format": "markdown", "mode": mode, "disable_multiprocessing": True}
    if not ocr:
        options["disable_ocr"] = True
    parser = ConfigParser(options)
    converter = PdfConverter(config=parser.generate_config_dict(), artifact_dict=create_model_dict(),
                             processor_list=parser.get_processors(), renderer=parser.get_renderer())
    document = converter.build_document(str(pdf))
    return converter.resolve_dependencies(MarkdownRenderer)(document)


# ---- Markdown cleanup -------------------------------------------------------------------------

def clean_markdown(md: str) -> str:
    md = re.sub(r'<span id="[^"]*"></span>', "", md)
    # Marker links citations to internal anchors: "[\[41,](#page-17-1) [72\]](#page-18-28)".
    md = re.sub(r"\[((?:\\.|[^\]])*)\]\(#page-[^)]*\)", lambda m: re.sub(r"\\([()])", r"\1", m[1]), md)
    md = re.sub(r"\\([\[\]])", r"\1", md)
    return md


REF_HEADING = re.compile(r"^#{1,6}\s+\**\s*(?:\d+\.?\s*)?(?:references|bibliography|参考\s*文献)\s*\**\s*$", re.I | re.M)
# "References" run into the previous paragraph, followed by the first entry in any style.
REF_INLINE = re.compile(r"\**\b(?:References|REFERENCES|Bibliography)\b\**\s*(?=-?\s*(?:\[1\]|1\.\s?[A-Z]))")


# Entry markers. Trailing spaces are only looked at, never consumed, so a stray number inside an
# entry ("115- - 122. 14.Kazi") cannot swallow the space the next marker needs.
NUMBERED_BRACKET = r"(?:^|(?<=\s))-?\s*\[(\d+)\](?=\s)"
NUMBERED_DOTTED = r"(?:^|(?<=\s))-?\s*(\d+)\.(?!\d)(?=\s?[^\s\d])"


def _numbered(text: str, pattern: str) -> list[tuple[int, int, str]]:
    """Entry starts whose numbers run 1, 2, 3, ...; the longest such run wins.

    Other numbers inside entries ("pp. 2.", "[0, 1]") and a stray "1." before the list
    ("Table 1. Results") do not break the run.
    """
    matches = list(re.finditer(pattern, text))
    best = []
    for first, match in enumerate(matches):
        if int(match[1]) != 1:
            continue
        run, expected = [], 1
        for candidate in matches[first:]:
            if int(candidate[1]) == expected:
                run.append((candidate.start(), candidate.end(), f"[{expected}]"))
                expected += 1
        if len(run) > len(best):
            best = run
    return best


def split_references(md: str) -> str:
    """Normalize the References heading and put each entry on its own "- [n] ..." line.

    Marker writes the heading as "#### **6. REFERENCES**" or runs it into the previous
    paragraph, and runs entries together: "[1] A ... [2] B" or "18.Lewis ... 19.McDirmid".
    Other styles (author-year, "[BLP10]") stay as Marker wrote them; they get no block IDs.
    """
    heading = REF_HEADING.search(md)
    if heading:
        md = md[:heading.start()] + "## References" + md[heading.end():]
        start = heading.start() + len("## References")
    else:
        inline = None
        for inline in REF_INLINE.finditer(md):
            pass
        if not inline:
            return md
        md = md[:inline.start()].rstrip() + "\n\n## References\n\n" + md[inline.end():]
        start = md.index("## References", inline.start()) + len("## References")
    nxt = re.search(r"^#{1,6}\s", md[start:], re.M)
    end = start + nxt.start() if nxt else len(md)
    section = md[start:end]
    # Marker links DOIs/URLs ("[doi:10.1/x](https://doi.org/10.1/x)"); the printed text is enough.
    section = re.sub(r"\[([^\]]*)\]\((?:https?://|www\.)[^)]*\)", r"\1", section)
    section = re.sub(r"</?su[bp]>|\*\*", "", section)
    section = re.sub(r"<((?:https?://)[^>\s]+)>", r"\1", section)  # autolinks
    section = re.sub(r"(https?:)\s+//", r"\1//", section)  # "https: //doi.org/..." broken at a line end
    # Images and captions that Marker placed inside the list stay after it.
    kept = "".join(m[0] + "\n\n" for m in re.finditer(r"^!\[[^\]]*\]\([^)]*\)\s*$|^Figure \d+:.*$", section, re.M))
    section = re.sub(r"^!\[[^\]]*\]\([^)]*\)\s*$|^Figure \d+:.*$", "", section, flags=re.M)
    text = re.sub(r"\s*\n\s*", " ", section).strip()
    starts = max(_numbered(text, NUMBERED_BRACKET), _numbered(text, NUMBERED_DOTTED), key=len)
    if len(starts) < 2:
        return md[:start] + "\n\n" + section.strip() + "\n\n" + kept + md[end:]
    head = text[:starts[0][0]].strip()
    entries = [f"- {label} {text[body:(starts[i + 1][0] if i + 1 < len(starts) else len(text))].strip()}".replace("-  ", "- ")
               for i, (_, body, label) in enumerate(starts)]
    body = ("\n\n" + head if head else "") + "\n\n" + "\n".join(entries) + "\n\n" + kept
    return md[:start] + body + md[end:]


# ---- When fast mode is not enough -------------------------------------------------------------

def needs_ocr(pdf: Path, md: str) -> list[str]:
    import pypdfium2 as pdfium
    reasons = []
    document = pdfium.PdfDocument(str(pdf))
    layer = "".join(document[i].get_textpage().get_text_range() for i in range(len(document)))
    words = lambda s: re.findall(r"[^\W\d_]{3,}", s.lower())
    if len(words(layer)) < 200 * len(document) * 0.1:
        reasons.append("PDF has (almost) no text layer")
    garbled = len(re.findall("\ufffd", re.sub(r"\]\([^)]*\)", "]", md)))
    if garbled:
        reasons.append(f"{garbled} characters without Unicode mapping")
    pdf_words, out_words = words(layer), set(words(md))
    if pdf_words and sum(w in out_words for w in pdf_words) / len(pdf_words) < 0.8:
        reasons.append("more than 20% of the PDF's words are missing")
    return reasons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ocr", choices=["auto", "never", "always"], default="auto",
                        help="auto: OCR (balanced mode, ~1 min) only when the fast result is broken")
    args = parser.parse_args()
    if not args.pdf.is_file():
        parser.error("PDF does not exist")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"mode": "balanced" if args.ocr == "always" else "fast"}
    rendered = convert(args.pdf, report["mode"], ocr=report["mode"] == "balanced")
    md = rendered.markdown
    if args.ocr == "auto" and (reasons := needs_ocr(args.pdf, md)):
        report["ocr_reasons"] = reasons
        if llama_server():
            os.environ["LLAMA_CPP_BINARY"] = llama_server()
            report["mode"] = "balanced"
            rendered = convert(args.pdf, "balanced", ocr=True)
            md = rendered.markdown
        else:
            report["ocr_skipped"] = "llama-server not found: set LLAMA_CPP_BINARY or install llama.cpp"

    for name, image in rendered.images.items():
        image.save(args.output / name)
    (args.output / "paper.md").write_text(split_references(clean_markdown(md)), encoding="utf-8")
    report |= {"images": len(rendered.images),
               "garbled": (args.output / "paper.md").read_text(encoding="utf-8").count("\ufffd")}
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
