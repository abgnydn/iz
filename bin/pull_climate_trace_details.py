"""
Pull /v6/assets/{id} for each Climate TRACE asset already joined to an iz
facility, extract per-year CO₂ + activity, write rich weak labels.

The /v6/assets list endpoint returns EmissionsSummary with null Emissions for
many records. /v6/assets/{id} returns full EmissionsDetails (per-gas, per-year,
with EmissionsQuantity + Activity + CapacityFactor). That's the actual signal.

Output: reports/climate_trace_tr_details.parquet
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
JOINED = REPO / "reports" / "climate_trace_tr_joined.parquet"
OUT = REPO / "reports" / "climate_trace_tr_details.parquet"
LOG_DIR = REPO / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_DIR / "ct_details.log")],
)
log = logging.getLogger("ct.details")

API = "https://api.climatetrace.org/v6"


def fetch_one(client: httpx.Client, asset_id: int) -> list[dict]:
    r = client.get(f"{API}/assets/{asset_id}", timeout=30.0)
    r.raise_for_status()
    j = r.json()
    rows = []
    base = {
        "ct_asset_id": j.get("Id"),
        "name": j.get("Name"),
        "native_id": j.get("NativeId"),
        "sector": j.get("Sector"),
        "asset_type": j.get("AssetType"),
        "reporting_entity": j.get("ReportingEntity"),
    }
    for d in j.get("EmissionsDetails", []) or []:
        rows.append({
            **base,
            "gas": d.get("Gas"),
            "year": d.get("Year"),
            "activity": d.get("Activity"),
            "activity_units": d.get("ActivityUnits"),
            "capacity": d.get("Capacity"),
            "capacity_units": d.get("CapacityUnits"),
            "capacity_factor": d.get("CapacityFactor"),
            "ef": d.get("EmissionsFactor"),
            "ef_units": d.get("EmissionsFactorUnits"),
            "emissions": d.get("EmissionsQuantity"),
        })
    return rows


def main() -> None:
    joined = pd.read_parquet(JOINED)
    asset_ids = sorted(joined["ct_asset_id"].dropna().unique().astype(int).tolist())
    log.info("assets to fetch: %d", len(asset_ids))

    all_rows: list[dict] = []
    with httpx.Client(http2=True, headers={"user-agent": "iz-bench/0.1"}) as client:
        for i, aid in enumerate(asset_ids, 1):
            try:
                rows = fetch_one(client, aid)
                all_rows.extend(rows)
                log.info("[%d/%d] %d → %d rows", i, len(asset_ids), aid, len(rows))
            except Exception as e:
                log.warning("[%d/%d] %d failed: %s", i, len(asset_ids), aid, e)
            time.sleep(0.05)

    df = pd.DataFrame(all_rows)
    log.info("total rows: %d  gases: %s", len(df), sorted(df["gas"].dropna().unique().tolist()))

    iz_lookup = joined[["ct_asset_id", "iz_id", "iz_company", "iz_scope", "lat", "lon"]].drop_duplicates("ct_asset_id")
    df = df.merge(iz_lookup, on="ct_asset_id", how="left")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    log.info("wrote → %s", OUT.relative_to(REPO))

    # Headline: per iz facility, sum co2e_100yr for the latest year.
    co2 = df[(df["gas"] == "co2e_100yr") & df["emissions"].notna() & df["iz_id"].notna()].copy()
    if not co2.empty:
        latest = co2.sort_values("year").groupby("iz_id").tail(1)
        latest = latest[["iz_id", "iz_company", "year", "emissions", "capacity_factor"]]
        latest = latest.sort_values("emissions", ascending=False)
        print()
        print("=" * 76)
        print("  Per-facility CO₂ (latest year, Climate TRACE):")
        print("=" * 76)
        for _, r in latest.head(25).iterrows():
            print(f"  {r['iz_id']:32s} {int(r['year'])}  {r['emissions']/1e6:7.3f} Mt  cf={r['capacity_factor']:.2f}")
        print()
        print(f"  facilities with CO₂ labels: {len(latest)} / {joined['iz_id'].nunique()}")


if __name__ == "__main__":
    main()
