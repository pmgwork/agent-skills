"""Link numeric citations to reference blocks and paper references to Vault notes."""
import json
import html
import re
import unicodedata
from pathlib import Path

from paper_common import PaperSaveError, doi_key, reference_entries, sanitize_title, title_key
from save_paper import FENCE_RE


def scalar(header: str, key: str) -> str:
    match = re.search(rf"^{key}:\s*([^\n]*)", header, re.M)
    if not match: return ""
    value = match[1].strip()
    if value.startswith('"'):
        try: return str(json.loads(value))
        except ValueError: return value.strip('"')
    if value.startswith("'"): return value.strip("'").replace("''", "'")
    return value.split(" #", 1)[0].strip()


def index_notes(vault: Path) -> list[dict]:
    result = []
    for path in sorted((vault / "papers").rglob("*.md")):
        if "assets" in path.relative_to(vault / "papers").parts: continue
        text = path.read_text(encoding="utf-8")
        fm = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        header = fm[1] if fm else ""
        heading = re.search(r"^#\s+(.+)$", text, re.M)
        title = scalar(header, "title") or (heading[1] if heading else path.stem)
        result.append({"target": path.relative_to(vault).with_suffix("").as_posix(),
                       "keys": {title_key(title), title_key(path.stem)},
                       "doi": doi_key(scalar(header, "doi")), "header": header})
    return result


def check_target(target: str) -> None:
    p = Path(target)
    if p.is_absolute() or p.parts[:1] != ("papers",) or ".." in p.parts or p.suffix == ".md":
        raise PaperSaveError("target must be Vault-relative papers/... without .md")
    if re.search(r"[:#^|\[\]%\r\n]", target):
        raise PaperSaveError(f"Existing filename cannot be linked safely: {target}")


def resolve_reference(ref: dict, notes: list[dict]) -> tuple[str, bool]:
    if ref.get("target"):
        check_target(ref["target"])
        if not any(n["target"] == ref["target"] for n in notes):
            raise PaperSaveError(f"Explicit target not found: {ref['target']}")
        return ref["target"], True
    doi = doi_key(ref.get("doi", ""))
    candidates = [n for n in notes if doi and n["doi"] == doi]
    if not candidates:
        key = title_key(ref["title"])
        candidates = [n for n in notes if key in n["keys"] and not (doi and n["doi"] and n["doi"] != doi)]
    if len(candidates) > 1:
        # Author/year only break a title ambiguity when the metadata supports it.
        narrowed = [n for n in candidates if
                    (not ref.get("year") or scalar(n["header"], "year") == str(ref["year"])) and
                    (not ref.get("first_author") or title_key(ref["first_author"]) in title_key(n["header"]))]
        if len(narrowed) != 1:
            raise PaperSaveError(f"Ambiguous existing notes for reference {ref['number']}; specify target")
        candidates = narrowed
    if candidates:
        target = candidates[0]["target"]
        check_target(target)
        return target, True
    target = "papers/" + sanitize_title(ref["title"])
    if any(n["target"] == target for n in notes):
        raise PaperSaveError(f"Filename belongs to a different/ambiguous paper: {target}")
    return target, False


# Shield existing links, code and math before interpreting bracketed numbers.
SHIELDS = re.compile(
    r"(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)"
    r"|\$\$[\s\S]*?\$\$|(?<!\\)\$(?!\$)[^\n$]*?(?<!\\)\$"
    r"|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]"
    r"|!?\[\[[^\n]*?\]\]"
    r"|!?\[[^\]\n]*\]\([^\n]*?\)"
    r"|!?\[[^\]\n]*\]\[[^\]\n]*\]"
)
CITATION = re.compile(r"(?<![\\!\[])\[(\d+(?:\s*[,;\-–]\s*\d+)*)\](?![\](])")


def link_citations(text: str, numbers: set[int], unmatched: list | None = None) -> tuple[str, set[int]]:
    cited = set()
    unmatched = [] if unmatched is None else unmatched

    def plain(fragment):
        def replace(match):
            content = match[1]
            ns = {int(x) for x in re.findall(r"\d+", content)}
            for start, end in re.findall(r"(\d+)\s*[-–]\s*(\d+)", content):
                start, end = int(start), int(end)
                if end < start or end - start > 1000:
                    unmatched.append(match[0]); return match[0]
                ns.update(range(start, end + 1))
            # "[0, 1]" intervals and other brackets that are not citations stay as they are.
            if ns - numbers:
                unmatched.append(match[0]); return match[0]
            cited.update(ns)
            linked = re.sub(r"\d+", lambda m: f"[[#^ref-{int(m[0])}|{m[0]}]]", content)
            # Literal citation brackets must not compete with Wikilink parsing.
            return "\\[ " + linked + " \\]"
        spans = list(SHIELDS.finditer(fragment))
        output = []; cursor = 0
        for span in spans:
            output.append(CITATION.sub(replace, fragment[cursor:span.start()]))
            output.append(span[0]); cursor = span.end()
        output.append(CITATION.sub(replace, fragment[cursor:]))
        return "".join(output)

    fm = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n|$)", text, re.S)
    header = fm[0] if fm else ""
    output = [header]; pending = []; active = None
    for line in text[len(header):].splitlines(keepends=True):
        fence = FENCE_RE.match(line)
        if fence:
            if pending: output.append(plain("".join(pending))); pending = []
            token = fence["fence"]
            if active is None: active = (token[0], len(token))
            elif token[0] == active[0] and len(token) >= active[1] and not line[fence.end():].strip(): active = None
            output.append(line)
        elif active: output.append(line)
        else: pending.append(line)
    if pending: output.append(plain("".join(pending)))
    return "".join(output), cited


def body_headings(text: str):
    fm = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n|$)", text, re.S)
    offset = fm.end() if fm else 0
    active = None
    for line in text[offset:].splitlines(keepends=True):
        fence = FENCE_RE.match(line)
        if fence:
            token = fence["fence"]
            if active is None: active = (token[0], len(token))
            elif token[0] == active[0] and len(token) >= active[1] and not line[fence.end():].strip(): active = None
        elif not active:
            heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading: yield offset, len(heading[1]), heading[2]
        offset += len(line)


REF_HEADING = re.compile(r"(?:\d+\.?\s+)?(references|bibliography|works cited|参考文献|文献)", re.I)


def find_reference_section(text: str) -> tuple[int, int] | None:
    """Character span of the References section body (after its heading line)."""
    headings = list(body_headings(text))
    for index, (pos, level, title) in enumerate(headings):
        if REF_HEADING.fullmatch(unicodedata.normalize("NFKC", title).strip()):
            start = text.index("\n", pos) + 1 if "\n" in text[pos:] else len(text)
            end = next((p for p, lv, _ in headings[index + 1:] if lv <= level), len(text))
            return start, end
    return None
def wiki_label(title: str) -> str:
    return (title.replace("&", "&amp;").replace("|", "&#124;")
            .replace("[", "&#91;").replace("]", "&#93;"))


# Punctuation, spacing and HTML entities that extractors write into Markdown ("Eye&amp;Head").
SEPARATOR = r"(?:&#?\w+;|[\W_])*"


def find_title(entry: str, title: str) -> re.Match | None:
    """The registered title as printed in the entry, ignoring case, punctuation and spacing."""
    title = re.sub(r"<[^>]+>", "", html.unescape(title))  # Crossref titles may carry JATS/HTML markup
    words = re.findall(r"\w+", title)
    for candidate in (words, [w for w in words if w.isascii()]):  # "Satori 悟り:" prints as "Satori:"
        if candidate and (match := re.search(SEPARATOR.join(map(re.escape, candidate)), entry, re.I)):
            return match
    # Same letters in the same order, split differently: "2.5D" / "2.5 D", "multiplane" / "Multi-Plane".
    letters = [c for c in "".join(w for w in words if w.isascii())]
    if len(letters) >= 12:
        return re.search(SEPARATOR.join(map(re.escape, letters)), entry, re.I)
    return None


def link_title(entry: str, match: re.Match, target: str) -> str:
    return entry[:match.start()] + f"[[{target}|{wiki_label(match[0])}]]" + entry[match.end():]


def link_references(section: str, refs: list[dict], vault: Path) -> tuple[str, list[dict], set[int], dict]:
    head, items, stray = reference_entries(section)
    issues = {"stray_fragments": stray, "duplicate_numbers": [], "unknown_numbers": []}
    seen_numbers, by_number = set(), {}
    for ref in refs:
        if not isinstance(ref, dict) or type(ref.get("number")) is not int or ref["number"] in by_number:
            raise PaperSaveError("references.json entries need unique integer numbers")
        by_number[ref["number"]] = ref
    issues["unknown_numbers"] = sorted(set(by_number) - {i["number"] for i in items})
    notes = index_notes(vault); seen_targets = {}; report = []
    output = [head]
    for item in items:
        number, entry = item["number"], item["lines"][0].rstrip("\n")
        # Wrapped continuation lines become one line so links and block IDs stay intact.
        if len(item["lines"]) > 1:
            entry = " ".join(line.strip() for line in item["lines"])
        if item["numbered"] and number in seen_numbers:
            # A second entry with the same number is an extraction error; leave it for review.
            issues["duplicate_numbers"].append(number)
            output.append(entry + "\n" + "".join(item["trailing"]))
            continue
        seen_numbers.add(number)
        block = f" ^ref-{number}" if item["numbered"] else ""
        ref = by_number.get(number)
        result = {"number": number}
        if ref and ref.get("title") and (ref.get("doi") or ref.get("target")):
            title = ref["title"]
            if not isinstance(title, str) or "\n" in title:
                raise PaperSaveError(f"Reference {number}: title must be one line")
            # A registered title missing from the entry means the DOI is wrong (typos happen).
            match = find_title(entry, title)
            if not match:
                result |= {"unlinked": True, "reason": "entry looks cut off by extraction"
                           if re.search(r"[,;:]\s*$", entry) else f"DOI title not in entry: {title}"}
            else:
                # Name unsaved notes after the printed title, as save_paper.py would when saving it.
                try:
                    target, exists = resolve_reference(ref | {"title": match[0]}, notes)
                except PaperSaveError as exc:
                    # Leave the entry unlinked rather than stopping the whole note.
                    result |= {"unlinked": True, "reason": str(exc)}
                    report.append(result)
                    output.append(entry + block + "\n" + "".join(item["trailing"]))
                    continue
                identity = ("doi", doi_key(ref["doi"])) if ref.get("doi") else ("target", target)
                if target in seen_targets and seen_targets[target][0] != identity:
                    result |= {"unlinked": True,
                               "reason": f"same note name as reference {seen_targets[target][1]}: {target}"}
                else:
                    seen_targets.setdefault(target, (identity, number))
                    entry = link_title(entry, match, target)
                    result |= {"target": target, "exists": exists}
        else:
            result["unlinked"] = True
        report.append(result)
        output.append(entry + block + "\n" + "".join(item["trailing"]))
    numbered = {i["number"] for i in items if i["numbered"]}
    return "".join(output), report, numbered, issues


def build_note(text: str, refs: list[dict], vault: Path) -> tuple[str, dict]:
    if not isinstance(refs, list): raise PaperSaveError("Reference manifest must be an array")
    if re.search(r"\^ref-\d+\b", SHIELDS.sub("", text)):
        raise PaperSaveError("Draft already contains reference block IDs")
    span = find_reference_section(text)
    unmatched = []
    if span is None:
        if refs: raise PaperSaveError("Draft has no References section")
        return text, {"references": [], "cited_numbers": [], "section_found": False}
    start, end = span
    section, report, numbers, issues = link_references(text[start:end], refs, vault)
    # Only body text outside the References section carries in-text citations.
    before, cited = link_citations(text[:start], numbers, unmatched)
    after, cited_after = link_citations(text[end:], numbers, unmatched)
    gaps = sorted(set(range(1, max(numbers) + 1)) - numbers) if numbers else []
    return before + section + after, {"references": report, "cited_numbers": sorted(cited | cited_after),
                                      "missing_numbers": gaps, "unmatched_brackets": unmatched[:20], **issues}
