"""Naming shared by note saving and reference linking."""
import re
import unicodedata


class PaperSaveError(RuntimeError):
    """The requested archive cannot be created without ambiguity or overwrite."""


def sanitize_title(title: str) -> str:
    """Filesystem-safe note name without Obsidian link delimiters."""
    cleaned = unicodedata.normalize("NFC", title)
    cleaned = re.sub(r'[/\\*?"<>|#^%\x00-\x1f\x7f]', "", cleaned)
    cleaned = re.sub(r"[:\-\u2013\u2014]", " ", cleaned)
    cleaned = re.sub(r"[.,'\"`()\[\]{}\u2018\u2019\u201c\u201d]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        raise PaperSaveError(f"Title has no usable filename: {title!r}")
    return cleaned


def title_key(title: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", title).casefold() if c.isalnum())


def doi_key(doi: str) -> str:
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi.strip(), flags=re.I).casefold().rstrip(".")


_NUMBERED = re.compile(r"^\s*(?:[-*]\s+)?(?:\[(\d+)\]|(\d+)\.)\s+(.*)$")
_BRACKET = re.compile(r"^\s*(?:[-*]\s+)?\[\d+\]\s")
_BULLET = re.compile(r"^\s*[-*]\s+(.*)$")


def reference_entries(section: str) -> tuple[str, list[dict], list[str]]:
    """Split a References section into (text before entries, entries, stray fragments).

    Extractors write entries in one dominant style ("- [12] ...", "12. ..." or unnumbered
    bullets). Lines in another style are stray fragments of a broken entry, not entries.
    Each entry: number (position for unnumbered lists), numbered, text, lines, trailing.
    """
    lines = section.splitlines(keepends=True)
    bracket = sum(bool(_BRACKET.match(l)) for l in lines)
    dotted = sum(bool(_NUMBERED.match(l)) for l in lines) - bracket
    bullets = sum(bool(_BULLET.match(l)) for l in lines) - sum(bool(_NUMBERED.match(l) and _BULLET.match(l)) for l in lines)
    style = ("bracket" if bracket and bracket >= dotted else "dotted" if dotted
             else "bullet" if bullets else None)
    head, items, stray = [], [], []
    for index, line in enumerate(lines):
        numbered = _NUMBERED.match(line)
        starts = (style == "bracket" and _BRACKET.match(line)) or \
                 (style == "dotted" and numbered and not _BRACKET.match(line)) or \
                 (style == "bullet" and line.strip() and (not items or _BULLET.match(line)
                                                          or not lines[index - 1].strip()))
        if starts:
            if style == "bullet":
                body = (_BULLET.match(line) or [None, line.strip()])[1]
                items.append({"number": len(items) + 1, "numbered": False, "text": body.strip(),
                              "lines": [line], "trailing": []})
            else:
                items.append({"number": int(numbered[1] or numbered[2]), "numbered": True,
                              "text": numbered[3].strip(), "lines": [line], "trailing": []})
        elif not items:
            head.append(line)
        elif line.strip() and not items[-1]["trailing"] and not numbered:
            items[-1]["lines"].append(line)  # wrapped continuation of the entry
            items[-1]["text"] += " " + line.strip()
        else:
            items[-1]["trailing"].append(line)
            if line.strip():
                stray.append(line.strip())
    return "".join(head), items, stray
