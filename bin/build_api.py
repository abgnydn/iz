"""
C2 + C5 — Static JSON API + annual refresh pipeline.

Static API (just dumps the bench to JSON files at predictable paths so any
client can fetch them):
  /api/facility/<id>.json    — per-facility full record
  /api/facility/index.json   — flat list of all facilities
  /api/sector/<scope>.json   — per-sector aggregates
  /api/bench.json            — full bench snapshot

Annual refresh stub (`bin/annual_refresh.py`):
  - Re-runs every script in bin/ that pulls fresh disclosures
  - Designed to be invoked by `cron 0 2 1 4 *` (April 1 at 02:00) when most TR
    operators have just published their previous-year IARs
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
API_DIR = REPO / "api"
API_DIR.mkdir(parents=True, exist_ok=True)


def main():
    facs = pd.read_csv(REPO / "data" / "tr_facilities.csv")
    kn = pd.read_csv(REPO / "data" / "tr_facility_known_emissions.csv")
    s1 = kn[kn["metric"] == "co2_scope1_t"].copy()
    s1["year"] = pd.to_numeric(s1["year"], errors="coerce")
    s1 = s1.sort_values("year", ascending=False).drop_duplicates("id")

    # Build per-facility JSON files
    facility_dir = API_DIR / "facility"
    facility_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for _, fac in facs.iterrows():
        fid = fac["id"]
        s1_row = s1[s1["id"] == fid]
        record = {
            "facility_id": fid,
            "operator": fac["company"],
            "group": fac["group"],
            "name": fac["plant_name"],
            "sector": fac["cbam_scope"],
            "city": fac["city"],
            "province": fac["province"],
            "lat": float(fac["lat"]),
            "lon": float(fac["lon"]),
            "annual_capacity_t": float(fac["annual_capacity_t"]),
            "cn_codes": fac["cn_codes"],
            "disclosure_url": fac["public_disclosure_url"],
        }
        if not s1_row.empty:
            record["scope1_t"] = float(s1_row["value"].iloc[0])
            record["scope1_year"] = int(s1_row["year"].iloc[0])
            record["scope1_provenance"] = s1_row["provenance"].iloc[0]
            record["scope1_source"] = s1_row["source"].iloc[0]
        (facility_dir / f"{fid}.json").write_text(json.dumps(record, indent=2, default=str))
        index.append({k: record[k] for k in ("facility_id","operator","sector","province","lat","lon","annual_capacity_t")})

    (API_DIR / "facility" / "index.json").write_text(json.dumps(index, indent=2))

    # Per-sector aggregates
    sector_dir = API_DIR / "sector"
    sector_dir.mkdir(parents=True, exist_ok=True)
    for sector, group in facs.groupby("cbam_scope"):
        sec_facs = [r["facility_id"] for r in index if r["sector"] == sector]
        agg = {
            "sector": sector,
            "n_facilities": len(sec_facs),
            "total_capacity_t": float(group["annual_capacity_t"].sum()),
            "facilities": sec_facs,
        }
        (sector_dir / f"{sector}.json").write_text(json.dumps(agg, indent=2))

    # Full snapshot
    bench = {
        "version": "v0.2",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "n_facilities": len(index),
        "facilities": index,
    }
    (API_DIR / "bench.json").write_text(json.dumps(bench, indent=2))

    print(f"wrote {len(index)} facility records + {sector_dir.relative_to(REPO)}/*.json + {API_DIR.relative_to(REPO)}/bench.json")


if __name__ == "__main__":
    main()
