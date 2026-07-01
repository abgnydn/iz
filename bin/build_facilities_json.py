"""
Builds site/bench/facilities.json for the public bench browser.

Joins:
 - data/tr_facilities.csv          (facility identity + capacity)
 - data/tr_facility_known_emissions.csv  (disclosure rows)
 - src/iz/bench.json       (per-sample features + cf_corrected labels + eu_default)
 - reports/lodo_aggregated.json    (per-facility median prediction across N outer runs, when present)

Per-row fields emitted:
 - id, company, plant, sector, city, capacity
 - truth, truth_year, truth_src, provenance, label_source
 - assurance (one of: iso14064 / tsrs_assured / operator_audited / derived / disputed / "")
 - notes (operator-side caveats e.g. Habaş plate mill split)
 - eu_default
 - pred_median, pred_range (from lodo_aggregated.json if facility is in disclosure leave-one-plant-out set)

The bench browser uses these fields directly.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAC = REPO / "data" / "tr_facilities.csv"
KNOWN = REPO / "data" / "tr_facility_known_emissions.csv"
BENCH = REPO / "src" / "iz" / "bench.json"
AGG = REPO / "reports" / "lodo_aggregated.json"
LOPO = REPO / "reports" / "lopo_ef_eval.json"
OUT = REPO / "site" / "bench" / "facilities.json"

PER_PLANT_METRICS = ("co2_scope1_t", "co2_scope12_total_t")


def classify_assurance(source: str, notes: str) -> str:
    """Best-effort tier classification from the source + notes text."""
    txt = f"{source} {notes}".lower()
    if "iso 14064" in txt or "iso14064" in txt:
        return "iso14064"
    if "mrv" in txt and "verified" in txt:
        return "iso14064"  # equivalent rigor for the BAGFAŞ N2O case
    if "tsrs" in txt or "kgk-verified" in txt or "kgk verified" in txt:
        return "tsrs_assured"
    return "operator_audited"


# Per-facility human notes that override / augment the CSV's notes column.
# These surface specific caveats a careful reviewer should know.
FACILITY_OVERRIDE_NOTES: dict[str, str] = {
    "habas-aliaga": (
        "EAF main line only (Çelikhane + Çubuk Haddehanesi). "
        "Habaş also operates a plate mill at the same site with separate Scope 1 = 193,961 (2024). "
        "If treating as 'Habaş Aliağa total,' add 193,961."
    ),
    "bagfas-bandirma": (
        "2024 was a partial-capacity year for BAGFAŞ (cf=0.29). "
        "An average-utilization year would push Scope 1 ~3× higher. "
        "N₂O catalyst installed 2015 cuts ~80% of nitric-acid process N₂O."
    ),
    "gubretas-izmit": (
        "Yarımca is a BLENDING/granulation facility — no NH₃ or urea process emissions. "
        "Fuel + refrigerant only. Do NOT use as a benchmark for integrated fertilizer plants."
    ),
    "tosyali-osmaniye": (
        "Disputed: Tosyalı Holding 2022 = 424,901 tCO₂ for ~5M t/yr capacity is implausibly low. "
        "Likely a scope-narrowing (Turkey-only vs Türkiye+Africa) — see Tosyalı 2021/22 SRs. "
        "Excluded from the leave-one-plant-out test set."
    ),
    "assan-tuzla": (
        "Combined Tuzla + Dilovası sites. Downstream rolling/foil only — no Hall-Héroult smelting. "
        "EF 0.379 t/t Al is ~23× lower than EU CBAM default 8.6 (calibrated for primary smelters)."
    ),
    "akcansa-buyukcekmece": (
        "Allocated from Akçansa 2025 group Scope 1 (5,484,015) × Büyükçekmece clinker share 27.6%. "
        "Group total is audit-grade; per-plant split is by disclosed clinker tonnage, not directly disclosed."
    ),
    "akcansa-canakkale": (
        "Allocated from Akçansa 2025 group × clinker share 63.2%. See Büyükçekmece note."
    ),
    "akcansa-ladik": (
        "Allocated from Akçansa 2025 group × clinker share 9.1%. See Büyükçekmece note."
    ),
    "toros-mersin": (
        "Allocated from Toros group (842,174) by NAMEPLATE CAPACITY share (45.5%). "
        "Mersin has the NH₃+urea line — likely process-heavier than capacity-share allocation reflects. "
        "Medium-confidence label."
    ),
    "toros-samsun": "Allocated from Toros group by capacity share 30.3%. NPK/CAN — less process-heavy.",
    "toros-ceyhan": "Allocated from Toros group by capacity share 24.2%. AN/CAN.",
}


def main() -> None:
    fac_rows = list(csv.DictReader(open(FAC)))
    known_rows = list(csv.DictReader(open(KNOWN)))
    bench = json.loads(BENCH.read_text())
    bench_by_id = {s["id"]: s for s in bench["samples"]}

    # Latest-year per-plant Scope 1 per id
    pp = [r for r in known_rows if r["metric"] in PER_PLANT_METRICS]
    pp.sort(key=lambda r: (r["id"], r["metric"], -int(r["year"]) if r["year"] else 0))
    latest: dict[str, dict] = {}
    for r in pp:
        # Prefer co2_scope1_t over co2_scope12_total_t
        existing = latest.get(r["id"])
        cur_prio = 0 if r["metric"] == "co2_scope1_t" else 1
        ex_prio = 0 if existing and existing["metric"] == "co2_scope1_t" else 1
        if (
            existing is None
            or cur_prio < ex_prio
            or (cur_prio == ex_prio and int(r["year"]) > int(existing["year"]))
        ):
            latest[r["id"]] = r

    # Aggregated leave-one-plant-out predictions (per-facility median + range from lodo_aggregated.json).
    # NOTE: this is the in-browser iz DEMO model, kept for the /verify/ demo only —
    # it is NOT the headline. The headline is the cf-corrected formula below.
    agg_by_id: dict[str, dict] = {}
    if AGG.exists():
        for r in json.loads(AGG.read_text()):
            preds = r.get("preds_all", [])
            agg_by_id[r["facility_id"]] = {
                "pred_median": r["pred_median"],
                "pred_min": min(preds) if preds else None,
                "pred_max": max(preds) if preds else None,
                "n_runs": r.get("n_runs", len(preds)),
            }

    # Honest headline prediction: cf-corrected formula evaluated LEAVE-ONE-PLANT-OUT
    # (reports/lopo_ef_eval.json). formula_pred is None for single-plant strata that
    # cannot be validated (their EF would be their own answer); those carry
    # formula_validatable=False so the page can say so instead of showing a number.
    lopo_by_id: dict[str, dict] = {}
    if LOPO.exists():
        for r in json.loads(LOPO.read_text()).get("per_plant", []):
            truth = r.get("truth") or 0
            rl = r.get("ratio_lopo")
            ri = r.get("ratio_in")
            lopo_by_id[r["id"]] = {
                "formula_pred": (rl * truth if (rl is not None and truth) else None),
                "formula_ratio": rl,
                "formula_pred_insample": (ri * truth if (ri is not None and truth) else None),
                "formula_validatable": rl is not None,
            }

    out_rows = []
    for fac in fac_rows:
        fid = fac["id"]
        bsample = bench_by_id.get(fid, {})
        k = latest.get(fid)
        agg = agg_by_id.get(fid)
        lopo = lopo_by_id.get(fid, {})
        row = {
            "id": fid,
            "company": fac["company"],
            "plant": fac["plant_name"],
            "sector": fac["cbam_scope"],
            "city": fac["city"],
            "capacity": int(fac["annual_capacity_t"]),
            "truth": float(k["value"]) if k else (bsample.get("y_raw") or None),
            "truth_year": int(k["year"]) if k and k["year"] else None,
            "truth_src": k["source"] if k else None,
            "provenance": (k["provenance"] if k else None),
            "assurance": classify_assurance(k["source"], k.get("notes", "")) if k else None,
            "notes": FACILITY_OVERRIDE_NOTES.get(fid) or (k["notes"] if k else None),
            "eu_default": bsample.get("eu_default"),
            "label_source": bsample.get("label_source"),
            # Honest headline: cf-corrected formula, leave-one-plant-out
            "formula_pred": lopo.get("formula_pred"),
            "formula_ratio": lopo.get("formula_ratio"),
            "formula_pred_insample": lopo.get("formula_pred_insample"),
            "formula_validatable": lopo.get("formula_validatable", None),
            # iz demo model (NOT the headline) — kept for the /verify/ browser demo
            "pred_median": agg["pred_median"] if agg else None,
            "pred_min": agg["pred_min"] if agg else None,
            "pred_max": agg["pred_max"] if agg else None,
            "n_runs": agg["n_runs"] if agg else 0,
        }
        out_rows.append(row)

    OUT.write_text(json.dumps(out_rows, indent=1, default=str))
    print(f"wrote {OUT.relative_to(REPO)}  ({len(out_rows)} facilities)")
    print(f"  with leave-one-plant-out predictions: {sum(1 for r in out_rows if r['pred_median'])}")
    print(f"  with disclosure label: {sum(1 for r in out_rows if r['truth_src'])}")
    print(f"  assurance tiers:")
    from collections import Counter
    tiers = Counter(r["assurance"] for r in out_rows if r["assurance"])
    for t, n in tiers.most_common():
        print(f"    {t:20s} {n}")


if __name__ == "__main__":
    main()
