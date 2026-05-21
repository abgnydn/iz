"""
iz Step 6 — Scrape TR facility sustainability disclosures.

Reads data/tr_facilities.csv, walks the public_disclosure_url column,
downloads any PDF sustainability reports we can find, and best-effort
extracts emissions / production rows into:

    data/disclosures/*.pdf                          — raw PDFs (gitignored)
    reports/tr_facility_disclosures.parquet         — long-format extracted rows
    reports/tr_facility_disclosure_inventory.csv    — flat summary: which PDFs
                                                       we got per facility, used
                                                       for manual auditing

Usage:
    uv run python bin/scrape_disclosures.py                  # all 57 facilities
    uv run python bin/scrape_disclosures.py --top 8          # first 8 only (smoke test)
    uv run python bin/scrape_disclosures.py --only akcansa   # all akcansa-* rows
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

import httpx
import pandas as pd

from iz.scrape.disclosures import scrape_facility

REPO = Path(__file__).resolve().parent.parent
CSV_PATH = REPO / "data" / "tr_facilities.csv"
LOG_PATH = REPO / "logs" / "03_scrape_disclosures.log"
PDF_DIR = REPO / "data" / "disclosures"
INV_PATH = REPO / "reports" / "tr_facility_disclosure_inventory.csv"
PARQUET_PATH = REPO / "reports" / "tr_facility_disclosures.parquet"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger("iz.scrape")


def load_facilities() -> list[dict]:
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=0, help="process only the first N facilities")
    ap.add_argument("--only", default="", help="substring filter on facility id")
    ap.add_argument("--max-pdfs", type=int, default=6, help="max PDFs per facility")
    args = ap.parse_args()

    facilities = load_facilities()
    if args.only:
        facilities = [f for f in facilities if args.only.lower() in f["id"].lower()]
    if args.top:
        facilities = facilities[: args.top]
    if not facilities:
        log.error("no facilities matched filters")
        sys.exit(1)

    log.info("scrape target: %d facilities", len(facilities))

    inventory: list[dict] = []
    all_rows: list[dict] = []
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(http2=True, verify=False) as client:  # http2 helps with Cloudflare-fronted sites
        for i, fac in enumerate(facilities, 1):
            log.info("--- [%d/%d] %s ---", i, len(facilities), fac["id"])
            try:
                candidates, pdfs, rows = scrape_facility(
                    fac, client=client, dst_dir=PDF_DIR, max_pdfs=args.max_pdfs
                )
            except Exception as e:
                log.error("  hard failure: %s", e)
                continue

            inventory.append(
                {
                    "id": fac["id"],
                    "company": fac["company"],
                    "scope": fac["cbam_scope"],
                    "disclosure_url": fac["public_disclosure_url"],
                    "candidate_pdfs": len(candidates),
                    "downloaded_pdfs": len(pdfs),
                    "extracted_rows": len(rows),
                    "pdf_filenames": "; ".join(p.name for p in pdfs),
                }
            )
            all_rows.extend(rows)

    # Write outputs
    INV_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(inventory).to_csv(INV_PATH, index=False)
    log.info("inventory → %s", INV_PATH.relative_to(REPO))

    if all_rows:
        df = pd.DataFrame(all_rows)
        df.to_parquet(PARQUET_PATH, index=False)
        log.info("disclosures → %s (%d rows)", PARQUET_PATH.relative_to(REPO), len(df))
    else:
        log.warning("no rows extracted; parquet not written")

    # Summary
    n_with_pdf = sum(1 for r in inventory if r["downloaded_pdfs"] > 0)
    n_with_rows = sum(1 for r in inventory if r["extracted_rows"] > 0)
    print()
    print("=" * 60)
    print(f"  facilities scraped:        {len(inventory)}")
    print(f"  facilities w/ ≥1 PDF:      {n_with_pdf}")
    print(f"  facilities w/ ≥1 row:      {n_with_rows}")
    print(f"  total rows extracted:      {len(all_rows)}")
    print(f"  inventory:                 {INV_PATH.relative_to(REPO)}")
    if all_rows:
        print(f"  disclosures parquet:       {PARQUET_PATH.relative_to(REPO)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
