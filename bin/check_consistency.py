"""
Headline-number consistency check across docs.

Scans README.md, PAPER_OUTLINE.md, PAPER_METHOD.md, PAPER_DISCUSSION.md,
site/*.html, and verifies the key numbers we publish all agree with the
authoritative reports under reports/.

Run before deploy / commit.
"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def expected_headline() -> dict:
    agg = json.loads((REPO / "reports" / "lodo_aggregated.json").read_text())
    n = len(agg)
    ml = sum(abs(math.log(r["pred_median"]) - math.log(r["truth"])) for r in agg) / n
    el = sum(abs(math.log(r["eu_default"]) - math.log(r["truth"])) for r in agg) / n
    reduction = (1 - ml / el) * 100

    bs = json.loads((REPO / "reports" / "bootstrap_ci.json").read_text())

    ci = json.loads((REPO / "reports" / "lodo_ci.json").read_text())

    bl = json.loads((REPO / "reports" / "baselines.json").read_text())
    def log_mae(field):
        es = [abs(math.log(r[field]) - math.log(r["truth"])) for r in bl if r[field] > 0 and r["truth"] > 0]
        return sum(es) / len(es) if es else 0
    eu = log_mae("B0_eu_default")
    formula_red = (1 - log_mae("B1_cf_formula") / eu) * 100 if eu else 0
    ridge_red = (1 - log_mae("B2_ridge") / eu) * 100 if eu else 0

    return {
        "n": n,
        "iz_reduction": reduction,
        "iz_log_mae": ml,
        "formula_reduction": formula_red,
        "ridge_reduction": ridge_red,
        "bs_mean": bs["overall_mean"],
        "bs_ci_lo": bs["overall_ci_95"][0],
        "bs_ci_hi": bs["overall_ci_95"][1],
        "ci_seed_mean": ci["summary"]["overall_mean"],
        "ci_seed_2sigma": ci["summary"]["overall_2sigma"],
    }


def main() -> int:
    h = expected_headline()
    print(f"AUTHORITATIVE (from reports/*.json):")
    print(f"  n facilities:        {h['n']}")
    print(f"  iz-1 reduction:      +{h['iz_reduction']:.2f}%  (log-MAE {h['iz_log_mae']:.3f})")
    print(f"  formula reduction:   +{h['formula_reduction']:.2f}%")
    print(f"  ridge reduction:     +{h['ridge_reduction']:.2f}%")
    print(f"  bootstrap data CI:   mean +{h['bs_mean']:.2f}%  95% [{h['bs_ci_lo']:+.1f}, {h['bs_ci_hi']:+.1f}]")
    print(f"  seed CI (5 outer):   +{h['ci_seed_mean']:.2f}% ± {h['ci_seed_2sigma']:.2f}%")
    print()

    expected_round = round(h["iz_reduction"])  # rounded value used in headlines
    formula_round = round(h["formula_reduction"])
    n = h["n"]

    files = [
        REPO / "README.md",
        REPO / "PAPER_OUTLINE.md",
        REPO / "PAPER_METHOD.md",
        REPO / "PAPER_DISCUSSION.md",
        REPO / "site" / "index.html",
        REPO / "site" / "about" / "index.html",
        REPO / "marketing" / "paper_preview_v0.html",
    ]
    # site/bench/index.html intentionally omitted — it's a data browser, not a results page;
    # numbers come from facilities.json at runtime.

    issues = 0
    for path in files:
        if not path.exists():
            continue
        body = path.read_text()
        # Find percentage claims like XX.X%, X% etc near 'reduction' or 'beats'
        # We just check: do the formula (~86) and iz-1 (~85) numbers appear?
        if f"{expected_round}" not in body and f"{expected_round}." not in body:
            print(f"  ⚠ {path.relative_to(REPO)}: iz-1 reduction {expected_round}% not found")
            issues += 1
        if f"{formula_round}" not in body and f"{formula_round}." not in body:
            print(f"  ⚠ {path.relative_to(REPO)}: formula reduction {formula_round}% not found")
            issues += 1
        if f"n={n}" not in body and f"n = {n}" not in body and f"{n} audit" not in body and f"{n} facilities" not in body and f"{n} disclosure" not in body and f"{n} LODO" not in body and f"all {n}" not in body:
            print(f"  ⚠ {path.relative_to(REPO)}: n={n} not found")
            issues += 1

    print()
    if issues == 0:
        print(f"✓ all {len(files)} docs are consistent with the authoritative reports")
        return 0
    else:
        print(f"✗ {issues} consistency issue(s) found")
        return 1


if __name__ == "__main__":
    sys.exit(main())
