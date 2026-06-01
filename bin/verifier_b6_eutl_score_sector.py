"""
Generalised B6 scorer — applies the TR-MRV-Bench cf-corrected formula to
EU plants in any sector (steel / aluminum / fertilizer / cement), using the
output of `bin/pull_eutl_sector.py`.

Usage:
    uv run python bin/verifier_b6_eutl_score_sector.py steel
    uv run python bin/verifier_b6_eutl_score_sector.py aluminum
    uv run python bin/verifier_b6_eutl_score_sector.py fertilizer

For each sector we run four validation lenses:
  1. Time-series YoY consistency
  2. Country-level coverage
  3. Operator-group rollup (parent-company matching by `name` substring)
  4. Direct per-plant formula test on the largest plants with hand-curated
     nameplate capacity from operator IARs / industry-body data

Plus a sector-aggregate reconciliation (Lens 5) where we have published
industry-wide nameplate capacity, average cf, and average EF.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Sector parameter sheets
# ---------------------------------------------------------------------------

SECTORS = {
    "steel": {
        "tr_ef_default": None,      # split by route — see KNOWN_PLANTS
        "eu_default_ef": 1.900,     # EU CBAM Article 4(3) default for steel
        "eu_nameplate_mt": 225.0,   # Eurofer 2024: EU crude steel capacity
        "eu_production_mt": 115.0,  # Eurofer 2024 production
        "operator_aliases": {
            "ArcelorMittal":  ["ArcelorMittal", "Mittal"],
            "Tata Steel":     ["Tata", "Corus"],
            "ThyssenKrupp":   ["ThyssenKrupp", "Thyssen Krupp"],
            "Salzgitter":     ["Salzgitter", "Peine"],
            "Voestalpine":    ["Voestalpine", "VOEST"],
            "Liberty Steel":  ["Liberty"],
            "SSAB":           ["SSAB"],
            "Acerinox":       ["Acerinox"],
            "Outokumpu":      ["Outokumpu"],
            "U.S. Steel Kosice": ["Kosice", "Košice"],
        },
        # Group totals (Mt/yr Scope 1, 2023 IAR group-wide global)
        "operator_group_mt": {
            "ArcelorMittal":  165.0,   # 2023 global
            "Tata Steel":      31.0,   # 2023 global (Europe + India)
            "ThyssenKrupp":    18.5,   # 2023 group
            "Salzgitter":       8.0,   # 2023
            "Voestalpine":     13.5,   # 2023
            "Liberty Steel":   24.0,
            "SSAB":             8.0,
            "Acerinox":         1.5,
            "Outokumpu":        2.7,
            "U.S. Steel Kosice": 5.5,
        },
        # Hand-curated top EU steel plants with operator-published capacity.
        # Tuple: (label, country, name_substring, capacity Mt/yr, route)
        "known_plants": [
            ("ArcelorMittal Dunkirk (FR)",   "FR", "Dunkerque",     7.0, "BF/BOF"),
            ("ArcelorMittal Gent (BE)",      "BE", "Gent",          5.0, "BF/BOF"),
            ("ArcelorMittal Bremen (DE)",    "DE", "Bremen",        4.0, "BF/BOF"),
            ("Voestalpine Linz (AT)",        "AT", "Linz",          5.5, "BF/BOF"),
            ("Salzgitter Flachstahl (DE)",   "DE", "Salzgitter",    4.5, "BF/BOF"),
            ("ThyssenKrupp Duisburg (DE)",   "DE", "Duisburg",     11.0, "BF/BOF"),
            ("Tata Steel IJmuiden (NL)",     "NL", "IJmuiden",      7.0, "BF/BOF"),
            ("U.S. Steel Košice (SK)",       "SK", "Košice",        4.5, "BF/BOF"),
            ("Liberty Galați (RO)",          "RO", "Galați",        3.0, "BF/BOF"),
            ("SSAB Raahe (FI)",              "FI", "Raahe",         2.5, "BF/BOF"),
            ("ArcelorMittal Asturias (ES)",  "ES", "Avilés",        4.0, "BF/BOF"),
            ("Acerinox Algeciras (ES)",      "ES", "Algeciras",     0.95, "EAF"),
            ("Outokumpu Tornio (FI)",        "FI", "Tornio",        1.6, "EAF"),
            ("Riva Verona (IT)",             "IT", "Verona",        1.4, "EAF"),
            ("Feralpi Lonato (IT)",          "IT", "Lonato",        1.2, "EAF"),
            ("Celsa Castellbisbal (ES)",     "ES", "Castellbisbal", 2.5, "EAF"),
            ("Megasa Naron (ES)",            "ES", "Narón",         1.0, "EAF"),
            ("Sidenor Basauri (ES)",         "ES", "Basauri",       1.0, "EAF"),
        ],
    },
    "aluminum": {
        "tr_ef_default": None,
        # NOTE: EU CBAM 8.6 t/t covers Scope 1 + 2 (anode + smelting + grid
        # electricity). EUTL captures Scope 1 only (anode + process). The
        # right comparison is EU CBAM "unwrought aluminium" Annex VIII
        # Scope-1-only default 1.471 t/t against EUTL Scope 1.
        "eu_default_ef": 1.471,      # EU CBAM Annex VIII Scope-1-only default
        "eu_nameplate_mt": 4.0,      # IAI EU primary aluminum capacity
        "eu_production_mt": 2.7,
        "operator_aliases": {
            "Aluminium Dunkerque": ["Dunkerque", "Aluminium Dunkerque"],
            "Norsk Hydro":         ["Hydro", "Norsk"],
            "Speira":              ["Speira"],
            "Rio Tinto":           ["Rio Tinto", "Alcan"],
            "Trimet":              ["Trimet"],
            "Alcoa":               ["Alcoa"],
            "Mytilineos":          ["Mytilineos", "Alouminion"],
            "Aluminij Mostar":     ["Mostar"],
            "San Ciprián":         ["San Ciprián", "San Cipriano"],
        },
        "operator_group_mt": {
            "Aluminium Dunkerque": 1.8,
            "Norsk Hydro":        12.0,
            "Speira":              1.0,
            "Rio Tinto":          30.0,
            "Trimet":              0.8,
            "Alcoa":              23.0,
            "Mytilineos":          1.6,
            "Aluminij Mostar":     0.9,
            "San Ciprián":         0.8,
        },
        "known_plants": [
            ("Aluminium Dunkerque (FR)",       "FR", "DUNKERQUE",       0.30, "primary"),
            ("Trimet Saint-Jean (FR)",         "FR", "Saint Jean",      0.13, "primary"),
            ("Trimet Essen (DE)",              "DE", "Essen",           0.16, "primary"),
            ("Trimet Hamburg (DE)",            "DE", "Hamburg",         0.13, "primary"),
            ("San Ciprián Aluminio (ES)",      "ES", "San Ciprián",     0.23, "primary"),
            ("ALRO Slatina (RO)",              "RO", "ALRO",            0.27, "primary"),
            ("Alcoa Portoscuso (IT)",          "IT", "Portoscuso",      0.15, "primary"),
            ("Hydro Sunndal (NO)",             "NO", "Sunndal",         0.39, "primary"),
            ("Hydro Karmøy (NO)",              "NO", "Karmøy",          0.18, "primary"),
            ("Hydro Årdal (NO)",               "NO", "Årdal",           0.18, "primary"),
            ("Hydro Høyanger (NO)",            "NO", "Høyanger",        0.07, "primary"),
            ("Alcoa Mosjøen (NO)",             "NO", "Mosjøen",         0.19, "primary"),
            ("Alcoa Lista (NO)",               "NO", "Lista",           0.09, "primary"),
            ("Alcoa Fjarðaál (IS)",            "IS", "Fjarðarál",       0.34, "primary"),
            ("Norðurál Grundartangi (IS)",     "IS", "Grundartangi",    0.32, "primary"),
            ("Rio Tinto ISAL (IS)",            "IS", "Rio Tinto",       0.21, "primary"),
            ("Lochaber Smelter (UK)",          "GB", "Lochaber",        0.04, "primary"),
            ("Anglesey Aluminium (UK)",        "GB", "Anglesey",        0.14, "primary"),
            ("Aluminij Mostar (SK)",           "SK", "Výroba hliníka",  0.10, "primary"),
            ("Kubikenborg (SE)",               "SE", "Kubikenborg",     0.13, "primary"),
        ],
        # Lens-5 aggregate uses only primary smelters
        "lens5_activity_filter": "primary aluminium",
    },
    "fertilizer": {
        "tr_ef_default": None,
        "eu_default_ef": 2.000,      # EU CBAM default for ammonia (per t NH3)
        "eu_nameplate_mt": 18.0,     # Fertilizers Europe EU ammonia capacity
        "eu_production_mt": 15.0,
        # Lens 5 aggregate filtered to ammonia only (nitric-acid-only plants
        # have a different EF and would dilute the comparison).
        "lens5_activity_filter": "ammonia",
        "operator_aliases": {
            "Yara":      ["Yara"],
            "BASF":      ["BASF"],
            "Borealis":  ["Borealis", "Linz Chemie"],
            "OCI":       ["OCI", "DSM Agro"],
            "Grupa Azoty":["Azoty", "Grupa Azoty", "Tarnów", "Police"],
            "Achema":    ["Achema"],
            "Nitrogénművek":["Nitrogénművek", "Pétfürdő"],
            "Lifosa":    ["Lifosa"],
            "Anwil":     ["Anwil"],
        },
        "operator_group_mt": {
            "Yara":         15.0,
            "BASF":         12.0,
            "Borealis":      4.5,
            "OCI":           5.0,
            "Grupa Azoty":   5.0,
            "Achema":        1.5,
            "Nitrogénművek": 0.8,
            "Lifosa":        0.6,
            "Anwil":         0.8,
        },
        "known_plants": [
            ("Yara Sluiskil (NL)",          "NL", "Sluiskil",    1.80, "integrated"),
            ("Yara Brunsbüttel (DE)",       "DE", "Brunsbüttel", 0.80, "integrated"),
            ("Yara Le Havre (FR)",          "FR", "Le Havre",    0.30, "nitric"),
            ("BASF Ludwigshafen (DE)",      "DE", "Ludwigshafen", 1.20, "integrated"),
            ("Borealis Linz (AT)",          "AT", "Linz",         0.50, "integrated"),
            ("OCI Geleen (NL)",             "NL", "Geleen",       1.20, "integrated"),
            ("Grupa Azoty Police (PL)",     "PL", "Police",       0.70, "integrated"),
            ("Grupa Azoty Tarnów (PL)",     "PL", "Tarnów",       0.70, "integrated"),
            ("Achema Jonava (LT)",          "LT", "Jonava",       0.60, "integrated"),
            ("Lifosa Kėdainiai (LT)",       "LT", "Kėdainiai",    0.50, "nitric"),
            ("Anwil Włocławek (PL)",        "PL", "Włocławek",    0.40, "integrated"),
            ("Nitrogénművek Pétfürdő (HU)", "HU", "Pétfürdő",     0.40, "integrated"),
        ],
    },
}

# Route-specific TR-bench emission factors (the same numbers used to predict
# TR plants in the n=21 LODO). NOTE on aluminum: "primary" Scope 1 is anode
# combustion + process — not the EU CBAM 8.6 which includes Scope 2 grid power.
ROUTE_EF = {
    "BF/BOF":      2.000,   # tCO₂/t crude steel (operator-audited mean)
    "EAF":         0.250,   # tCO₂/t crude steel (TR EAF mean)
    "primary":     2.000,   # tCO₂/t Al Scope 1 only (anodes + PFC; IAI 2023 EU avg)
    "downstream":  0.450,   # tCO₂/t Al rolling/extrusion (TR Assan, ASAŞ)
    "integrated":  2.000,   # tCO₂/t NH3 (integrated ammonia + nitric, no N₂O catalyst)
    "n2o_controlled": 0.500, # tCO₂/t NH3-equivalent with N₂O abatement
    "nitric":      0.050,   # tCO₂/t HNO3 with N₂O catalyst
    "blender":     0.025,   # tCO₂/t fertilizer (mixing only, no NH3/HNO3 process)
}


# ---------------------------------------------------------------------------
# Scoring lenses
# ---------------------------------------------------------------------------

def headline_log_mae(pred: pd.Series, truth: pd.Series) -> float:
    valid = pred.notna() & truth.notna() & (pred > 0) & (truth > 0)
    p = pred[valid].to_numpy()
    t = truth[valid].to_numpy()
    if len(p) == 0:
        return float("nan")
    return float(np.mean(np.abs(np.log(p) - np.log(t))))


def run(sector: str) -> None:
    cfg = SECTORS[sector]
    log_path = REPO / "logs" / f"b6_eutl_score_{sector}.log"
    out_md = REPO / "reports" / "verifiers" / f"b6_eutl_{sector}.md"
    out_json = REPO / "reports" / "verifiers" / f"b6_eutl_{sector}.json"
    inst_path = REPO / "data" / "eutl" / f"eutl_{sector}_installations.parquet"
    comp_path = REPO / "data" / "eutl" / f"eutl_{sector}_compliance.parquet"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(log_path, mode="w"), logging.StreamHandler()],
        force=True,
    )
    log = logging.getLogger(f"b6.{sector}")

    inst = pd.read_parquet(inst_path)
    comp = pd.read_parquet(comp_path)
    log.info("loaded %d installations and %d compliance rows", len(inst), len(comp))

    v = comp[comp["verified"].notna()].copy()
    v["year"] = v["year"].astype(int)
    log.info("verified rows: %d", len(v))

    # Lens 1: time series
    yoy = (
        v.sort_values(["id", "year"])
        .assign(prev=lambda d: d.groupby("id")["verified"].shift(1))
        .assign(yoy_pct=lambda d: (d["verified"] - d["prev"]) / d["prev"] * 100)
    )
    yoy_stats = {
        "median_abs_yoy_pct": float(yoy["yoy_pct"].abs().median()),
        "p90_abs_yoy_pct": float(yoy["yoy_pct"].abs().quantile(0.90)),
        "share_within_10pct": float((yoy["yoy_pct"].abs() < 10).mean()),
        "share_within_25pct": float((yoy["yoy_pct"].abs() < 25).mean()),
    }

    # Lens 2: country coverage
    latest = (
        v[v["year"] >= 2020]
        .sort_values("year")
        .groupby("id")
        .tail(1)
        .merge(inst[["id", "country"]], on="id")
    )
    country_totals = (
        latest.groupby("country")
        .agg(plants=("id", "nunique"), total_mt=("verified", lambda s: float(s.sum()) / 1e6))
        .sort_values("total_mt", ascending=False)
    )

    # Lens 3: operator rollup
    inst_named = inst[["id", "name"]].copy()
    latest_named = latest.merge(inst_named, on="id", how="left")
    operator_rollup = []
    for op, aliases in cfg["operator_aliases"].items():
        pattern = "|".join(aliases)
        mask = latest_named["name"].str.contains(pattern, case=False, na=False, regex=True)
        eu_sum_mt = float(latest_named.loc[mask, "verified"].sum()) / 1e6
        n_plants = int(mask.sum())
        group_mt = cfg["operator_group_mt"].get(op, 0)
        operator_rollup.append({
            "operator": op,
            "eu_eutl_sum_mt": eu_sum_mt,
            "operator_disclosed_group_mt": group_mt,
            "eu_plants_matched": n_plants,
            "ratio_eu_to_global": (eu_sum_mt / group_mt) if group_mt > 0 else None,
        })

    # Lens 4: per-plant formula test
    eu_cf = cfg["eu_production_mt"] / cfg["eu_nameplate_mt"]
    formula_rows = []
    for label, country, needle, cap_mt, route in cfg["known_plants"]:
        cap_t = cap_mt * 1e6
        cand = inst[
            inst["id"].str.startswith(country + "_") &
            inst["name"].str.contains(needle, case=False, na=False)
        ]
        if cand.empty:
            continue
        match_ids = cand["id"].tolist()
        rec = v[v["id"].isin(match_ids) & (v["year"] >= 2020)]
        if rec.empty:
            continue
        latest_year = int(rec["year"].max())
        verified_t = float(rec[rec["year"] == latest_year]["verified"].sum())
        ef = ROUTE_EF[route]
        predicted_t = cap_t * ef * eu_cf
        eu_default_pred = cap_t * cfg["eu_default_ef"] * eu_cf
        formula_rows.append({
            "id_matches": "|".join(match_ids),
            "label": label,
            "route": route,
            "year": latest_year,
            "capacity_mt": cap_mt,
            "verified_t": verified_t,
            "predicted_t": predicted_t,
            "ratio": predicted_t / verified_t if verified_t > 0 else None,
            "eu_default_pred_t": eu_default_pred,
            "eu_default_ratio": eu_default_pred / verified_t if verified_t > 0 else None,
        })
    formula_df = pd.DataFrame(formula_rows)
    matched = formula_df[formula_df["verified_t"].notna()].copy()
    log_mae_formula = headline_log_mae(matched["predicted_t"], matched["verified_t"])
    log_mae_eu = headline_log_mae(matched["eu_default_pred_t"], matched["verified_t"])
    pct_within_15 = float(((matched["ratio"] > 0.85) & (matched["ratio"] < 1.15)).mean()) if len(matched) else 0.0

    # Lens 5: sector aggregate (optionally filter to a single activity)
    latest_for_agg = latest.merge(inst[["id", "activity"]], on="id")
    activity_filter = cfg.get("lens5_activity_filter")
    if activity_filter:
        latest_for_agg = latest_for_agg[
            latest_for_agg["activity"].str.contains(activity_filter, case=False, na=False)
        ]
    eutl_total_mt = float(latest_for_agg["verified"].sum()) / 1e6
    # Use the largest route's EF as a single sector-wide proxy
    # (more route-aware breakdown in Lens 4)
    sector_default_route = "BF/BOF" if sector == "steel" else "primary" if sector == "aluminum" else "integrated"
    sector_default_ef = ROUTE_EF[sector_default_route]
    pred_formula_mt = cfg["eu_nameplate_mt"] * sector_default_ef * eu_cf
    pred_eu_default = cfg["eu_nameplate_mt"] * cfg["eu_default_ef"] * eu_cf
    aggregate = {
        "eu_nameplate_capacity_mt": cfg["eu_nameplate_mt"],
        "eu_production_mt": cfg["eu_production_mt"],
        "eu_avg_cf": eu_cf,
        "eutl_total_verified_mt": eutl_total_mt,
        "formula_pred_mt_at_route_ef": pred_formula_mt,
        "formula_route_used": sector_default_route,
        "eu_default_pred_mt": pred_eu_default,
        "formula_ratio": pred_formula_mt / eutl_total_mt if eutl_total_mt > 0 else None,
        "eu_default_ratio": pred_eu_default / eutl_total_mt if eutl_total_mt > 0 else None,
    }

    log.info("Lens 1 yoy: %s", yoy_stats)
    log.info("Lens 2 (top 10 countries):\n%s", country_totals.head(10).to_string())
    log.info("Lens 3 operator rollup:\n%s", pd.DataFrame(operator_rollup).to_string())
    log.info("Lens 4 (n=%d):", len(matched))
    log.info("  formula log-MAE: %.3f", log_mae_formula)
    log.info("  EU default log-MAE: %.3f", log_mae_eu)
    log.info("  share ±15%%: %.2f", pct_within_15)
    log.info("Lens 5 aggregate: %s", aggregate)

    summary = {
        "sector": sector,
        "n_installations_pulled": int(len(inst)),
        "n_verified_facility_years": int(len(v)),
        "lens_1_time_series": yoy_stats,
        "lens_2_country_coverage": country_totals.reset_index().to_dict(orient="records"),
        "lens_3_operator_rollup": operator_rollup,
        "lens_4_formula_test": {
            "n_plants_with_capacity": int(len(matched)),
            "log_mae_formula": log_mae_formula,
            "log_mae_eu_default": log_mae_eu,
            "share_within_15pct": pct_within_15,
            "plants": matched.to_dict(orient="records"),
        },
        "lens_5_sector_aggregate": aggregate,
    }
    out_json.write_text(json.dumps(summary, indent=2, default=str))

    # Markdown
    md = [
        f"# Verifier B6 — EUTL EU {sector.title()} External Validation",
        "",
        f"*Generated {pd.Timestamp.now('UTC').date()} from EUTL via euets.info. n={len(inst)} EU {sector} installations × ~20 years = {len(v):,} audit-grade verified Scope 1 facility-years.*",
        "",
        "## Lens 1 — Time-series YoY consistency",
        "",
        f"- Median |ΔYoY|: {yoy_stats['median_abs_yoy_pct']:.1f}%",
        f"- P90 |ΔYoY|: {yoy_stats['p90_abs_yoy_pct']:.1f}%",
        f"- Share within ±10% YoY: {yoy_stats['share_within_10pct']*100:.0f}%",
        f"- Share within ±25% YoY: {yoy_stats['share_within_25pct']*100:.0f}%",
        "",
        "## Lens 2 — Country coverage (latest year per plant)",
        "",
        "| Country | Plants | Mt/yr |",
        "|---|---:|---:|",
    ]
    for _, r in country_totals.head(15).iterrows():
        md.append(f"| {r.name} | {int(r['plants'])} | {r['total_mt']:.2f} |")

    md += [
        "",
        "## Lens 3 — Operator group rollup",
        "",
        "| Operator | EU plants | EUTL EU sum (Mt) | Disclosed group (Mt) | EU share |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in operator_rollup:
        ratio = r["ratio_eu_to_global"]
        ratio_str = f"{ratio*100:.0f}%" if ratio is not None else "—"
        md.append(f"| {r['operator']} | {r['eu_plants_matched']} | {r['eu_eutl_sum_mt']:.2f} | {r['operator_disclosed_group_mt']:.2f} | {ratio_str} |")

    md += [
        "",
        f"## Lens 4 — Direct formula test (n={len(matched)})",
        "",
        f"Applied `cap × route-EF × EU_cf ({eu_cf:.2f})` to {len(matched)} EU plants with operator-published capacity.",
        "",
        f"- **log-MAE formula vs EUTL: {log_mae_formula:.3f}**",
        f"- **log-MAE EU CBAM default vs EUTL: {log_mae_eu:.3f}**",
        (f"- **Reduction vs EU default: {(1 - log_mae_formula/log_mae_eu)*100:.1f}%**" if log_mae_eu > 0 else ""),
        f"- **Plants within ±15%: {int(pct_within_15 * len(matched))}/{len(matched)}**",
        "",
        "| Plant | Route | Capacity (Mt) | EUTL verified (Mt) | Formula (Mt) | Ratio | EU default (Mt) | EU/verified |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in matched.iterrows():
        md.append(
            f"| {r['label']} | {r['route']} | {r['capacity_mt']:.2f} | "
            f"{r['verified_t']/1e6:.2f} | {r['predicted_t']/1e6:.2f} | {r['ratio']:.2f}× | "
            f"{r['eu_default_pred_t']/1e6:.2f} | {r['eu_default_ratio']:.2f}× |"
        )

    md += [
        "",
        "## Lens 5 — Sector aggregate",
        "",
        f"| Estimator | Predicted Mt/yr | EUTL truth (Mt/yr) | Ratio |",
        "|---|---:|---:|---:|",
        f"| Formula at `{aggregate['formula_route_used']}` route EF × EU cf | {pred_formula_mt:.1f} | {eutl_total_mt:.1f} | {aggregate['formula_ratio']:.2f}× |",
        f"| EU CBAM default | {pred_eu_default:.1f} | {eutl_total_mt:.1f} | {aggregate['eu_default_ratio']:.2f}× |",
        "",
        "## Sources",
        "",
        "- [EUTL via euets.info](https://www.euets.info)",
        "- Operator IARs and industry-body data for capacity",
    ]
    out_md.write_text("\n".join(md))
    log.info("wrote %s and %s", out_md.relative_to(REPO), out_json.relative_to(REPO))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in SECTORS:
        print(f"usage: {sys.argv[0]} {{{'|'.join(SECTORS)}}}")
        sys.exit(1)
    run(sys.argv[1])
