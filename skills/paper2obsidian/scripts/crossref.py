"""Publisher metadata from Crossref/doi.org: the paper record, BibTeX, reference DOIs and their titles."""
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from paper_common import doi_key, sanitize_title, title_key

DOI_IN_TEXT = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+", re.I)
ARXIV_ID = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})", re.I)
# Crossref routes requests that name a contact to its more generous "polite" pool.
HEADERS = {"User-Agent": "paper2obsidian (personal Obsidian archive"
           + (f"; mailto:{os.environ['CROSSREF_MAILTO']})" if os.environ.get("CROSSREF_MAILTO") else ")")}


def _open(url: str, headers: dict, timeout: float):
    for attempt in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 2:
                raise
            time.sleep(float(exc.headers.get("Retry-After") or 2 * (attempt + 1)))


def first_pages(pdf_path) -> list[str]:
    import pypdfium2 as pdfium
    document = pdfium.PdfDocument(str(pdf_path))
    return [document[i].get_textpage().get_text_range() for i in range(min(2, len(document)))]


def candidate_dois(texts: list[str]) -> list[str]:
    """The paper's own DOI is printed on page 1 or 2 (footer, citation box); cited DOIs come later."""
    found = []
    for text in texts:
        compact = re.sub(r"(?<=10\.)\s+|(?<=/)\s+", "", text)
        found += [m.rstrip(".,;)") for m in DOI_IN_TEXT.findall(compact)]
        # A DOI wrapped at the line end ("10.1145/2702123.2702\n140") is tried joined, too.
        found += [m.rstrip(".,;)") for m in DOI_IN_TEXT.findall(re.sub(r"(?<=[\d.])\s*\n\s*(?=\d)", "", compact))]
        found += [f"10.48550/arXiv.{m}" for m in ARXIV_ID.findall(text)]
    return list(dict.fromkeys(found))


CONTAINER_TYPES = {"proceedings", "proceedings-series", "journal", "journal-issue", "journal-volume", "book-series"}


def full_title(message: dict) -> str:
    """Crossref stores "Title: Subtitle" as separate fields for some publishers."""
    title = (message.get("title") or [""])[0].strip()
    subtitle = (message.get("subtitle") or [""])[0].strip()
    return f"{title}: {subtitle}" if subtitle and title_key(subtitle) not in title_key(title) else title


def search_title(title: str, timeout: float = 15) -> dict | None:
    query = urllib.parse.urlencode({"query.bibliographic": title, "rows": 3})
    with _open(f"https://api.crossref.org/works?{query}", HEADERS, timeout) as response:
        items = json.load(response)["message"]["items"]
    return next((i for i in items if title_key(full_title(i)) == title_key(title)), None)


def find_work(pdf_path, headings: list[str], doi: str | None) -> tuple[dict | None, str]:
    """Return the Crossref record whose title is printed on the first pages, and how it was found."""
    if doi:
        return fetch_work(doi), "given"
    texts = first_pages(pdf_path)
    printed = title_key(" ".join(texts))

    def matches(message):
        # Page 1 also prints the proceedings' DOI and title ("ACM Reference Format"); that is not the paper.
        key = title_key(full_title(message))
        return message.get("type") not in CONTAINER_TYPES and bool(key) and key in printed

    found = []
    for candidate in candidate_dois(texts)[:4]:
        try:
            message = fetch_work(candidate)
        except OSError:
            continue
        if matches(message):
            found.append(message)
    if found:
        # Prefer the record whose title is the paper's heading.
        title = title_key(" ".join(headings[:2]))
        return next((m for m in found if title_key(full_title(m)) in title), found[0]), "doi on first pages"
    import pypdfium2 as pdfium
    titles = [pdfium.PdfDocument(str(pdf_path)).get_metadata_dict().get("Title", "").strip()] + headings[:2]
    for title in titles:
        if len(title) >= 12 and (message := search_title(title)) and matches(message):
            return message, "title search"
    return None, "not found"


def fetch_work(doi: str, timeout: float = 15) -> dict:
    try:
        with _open(f"https://api.crossref.org/works/{doi}", HEADERS, timeout) as response:
            return json.load(response)["message"]
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    # Not a Crossref DOI (e.g. DataCite for Eurographics, arXiv): doi.org serves CSL JSON for any registrar.
    with _open(f"https://doi.org/{doi}", HEADERS | {"Accept": "application/vnd.citationstyles.csl+json"}, timeout) as response:
        csl = json.load(response)
    title = csl.get("title")
    return {"DOI": csl.get("DOI", doi), "title": title if isinstance(title, list) else [title or ""],
            "author": csl.get("author", []), "issued": csl.get("issued", {}),
            "container-title": [csl["container-title"]] if isinstance(csl.get("container-title"), str)
            else csl.get("container-title") or []}


def fetch_bibtex(doi: str, timeout: float = 15) -> str:
    with _open(f"https://doi.org/{doi}", HEADERS | {"Accept": "application/x-bibtex"}, timeout) as response:
        return response.read().decode("utf-8").strip()


def citekey(family: str, year: int | None, title: str) -> str:
    def ascii_key(text):
        return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower())
    words = [w for w in re.findall(r"[\w'’-]+", title) if w.lower() not in {"a", "an", "the"}]
    return ascii_key(family) + (str(year) if year else "") + (ascii_key(words[0]) if words else "")


def metadata(message: dict, bibtex: str | None) -> dict:
    title = full_title(message)
    authors = [" ".join(p for p in (a.get("given"), a.get("family")) if p) or a.get("name", "")
               for a in message.get("author", [])]
    issued = (message.get("issued") or message.get("published") or {}).get("date-parts", [[None]])[0][0]
    family = (message.get("author") or [{}])[0].get("family") or (authors[0].split()[-1] if authors else "")
    key = citekey(family, issued, title)
    if bibtex:
        bibtex = re.sub(r"^(@\w+\{)[^,]*,", lambda m: m[1] + key + ",", bibtex, count=1)
    return {"title": title, "authors": authors, "year": issued, "doi": message["DOI"],
            "source": (message.get("container-title") or [None])[0], "citekey": key, "bibtex": bibtex}


def frontmatter(meta: dict) -> str:
    lines = ["---", f"title: {json.dumps(meta['title'], ensure_ascii=False)}"]
    if meta["year"]:
        lines.append(f"year: {meta['year']}")
    lines.append(f"doi: {json.dumps('https://doi.org/' + meta['doi'])}")
    if meta["authors"]:
        lines.append("authors:")
        lines += [f"  - {json.dumps(a, ensure_ascii=False)}" for a in meta["authors"]]
    if meta["source"]:
        lines.append(f"source: {json.dumps(meta['source'], ensure_ascii=False)}")
    lines += [f"citekey: {meta['citekey']}", "---", ""]
    return "\n".join(lines) + "\n"


def tail_sections(meta: dict) -> str:
    name = sanitize_title(meta["title"])
    text = f"\n\n## PDF\n\n[Original PDF](<assets/{name}/{name}.pdf>)\n"
    if meta["bibtex"]:
        text += f"\n## BibTeX\n\n```bibtex\n{meta['bibtex']}\n```\n"
    return text


def _words(text: str) -> set[str]:
    return {w.casefold() for w in re.findall(r"[^\W\d_]{4,}", text)}


def _agrees(raw: str, item: dict) -> bool | None:
    """Does Crossref's entry describe the same work as the PDF's entry with the same position?"""
    if item.get("DOI") and doi_key(item["DOI"]) in re.sub(r"\s+", "", raw).casefold():
        return True
    record = " ".join(str(item.get(k, "")) for k in ("unstructured", "article-title", "author", "year"))
    words = _words(record)
    if not words:
        return None  # Publisher deposited only a DOI; the PDF text cannot confirm or refute it.
    return len(words & _words(raw)) >= 0.6 * len(words)


def reference_dois(pdf_items: list[dict], message: dict) -> tuple[dict[int, str], dict]:
    """Map the PDF's reference numbers to Crossref DOIs when both lists line up."""
    items = message.get("reference") or []
    if not items:
        return {}, {"crossref": "no reference list"}
    pdf_sorted = sorted(pdf_items, key=lambda r: r["number"])
    if len(pdf_sorted) != len(items):
        return {}, {"crossref": f"count mismatch: pdf {len(pdf_sorted)}, crossref {len(items)}"}
    agree = [_agrees(p["raw"], item) for p, item in zip(pdf_sorted, items)]
    checked = [a for a in agree if a is not None]
    if not checked or sum(checked) < 0.8 * len(checked):
        return {}, {"crossref": f"order mismatch: {sum(checked)}/{len(checked)} agree"}
    dois = {p["number"]: item["DOI"] for p, item, a in zip(pdf_sorted, items, agree) if item.get("DOI") and a is not False}
    return dois, {"crossref": "aligned", "disagreeing_numbers": [p["number"] for p, a in zip(pdf_sorted, agree) if a is False]}


def titles_for_dois(dois: list[str], timeout: float = 20) -> dict[str, str]:
    """Registered titles keyed by doi_key: Crossref in batches, then doi.org for other registrars (arXiv/DataCite)."""
    wanted = list(dict.fromkeys(dois)); titles = {}
    for start in range(0, len(wanted), 40):
        chunk = wanted[start:start + 40]
        query = urllib.parse.urlencode({"filter": ",".join(f"doi:{d}" for d in chunk), "rows": len(chunk),
                                        "select": "DOI,title,subtitle"})
        try:
            with _open(f"https://api.crossref.org/works?{query}", HEADERS, timeout) as response:
                for item in json.load(response)["message"]["items"]:
                    if title := full_title(item):
                        titles[doi_key(item["DOI"])] = title
        except (OSError, ValueError, KeyError):
            pass
    def via_doi_org(doi):
        try:
            with _open(f"https://doi.org/{doi}", HEADERS | {"Accept": "application/vnd.citationstyles.csl+json"}, timeout) as response:
                title = json.load(response).get("title")
        except (OSError, ValueError):
            return doi, None
        if isinstance(title, list): title = title[0] if title else None
        return doi, re.sub(r"\s+", " ", title).strip() if title else None

    rest = [d for d in wanted if doi_key(d) not in titles]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for doi, title in pool.map(via_doi_org, rest):
            if title: titles[doi_key(doi)] = title
    return titles
