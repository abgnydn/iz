"""
Minimal sanity tests for the bench export + facility build.

Run with: .venv/bin/python -m pytest tests/

These tests don't drive the WebGPU model — that requires Playwright + a
running HTTP server. They check the static data artifacts and the
formula-side invariants that should hold every time.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent


def test_facilities_csv_loads() -> None:
    df = pd.read_csv(REPO / "data" / "tr_facilities.csv")
    assert len(df) >= 57, "expected at least 57 facilities in tr_facilities.csv"
    assert df["id"].is_unique, "facility ids must be unique"
    assert df["annual_capacity_t"].min() > 0
    assert set(df["cbam_scope"].unique()).issubset({"cement", "steel", "aluminum", "fertilizer"})


def test_known_emissions_csv_loads() -> None:
    df = pd.read_csv(REPO / "data" / "tr_facility_known_emissions.csv")
    assert "provenance" in df.columns
    assert {"direct", "allocated", "derived", "disputed"} & set(df["provenance"].dropna().unique())
    # Every per-plant scope1 row should have an associated facility id
    fac = pd.read_csv(REPO / "data" / "tr_facilities.csv")
    pp = df[df["metric"].isin(["co2_scope1_t", "co2_scope12_total_t"])]
    pp_ids = set(pp["id"]) - {"tr-cement-industry", "akcansa-group"}
    missing = pp_ids - set(fac["id"])
    assert not missing, f"per-plant emission rows reference unknown facilities: {missing}"


def test_disclosed_cf_in_range() -> None:
    """Every disclosed cf must be a real production ratio in [0, 1.2]."""
    import bin.export_bench_browser as eb  # type: ignore
    for fid, cf in eb.DISCLOSED_CF.items():
        assert 0 < cf < 1.2, f"disclosed cf for {fid} out of range: {cf}"


def test_route_maps_cover_strata() -> None:
    import bin.export_bench_browser as eb  # type: ignore
    assert "BF/BOF" in eb.STEEL_ROUTE_EF
    assert "EAF" in eb.STEEL_ROUTE_EF
    assert eb.STEEL_ROUTE_EF["BF/BOF"] > eb.STEEL_ROUTE_EF["EAF"], "BF/BOF EF must exceed EAF"
    assert eb.ALU_ROUTE_EF["primary"] > eb.ALU_ROUTE_EF["downstream"] * 5, "primary Al must be ~10× downstream"
    assert eb.FERT_ROUTE_EF["integrated"] > eb.FERT_ROUTE_EF["integrated-n2o-controlled"] * 5


def test_bench_json_is_complete() -> None:
    bench = json.loads((REPO / "src" / "iz_browser" / "bench.json").read_text())
    samples = bench["samples"]
    assert len(samples) >= 50, "expected ~59 samples"
    by_source = {}
    for s in samples:
        by_source[s["label_source"]] = by_source.get(s["label_source"], 0) + 1
    assert by_source.get("disclosure", 0) >= 18, "expected ≥18 disclosure-labeled rows"


def test_lodo_results_when_present() -> None:
    path = REPO / "reports" / "lodo_results.json"
    if not path.exists():
        pytest.skip("no lodo_results.json (run bin/e2e_lodo.py first)")
    rows = json.loads(path.read_text())
    assert len(rows) >= 18, f"expected ≥18 LODO holdouts, got {len(rows)}"
    for r in rows:
        assert r["truth"] > 0
        assert r["pred_median"] > 0
        assert r["eu_default"] > 0
        # No prediction should be wildly off across orders of magnitude
        ratio = r["pred_median"] / r["truth"]
        assert 0.05 < ratio < 20, f"{r['facility_id']} prediction implausible: {ratio:.2f}× truth"


def test_facilities_json_for_site() -> None:
    path = REPO / "site" / "bench" / "facilities.json"
    if not path.exists():
        pytest.skip("no site/bench/facilities.json (run bin/build_facilities_json.py first)")
    rows = json.loads(path.read_text())
    assert len(rows) >= 57
    n_truth = sum(1 for r in rows if r["truth"] is not None and r.get("truth_src"))
    assert n_truth >= 18
    # All disclosure rows should have an assurance tier
    for r in rows:
        if r.get("truth_src"):
            assert r.get("assurance") in {"iso14064", "tsrs_assured", "operator_audited", None}


def test_eu_defaults_in_bench() -> None:
    """EU defaults should be capacity × the canonical default EF (no facility-specific tuning)."""
    bench = json.loads((REPO / "src" / "iz_browser" / "bench.json").read_text())
    fac = pd.read_csv(REPO / "data" / "tr_facilities.csv").set_index("id")
    EU_DEFAULT_EF = {"cement": 1.584, "steel": 1.900, "aluminum": 1.500, "fertilizer": 0.800}
    for s in bench["samples"]:
        cap = fac.loc[s["id"], "annual_capacity_t"]
        scope = fac.loc[s["id"], "cbam_scope"]
        expected = cap * EU_DEFAULT_EF[scope]
        actual = s["eu_default"]
        assert abs(actual - expected) / expected < 1e-6, (
            f"{s['id']} EU default mismatch: bench={actual}, computed={expected}"
        )


def test_log_mae_calculation_consistent() -> None:
    """Verify the headline reduction number is reproducible from the raw rows."""
    path = REPO / "reports" / "lodo_results.json"
    if not path.exists():
        pytest.skip("no lodo_results.json")
    rows = json.loads(path.read_text())
    ml = sum(abs(math.log(r["pred_median"]) - math.log(r["truth"])) for r in rows) / len(rows)
    el = sum(abs(math.log(r["eu_default"]) - math.log(r["truth"])) for r in rows) / len(rows)
    reduction = (1 - ml / el) * 100
    # Should be in the +75% to +90% range; well outside this means something is wrong
    assert 70 < reduction < 95, f"reduction {reduction:.1f}% outside expected range"
