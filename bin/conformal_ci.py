"""
Split-conformal prediction interval on the cf-corrected formula's leave-one-plant-out predictions.

Method: split-conformal (Vovk; Shafer & Vovk 2008). For each leave-one-plant-out test point
the held-out facility itself is the "test" — but we don't have a true
calibration set since every facility is held out in turn. We adapt:

For each held-out facility i, treat the other n-1 leave-one-plant-out predictions as
the calibration set. Conformity score is |log(pred) - log(truth)|. The
conformal prediction interval at confidence (1-α) for facility i is:

  [exp(log(pred_i) - q_{1-α}), exp(log(pred_i) + q_{1-α})]

where q_{1-α} is the (1-α)(n+1)/n quantile of the calibration scores.

This is a leave-one-out / jackknife+ style conformal — gives a
distribution-free coverage guarantee asymptotically. With n=19 the
guarantee is approximate; Chen et al. (arXiv:2512.04566) addresses
small-calibration-set corrections.

Output: reports/conformal_ci.json
"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOPO = REPO / "reports" / "lopo_ef_eval.json"   # cf-corrected formula, leave-one-plant-out
OUT = REPO / "reports" / "conformal_ci.json"
FAC = REPO / "site" / "bench" / "facilities.json"

# Stratum assignment matches the leave-one-plant-out stratified split.
STEEL_ROUTE_MAP = {
    "erdemir-eregli": "BF/BOF", "isdemir-iskenderun": "BF/BOF", "kardemir-karabuk": "BF/BOF",
    "colakoglu-gebze": "EAF", "izdemir-aliaga": "EAF", "habas-aliaga": "EAF",
}
ALU_ROUTE_MAP = {"assan-tuzla": "downstream", "asas-akyazi": "downstream"}
FERT_ROUTE_MAP = {
    "toros-mersin": "integrated", "toros-samsun": "integrated", "toros-ceyhan": "integrated",
    "bagfas-bandirma": "N2O-controlled", "gubretas-izmit": "blender",
}


def stratum_of(fid: str, sector: str) -> str:
    if sector == "steel":
        return f"steel-{STEEL_ROUTE_MAP.get(fid, 'EAF')}"
    if sector == "aluminum":
        return f"aluminum-{ALU_ROUTE_MAP.get(fid, 'downstream')}"
    if sector == "fertilizer":
        return f"fertilizer-{FERT_ROUTE_MAP.get(fid, 'integrated')}"
    return sector


def main(alpha: float = 0.05) -> int:
    # Use the cf-corrected formula's leave-one-plant-out predictions — only the
    # validatable plants (single-plant strata have no LOPO prediction).
    rows = [r for r in json.loads(LOPO.read_text())["per_plant"] if r.get("ratio_lopo") is not None]
    if len(rows) < 5:
        print("not enough leave-one-plant-out rows", file=sys.stderr)
        return 1

    # Join with facilities.json to get sector
    fac_sector = {}
    if FAC.exists():
        for f in json.loads(FAC.read_text()):
            fac_sector[f["id"]] = f.get("sector", "")

    # Log-space conformity scores on the formula's leave-one-plant-out predictions
    scores = []
    for r in rows:
        truth = r["truth"]
        pred = r["ratio_lopo"] * truth
        if pred > 0 and truth > 0:
            fid = r["id"]
            sector = fac_sector.get(fid, "")
            scores.append({
                "facility_id": fid,
                "stratum": stratum_of(fid, sector),
                "truth": truth,
                "formula_pred": pred,
                "log_err": abs(math.log(pred) - math.log(truth)),
            })

    n = len(scores)
    print(f"conformal calibration on n={n} leave-one-plant-out predictions, α={alpha}")
    print()

    # ---- Global jackknife conformal: per facility, calibrate on the other n-1 ----
    per_facility = []
    for i, s in enumerate(scores):
        others = [scores[j]["log_err"] for j in range(n) if j != i]
        others.sort()
        k = math.ceil((1 - alpha) * len(others))
        k = min(k, len(others)) - 1
        q_global = others[k]
        lo_g = math.exp(math.log(s["formula_pred"]) - q_global)
        hi_g = math.exp(math.log(s["formula_pred"]) + q_global)
        covered_g = lo_g <= s["truth"] <= hi_g

        # ---- Per-stratum: calibrate only on same-stratum facilities ----
        same = [scores[j]["log_err"] for j in range(n) if j != i and scores[j]["stratum"] == s["stratum"]]
        if len(same) >= 2:
            same.sort()
            k2 = math.ceil((1 - alpha) * len(same))
            k2 = min(k2, len(same)) - 1
            q_strat = same[k2]
            lo_s = math.exp(math.log(s["formula_pred"]) - q_strat)
            hi_s = math.exp(math.log(s["formula_pred"]) + q_strat)
            covered_s = lo_s <= s["truth"] <= hi_s
        else:
            # Fall back to global when stratum has <3 facilities (e.g. BAGFAŞ N2O singleton)
            q_strat = q_global
            lo_s, hi_s, covered_s = lo_g, hi_g, covered_g

        per_facility.append({
            "facility_id": s["facility_id"],
            "stratum": s["stratum"],
            "truth": s["truth"],
            "formula_pred": s["formula_pred"],
            "ci_lo": lo_g,
            "ci_hi": hi_g,
            "covered": covered_g,
            "q_used": q_global,
            "ci_lo_stratum": lo_s,
            "ci_hi_stratum": hi_s,
            "covered_stratum": covered_s,
            "q_stratum": q_strat,
        })

    n_cov = sum(1 for r in per_facility if r["covered"])
    cov_rate = n_cov / n * 100
    print(f"Empirical coverage at α={alpha} (i.e. target {(1-alpha)*100:.0f}%): {n_cov}/{n} = {cov_rate:.1f}%")
    print()

    # Aggregate one number: median q across facilities (the "typical" half-width in log space)
    qs = sorted(r["q_used"] for r in per_facility)
    median_q = qs[len(qs)//2]
    print(f"Median log-space half-width: {median_q:.3f}  →  multiplicative factor exp(q) = {math.exp(median_q):.2f}×")
    print(f"  (i.e. typical prediction interval is [pred / {math.exp(median_q):.2f}, pred × {math.exp(median_q):.2f}])")
    print()

    # Per-facility table
    print(f"{'facility':32s} {'truth':>12s} {'pred (med)':>12s} {'CI lo':>12s} {'CI hi':>12s} {'covered':>8s}")
    print("-" * 95)
    for r in per_facility:
        print(f"  {r['facility_id']:30s} {int(r['truth']):>12,d} {int(r["formula_pred"]):>12,d} "
              f"{int(r['ci_lo']):>12,d} {int(r['ci_hi']):>12,d} {'✓' if r['covered'] else '✗':>7s}")

    # Per-stratum coverage summary
    from collections import defaultdict
    by_stratum: dict[str, list[dict]] = defaultdict(list)
    for r in per_facility:
        by_stratum[r["stratum"]].append(r)
    stratum_summary = []
    print()
    print("Per-stratum coverage + tightening (stratum CI vs global CI):")
    print(f"{'stratum':28s} {'n':>3s} {'cov(s)':>8s} {'cov(g)':>8s} {'q(s)':>8s} {'factor(s)':>10s} {'tighter':>9s}")
    print("-" * 80)
    for strat, items in sorted(by_stratum.items()):
        n_s = len(items)
        cov_s = sum(1 for x in items if x["covered_stratum"]) / n_s * 100
        cov_g = sum(1 for x in items if x["covered"]) / n_s * 100
        qs_sorted = sorted(x["q_stratum"] for x in items)
        qg_sorted = sorted(x["q_used"] for x in items)
        med_qs = qs_sorted[len(qs_sorted) // 2]
        med_qg = qg_sorted[len(qg_sorted) // 2]
        factor_s = math.exp(med_qs)
        tighter = "—" if med_qg == 0 else f"{(med_qg - med_qs) / med_qg * 100:+.0f}%"
        stratum_summary.append({
            "stratum": strat,
            "n": n_s,
            "empirical_coverage_stratum_pct": cov_s,
            "empirical_coverage_global_pct": cov_g,
            "median_q_stratum": med_qs,
            "median_q_global": med_qg,
            "multiplicative_factor_stratum": factor_s,
            "tightening_vs_global_pct": (med_qg - med_qs) / med_qg * 100 if med_qg else 0,
        })
        print(f"  {strat:26s} {n_s:>3d} {cov_s:>7.0f}% {cov_g:>7.0f}% {med_qs:>8.3f} {factor_s:>9.2f}× {tighter:>9s}")

    OUT.write_text(json.dumps({
        "alpha": alpha,
        "n": n,
        "empirical_coverage_pct": cov_rate,
        "median_log_halfwidth": median_q,
        "multiplicative_factor": math.exp(median_q),
        "per_facility": per_facility,
        "per_stratum": stratum_summary,
    }, indent=2))
    print(f"\nwrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(alpha=0.05))
