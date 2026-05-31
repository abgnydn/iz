"""
C5 — Annual refresh pipeline.

When operators publish their previous-year IARs (typically March-April), this
script:
  1. Re-pulls Climate TRACE per-asset details
  2. Re-runs disclosure URL freshness check
  3. Re-runs all 5 fusion analyses
  4. Re-runs all verifiers
  5. Re-builds the static JSON API
  6. Re-runs the headline LODO with refreshed bench

Designed to be invoked by cron:
    0 2 1 4 *    cd ~/iz && uv run python bin/annual_refresh.py

(02:00 on April 1 each year — gives ~6-8 weeks after TR IAR publication peak.)
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

STEPS = [
    # (label, command)
    ("Climate TRACE refresh", ["uv", "run", "python", "bin/pull_climate_trace_details.py"]),
    ("Build bench JSON",       ["uv", "run", "python", "bin/export_bench_browser.py"]),
    ("Build API",              ["uv", "run", "python", "bin/build_api.py"]),
    ("Run baselines",          ["uv", "run", "python", "bin/baselines.py"]),
    ("Subset metrics",         ["uv", "run", "python", "bin/subset_metrics.py"]),
    ("Fusion #1 — CBAM",       ["uv", "run", "python", "bin/fusion_1_cbam_exposure.py"]),
    ("Fusion #2 — TR-ETS",     ["uv", "run", "python", "bin/fusion_2_trets.py"]),
    ("Fusion #3 — KAP",        ["uv", "run", "python", "bin/fusion_3_kap_financials.py"]),
    ("Fusion #4 — Health",     ["uv", "run", "python", "bin/fusion_4_health_nox.py"]),
    ("Fusion #5 — ESG",        ["uv", "run", "python", "bin/fusion_5_esg.py"]),
    ("Fusion A1 — Scope 2",    ["uv", "run", "python", "bin/fusion_a1_scope2.py"]),
    ("Fusion A3 — Verifier x", ["uv", "run", "python", "bin/fusion_a3_verifier_crosscheck.py"]),
    ("Verifier B1 — multiyear",["uv", "run", "python", "bin/verifier_b1_multiyear.py"]),
    ("Verifier B4 — bootstrap",["uv", "run", "python", "bin/verifier_b4_sector_bootstrap.py"]),
    ("EUTL B6 pull",           ["uv", "run", "python", "bin/pull_eutl_cement.py"]),
    ("EUTL B6 score",          ["uv", "run", "python", "bin/verifier_b6_eutl_score.py"]),
    ("Headline LODO",          ["uv", "run", "python", "bin/e2e_lodo_aggregate.py", "5"]),
    ("Regenerate figure",      ["uv", "run", "python", "bin/figure_lodo.py"]),
]


def main():
    failed = []
    started = time.time()
    for label, cmd in STEPS:
        print(f"\n=== {label} ===", flush=True)
        try:
            subprocess.run(cmd, cwd=str(REPO), check=True)
        except subprocess.CalledProcessError as e:
            print(f"  ❌ failed: code {e.returncode}", flush=True)
            failed.append(label)
    elapsed = time.time() - started
    print(f"\n{'='*60}")
    print(f"  Refresh complete in {elapsed/60:.1f} min")
    if failed:
        print(f"  Failures: {failed}")
        sys.exit(1)
    print(f"  All steps OK.")


if __name__ == "__main__":
    main()
