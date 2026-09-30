#!/usr/bin/env python3
"""Link numeric citations to reference blocks and paper references to Vault notes."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import quote

from paper_common import PaperSaveError, doi_key, sanitize_title, title_key
from save_paper import FENCE_RE, get_vault_root


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


def link_citations(text: str, numbers: set[int]) -> tuple[str, set[int]]:
    cited = set()

    def plain(fragment):
        def replace(match):
            content = match[1]
            ns = {int(x) for x in re.findall(r"\d+", content)}
            for start, end in re.findall(r"(\d+)\s*[-–]\s*(\d+)", content):
                start, end = int(start), int(end)
                if end < start or end - start > 1000: raise PaperSaveError("Invalid citation range")
                ns.update(range(start, end + 1))
            if ns - numbers: raise PaperSaveError(f"Citation has no reference: {sorted(ns - numbers)}")
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


def wiki_label(title: str) -> str:
    return (title.replace("&", "&amp;").replace("|", "&#124;")
            .replace("[", "&#91;").replace("]", "&#93;"))


def render_references(refs: list[dict], vault: Path) -> tuple[str, list[dict]]:
    notes = index_notes(vault); seen_numbers = set(); seen_targets = {}; rows = []; report = []
    for ref in refs:
        if not isinstance(ref, dict): raise PaperSaveError("Each reference must be an object")
        number = ref.get("number")
        if type(number) is not int or number < 1 or number in seen_numbers:
            raise PaperSaveError("Reference numbers must be unique positive integers")
        seen_numbers.add(number)
        title = ref.get("title")
        if not isinstance(title, str) or not title.strip() or "\n" in title or "\r" in title:
            raise PaperSaveError(f"Missing/split reference title: {number}")
        kind = ref.get("kind")
        if kind == "paper":
            for key in ("doi", "first_author", "target"):
                if key in ref and not isinstance(ref[key], str):
                    raise PaperSaveError(f"Reference {number}: {key} must be a string")
            target, exists = resolve_reference(ref, notes)
            identity = ("doi", doi_key(ref["doi"])) if ref.get("doi") else ("title", title_key(title), str(ref.get("year", "")))
            if target in seen_targets and seen_targets[target] != identity:
                raise PaperSaveError(f"Different references resolve to the same filename: {target}")
            seen_targets[target] = identity
            label = f"[[{target}|{wiki_label(title)}]]"
            report.append({"number": number, "target": target, "exists": exists})
        elif kind in {"web", "video", "artwork", "other"}:
            url = ref.get("url", "")
            if url:
                if not isinstance(url, str) or not re.match(r"^https?://", url) or re.search(r"[\s<>]", url):
                    raise PaperSaveError(f"Non-paper URL must be original HTTP(S): {number}")
                escaped = title.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
                encoded = quote(url, safe=":/?#%=&+@;,~!$*'")
                label = f"[{escaped}](<{encoded}>)"
                report.append({"number": number, "url": url})
            else:
                label = ref.get("citation")
                if not isinstance(label, str) or not label.strip() or re.search(r"[\r\n]|\^ref-\d+", label):
                    raise PaperSaveError(f"Non-paper without URL needs original citation text: {number}")
                report.append({"number": number, "unlinked": True})
        else: raise PaperSaveError(f"Classify reference {number}: paper/web/video/artwork/other")
        rows.append((number, f"{number}. {label} ^ref-{number}"))
    return "## References\n\n" + "\n".join(row for _, row in sorted(rows)) + "\n", report


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


def build_note(text: str, refs: list[dict], vault: Path) -> tuple[str, dict]:
    if not isinstance(refs, list): raise PaperSaveError("Reference manifest must be an array")
    if any(title in {"References", "Bibliography"} for _, _, title in body_headings(text)):
        raise PaperSaveError("Draft must omit References; provide them in the JSON manifest")
    if re.search(r"\^ref-\d+\b", SHIELDS.sub("", text)):
        raise PaperSaveError("Draft already contains reference block IDs")
    references, report = render_references(refs, vault)
    linked, cited = link_citations(text, {r["number"] for r in refs})
    # Keep the PDF/BibTeX tail, if present, after References.
    pos = next((pos for pos, level, title in body_headings(linked)
                if level == 2 and title in {"PDF", "BibTeX"}), len(linked))
    final = linked[:pos].rstrip() + "\n\n" + references + "\n" + linked[pos:]
    return final, {"references": report, "cited_numbers": sorted(cited)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--references", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--vault-root", type=Path, help="Explicit test Vault; otherwise PAPER_SAVE_VAULT_ROOT")
    args = parser.parse_args()
    try:
        vault = args.vault_root.resolve() if args.vault_root else get_vault_root()
        if not vault.is_dir(): raise PaperSaveError("Vault root does not exist")
        text = args.markdown.read_text(encoding="utf-8")
        refs = json.loads(args.references.read_text(encoding="utf-8"))
        result, report = build_note(text, refs, vault)
        with args.output.open("x", encoding="utf-8") as file: file.write(result)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (OSError, ValueError, PaperSaveError) as exc:
        parser.exit(1, f"paper2obsidian error: {exc}\n")


if __name__ == "__main__":
    main()
