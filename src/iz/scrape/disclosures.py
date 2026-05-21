"""
Public sustainability-disclosure scraper for TR CBAM-scope facilities.

v0 scope: discover + download PDF sustainability reports + extract any
emissions / production tables we can parse with pdfplumber. PDF tables
are unstructured by design — accuracy is best-effort, gaps go into the
confidence column.

Output shape (long format, easy to join + filter):
    id              str   — slug from tr_facilities.csv (e.g. "akcansa-buyukcekmece")
    company         str   — company name (denormalized for sanity)
    year            int   — reporting year
    metric          str   — co2_scope1_t, cement_produced_t, clinker_produced_t,
                            specific_co2_t_per_t, electricity_mwh, ...
    value           float — numeric value
    unit            str   — tCO₂, t, MWh, %, ...
    source_doc      str   — local PDF filename
    source_page     int   — page number where this row was extracted
    confidence      str   — 'high' (clean ESG-table extraction), 'medium'
                            (PDF table with some noise), 'low' (heuristic text-grep)
    notes           str   — free-form
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.6 Safari/605.1.15"
)
BROWSER_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}
HTTP_TIMEOUT = 30
PDF_DIR_DEFAULT = Path.home() / "iz" / "data" / "disclosures"


# ─────────────────────────────────────────────────────────────────────────────
# PDF discovery
# ─────────────────────────────────────────────────────────────────────────────

PDF_KEYWORDS = re.compile(
    r"(sustainab|sürdürül|cdp|esg|carbon|emiss|climate|iklim|gri|integrated|annual.{0,5}report|"
    r"faaliyet|enviro|ydp|environment|csr)",
    re.IGNORECASE,
)
PDF_BLOCKLIST = re.compile(r"(brochure|catalog|product.{0,10}data)", re.IGNORECASE)


@dataclass
class PdfCandidate:
    url: str
    anchor_text: str
    year: int | None  # extracted from URL or text if obvious


def _maybe_year(s: str) -> int | None:
    """Pull a 4-digit year from text/URL if one is in range."""
    for m in re.finditer(r"(20[12][0-9])", s):
        y = int(m.group(1))
        if 2015 <= y <= 2026:
            return y
    return None


def find_pdf_links(html_url: str, *, client: httpx.Client) -> list[PdfCandidate]:
    """Fetch a sustainability landing page, return PDF candidates that look
    like emissions / sustainability / ESG / annual reports."""
    log.info("GET %s", html_url)
    try:
        r = client.get(html_url, headers=BROWSER_HEADERS, timeout=HTTP_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        log.warning("  fetch failed: %s", e)
        return []

    soup = BeautifulSoup(r.text, "lxml")
    out: list[PdfCandidate] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "#")):
            continue
        abs_url = urljoin(str(r.url), href)
        if not abs_url.lower().endswith(".pdf"):
            # also accept query-string PDFs occasionally hosted by CMS
            if "pdf" not in abs_url.lower() and not href.lower().endswith(".pdf"):
                continue
        if abs_url in seen:
            continue
        seen.add(abs_url)

        text = (a.get_text() or "").strip()
        # filter by relevance
        haystack = f"{text} {href}"
        if not PDF_KEYWORDS.search(haystack):
            continue
        if PDF_BLOCKLIST.search(haystack):
            continue

        year = _maybe_year(haystack) or _maybe_year(abs_url)
        out.append(PdfCandidate(url=abs_url, anchor_text=text[:120], year=year))

    log.info("  found %d candidate PDFs", len(out))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Download
# ─────────────────────────────────────────────────────────────────────────────


def _local_name(facility_id: str, url: str, year: int | None) -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    y = year or "noyr"
    base = Path(urlparse(url).path).stem[:60]
    safe_base = re.sub(r"[^A-Za-z0-9_-]+", "_", base)
    return f"{facility_id}__{y}__{safe_base}__{h}.pdf"


def download_pdf(
    candidate: PdfCandidate,
    facility_id: str,
    *,
    client: httpx.Client,
    dst_dir: Path = PDF_DIR_DEFAULT,
    max_bytes: int = 100 * 1024 * 1024,  # 100 MB ceiling per file
) -> Path | None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / _local_name(facility_id, candidate.url, candidate.year)
    if dst.exists() and dst.stat().st_size > 0:
        log.info("  cached: %s (%.1f MB)", dst.name, dst.stat().st_size / 1e6)
        return dst
    try:
        with client.stream(
            "GET",
            candidate.url,
            headers=BROWSER_HEADERS,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
        ) as r:
            r.raise_for_status()
            tmp = dst.with_suffix(dst.suffix + ".part")
            n = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)
                    n += len(chunk)
                    if n > max_bytes:
                        raise RuntimeError(f"exceeded {max_bytes} bytes")
            tmp.rename(dst)
            log.info("  downloaded %s (%.1f MB)", dst.name, n / 1e6)
            return dst
    except Exception as e:
        log.warning("  download failed: %s", e)
        # cleanup any partial
        for p in dst.parent.glob(dst.name + ".part"):
            p.unlink(missing_ok=True)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Extraction
# ─────────────────────────────────────────────────────────────────────────────

# Loose regex hits for plausible emissions / production rows.
# We extract anything that looks like a numeric value with a year + unit.
EMISSIONS_PATTERNS = [
    # tCO₂ direct emissions
    (re.compile(r"(scope\s*1|direct.{0,20}(emission|co2|ghg)|do[ğg]rudan\s+emisyon)", re.I), "co2_scope1_t"),
    (re.compile(r"(scope\s*2|indirect.{0,20}(emission|co2|ghg)|dolayl[ıi]\s+emisyon)", re.I), "co2_scope2_t"),
    (re.compile(r"specific.{0,20}(co2|emission|emisyon)", re.I), "specific_co2_t_per_t"),
    (re.compile(r"(cement\s+produced|production.{0,15}cement|[çc]imento.{0,15}üretim)", re.I), "cement_produced_t"),
    (re.compile(r"(clinker\s+produced|production.{0,15}clinker|klinker.{0,15}üretim)", re.I), "clinker_produced_t"),
    (re.compile(r"(crude\s+steel|ham\s*çelik)", re.I), "crude_steel_t"),
    (re.compile(r"(electricity\s+consum|elektrik\s+tüketim)", re.I), "electricity_consumed_mwh"),
]
NUMBER_RE = re.compile(
    r"([+-]?(?:\d{1,3}(?:[.,\s]\d{3})+|\d+)(?:[.,]\d+)?)",
)


def _to_float(s: str) -> float | None:
    s = s.strip().replace(" ", "")
    # Turkish often uses "." as thousands and "," as decimal
    if "," in s and "." in s:
        # last separator wins as decimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # might be decimal (4,5) or thousands (4,500)
        if re.match(r"^[+-]?\d{1,3}(?:,\d{3})+$", s):
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _extract_from_text(text: str, page_no: int, source_doc: str) -> Iterable[dict]:
    for pattern, metric in EMISSIONS_PATTERNS:
        for m in pattern.finditer(text):
            window_start = max(0, m.start() - 80)
            window_end = min(len(text), m.end() + 160)
            window = text[window_start:window_end]
            year = _maybe_year(window)
            for nm in NUMBER_RE.finditer(window):
                val = _to_float(nm.group(1))
                if val is None or val == 0:
                    continue
                # Reject obviously-out-of-range
                if metric == "co2_scope1_t" and not (1e3 <= val <= 5e7):
                    continue
                if metric == "cement_produced_t" and not (1e5 <= val <= 1e8):
                    continue
                if metric == "crude_steel_t" and not (1e5 <= val <= 2e7):
                    continue
                if metric == "specific_co2_t_per_t" and not (0.3 <= val <= 1.8):
                    continue
                if metric == "electricity_consumed_mwh" and not (1e3 <= val <= 1e7):
                    continue
                if metric == "co2_scope2_t" and not (1e2 <= val <= 2e6):
                    continue
                yield {
                    "year": year,
                    "metric": metric,
                    "value": val,
                    "unit": _default_unit(metric),
                    "source_doc": source_doc,
                    "source_page": page_no,
                    "confidence": "low",  # text-grep
                    "notes": window[:120].replace("\n", " "),
                }


def _default_unit(metric: str) -> str:
    return {
        "co2_scope1_t": "tCO2",
        "co2_scope2_t": "tCO2",
        "specific_co2_t_per_t": "tCO2/t",
        "cement_produced_t": "t",
        "clinker_produced_t": "t",
        "crude_steel_t": "t",
        "electricity_consumed_mwh": "MWh",
    }.get(metric, "")


def extract_emissions(pdf_path: Path, facility_id: str, company: str) -> list[dict]:
    """Best-effort emissions extraction from a single PDF. Returns rows in
    the long format described at the module docstring.

    v0 strategy: text-grep with regex windows. Tables-via-pdfplumber will be
    a v1 improvement once we know which layouts are common.
    """
    import pdfplumber

    rows: list[dict] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                for r in _extract_from_text(text, page_no, pdf_path.name):
                    rows.append({"id": facility_id, "company": company, **r})
    except Exception as e:
        log.warning("  pdfplumber failed on %s: %s", pdf_path.name, e)
        return rows

    # Light dedup: same (id, year, metric, source_page) → keep highest plausible value.
    deduped: dict[tuple, dict] = {}
    for r in rows:
        key = (r["id"], r["year"], r["metric"], r["source_page"])
        if key not in deduped or r["value"] > deduped[key]["value"]:
            deduped[key] = r
    return list(deduped.values())


# ─────────────────────────────────────────────────────────────────────────────
# Top-level driver
# ─────────────────────────────────────────────────────────────────────────────


def scrape_facility(
    facility: dict,
    *,
    client: httpx.Client,
    dst_dir: Path = PDF_DIR_DEFAULT,
    max_pdfs: int = 8,
) -> tuple[list[PdfCandidate], list[Path], list[dict]]:
    fid = facility["id"]
    url = facility.get("public_disclosure_url", "")
    if not url or url in {"—", ""}:
        log.info("[%s] no disclosure URL — skipping", fid)
        return [], [], []
    log.info("[%s] starting (%s)", fid, facility.get("company", ""))
    candidates = find_pdf_links(url, client=client)
    # Take the most recent N
    candidates_sorted = sorted(candidates, key=lambda c: (c.year or 0), reverse=True)[:max_pdfs]

    pdfs: list[Path] = []
    rows: list[dict] = []
    for c in candidates_sorted:
        p = download_pdf(c, fid, client=client, dst_dir=dst_dir)
        if p is None:
            continue
        pdfs.append(p)
        rows.extend(extract_emissions(p, fid, facility.get("company", "")))

    log.info("[%s] done — %d PDFs, %d candidate rows extracted", fid, len(pdfs), len(rows))
    return candidates, pdfs, rows
