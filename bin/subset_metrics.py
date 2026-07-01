"""
Subset metrics — answer "does the headline depend on which provenance tier?"

Computes B0/B1/B2 log-MAE on:
  (a) ALL n=21 disclosure facilities (the headline)
  (b) DIRECT only (~14, excludes allocated and composite — the strictest read)
  (c) DIRECT + COMPOSITE (excludes only allocated — sanity check)

Fixes self-critique #12: "I didn't verify the formula-vs-model finding by
holding-out only directly-disclosed facilities."
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
BASELINES = REPO / "reports" / "baselines.json"
KNOWN = REPO / "data" / "tr_facility_known_emissions.csv"


def main() -> None:
    rows = json.loads(BASELINES.read_text())
    kn = pd.read_csv(KNOWN)
    pp = kn[kn["metric"] == "co2_scope1_t"].copy()
    pp["year"] = pd.to_numeric(pp["year"], errors="coerce")
    pp = pp.sort_values("year", ascending=False).drop_duplicates("id")
    prov = dict(zip(pp["id"], pp["provenance"]))

    # Optional iz from aggregated leave-one-plant-out
    iz_path = REPO / "reports" / "lodo_aggregated.json"
    iz_by_fid = {}
    if iz_path.exists():
        iz_by_fid = {r["facility_id"]: r["pred_median"] for r in json.loads(iz_path.read_text())}

    subsets = {
        "all (n=21)":          lambda p: True,
        "direct only":          lambda p: p == "direct",
        "direct + composite":   lambda p: p in ("direct", "composite"),
        "allocated only":       lambda p: p == "allocated",
    }

    print(f"{'subset':22s} {'n':>3s}  {'B0 EU':>8s}  {'B1 formula':>10s}  {'B2 ridge':>9s}  {'iz NN':>8s}  {'B1 reduction':>12s}")
    print("-" * 90)
    for name, pred in subsets.items():
        keep = [r for r in rows if pred(prov.get(r["facility_id"], "unknown"))]
        if not keep:
            continue
        def lm(field):
            errs = [abs(math.log(r[field]) - math.log(r["truth"])) for r in keep if r[field] > 0 and r["truth"] > 0]
            return sum(errs) / len(errs) if errs else 0
        b0, b1, b2 = lm("B0_eu_default"), lm("B1_cf_formula"), lm("B2_ridge")
        iz_errs = [abs(math.log(iz_by_fid[r["facility_id"]]) - math.log(r["truth"]))
                   for r in keep if r["facility_id"] in iz_by_fid and r["truth"] > 0]
        iz = sum(iz_errs) / len(iz_errs) if iz_errs else float("nan")
        red = (1 - b1 / b0) * 100 if b0 > 0 else 0
        iz_str = f"{iz:.3f}" if iz_errs else "—"
        print(f"{name:22s} {len(keep):>3d}  {b0:>8.3f}  {b1:>10.3f}  {b2:>9.3f}  {iz_str:>8s}  {red:>11.1f}%")
    print()


if __name__ == "__main__":
    main()
