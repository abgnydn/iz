"""
Verifier B4 — Per-sector bootstrap CI on the formula's log-MAE reduction.

We have overall 85.3% with bootstrap CI [+72.0%, +90.6%] across n=21 LODO facilities.
This script computes the same metric per sector (cement, EAF steel, BF/BOF steel,
aluminum, fertilizer-integrated, fertilizer-N₂O, fertilizer-blender) with sector-
size-aware bootstrap.

A sector with n=1 (e.g., EAF, N₂O-controlled, blender) gets a flagged "single
facility, no bootstrap meaningful" entry. Where n≥3, real CIs.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
BASELINES = REPO / "reports" / "baselines.json"
OUT_DIR = REPO / "reports" / "verifiers"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / "b4_sector_bootstrap.json"
OUT_MD = OUT_DIR / "b4_sector_bootstrap.md"

SECTORS = {
    "cement":           ["akcansa-buyukcekmece","akcansa-canakkale","akcansa-ladik","nuh-hereke",
                         "afyon-cimento","batisoke-soke","goltas-isparta","bursa-cimento"],
    "steel-BF/BOF":     ["erdemir-eregli","isdemir-iskenderun","kardemir-karabuk"],
    "steel-EAF":        ["colakoglu-gebze","habas-aliaga","izdemir-aliaga"],
    "aluminum-downstream": ["assan-tuzla","asas-akyazi"],
    "fertilizer-integrated": ["toros-mersin","toros-samsun","toros-ceyhan"],
    "fertilizer-N2O":   ["bagfas-bandirma"],
    "fertilizer-blender": ["gubretas-izmit"],
}

N_BOOTSTRAP = 5000
RNG_SEED = 42


def main():
    rows = json.loads(BASELINES.read_text())
    by_fid = {r["facility_id"]: r for r in rows}

    random.seed(RNG_SEED)
    np.random.seed(RNG_SEED)

    out = {}
    for sec, fids in SECTORS.items():
        rs = [by_fid[f] for f in fids if f in by_fid]
        if not rs:
            continue
        ml = np.array([abs(math.log(r["B1_cf_formula"]) - math.log(r["truth"])) for r in rs])
        el = np.array([abs(math.log(r["B0_eu_default"]) - math.log(r["truth"])) for r in rs])
        red = (1 - ml.mean() / el.mean()) * 100 if el.mean() > 0 else float("nan")

        # Bootstrap: resample facility indices with replacement
        if len(rs) >= 2:
            boot_reds = []
            n = len(rs)
            idx = np.arange(n)
            for _ in range(N_BOOTSTRAP):
                samp = np.random.choice(idx, size=n, replace=True)
                m = ml[samp].mean()
                e = el[samp].mean()
                if e > 0:
                    boot_reds.append((1 - m / e) * 100)
            boot_reds = np.array(boot_reds)
            ci_lo, ci_hi = np.percentile(boot_reds, [2.5, 97.5])
            out[sec] = {
                "n": len(rs),
                "facilities": [r["facility_id"] for r in rs],
                "formula_log_mae": float(ml.mean()),
                "eu_log_mae": float(el.mean()),
                "reduction_pct": float(red),
                "ci_lo_pct": float(ci_lo),
                "ci_hi_pct": float(ci_hi),
                "n_bootstrap": N_BOOTSTRAP,
            }
        else:
            # Single facility — no bootstrap
            out[sec] = {
                "n": len(rs),
                "facilities": [r["facility_id"] for r in rs],
                "formula_log_mae": float(ml.mean()),
                "eu_log_mae": float(el.mean()),
                "reduction_pct": float(red),
                "ci_lo_pct": None,
                "ci_hi_pct": None,
                "n_bootstrap": 0,
                "note": "n=1 — bootstrap not meaningful",
            }

    OUT_JSON.write_text(json.dumps(out, indent=2))

    md = ["# Verifier B4 — Per-Sector Bootstrap CI\n"]
    md.append("*Resamples facility indices with replacement 5000× per sector. Reports the formula's log-MAE reduction vs EU default, with 95% CI from the bootstrap distribution.*\n")
    md.append("## Per-sector formula reduction (95% bootstrap CI)\n")
    md.append("| Sector | n | Formula log-MAE | EU log-MAE | Reduction | 95% CI |")
    md.append("|---|---|---|---|---|---|")
    for sec, d in out.items():
        if d["ci_lo_pct"] is not None:
            ci = f"[{d['ci_lo_pct']:+.1f}%, {d['ci_hi_pct']:+.1f}%]"
        else:
            ci = "n=1"
        md.append(f"| {sec} | {d['n']} | {d['formula_log_mae']:.3f} | {d['eu_log_mae']:.3f} | **{d['reduction_pct']:+.1f}%** | {ci} |")
    md.append("\n## What survives resampling\n")
    survives = [s for s, d in out.items() if d['ci_lo_pct'] is not None and d['ci_lo_pct'] > 0]
    fails = [s for s, d in out.items() if d['ci_lo_pct'] is not None and d['ci_lo_pct'] <= 0]
    md.append(f"**Sectors where the entire 95% CI is positive** (formula reliably beats EU): {', '.join(survives) if survives else 'none'}")
    md.append(f"\n**Sectors where the CI crosses zero** (formula advantage is not significant): {', '.join(fails) if fails else 'none'}")
    md.append(f"\n**Single-facility strata (no CI possible at n=1)**: " + ", ".join(s for s, d in out.items() if d['n'] == 1))

    OUT_MD.write_text("\n".join(md))
    print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print(f"wrote {OUT_MD.relative_to(REPO)}")
    print()
    for sec, d in out.items():
        ci = f"[{d['ci_lo_pct']:+.1f}, {d['ci_hi_pct']:+.1f}]" if d['ci_lo_pct'] is not None else "n=1"
        print(f"  {sec:24s} n={d['n']}  reduction {d['reduction_pct']:+6.1f}%  CI {ci}")


if __name__ == "__main__":
    main()
