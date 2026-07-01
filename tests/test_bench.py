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
    bench = json.loads((REPO / "src" / "iz" / "bench.json").read_text())
    samples = bench["samples"]
    assert len(samples) >= 50, "expected ~59 samples"
    by_source = {}
    for s in samples:
        by_source[s["label_source"]] = by_source.get(s["label_source"], 0) + 1
    assert by_source.get("disclosure", 0) >= 18, "expected ≥18 disclosure-labeled rows"


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
    bench = json.loads((REPO / "src" / "iz" / "bench.json").read_text())
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


def test_facility_pages_exist() -> None:
    """Each row in facilities.json should have a generated detail page + audit summary."""
    fac_json = REPO / "site" / "bench" / "facilities.json"
    if not fac_json.exists():
        pytest.skip("no site/bench/facilities.json (run bin/build_facilities_json.py first)")
    facs = json.loads(fac_json.read_text())
    missing_detail = []
    missing_summary = []
    for f in facs:
        detail = REPO / "site" / "bench" / f["id"] / "index.html"
        summary = REPO / "site" / "bench" / f["id"] / "audit-summary" / "index.html"
        if not detail.exists():
            missing_detail.append(f["id"])
        if not summary.exists():
            missing_summary.append(f["id"])
    if missing_detail or missing_summary:
        pytest.skip(
            f"detail pages not generated yet (run bin/build_facility_pages.py): "
            f"missing {len(missing_detail)} details, {len(missing_summary)} summaries"
        )
    # Spot check one for required content
    sample = json.loads(fac_json.read_text())[0]
    detail = (REPO / "site" / "bench" / sample["id"] / "index.html").read_text()
    summary = (REPO / "site" / "bench" / sample["id"] / "audit-summary" / "index.html").read_text()
    assert sample["plant"] in detail
    assert sample["company"] in detail
    assert "audit-summary" in detail, "detail page must link to its audit summary"
    assert "Verifier checklist" in summary
    assert sample["plant"] in summary
    assert "TR-MRV-Bench" in summary


def test_log_mae_calculation_consistent() -> None:
    """Verify the HEADLINE (cf-corrected formula, leave-one-plant-out) reduction is
    reproducible and in range. The headline is the formula, not the iz demo net —
    so this checks reports/lopo_ef_eval.json (deterministic), produced by
    bin/lopo_ef_eval.py."""
    path = REPO / "reports" / "lopo_ef_eval.json"
    if not path.exists():
        pytest.skip("no lopo_ef_eval.json (run bin/lopo_ef_eval.py first)")
    d = json.loads(path.read_text())
    rows = [r for r in d["per_plant"] if r.get("ratio_lopo") is not None]
    # Exactly the validatable plants; single-plant strata are excluded, not scored.
    assert d["n_predictable"] == len(rows) >= 15
    ml = sum(abs(math.log(r["ratio_lopo"] * r["truth"]) - math.log(r["truth"])) for r in rows) / len(rows)
    el = sum(abs(math.log(r["eu_default"]) - math.log(r["truth"])) for r in rows) / len(rows)
    reduction = (1 - ml / el) * 100
    assert abs(reduction - d["reduction_lopo_predictable"]) < 0.5, "reduction not reproducible from rows"
    # Should be in the +75% to +90% range; well outside this means something is wrong
    assert 75 < reduction < 90, f"honest LOPO reduction {reduction:.1f}% outside expected range"
