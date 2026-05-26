"""
LODO with bootstrap confidence intervals.

Runs N outer LODO passes, each with 3 inner seeds. Reports per-outer-run
log-MAE reductions, then computes mean ± 2σ across outer runs (≈ 95% CI).
Distinct from e2e_lodo_aggregate which only takes per-facility median;
this script preserves per-run variance for honest CI reporting.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path
from statistics import mean, stdev

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "reports" / "lodo_results.json"
OUT = REPO / "reports" / "lodo_ci.json"

N_OUTER = int(sys.argv[1]) if len(sys.argv) > 1 else 8


def main() -> None:
    per_run_reductions = []
    per_run_per_sector = {"cement": [], "BF/BOF": [], "EAF": []}

    env = {**os.environ, "IZ_NO_CT": "1"}

    sectors = {
        "cement": ["akcansa-buyukcekmece","akcansa-canakkale","akcansa-ladik","nuh-hereke"],
        "BF/BOF": ["erdemir-eregli","isdemir-iskenderun","kardemir-karabuk"],
        "EAF": ["colakoglu-gebze"],
    }

    for i in range(N_OUTER):
        print(f"\n=== outer run {i+1}/{N_OUTER} ===")
        subprocess.run(["uv", "run", "python", "bin/e2e_lodo.py"], cwd=str(REPO), env=env, check=True)
        rows = json.loads(RESULTS.read_text())
        ml = [abs(math.log(r["pred_median"]) - math.log(r["truth"])) for r in rows]
        el = [abs(math.log(r["eu_default"]) - math.log(r["truth"])) for r in rows]
        red = (1 - sum(ml)/len(ml) / (sum(el)/len(el))) * 100
        per_run_reductions.append(red)
        print(f"  overall: {red:.2f}%")
        for sec, fids in sectors.items():
            rs = [r for r in rows if r["facility_id"] in fids]
            mm = sum(abs(math.log(r["pred_median"]) - math.log(r["truth"])) for r in rs)/len(rs)
            em = sum(abs(math.log(r["eu_default"]) - math.log(r["truth"])) for r in rs)/len(rs)
            r_sec = (1 - mm/em) * 100
            per_run_per_sector[sec].append(r_sec)
            print(f"  {sec:7s}: {r_sec:+.2f}%")

    def fmt(vals):
        m = mean(vals); s = stdev(vals) if len(vals) > 1 else 0
        return f"{m:+.1f}% ± {2*s:.1f} (n={len(vals)}, range {min(vals):+.1f} to {max(vals):+.1f})"

    print("\n" + "=" * 80)
    print(f"  {N_OUTER}-run summary (each = 3-seed median across 8 LODO holdouts)")
    print("=" * 80)
    print(f"  overall:   {fmt(per_run_reductions)}")
    for sec, vals in per_run_per_sector.items():
        print(f"  {sec:9s}: {fmt(vals)}")
    print("=" * 80)

    OUT.write_text(json.dumps({
        "n_outer": N_OUTER,
        "overall": per_run_reductions,
        "per_sector": per_run_per_sector,
        "summary": {
            "overall_mean": mean(per_run_reductions),
            "overall_2sigma": 2 * stdev(per_run_reductions) if len(per_run_reductions) > 1 else 0,
        },
    }, indent=2))
    print(f"\nwrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
