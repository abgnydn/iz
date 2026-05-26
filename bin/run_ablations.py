"""
Ablation runner — quantifies what each component contributes.

Reads results from each LODO-aggregate run, builds a comparison table.
Uses N_OUTER=3 per variant (vs 5 for headline) to keep wall clock under 30 min.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "reports" / "ablations"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Each row: (name, env vars dict, description)
VARIANTS = [
    ("full",       {},                                        "Full iz-1 (route + disc_cf + ct + physics-informed prior)"),
    ("no_prior",   {"IZ_NO_PRIOR": "1"},                       "Prior off → train.js falls back to yMean offset"),
    ("no_disc",    {"IZ_NO_DISC_CF": "1"},                     "Disclosed-cf feature off (prior still uses CT/sector)"),
    ("no_route",   {"IZ_NO_ROUTE": "1"},                       "Steel route off → all steel uses TR_actual_EF 1.44"),
    ("no_ct",      {"IZ_NO_CT": "1"},                          "CT features off"),
    ("no_disc_no_route", {"IZ_NO_DISC_CF": "1", "IZ_NO_ROUTE": "1"}, "Both ablated → minimal feature set"),
]

N_OUTER = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def run_variant(name: str, env_vars: dict) -> dict:
    env = {**os.environ, **env_vars}
    out_file = OUT_DIR / f"lodo_{name}.json"
    print(f"\n{'='*80}\nVARIANT: {name}  {env_vars}\n{'='*80}")
    # Run the aggregator (which itself runs N_OUTER × 3 = 3N seeds per facility)
    subprocess.run(
        ["uv", "run", "python", "bin/e2e_lodo_aggregate.py", str(N_OUTER)],
        cwd=str(REPO), env=env, check=True,
    )
    # Copy the result
    src = REPO / "reports" / "lodo_aggregated.json"
    out_file.write_text(src.read_text())

    rows = json.loads(src.read_text())
    ml = [abs(math.log(r["pred_median"]) - math.log(r["truth"])) for r in rows if r["pred_median"] > 0]
    el = [abs(math.log(r["eu_default"]) - math.log(r["truth"])) for r in rows if r["eu_default"] > 0]
    # Per-sector
    sectors = {
        "cement": ["akcansa-buyukcekmece","akcansa-canakkale","akcansa-ladik","nuh-hereke"],
        "BF/BOF": ["erdemir-eregli","isdemir-iskenderun","kardemir-karabuk"],
        "EAF": ["colakoglu-gebze"],
    }
    sector_reductions = {}
    for sec, fids in sectors.items():
        rs = [r for r in rows if r["facility_id"] in fids]
        if not rs:
            continue
        mm = sum(abs(math.log(r["pred_median"]) - math.log(r["truth"])) for r in rs)/len(rs)
        em = sum(abs(math.log(r["eu_default"]) - math.log(r["truth"])) for r in rs)/len(rs)
        sector_reductions[sec] = (1 - mm/em) * 100 if em > 0 else 0
    overall = (1 - sum(ml)/len(ml) / (sum(el)/len(el))) * 100
    return {
        "name": name,
        "n": len(ml),
        "iz_log_mae": sum(ml)/len(ml),
        "eu_log_mae": sum(el)/len(el),
        "reduction": overall,
        "per_sector": sector_reductions,
    }


def main() -> None:
    results = []
    for name, env, _ in VARIANTS:
        results.append(run_variant(name, env))

    print()
    print("=" * 90)
    print(f"  ABLATION MATRIX  (n=8 LODO disclosure facilities, {N_OUTER} outer × 3 inner = {N_OUTER*3} seeds each)")
    print("=" * 90)
    header = f"  {'variant':22s} {'iz log-MAE':>11s} {'reduction':>10s}   {'cement':>9s} {'BF/BOF':>9s} {'EAF':>9s}"
    print(header)
    print("-" * 90)
    for r in results:
        sec = r["per_sector"]
        cm = sec.get("cement", float("nan"))
        bf = sec.get("BF/BOF", float("nan"))
        ef = sec.get("EAF", float("nan"))
        print(f"  {r['name']:22s} {r['iz_log_mae']:>11.3f} {r['reduction']:>9.1f}%   {cm:>+8.1f}% {bf:>+8.1f}% {ef:>+8.1f}%")
    print("=" * 90)
    (OUT_DIR / "summary.json").write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()
