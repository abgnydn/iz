"""
Honest leave-one-plant-out (LOPO) evaluation of the cf-corrected formula.

The headline `+85% log-MAE reduction` is an IN-SAMPLE number: the route
emission-factors (FERT_ROUTE_EF, ALU_ROUTE_EF, ...) were hand-set from the same
audit-grade plants the formula is then scored on. For single-plant routes
(fertilizer-N2O, fertilizer-blender) the EF is literally that one plant's
audited emissions / (capacity x cf) — the formula cannot help but reproduce it.

This script removes that leak. For each audit plant i we predict its Scope 1
using an emission-factor derived ONLY from the OTHER audit plants that share its
EF group (route for steel/Al/fertilizer, sector for cement):

    implied_ef_j = truth_j / (capacity_j * cf_j)          # what each plant "says" the EF is
    EF_lopo(i)   = median{ implied_ef_j : group(j)==group(i), j != i }
    pred_lopo(i) = capacity_i * EF_lopo(i) * cf_i

Capacity and cf come from operator production disclosures (non-leaky w.r.t.
emissions); only the EF is re-derived. Plants whose EF group has no OTHER member
(single-plant strata) are UNPREDICTABLE under LOPO and reported separately — that
is the honest finding, not a number to paper over.

Run: .venv/bin/python bin/lopo_ef_eval.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from statistics import median

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "bin"))
from export_bench_browser import (  # noqa: E402
    ALU_ROUTE_MAP,
    DISCLOSED_CF,
    EU_DEFAULT_EF,
    FERT_ROUTE_MAP,
    SECTOR_DEFAULT_CF,
    STEEL_ROUTE_MAP,
    TR_ACTUAL_EF,
    ALU_ROUTE_EF,
    FERT_ROUTE_EF,
    STEEL_ROUTE_EF,
)

FACS = REPO / "data" / "tr_facilities.csv"
KNOWN = REPO / "data" / "tr_facility_known_emissions.csv"
OUT = REPO / "reports" / "lopo_ef_eval.json"


def audit_truth() -> dict[str, float]:
    """Latest per-plant Scope 1 audit label (same set the headline uses)."""
    kn = pd.read_csv(KNOWN)
    pp = kn[kn["metric"] == "co2_scope1_t"].copy()
    pp["year"] = pd.to_numeric(pp["year"], errors="coerce")
    pp = pp.sort_values("year", ascending=False).drop_duplicates("id")
    return {r["id"]: float(r["value"]) for _, r in pp.iterrows()}


def ef_group(fid: str, scope: str) -> str:
    if scope == "steel" and fid in STEEL_ROUTE_MAP:
        return f"steel:{STEEL_ROUTE_MAP[fid]}"
    if scope == "aluminum" and fid in ALU_ROUTE_MAP:
        return f"aluminum:{ALU_ROUTE_MAP[fid]}"
    if scope == "fertilizer" and fid in FERT_ROUTE_MAP:
        return f"fertilizer:{FERT_ROUTE_MAP[fid]}"
    return f"{scope}:sector"


def in_sample_ef(fid: str, scope: str) -> float:
    if scope == "steel" and fid in STEEL_ROUTE_MAP:
        return STEEL_ROUTE_EF[STEEL_ROUTE_MAP[fid]]
    if scope == "aluminum" and fid in ALU_ROUTE_MAP:
        return ALU_ROUTE_EF[ALU_ROUTE_MAP[fid]]
    if scope == "fertilizer" and fid in FERT_ROUTE_MAP:
        return FERT_ROUTE_EF[FERT_ROUTE_MAP[fid]]
    return TR_ACTUAL_EF[scope]


def log_mae_reduction(preds: dict, truth: dict, eu: dict, ids: list[str]) -> tuple[float, float]:
    ids = [i for i in ids if preds.get(i, 0) > 0 and truth[i] > 0 and eu[i] > 0]
    if not ids:
        return float("nan"), float("nan")
    mm = sum(abs(math.log(preds[i]) - math.log(truth[i])) for i in ids) / len(ids)
    em = sum(abs(math.log(eu[i]) - math.log(truth[i])) for i in ids) / len(ids)
    red = (1 - mm / em) * 100 if em > 0 else float("nan")
    return red, mm


def main() -> None:
    facs = pd.read_csv(FACS).set_index("id")
    truth = audit_truth()
    plants = [fid for fid in truth if fid in facs.index]

    rows = []
    groups: dict[str, list[str]] = {}
    for fid in plants:
        scope = facs.loc[fid, "cbam_scope"]
        cap = float(facs.loc[fid, "annual_capacity_t"])
        cf = DISCLOSED_CF.get(fid, SECTOR_DEFAULT_CF[scope])
        g = ef_group(fid, scope)
        groups.setdefault(g, []).append(fid)
        rows.append({
            "id": fid, "scope": scope, "cap": cap, "cf": cf, "group": g,
            "truth": truth[fid],
            "eu_default": cap * EU_DEFAULT_EF.get(scope, 0.0),
            "implied_ef": truth[fid] / (cap * cf) if cap * cf > 0 else 0.0,
            "in_sample_ef": in_sample_ef(fid, scope),
        })
    by_id = {r["id"]: r for r in rows}

    in_pred, lopo_pred = {}, {}
    predictable, unpredictable = [], []
    for r in rows:
        fid, g = r["id"], r["group"]
        in_pred[fid] = r["cap"] * r["in_sample_ef"] * r["cf"]
        others = [by_id[o]["implied_ef"] for o in groups[g] if o != fid and by_id[o]["implied_ef"] > 0]
        if others:
            ef_lopo = median(others)
            lopo_pred[fid] = r["cap"] * ef_lopo * r["cf"]
            r["ef_lopo"] = ef_lopo
            r["ratio_in"] = in_pred[fid] / r["truth"]
            r["ratio_lopo"] = lopo_pred[fid] / r["truth"]
            predictable.append(fid)
        else:
            r["ef_lopo"] = None
            r["ratio_in"] = in_pred[fid] / r["truth"]
            r["ratio_lopo"] = None
            unpredictable.append(fid)

    eu = {r["id"]: r["eu_default"] for r in rows}
    all_ids = [r["id"] for r in rows]
    red_in_all, mae_in_all = log_mae_reduction(in_pred, truth, eu, all_ids)
    red_in_pred, _ = log_mae_reduction(in_pred, truth, eu, predictable)
    red_lopo, mae_lopo = log_mae_reduction(lopo_pred, truth, eu, predictable)

    # Report
    print("=" * 104)
    print("  HONEST LEAVE-ONE-PLANT-OUT EF EVALUATION")
    print("=" * 104)
    print(f"  {'plant':22s} {'group':26s} {'truth':>12s} {'EF(in)':>7s} {'EF(lopo)':>9s} "
          f"{'ratio_in':>9s} {'ratio_lopo':>11s}")
    print("-" * 104)
    for r in sorted(rows, key=lambda x: (x["group"], x["id"])):
        efl = f"{r['ef_lopo']:.3f}" if r["ef_lopo"] is not None else "  —"
        rl = f"{r['ratio_lopo']:.2f}x" if r["ratio_lopo"] is not None else "UNPREDICT"
        print(f"  {r['id']:22s} {r['group']:26s} {r['truth']:>12,.0f} "
              f"{r['in_sample_ef']:>7.3f} {efl:>9s} {r['ratio_in']:>8.2f}x {rl:>11s}")
    print("-" * 104)
    print(f"  Single-plant strata (cannot validate — EF is literally the plant's own answer):")
    for fid in unpredictable:
        print(f"      {fid:22s} {by_id[fid]['group']:26s} in-sample ratio {by_id[fid]['ratio_in']:.2f}x  <- looks perfect ONLY because self-fit")
    print("=" * 104)
    print(f"  IN-SAMPLE  (leaky, current headline)  n={len(all_ids)}   log-MAE reduction vs EU: {red_in_all:+.1f}%")
    print(f"  IN-SAMPLE  on predictable subset      n={len(predictable)}   reduction vs EU: {red_in_pred:+.1f}%")
    print(f"  LOPO-EF    (honest)                   n={len(predictable)}   reduction vs EU: {red_lopo:+.1f}%")
    print(f"  {len(unpredictable)} plant(s) UNPREDICTABLE under LOPO (single-plant strata): {unpredictable}")
    print("=" * 104)

    OUT.write_text(json.dumps({
        "n_total": len(all_ids),
        "n_predictable": len(predictable),
        "unpredictable_single_plant_strata": unpredictable,
        "reduction_in_sample_all": red_in_all,
        "reduction_in_sample_predictable": red_in_pred,
        "reduction_lopo_predictable": red_lopo,
        "per_plant": rows,
    }, indent=2, default=str))
    print(f"wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
