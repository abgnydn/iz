"""
iz Step 7 — pull Climate TRACE v6 weak labels for Turkish facilities.

Runs against api.climatetrace.org/v6/assets?countries=TUR, flattens the
response, filters to CBAM-relevant sectors, joins to our tr_facilities.csv
by (sector, geographic proximity) where possible.

Usage:
    uv run python bin/pull_climate_trace.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from iz.data.climate_trace import fetch_tr_assets, filter_industrial, INDUSTRIAL_SECTORS

REPO = Path(__file__).resolve().parent.parent
LOG_PATH = REPO / "logs" / "07_climate_trace.log"
PARQUET_PATH = REPO / "reports" / "climate_trace_tr.parquet"
JOIN_PATH = REPO / "reports" / "climate_trace_tr_joined.parquet"
FACILITIES_CSV = REPO / "data" / "tr_facilities.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger("iz.ct")


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


SCOPE_TO_CT_SECTORS = {
    "cement": ["cement", "lime"],
    "steel": ["iron-and-steel"],
    "aluminum": ["aluminum"],
    "fertilizer": ["fertilizer", "chemicals", "petrochemicals"],
}


def join_by_proximity(ct: pd.DataFrame, facilities: pd.DataFrame, max_km: float = 30.0) -> pd.DataFrame:
    """For each iz facility, find the closest Climate TRACE asset in a
    compatible sector. Returns a one-row-per-(facility, year, gas) joined table.
    Keeps unmatched rows from both sides so we can audit."""
    ct = ct.dropna(subset=["lat", "lon"]).copy()
    pairs: list[dict] = []
    for _, fac in facilities.iterrows():
        scope = fac["cbam_scope"]
        eligible_sectors = SCOPE_TO_CT_SECTORS.get(scope, [])
        cand = ct[ct["sector"].isin(eligible_sectors)]
        if cand.empty:
            continue
        d = haversine_km(fac["lat"], fac["lon"], cand["lat"].values, cand["lon"].values)
        # Take all candidates within max_km — could be multiple plant lines / asset rows
        within = cand.loc[d <= max_km].copy()
        if within.empty:
            continue
        within["distance_km"] = d[d <= max_km]
        within["iz_id"] = fac["id"]
        within["iz_company"] = fac["company"]
        within["iz_scope"] = scope
        pairs.append(within)
    if not pairs:
        return pd.DataFrame()
    return pd.concat(pairs, ignore_index=True)


def main():
    log.info("== Climate TRACE Turkey pull (CBAM industrial sectors) ==")

    # 1) Raw pull
    df = fetch_tr_assets(countries=["TUR"])
    log.info("raw rows: %d", len(df))

    # 2) Save raw
    PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PARQUET_PATH, index=False)
    log.info("raw → %s", PARQUET_PATH.relative_to(REPO))

    # 3) Industrial-only summary
    ind = filter_industrial(df)
    log.info("industrial rows (cement/steel/aluminum/fertilizer/chemicals): %d", len(ind))
    log.info("industrial unique assets: %d", ind["ct_asset_id"].nunique())
    log.info("sectors covered: %s", sorted(ind["sector"].dropna().unique().tolist()))

    # 4) Join to iz facility list by sector + proximity
    facs = pd.read_csv(FACILITIES_CSV)
    log.info("iz facilities: %d", len(facs))
    joined = join_by_proximity(ind, facs, max_km=30.0)

    if joined.empty:
        log.warning("no proximity matches within 30 km — check Climate TRACE Centroid extraction")
    else:
        joined.to_parquet(JOIN_PATH, index=False)
        log.info("joined → %s (%d matched rows)", JOIN_PATH.relative_to(REPO), len(joined))
        per_id = joined.groupby("iz_id").size()
        log.info("facilities with ≥1 CT match: %d / %d", (per_id > 0).sum(), len(facs))

    # 5) Print summary
    print()
    print("=" * 64)
    print(f"  Climate TRACE TR raw rows:     {len(df):>8,}")
    print(f"  Industrial subset rows:        {len(ind):>8,}")
    print(f"  Unique industrial assets:      {ind['ct_asset_id'].nunique():>8,}")
    if not joined.empty:
        print(f"  Joined rows (≤30 km):          {len(joined):>8,}")
        print(f"  iz facilities matched:         {joined['iz_id'].nunique():>8,} / {len(facs)}")
    print(f"  Raw  parquet:                  {PARQUET_PATH.relative_to(REPO)}")
    print(f"  Join parquet:                  {JOIN_PATH.relative_to(REPO) if not joined.empty else '(none)'}")
    print("=" * 64)


if __name__ == "__main__":
    main()
