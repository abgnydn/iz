"""
Stable LODO headline by aggregating across multiple LODO runs.

Each LODO run already takes 3-seed median per facility. This script wraps that
in N outer repetitions and produces a final per-facility prediction =
median across all (outer × inner) = 3N seeds. Reduces variance.

Writes aggregated results to reports/lodo_aggregated.json.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "reports" / "lodo_results.json"
OUT = REPO / "reports" / "lodo_aggregated.json"

N_OUTER = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def main() -> None:
    per_facility: dict[str, list[float]] = defaultdict(list)
    truths: dict[str, float] = {}
    eus: dict[str, float] = {}

    for outer in range(N_OUTER):
        print(f"\n=== outer run {outer+1}/{N_OUTER} ===")
        subprocess.run(["uv", "run", "python", "bin/e2e_lodo.py"], cwd=str(REPO), check=True)
        rows = json.loads(RESULTS.read_text())
        for r in rows:
            per_facility[r["facility_id"]].append(r["pred_median"])
            truths[r["facility_id"]] = r["truth"]
            eus[r["facility_id"]] = r["eu_default"]

    # Aggregate
    agg = []
    for fid, preds in sorted(per_facility.items()):
        med = median(preds)
        agg.append({
            "facility_id": fid,
            "truth": truths[fid],
            "pred_median": med,
            "eu_default": eus[fid],
            "n_runs": len(preds),
            "preds_all": preds,
            "ratio_median": med / max(truths[fid], 1),
        })

    OUT.write_text(json.dumps(agg, indent=2))
    print()
    print("=" * 90)
    print(f"  Aggregated LODO ({N_OUTER} outer runs × 3 seeds = {N_OUTER*3} seeds per facility)")
    print("=" * 90)
    print(f"  {'facility':32s} {'truth':>14s} {'pred (med)':>14s} {'ratio':>6s} {'EU default':>14s} {'Δ EU':>6s}")
    print("-" * 90)
    model_log = []
    eu_log = []
    for r in agg:
        t, p, e = r["truth"], r["pred_median"], r["eu_default"]
        d_eu = (e - p) / e * 100
        print(f"  {r['facility_id']:32s} {t:>14,.0f} {p:>14,.0f} {r['ratio_median']:>5.2f}× {e:>14,.0f} {d_eu:>+5.0f}%")
        if t > 0 and p > 0 and e > 0:
            model_log.append(abs(math.log(p) - math.log(t)))
            eu_log.append(abs(math.log(e) - math.log(t)))
    print("-" * 90)
    if model_log:
        mm = sum(model_log) / len(model_log)
        em = sum(eu_log) / len(eu_log)
        red = (1 - mm / em) * 100
        print(f"  log-MAE  iz-1 {mm:.3f}  EU {em:.3f}  reduction {red:.1f}%  n={len(model_log)}")
    print("=" * 90)
    print(f"\nwrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
