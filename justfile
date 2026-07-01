# TR-MRV-Bench / iz — task runner.  `just` to list, `just <target>` to run.
# The headline path is pure Python: no browser, no GPU.

set shell := ["bash", "-cu"]

default:
    @just --list

# Install deps
sync:
    uv sync

# Refresh all external data from source (Climate TRACE + EUTL). Committed by default.
fetch-data:
    bin/fetch_all_data.sh

# Rebuild the bench + public artifacts from committed data
build:
    uv run python bin/export_bench_browser.py
    uv run python bin/build_facilities_json.py
    uv run python bin/build_facility_pages.py

# The honest headline: leave-one-plant-out EF (+82.3%, n=19) + baselines + B6
repro:
    uv run python bin/lopo_ef_eval.py
    uv run python bin/baselines.py
    uv run python bin/verifier_b6_eutl_score.py

# Sanity tests (no browser/GPU)
test:
    uv run --with pytest python -m pytest tests/ -q

# Deploy site to Cloudflare Pages (only for direct-upload/preview; Git-connected auto-deploys on merge)
deploy:
    wrangler pages deploy site --project-name iz-b0n

# Everything a clean clone needs to reproduce the headline
all: sync build repro test
