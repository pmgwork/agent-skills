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
