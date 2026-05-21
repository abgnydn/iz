"""
iz Step 6b — Download the curated set of known sustainability-report PDFs.

Reads data/known_disclosure_pdfs.csv (hand-picked URLs we found via web search,
since corporate sites' auto-discovery is broken by JS rendering / CDN WAF).
Skips rows where `doc_type` is 'landing' (HTML pages, not PDFs).

Output:
    data/disclosures/<id>__<year>__<slug>__<hash>.pdf
    reports/known_pdfs_inventory.csv

Then runs extraction on each downloaded PDF and merges results into
reports/tr_facility_disclosures.parquet.

Usage:
    uv run python bin/download_known_pdfs.py
"""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

import httpx
import pandas as pd

from iz.scrape.disclosures import (
    BROWSER_HEADERS,
    PdfCandidate,
    download_pdf,
    extract_emissions,
)

REPO = Path(__file__).resolve().parent.parent
KNOWN_CSV = REPO / "data" / "known_disclosure_pdfs.csv"
FACS_CSV = REPO / "data" / "tr_facilities.csv"
LOG_PATH = REPO / "logs" / "03b_download_known_pdfs.log"
PDF_DIR = REPO / "data" / "disclosures"
INV_PATH = REPO / "reports" / "known_pdfs_inventory.csv"
PARQUET_PATH = REPO / "reports" / "tr_facility_disclosures.parquet"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger("iz.scrape.known")


def load_facility_companies() -> dict[str, str]:
    with open(FACS_CSV, encoding="utf-8") as f:
        return {row["id"]: row["company"] for row in csv.DictReader(f)}


def main():
    if not KNOWN_CSV.exists():
        log.error("missing %s", KNOWN_CSV)
        sys.exit(1)

    companies = load_facility_companies()
    with open(KNOWN_CSV, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["doc_type"] != "landing"]
    log.info("known PDFs to fetch: %d", len(rows))

    inventory: list[dict] = []
    all_extracted: list[dict] = []
    seen_urls: set[str] = set()
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(http2=True, verify=False, headers=BROWSER_HEADERS, timeout=60) as client:
        for i, row in enumerate(rows, 1):
            url = row["url"]
            fid = row["id"]
            year = int(row["year"]) if row["year"].isdigit() else None
            log.info("[%d/%d] %s @ %s", i, len(rows), fid, url)

            if url in seen_urls:
                log.info("  already fetched (shared group report) — extraction handled with the first occurrence")
                # Still build an inventory row pointing at the shared file
                inventory.append({"id": fid, "year": year, "url": url, "status": "shared", "pdf": "(see other rows)"})
                continue
            seen_urls.add(url)

            cand = PdfCandidate(url=url, anchor_text=row["doc_type"], year=year)
            pdf_path = download_pdf(cand, fid, client=client, dst_dir=PDF_DIR)
            if pdf_path is None:
                inventory.append({"id": fid, "year": year, "url": url, "status": "failed", "pdf": ""})
                continue
            inventory.append({"id": fid, "year": year, "url": url, "status": "ok", "pdf": pdf_path.name})

            # Extract for this facility
            company = companies.get(fid, "")
            rows_extracted = extract_emissions(pdf_path, fid, company)
            all_extracted.extend(rows_extracted)
            log.info("  extracted %d candidate rows", len(rows_extracted))

    INV_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(inventory).to_csv(INV_PATH, index=False)
    log.info("inventory → %s", INV_PATH.relative_to(REPO))

    if all_extracted:
        df_new = pd.DataFrame(all_extracted)
        if PARQUET_PATH.exists():
            df_old = pd.read_parquet(PARQUET_PATH)
            df = pd.concat([df_old, df_new], ignore_index=True)
            df = df.drop_duplicates(subset=["id", "year", "metric", "source_doc", "source_page"], keep="last")
        else:
            df = df_new
        df.to_parquet(PARQUET_PATH, index=False)
        log.info("disclosures → %s (%d total rows)", PARQUET_PATH.relative_to(REPO), len(df))

    n_ok = sum(1 for r in inventory if r["status"] == "ok")
    n_fail = sum(1 for r in inventory if r["status"] == "failed")
    print()
    print("=" * 60)
    print(f"  curated PDFs:           {len(rows)}")
    print(f"  downloaded:             {n_ok}")
    print(f"  failed:                 {n_fail}")
    print(f"  rows extracted:         {len(all_extracted)}")
    print(f"  inventory:              {INV_PATH.relative_to(REPO)}")
    if all_extracted:
        print(f"  disclosures parquet:    {PARQUET_PATH.relative_to(REPO)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
