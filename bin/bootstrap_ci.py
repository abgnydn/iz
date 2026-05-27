"""
Bootstrap data-variance CI on the n=20 LODO headline.

The 5-outer × 3-inner CI gives us *seed* variance: how much does the
prediction change if we re-train? That number was ±0.3%.

This script computes *data* variance: how much does the headline change
if we held out a different sample of facilities? We bootstrap-resample
the 20 facilities (with replacement) 1000 times, compute the reduction
for each resample, and report mean + 2.5/97.5 percentile.

If the data CI is also tight, the headline is robust to facility choice.
If the data CI is wide, the headline depends heavily on the specific
20 facilities we found.
"""
from __future__ import annotations
import json
import math
import random
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AGG = REPO / "reports" / "lodo_aggregated.json"

N_BOOTSTRAP = 5000
SEED = 42


def main() -> None:
    rows = json.loads(AGG.read_text())
    n = len(rows)
    if n < 5:
        print("not enough rows")
        return

    # Cache per-row log-error pairs
    pairs = []
    for r in rows:
        if r["truth"] > 0 and r["pred_median"] > 0 and r["eu_default"] > 0:
            ml = abs(math.log(r["pred_median"]) - math.log(r["truth"]))
            el = abs(math.log(r["eu_default"]) - math.log(r["truth"]))
            pairs.append((ml, el, r["facility_id"]))

    print(f"data points: {len(pairs)}")
    print()

    rng = random.Random(SEED)
    reductions = []
    for _ in range(N_BOOTSTRAP):
        sample = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        mm = sum(p[0] for p in sample) / len(sample)
        em = sum(p[1] for p in sample) / len(sample)
        reductions.append((1 - mm / em) * 100)

    reductions.sort()
    mean = sum(reductions) / len(reductions)
    p025 = reductions[int(0.025 * len(reductions))]
    p975 = reductions[int(0.975 * len(reductions))]
    p50 = reductions[int(0.5 * len(reductions))]
    p05 = reductions[int(0.05 * len(reductions))]
    p95 = reductions[int(0.95 * len(reductions))]

    # Per-stratum bootstrap too
    strata = {
        "cement": ["akcansa-buyukcekmece", "akcansa-canakkale", "akcansa-ladik", "nuh-hereke",
                   "afyon-cimento", "batisoke-soke", "goltas-isparta"],
        "BF/BOF": ["erdemir-eregli", "isdemir-iskenderun", "kardemir-karabuk"],
        "EAF":    ["colakoglu-gebze", "habas-aliaga", "izdemir-aliaga"],
        "aluminum-dnstm": ["assan-tuzla", "asas-akyazi"],
        "fertilizer": ["toros-mersin", "toros-samsun", "toros-ceyhan",
                       "bagfas-bandirma", "gubretas-izmit"],
    }
    by_stratum = {s: [p for p in pairs if p[2] in fids] for s, fids in strata.items()}

    print("Overall (data bootstrap, n={n} facilities, {b} resamples)".format(n=len(pairs), b=N_BOOTSTRAP))
    print(f"  mean reduction:        +{mean:.2f}%")
    print(f"  median:                +{p50:.2f}%")
    print(f"  90% CI (5th–95th):     +{p05:.1f}% to +{p95:.1f}%")
    print(f"  95% CI (2.5–97.5th):   +{p025:.1f}% to +{p975:.1f}%")
    print()
    print("Per stratum:")
    for s, p in by_stratum.items():
        if len(p) < 2:
            print(f"  {s:18s} n={len(p)} — skipped (need ≥2 for resampling)")
            continue
        reds = []
        for _ in range(N_BOOTSTRAP):
            sample = [p[rng.randrange(len(p))] for _ in range(len(p))]
            mm = sum(x[0] for x in sample) / len(sample)
            em = sum(x[1] for x in sample) / len(sample)
            if em > 0:
                reds.append((1 - mm / em) * 100)
        reds.sort()
        rm = sum(reds) / len(reds)
        rp025 = reds[int(0.025 * len(reds))]
        rp975 = reds[int(0.975 * len(reds))]
        print(f"  {s:18s} n={len(p)} mean +{rm:6.1f}%  95% CI [{rp025:+6.1f}, {rp975:+6.1f}]")

    OUT = REPO / "reports" / "bootstrap_ci.json"
    OUT.write_text(json.dumps({
        "n_bootstrap": N_BOOTSTRAP,
        "n_facilities": len(pairs),
        "seed": SEED,
        "overall_mean": mean,
        "overall_ci_95": [p025, p975],
        "overall_ci_90": [p05, p95],
    }, indent=2))
    print(f"\nwrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
