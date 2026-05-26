"""
Baselines for iz-1 v0 comparison.

Three baselines on the same n=8 LODO split:
  B0  EU CBAM default               = capacity × EU_DEFAULT_EF
  B1  cf_corrected formula (no ML)  = capacity × EF × cf   (the physics prior alone)
  B2  Ridge regression (linear ML)  = same features as iz-1, scikit-learn ridge

Outputs per-facility predictions + log-MAE for each. Lets us isolate iz-1's
actual contribution from "the formula already does most of the work" (#15) and
"any ML model would beat the EU default" (#20).
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
BENCH = REPO / "src" / "iz_browser" / "bench.json"
LODO = REPO / "reports" / "lodo_aggregated.json"
OUT = REPO / "reports" / "baselines.json"


def export_bench(holdout: str = "") -> dict:
    env = {**os.environ, "IZ_HOLDOUT": holdout, "IZ_NO_CT": "1"}
    subprocess.run(
        ["uv", "run", "python", "bin/export_bench_browser.py"],
        cwd=str(REPO), env=env, check=True, capture_output=True,
    )
    return json.loads(BENCH.read_text())


def disclosure_facilities() -> list[tuple[str, float]]:
    kn = pd.read_csv(REPO / "data" / "tr_facility_known_emissions.csv")
    pp = kn[kn["metric"] == "co2_scope1_t"].copy()
    pp["year"] = pd.to_numeric(pp["year"], errors="coerce")
    pp = pp.sort_values("year", ascending=False).drop_duplicates("id")
    return sorted([(r["id"], float(r["value"])) for _, r in pp.iterrows()])


def ridge_fit_predict(X_train: np.ndarray, y_train: np.ndarray, w_train: np.ndarray, X_test: np.ndarray, alpha: float = 1.0) -> float:
    """Weighted ridge regression in closed form: w = (X^T W X + αI)^-1 X^T W y."""
    W = np.diag(w_train)
    XtWX = X_train.T @ W @ X_train
    XtWy = X_train.T @ W @ y_train
    coef = np.linalg.solve(XtWX + alpha * np.eye(X_train.shape[1]), XtWy)
    return float(X_test @ coef)


def main() -> None:
    discs = disclosure_facilities()
    print(f"Computing baselines over {len(discs)} disclosure facilities (LODO)")
    print("=" * 90)

    rows_out = []
    for fid, truth in discs:
        # Re-export bench with this facility forced into test
        bench = export_bench(holdout=fid)
        samples = bench["samples"]
        feat_mean = np.array(bench["schema"]["feat_mean"])
        feat_std = np.array(bench["schema"]["feat_std"])

        # B0: EU default
        test_sample = next(s for s in samples if s["id"] == fid)
        eu = test_sample["eu_default"]

        # B1: cf_corrected formula alone — exposed as `y_prior` per sample
        b1 = test_sample.get("y_prior", 0.0)

        # B2: Ridge on full feature vector, residual against y_prior_log (same as iz-1 training target)
        train = [s for s in samples if s["split"] == "train"]
        X_tr = np.array([s["feat"] for s in train], dtype=np.float64)
        X_tr = (X_tr - feat_mean) / feat_std
        # Augment with bias column
        X_tr = np.hstack([X_tr, np.ones((len(X_tr), 1))])
        y_log_tr = np.array([s["y_log"] for s in train], dtype=np.float64)
        prior_log_tr = np.array([s.get("y_prior_log", y_log_tr.mean()) for s in train], dtype=np.float64)
        w_tr = np.array([s["w"] for s in train], dtype=np.float64)
        resid_tr = y_log_tr - prior_log_tr

        X_te = (np.array(test_sample["feat"], dtype=np.float64) - feat_mean) / feat_std
        X_te = np.concatenate([X_te, [1.0]])
        residual_pred = ridge_fit_predict(X_tr, resid_tr, w_tr, X_te, alpha=1.0)
        b2_log = test_sample["y_prior_log"] + residual_pred
        b2 = math.expm1(b2_log)

        rows_out.append({
            "facility_id": fid,
            "truth": truth,
            "B0_eu_default": eu,
            "B1_cf_formula": b1,
            "B2_ridge": b2,
        })
        print(f"  {fid:32s} truth {truth:>12,.0f}  EU {eu:>12,.0f}  formula {b1:>12,.0f}  ridge {b2:>12,.0f}")

    OUT.write_text(json.dumps(rows_out, indent=2))

    # Aggregate
    def log_mae(field: str) -> float:
        errs = [abs(math.log(r[field]) - math.log(r["truth"])) for r in rows_out if r[field] > 0 and r["truth"] > 0]
        return sum(errs) / len(errs)

    # Pull iz-1 predictions from aggregated LODO
    iz_rows = json.loads(LODO.read_text())
    iz_by_fid = {r["facility_id"]: r["pred_median"] for r in iz_rows}
    iz_errs = [abs(math.log(iz_by_fid[r["facility_id"]]) - math.log(r["truth"])) for r in rows_out if r["facility_id"] in iz_by_fid]
    iz_mae = sum(iz_errs) / len(iz_errs)

    print()
    print("=" * 90)
    print(f"  {'baseline':32s} {'log-MAE':>10s} {'reduction vs EU':>17s}")
    print("-" * 90)
    eu_mae = log_mae("B0_eu_default")
    for name, mae in [
        ("B0  EU CBAM default",    eu_mae),
        ("B1  cf_corrected formula", log_mae("B1_cf_formula")),
        ("B2  Ridge regression",   log_mae("B2_ridge")),
        ("    iz-1 (15 seeds, no CT)", iz_mae),
    ]:
        red = (1 - mae / eu_mae) * 100 if eu_mae > 0 else 0
        print(f"  {name:32s} {mae:>10.3f} {red:>15.1f}%")
    print("=" * 90)
    print(f"\nwrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
