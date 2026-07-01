#!/usr/bin/env bash
# Fetch every external dataset TR-MRV-Bench depends on, so a clean clone can
# reproduce the headline AND the verifiers offline afterwards.
#
# All sources are public and require no auth:
#   - Climate TRACE v6   (api.climatetrace.org)      -> reports/climate_trace_tr*.parquet
#   - EUTL / EU ETS      (euets.info public API)     -> data/eutl/*.parquet   (B6, B7)
#
# The fetched artifacts are committed to the repo as a pinned snapshot; this
# script only needs to be re-run to refresh them. Usage:
#
#   uv sync
#   bin/fetch_all_data.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-.venv/bin/python}"

echo "==> [1/2] Climate TRACE weak labels"
"$PY" bin/pull_climate_trace.py
"$PY" bin/pull_climate_trace_details.py

echo "==> [2/2] EUTL verified emissions (cement + steel + aluminum + fertilizer)"
"$PY" bin/pull_eutl_cement.py
for sector in steel aluminum fertilizer; do
  "$PY" bin/pull_eutl_sector.py "$sector"
done

echo
echo "==> Done. Fetched artifacts:"
ls -la reports/climate_trace_tr*.parquet data/eutl/*.parquet
echo
echo "Next: rebuild the bench and re-run the headline / verifiers:"
echo "  .venv/bin/python bin/export_bench_browser.py"
echo "  .venv/bin/python bin/verifier_b6_eutl_score.py"
