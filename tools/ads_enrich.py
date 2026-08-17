#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["bibtexparser~=1.4"]
# ///
"""Enrich a Better BibTeX export with canonical metadata from NASA ADS.

    references.zotero.bib  [BBT auto-export target, never edited]
        -> references.bib  [GENERATED] → \\bibliography{references}

For each entry, resolve an ADS bibcode, fetch ADS's own BibTeX record, and take
it wholesale -- but keep the Zotero/BBT key. ADS's bibcode keys would disagree
with every \\citep{} in the manuscript and break all citations at once.

Resolution order:
    existing bibcode (`bibcode`/`adsurl`) -> DOI -> arXiv eprint
    -> arXiv ID scraped from `url`/`journal`

ADS emits journal macros from a wider set than AASTeX defines, so every macro 
is checked against the vendored class and unknown ones fall back to the full
journal name.

Usage:
    export ADS_DEV_KEY=...   # https://ui.adsabs.harvard.edu/user/settings/token
    uv run tools/ads_enrich.py --in references.zotero.bib --out references.bib
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter

ADS_API = "https://api.adsabs.harvard.edu/v1"
EXPORT_CHUNK = 100
TIMEOUT = 30

# Noise that makes the .bib unreadable and undiffable.
STRIP_FIELDS = {"abstract", "keywords", "file", "note", "adsnote", "month"}

# Printed first, keeps reruns byte-identical, so diffs show real 
# metadata changes only.
DISPLAY_ORDER = (
    "author", "title", "journal", "booktitle", "publisher", "year",
    "volume", "number", "eid", "pages", "doi", "archiveprefix",
    "eprint", "primaryclass", "adsurl", "bibcode",
)


# --------------------------------------------------------------------------
# Journal macros
# --------------------------------------------------------------------------

def class_journal_macros(cls_path: Path) -> set[str]:
    """Journal macros the AASTeX class defines."""
    if not cls_path.exists():
        print(f"warn: {cls_path} not found; skipping journal-macro validation",
              file=sys.stderr)
        return set()
    text = cls_path.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"\\newcommand\\([a-zA-Z]+)\{\\ref@jnl", text))


def macro_name(value: str) -> str | None:
    """Return the macro name if `value` is exactly one LaTeX macro, else None."""
    m = re.fullmatch(r"\s*\{?\s*\\([a-zA-Z]+)\s*\}?\s*", value or "")
    return m.group(1) if m else None


# --------------------------------------------------------------------------
# Identifier extraction
# --------------------------------------------------------------------------

ARXIV_RE = re.compile(r"(?:arxiv[:/ ]\s*)?(\d{4}\.\d{4,5}(?:v\d+)?)", re.I)
OLD_ARXIV_RE = re.compile(r"(?:arxiv[:/ ]\s*)?([a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)", re.I)
BIBCODE_RE = re.compile(r"\b(\d{4}[A-Za-z0-9.&]{5}[A-Za-z0-9.]{4}[ELPQ-Z0-9.][0-9.]{4}[A-Z])\b")


def known_bibcode(entry: dict) -> str | None:
    """Bibcode already present in the record, if any."""
    for field in ("bibcode", "adsurl", "url"):
        value = entry.get(field, "")
        if not value:
            continue
        if field == "bibcode":
            return value.strip()
        unquoted = urllib.parse.unquote(value)
        m = re.search(r"/abs/([^/\s}]+)", unquoted)
        if m:
            candidate = m.group(1).strip()
            if BIBCODE_RE.fullmatch(candidate):
                return candidate
    return None


def arxiv_id(entry: dict) -> str | None:
    """arXiv identifier from `eprint`, or scraped from `url`/`journal`."""
    eprint = (entry.get("eprint") or "").strip()
    if eprint:
        for rx in (ARXIV_RE, OLD_ARXIV_RE):
            m = rx.fullmatch(eprint) or rx.search(eprint)
            if m:
                return m.group(1)
    for field in ("url", "journal", "journaltitle", "howpublished"):
        value = entry.get(field, "")
        if "arxiv" not in value.lower():
            continue
        for rx in (ARXIV_RE, OLD_ARXIV_RE):
            m = rx.search(value)
            if m:
                return m.group(1)
    return None


def resolution_queries(entry: dict) -> list[tuple[str, str]]:
    """(cache-key, ADS query) pairs to try, in precedence order."""
    queries: list[tuple[str, str]] = []
    doi = (entry.get("doi") or "").strip().rstrip(".")
    if doi:
        queries.append((f"doi:{doi.lower()}", f'doi:"{doi}"'))
    axv = arxiv_id(entry)
    if axv:
        queries.append((f"arxiv:{axv.lower()}", f'identifier:"arXiv:{axv}"'))
    return queries


# --------------------------------------------------------------------------
# ADS client
# --------------------------------------------------------------------------

class AdsClient:
    def __init__(self, token: str | None, offline: bool):
        self.token = token
        self.offline = offline
        self.calls = 0
        self.rate_remaining: str | None = None

    def _request(self, url: str, data: bytes | None = None) -> dict:
        if self.offline:
            raise RuntimeError("offline")
        if not self.token:
            raise RuntimeError("ADS_DEV_KEY is not set")
        headers = {"Authorization": f"Bearer {self.token}"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers)
        self.calls += 1
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            self.rate_remaining = resp.headers.get("X-RateLimit-Remaining",
                                                   self.rate_remaining)
            return json.loads(resp.read().decode("utf-8"))

    def resolve(self, query: str) -> str | None:
        params = urllib.parse.urlencode({"q": query, "fl": "bibcode", "rows": 1})
        payload = self._request(f"{ADS_API}/search/query?{params}")
        docs = payload.get("response", {}).get("docs", [])
        return docs[0]["bibcode"] if docs else None

    def export(self, bibcodes: list[str]) -> dict[str, str]:
        """bibcode → its ADS BibTeX record, for a batch of bibcodes."""
        out: dict[str, str] = {}
        for i in range(0, len(bibcodes), EXPORT_CHUNK):
            chunk = bibcodes[i:i + EXPORT_CHUNK]
            body = json.dumps({"bibcode": chunk}).encode("utf-8")
            payload = self._request(f"{ADS_API}/export/bibtex", data=body)
            for record in split_records(payload.get("export", "")):
                key = record.split("{", 1)[1].split(",", 1)[0].strip()
                out[key] = record
        return out


def split_records(blob: str) -> list[str]:
    """Split a concatenated BibTeX blob into individual entry strings."""
    records, depth, current = [], 0, []
    for line in blob.splitlines(keepends=True):
        if not current and not line.lstrip().startswith("@"):
            continue
        current.append(line)
        depth += line.count("{") - line.count("}")
        if current and depth <= 0:
            records.append("".join(current).strip())
            current, depth = [], 0
    if current:
        records.append("".join(current).strip())
    return records


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------

def load_cache(path: Path) -> dict:
    if path.exists():
        try:
            cache = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"warn: {path} is corrupt; starting a fresh cache",
                  file=sys.stderr)
            cache = {}
    else:
        cache = {}
    cache.setdefault("identifiers", {})   # "doi:10.x/y" -> bibcode or null
    cache.setdefault("bibtex", {})        # bibcode -> ADS BibTeX record
    cache.setdefault("source_sha256", "") # input digest at last successful write
    return cache


def save_cache(path: Path, cache: dict) -> None:
    atomic_write(path, json.dumps(cache, indent=1, sort_keys=True) + "\n")


def atomic_write(path: Path, text: str) -> None:
    """Write via temp file + rename, so a crash never truncates the target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# --------------------------------------------------------------------------
# Merge
# --------------------------------------------------------------------------

def parse_bib(text: str):
    parser = BibTexParser(common_strings=True)
    parser.homogenize_fields = False
    parser.ignore_nonstandard_types = False
    return bibtexparser.loads(text, parser)


def merge(zot: dict, ads: dict, macros: set[str], warnings: list[str]) -> dict:
    """ADS record wholesale, Zotero key. Returns the merged entry."""
    merged = dict(ads)
    merged["ID"] = zot["ID"]                # the key the manuscript cites by
    merged["ENTRYTYPE"] = ads.get("ENTRYTYPE", zot.get("ENTRYTYPE", "article"))

    for field in STRIP_FIELDS:
        merged.pop(field, None)

    # Redundant aliases: harmless under natbib, wrong under biblatex.
    if merged.get("journal"):
        merged.pop("journaltitle", None)
    if merged.get("year"):
        merged.pop("date", None)

    # For unidentified macros, falls back to a full journal name.
    journal = merged.get("journal", "")
    name = macro_name(journal)
    if name and macros and name not in macros:
        fallback = (zot.get("journal") or zot.get("journaltitle") or "").strip()
        if fallback and not macro_name(fallback):
            merged["journal"] = fallback
            warnings.append(
                f"{zot['ID']}: ADS returned undefined macro \\{name}; "
                f"used the Zotero journal name instead")
        else:
            merged.pop("journal", None)
            warnings.append(
                f"{zot['ID']}: ADS returned undefined macro \\{name} and Zotero "
                f"has no journal name; DROPPED the journal field -- fix by hand")
    return merged


def write_bib(db, path: Path) -> None:
    # The BBT export's %% header round-trips as @comment{...} and would
    # otherwise accumulate in the generated file on every run.
    db.comments = []
    db.preambles = []
    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = ("ID",)
    writer.display_order = DISPLAY_ORDER
    writer.add_trailing_comma = False
    header = (
        "%% GENERATED FILE -- do not edit.\n"
        "%% Source: references.zotero.bib (Better BibTeX auto-export)\n"
        "%% Regenerate: uv run tools/ads_enrich.py --in references.zotero.bib "
        "--out references.bib\n\n"
    )
    atomic_write(path, header + bibtexparser.dumps(db, writer))


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", default="references.zotero.bib", type=Path)
    ap.add_argument("--out", dest="dst", default="references.bib", type=Path)
    ap.add_argument("--cache", default=".ads-cache.json", type=Path)
    ap.add_argument("--cls", default="aastex702.cls", type=Path,
                    help="class file to validate journal macros against")
    ap.add_argument("--offline", action="store_true",
                    help="cache only: no token, no network, byte-identical reruns")
    ap.add_argument("--refresh", action="store_true",
                    help="ignore cached identifier lookups and re-query ADS")
    ap.add_argument("--if-changed", action="store_true",
                    help="exit immediately if the input is byte-identical to "
                         "the last successful run (for the .latexmkrc hook)")
    args = ap.parse_args()

    if not args.src.exists():
        print(f"error: {args.src} not found", file=sys.stderr)
        return 2

    source_bytes = args.src.read_bytes()
    source_digest = hashlib.sha256(source_bytes).hexdigest()

    # Better BibTeX rewrites its export target on ANY library change, so mtime
    # alone fires constantly with byte-identical content. Compare the digest.
    if args.if_changed and args.dst.exists():
        if load_cache(args.cache).get("source_sha256") == source_digest:
            # Satisfy make's staleness check so this does not re-fire on every
            # subsequent invocation.
            os.utime(args.dst, None)
            return 0

    token = os.environ.get("ADS_DEV_KEY")
    if not args.offline and not token:
        # Degrade rather than fail: for anyone not using ADS, the pass-through
        # copy is the correct output, not an error.
        print("note: ADS_DEV_KEY is not set; running --offline (cache only).\n"
              "      Entries pass through unenriched. To enrich from ADS:\n"
              "      export ADS_DEV_KEY=...  "
              "# https://ui.adsabs.harvard.edu/user/settings/token",
              file=sys.stderr)
        args.offline = True

    db = parse_bib(source_bytes.decode("utf-8"))
    macros = class_journal_macros(args.cls)
    cache = load_cache(args.cache)
    client = AdsClient(token, args.offline)

    # ---- pass 1: resolve every entry to a bibcode -------------------------
    resolved: dict[str, str] = {}     # entry ID → bibcode
    unresolved: list[tuple[str, str]] = []
    for entry in db.entries:
        eid = entry["ID"]
        bibcode = known_bibcode(entry)
        if bibcode:
            resolved[eid] = bibcode
            continue
        queries = resolution_queries(entry)
        if not queries:
            unresolved.append((eid, "no doi, no arXiv id, no bibcode"))
            continue
        for cache_key, query in queries:
            if not args.refresh and cache_key in cache["identifiers"]:
                hit = cache["identifiers"][cache_key]
            else:
                try:
                    hit = client.resolve(query)
                    cache["identifiers"][cache_key] = hit
                except RuntimeError:
                    hit = None                      # offline; cache miss
                except (urllib.error.URLError, urllib.error.HTTPError) as exc:
                    print(f"warn: ADS lookup failed for {eid} ({exc})",
                          file=sys.stderr)
                    hit = None
            if hit:
                resolved[eid] = hit
                break
        else:
            why = "not in cache" if args.offline else "no ADS match"
            unresolved.append((eid, f"{why} for {', '.join(q for q, _ in queries)}"))

    # ---- pass 2: fetch BibTeX for the bibcodes we don't have yet ----------
    needed = sorted({b for b in resolved.values() if b not in cache["bibtex"]})
    if needed and not args.offline:
        try:
            cache["bibtex"].update(client.export(needed))
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as exc:
            print(f"warn: ADS export failed ({exc}); falling back to cache",
                  file=sys.stderr)
    elif needed and args.offline:
        print(f"warn: {len(needed)} bibcode(s) not in cache; --offline leaves "
              f"them unenriched", file=sys.stderr)

    # ---- pass 3: merge ----------------------------------------------------
    warnings: list[str] = []
    seen_bibcodes: dict[str, str] = {}
    merged_count = 0
    for i, entry in enumerate(db.entries):
        eid = entry["ID"]
        bibcode = resolved.get(eid)
        record = cache["bibtex"].get(bibcode) if bibcode else None
        if not record:
            if bibcode:
                why = ("not cached yet -- set ADS_DEV_KEY and rerun to enrich"
                       if args.offline else "no BibTeX record returned by ADS")
                unresolved.append((eid, f"{bibcode}: {why}"))
            continue
        if bibcode in seen_bibcodes:
            warnings.append(
                f"{eid}: same bibcode {bibcode} as {seen_bibcodes[bibcode]} "
                f"-- duplicate entry in the Zotero collection?")
        seen_bibcodes[bibcode] = eid
        parsed = parse_bib(record)
        if not parsed.entries:
            warnings.append(f"{eid}: could not parse ADS record for {bibcode}")
            continue
        db.entries[i] = merge(entry, parsed.entries[0], macros, warnings)
        merged_count += 1

    # Pass-through entries are the one remaining way an undefined macro can
    # reach references.bib. Warn rather than rewrite, so "untouched" holds.
    if macros:
        merged_ids = {e["ID"] for e in db.entries} - {eid for eid, _ in unresolved}
        for entry in db.entries:
            if entry["ID"] in merged_ids:
                continue
            name = macro_name(entry.get("journal", ""))
            if name and name not in macros:
                warnings.append(
                    f"{entry['ID']}: journal macro \\{name} is NOT defined by "
                    f"{args.cls} and will hard-error the compile. Replace it "
                    f"with the full journal name in Zotero.")

    write_bib(db, args.dst)
    # Only after a successful write: a crash must not convince the next
    # --if-changed run that this input was already processed.
    cache["source_sha256"] = source_digest
    save_cache(args.cache, cache)

    # ---- report -----------------------------------------------------------
    total = len(db.entries)
    print(f"{args.dst}: {merged_count}/{total} entries enriched from ADS "
          f"({client.calls} API call{'' if client.calls == 1 else 's'})",
          file=sys.stderr)
    for warning in warnings:
        print(f"  warn: {warning}", file=sys.stderr)
    if unresolved:
        print(f"  passed through unenriched ({len(unresolved)}) -- confirm each "
              f"is intentional:", file=sys.stderr)
        for eid, why in unresolved:
            print(f"    {eid}: {why}", file=sys.stderr)
    if client.rate_remaining is not None:
        print(f"  ADS rate limit remaining: {client.rate_remaining}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
