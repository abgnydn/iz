"""
Split-conformal prediction interval on iz-1 LODO predictions.

Method: split-conformal (Vovk; Shafer & Vovk 2008). For each LODO test point
the held-out facility itself is the "test" — but we don't have a true
calibration set since every facility is held out in turn. We adapt:

For each held-out facility i, treat the other 20 LODO-test predictions as
the calibration set. Conformity score is |log(pred) - log(truth)|. The
conformal prediction interval at confidence (1-α) for facility i is:

  [exp(log(pred_i) - q_{1-α}), exp(log(pred_i) + q_{1-α})]

where q_{1-α} is the (1-α)(n+1)/n quantile of the calibration scores.

This is a leave-one-out / jackknife+ style conformal — gives a
distribution-free coverage guarantee asymptotically. With n=21 the
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
LODO = REPO / "reports" / "lodo_aggregated.json"
OUT = REPO / "reports" / "conformal_ci.json"


def main(alpha: float = 0.05) -> int:
    rows = json.loads(LODO.read_text())
    if len(rows) < 5:
        print("not enough LODO rows", file=sys.stderr)
        return 1

    # Log-space conformity scores
    scores = []
    for r in rows:
        if r["pred_median"] > 0 and r["truth"] > 0:
            scores.append({
                "facility_id": r["facility_id"],
                "truth": r["truth"],
                "pred_median": r["pred_median"],
                "log_err": abs(math.log(r["pred_median"]) - math.log(r["truth"])),
            })

    n = len(scores)
    print(f"conformal calibration on n={n} LODO predictions, α={alpha}")
    print()

    # Jackknife conformal: per facility, calibrate on the other n-1
    per_facility = []
    for i, s in enumerate(scores):
        others = [scores[j]["log_err"] for j in range(n) if j != i]
        others.sort()
        # (1-α)(n-1+1)/(n-1) quantile of |log err|, clamped to last entry
        k = math.ceil((1 - alpha) * len(others))
        k = min(k, len(others)) - 1  # 0-indexed
        q = others[k]
        lo = math.exp(math.log(s["pred_median"]) - q)
        hi = math.exp(math.log(s["pred_median"]) + q)
        covered = lo <= s["truth"] <= hi
        per_facility.append({
            "facility_id": s["facility_id"],
            "truth": s["truth"],
            "pred_median": s["pred_median"],
            "ci_lo": lo,
            "ci_hi": hi,
            "covered": covered,
            "q_used": q,
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
        print(f"  {r['facility_id']:30s} {int(r['truth']):>12,d} {int(r['pred_median']):>12,d} "
              f"{int(r['ci_lo']):>12,d} {int(r['ci_hi']):>12,d} {'✓' if r['covered'] else '✗':>7s}")

    OUT.write_text(json.dumps({
        "alpha": alpha,
        "n": n,
        "empirical_coverage_pct": cov_rate,
        "median_log_halfwidth": median_q,
        "multiplicative_factor": math.exp(median_q),
        "per_facility": per_facility,
    }, indent=2))
    print(f"\nwrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(alpha=0.05))
