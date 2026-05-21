"""
iz Step 8 — Sentinel-5P bbox time series for all TR-MRV-Bench facilities.

Bandwidth-bound. Designed to be run in the background and monitored.
Per-facility shard so partial failures don't kill the whole run.

Usage:
    uv run python bin/extract_s5p_bench.py                  # all facilities, last 3 years
    uv run python bin/extract_s5p_bench.py --days 365       # last year only
    uv run python bin/extract_s5p_bench.py --top 5          # smoke test
    uv run python bin/extract_s5p_bench.py --only akcansa   # one company
"""

from __future__ import annotations

import argparse
import csv
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from iz.data.s5p_stream import extract_facility

REPO = Path(__file__).resolve().parent.parent
FACS_CSV = REPO / "data" / "tr_facilities.csv"
LOG_PATH = REPO / "logs" / "08_s5p_bench.log"
CACHE_DIR = REPO / "data" / "s5p_cache"
OUT_DIR = REPO / "data" / "s5p"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="a"), logging.StreamHandler()],
)
log = logging.getLogger("iz.s5p.bench")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365 * 3, help="lookback window (default 3 years)")
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--max-scenes", type=int, default=180, help="cap scenes per facility per run")
    args = ap.parse_args()

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    log.info("== S5P bench extract == window %s → %s", start.date(), end.date())

    with open(FACS_CSV, encoding="utf-8") as f:
        facilities = list(csv.DictReader(f))
    if args.only:
        facilities = [f for f in facilities if args.only.lower() in f["id"].lower()]
    if args.top:
        facilities = facilities[: args.top]
    log.info("facilities to process: %d", len(facilities))

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    for i, fac in enumerate(facilities, 1):
        fid = fac["id"]
        try:
            lat = float(fac["lat"])
            lon = float(fac["lon"])
        except (KeyError, ValueError):
            log.warning("[%s] bad lat/lon; skipping", fid)
            continue
        out = OUT_DIR / f"{fid}.parquet"
        if out.exists() and out.stat().st_size > 1024:
            log.info("[%d/%d] %s — cached, skipping (delete to refresh)", i, len(facilities), fid)
            continue
        log.info("[%d/%d] %s @ (%.4f, %.4f)", i, len(facilities), fid, lat, lon)
        try:
            n = extract_facility(
                fid, lat, lon, start, end,
                pdf_cache=CACHE_DIR, out_parquet=out, max_scenes=args.max_scenes,
            )
        except Exception as e:
            log.error("  hard failure: %s", e)
            n = 0
        summary.append({"id": fid, "rows": n})

    # Final report
    total = sum(s["rows"] for s in summary)
    print()
    print("=" * 60)
    print(f"  facilities processed: {len(summary)}")
    print(f"  total scene rows:     {total}")
    print(f"  shards directory:     {OUT_DIR.relative_to(REPO)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
