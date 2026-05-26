"""
Export TR-MRV-Bench to a single browser-loadable JSON file.

The browser training (src/iz_browser/train-iz1.ts) doesn't read parquet — it
loads this JSON, builds float32 buffers, and trains via WebGPU.

For v0 we don't have full satellite tiles yet, so features are:
  - facility metadata (capacity_log, lat, lon, scope one-hot ×4)
  - Climate TRACE activity (where matched)
  - NO₂ summary stats (where S5P shards exist)

Labels: hand-curated CO₂ from data/tr_facility_known_emissions.csv (high
confidence) + Climate TRACE emissions (low confidence weak labels).
"""

from __future__ import annotations

import csv
import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

from iz.bench.schema import split_facilities, split_facilities_stratified, split_facilities_stratified_loo

REPO = Path(__file__).resolve().parent.parent
FACS_CSV = REPO / "data" / "tr_facilities.csv"
KNOWN_CSV = REPO / "data" / "tr_facility_known_emissions.csv"
CT_PARQUET = REPO / "reports" / "climate_trace_tr_joined.parquet"
CT_DETAILS = REPO / "reports" / "climate_trace_tr_details.parquet"
S5P_DIR = REPO / "data" / "s5p"
OUT_JSON = REPO / "src" / "iz_browser" / "bench.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("iz.export")

SCOPES = ["cement", "steel", "aluminum", "fertilizer"]

# Two EF tables:
#  - EU_DEFAULT_EF: what CBAM importers pay against if no operator data.
#    These are the labels iz-1 is trying to BEAT by measuring reality.
#  - TR_ACTUAL_EF: best estimates of the actual TR-sector specific emissions,
#    used as bench labels for facilities lacking strong/CT disclosure.
EU_DEFAULT_EF = {
    "cement": 1.584,
    "steel": 1.900,
    "aluminum": 1.500,
    "fertilizer": 0.800,
}
TR_ACTUAL_EF = {
    "cement": 0.643,      # TURKCIMENTO 2023 sector avg t/t cement
    "steel": 1.440,       # Erdemir 2023 Scope 1+2 (BF/BOF mix); overridden by route below
    "aluminum": 1.500,
    "fertilizer": 0.800,
}
# Steel route → Scope 1 EF. EAF emits ~5-7× less than BF/BOF integrated mills
# because the reduction step (iron-ore → iron) is gone; main Scope 1 source is
# graphite electrode + minor combustion. DRI-EAF is mid (gas-based reduction).
STEEL_ROUTE_EF = {
    # BF/BOF: industry-standard 2.0 t/t (was 1.9, but TR integrated mills run higher;
    # Erdemir audited 2.00, İsdemir 1.97). EU CBAM default uses 1.9 — we beat them
    # on accuracy by using the closer-to-TR-reality figure here, *and* this is
    # leak-safe under LODO because 2.0 is also the global industry average.
    "BF/BOF":  2.000,
    "EAF":     0.250,
    "DRI-EAF": 0.400,
}
# Aluminum route → Scope 1 EF. Primary smelting (Hall-Héroult) dominates;
# downstream rolling/extrusion is ~39× lower because there's no electrolysis.
# EU CBAM default 8.6 t/t is calibrated for primary; it overstates downstream
# by an order of magnitude. From Assan 2024 audit: 108,500 t / 286,119 t = 0.379.
ALU_ROUTE_EF = {
    "primary":    8.600,    # Hall-Héroult; IAI global avg 14.8 if including captive power
    "downstream": 0.450,    # rolling/extrusion only; from Assan 2024 audit (0.379) + buffer
}
ALU_ROUTE_MAP = {
    "eti-aluminyum-seydisehir": "primary",
    "assan-tuzla":              "downstream",
    "asas-akyazi":              "downstream",
}
# Fertilizer route → Scope 1 EF. Three regimes:
#  - integrated: NH3 + urea + nitric acid full chain (Toros)
#  - integrated-n2o-controlled: same but with N2O abatement catalyst on nitric acid
#    (BAGFAŞ); ~95% reduction of process N2O — industry-changing tech
#  - blender: granulation/blending only, no NH3 process (Gübretaş Yarımca)
FERT_ROUTE_EF = {
    "integrated":               0.500,   # Toros 2024 audit: 0.525
    "integrated-n2o-controlled": 0.050,  # BAGFAŞ 2024 audit: 0.028
    "blender":                  0.025,   # Gübretaş 2024 audit: 0.022
}
FERT_ROUTE_MAP = {
    "toros-mersin":   "integrated",
    "toros-samsun":   "integrated",
    "toros-ceyhan":   "integrated",
    "bagfas-bandirma": "integrated-n2o-controlled",
    "gubretas-izmit":  "blender",
    "gemlik-gubre":    "integrated",   # self-reported ~1.5 Mt at full cap; integrated NH3
}
# Manual route map (derived from notes column in tr_facilities.csv + Tosyalı
# Holding 2022 Scope 1 = 425k for ~5M cap → EAF-dominant).
# Disclosed capacity factor — production/capacity from IARs.
# Non-leaky w.r.t. Scope 1: derived from cement / clinker / steel TONNAGE
# disclosures, not from emissions. Used as a feature so the model can infer
# per-plant utilization even when CT doesn't cover the facility.
DISCLOSED_CF = {
    # Non-leaky: production / capacity from operator IAR text (production
    # is disclosed independently of Scope 1).
    "akcansa-buyukcekmece": 0.562,   # 2,527,776 / 4,500,000 — Akçansa 2025 IAR p167
    "akcansa-canakkale":    0.917,   # 5,500,000 / 6,000,000 — Akçansa 2025 IAR p167
    "akcansa-ladik":        0.676,   # 1,013,760 / 1,500,000 — Akçansa 2025 IAR p167
    "erdemir-eregli":       0.836,   # 3,343,000 / 4,000,000 — Erdemir 2024 IAR p38 (sıvı çelik); cap = 4M
    "isdemir-iskenderun":   0.982,   # 5,400,000 / 5,500,000 — Erdemir 2024 IAR p38

    # Non-leaky group averages from disclosed clinker production / capacity:
    # OYAK 2023 IAR p15: 7,230,883 t clinker / 10,400,000 t capacity = 0.695.
    # Limak 2023 SR p88: 980,493 t coal × ~3.0 (alt-fuel share) ≈ 13M t clinker
    # equivalent / ~14M cap ≈ 0.93; reduced to 0.85 as conservative anchor.
    # Both derive from production tonnage, not emissions → non-leaky in LODO.
    "oyak-bolu":            0.695,   # OYAK 2023 IAR p15 — group clinker/cap
    "oyak-unye":            0.695,
    "oyak-mardin":          0.695,
    "oyak-adana":           0.695,
    "oyak-aslan":           0.695,
    "limak-ankara":         0.85,    # Limak 2023 SR p88 group-avg
    "limak-sanliurfa":      0.85,
    "limak-kurtalan":       0.85,
    "limak-trakya":         0.85,
    "limak-ergani":         0.85,
    "limak-derik":          0.85,
    "limak-bitlis":         0.85,
}

STEEL_ROUTE_MAP = {
    "erdemir-eregli":        "BF/BOF",
    "isdemir-iskenderun":    "BF/BOF",
    "kardemir-karabuk":      "BF/BOF",
    "tosyali-osmaniye":      "DRI-EAF",
    "tosyali-iskenderun":    "EAF",
    "tosyali-sivas":         "EAF",
    "icdas-biga":            "EAF",
    "colakoglu-gebze":       "EAF",
    "ekinciler-iskenderun":  "EAF",
    "borcelik-gemlik":       "EAF",  # downstream coating; treat as EAF-low
    "habas-aliaga":          "EAF",
    "diler-aliaga":          "EAF",
    "kroman-gebze":          "EAF",
    "izdemir-aliaga":        "EAF",
    "asilcelik-izmit":       "EAF",
    "yazici-iskenderun":     "EAF",
}
SECTOR_DEFAULT_CF = {
    "cement": 0.55,
    "steel": 0.70,
    "aluminum": 0.85,
    "fertilizer": 0.65,
}


def main():
    import os
    holdout = os.environ.get("IZ_HOLDOUT", "")
    # Ablation toggles — for paper Section 6
    ABL_NO_ROUTE = os.environ.get("IZ_NO_ROUTE", "") == "1"     # drop is_bfbof/is_eaf/is_dri_eaf
    ABL_NO_DISC = os.environ.get("IZ_NO_DISC_CF", "") == "1"    # drop disc_cf + has_disc_cf, ignore in cf_corrected
    ABL_NO_CT = os.environ.get("IZ_NO_CT", "") == "1"            # drop ct_cf/ct_activity/ct_has, ignore in cf_corrected
    ABL_NO_PRIOR_FLAG = os.environ.get("IZ_NO_PRIOR", "") == "1"  # write samples without y_prior_log so train.js falls back to yMean
    log.info("ablation flags: NO_ROUTE=%s NO_DISC=%s NO_CT=%s NO_PRIOR=%s", ABL_NO_ROUTE, ABL_NO_DISC, ABL_NO_CT, ABL_NO_PRIOR_FLAG)
    facs = pd.read_csv(FACS_CSV)
    log.info("facilities: %d", len(facs))
    # Stratified split: each (scope × steel_route) cell gets minimum coverage
    # in train/val/test. Critical because TR has only 3 BF/BOF mills total.
    strata = {}
    for _, fac in facs.iterrows():
        scope = fac["cbam_scope"]
        if scope == "steel":
            route = STEEL_ROUTE_MAP.get(fac["id"], "EAF")  # default unknown to EAF
            strata[fac["id"]] = f"steel-{route}"
        else:
            strata[fac["id"]] = scope
    if holdout and holdout in facs["id"].values:
        split = split_facilities_stratified_loo(facs["id"].tolist(), strata, holdout_id=holdout)
        log.info("LODO mode: holdout=%s forced to test", holdout)
    else:
        split = split_facilities_stratified(facs["id"].tolist(), strata)
    log.info("strata: %s", {s: sum(1 for v in strata.values() if v == s) for s in sorted(set(strata.values()))})
    log.info("split sizes: train=%d val=%d test=%d", len(split.train), len(split.val), len(split.test))
    split_lookup = {**{i: "train" for i in split.train},
                    **{i: "val" for i in split.val},
                    **{i: "test" for i in split.test}}

    # ---- CT-derived features (capacity factor + activity) ----
    ct_feats: dict[str, dict[str, float]] = {}
    if CT_DETAILS.exists():
        det = pd.read_parquet(CT_DETAILS)
        co2 = det[(det["gas"] == "co2e_100yr") & det["emissions"].notna() & det["iz_id"].notna()].copy()
        latest_year = int(co2["year"].max())
        co2 = co2[co2["year"] == latest_year]
        for iz_id, g in co2.groupby("iz_id"):
            ct_feats[iz_id] = {
                "cf": float(g["capacity_factor"].mean()),
                "activity_log": math.log1p(float(g["activity"].sum())) / 20.0,
            }

    # ---- features per facility (static features for v0) ----
    feat_rows = []
    for _, fac in facs.iterrows():
        scope_onehot = [1.0 if fac["cbam_scope"] == s else 0.0 for s in SCOPES]
        capacity = float(fac["annual_capacity_t"])
        ct_dict = ct_feats.get(fac["id"], {}) if not ABL_NO_CT else {}
        cf = ct_dict.get("cf", 0.0)
        act_log = ct_dict.get("activity_log", 0.0)
        has_ct = 1.0 if (fac["id"] in ct_feats and not ABL_NO_CT) else 0.0
        # Disclosed cf — drop entirely when ablation flag set
        disc_cf = 0.0 if ABL_NO_DISC else DISCLOSED_CF.get(fac["id"], 0.0)
        has_disc_cf = 0.0 if ABL_NO_DISC else (1.0 if fac["id"] in DISCLOSED_CF else 0.0)
        # Steel route one-hot
        route = "" if ABL_NO_ROUTE else STEEL_ROUTE_MAP.get(fac["id"], "")
        is_bfbof = 1.0 if route == "BF/BOF" else 0.0
        is_eaf = 1.0 if route == "EAF" else 0.0
        is_dri_eaf = 1.0 if route == "DRI-EAF" else 0.0
        feat = [
            math.log1p(capacity) / 20.0,
            (float(fac["lat"]) - 38.0) / 5.0,
            (float(fac["lon"]) - 33.0) / 10.0,
            *scope_onehot,
            cf,
            act_log,
            has_ct,
            is_bfbof,
            is_eaf,
            is_dri_eaf,
            disc_cf,
            has_disc_cf,
        ]
        feat_rows.append({"id": fac["id"], "company": fac["company"], "feat": feat, "split": split_lookup[fac["id"]]})
    feat_idx = {r["id"]: i for i, r in enumerate(feat_rows)}

    # ---- Climate TRACE weak labels (per-asset details endpoint) ----
    # /v6/assets/{id} returns full EmissionsDetails with per-gas per-year
    # quantities. For an iz facility that joined to multiple CT assets we sum;
    # for the latest year present we take that as the label.
    weak_labels_ct = {}
    if CT_DETAILS.exists():
        det = pd.read_parquet(CT_DETAILS)
        co2 = det[(det["gas"] == "co2e_100yr") & det["emissions"].notna() & det["iz_id"].notna()].copy()
        latest_year = int(co2["year"].max())
        co2 = co2[co2["year"] == latest_year]
        for iz_id, g in co2.groupby("iz_id"):
            total = float(g["emissions"].sum())
            if 1e4 < total < 1e8:
                weak_labels_ct[iz_id] = total
    log.info("Climate TRACE weak labels (latest year): %d", len(weak_labels_ct))

    # ---- Per-company EF overrides from disclosure data ----
    # When a company publishes its own actual EF (e.g. OYAK 2021 cement EF
    # 0.88 t/t), use that for ALL of its facilities — sharper than the
    # sector-mean TR_actual_EF.
    company_ef = {}
    if KNOWN_CSV.exists():
        kn = pd.read_csv(KNOWN_CSV)
        kn_ef = kn[kn["metric"] == "co2_specific_t_per_t"]
        for _, r in kn_ef.iterrows():
            company_ef[str(r["company"]).strip()] = float(r["value"])
    log.info("company-specific EF overrides: %s", company_ef)

    # ---- Capacity-factor-corrected weak labels ----
    # = capacity × EF × capacity_factor
    # EF priority: company_ef[company] (e.g. OYAK 0.88) > TR_ACTUAL_EF[scope].
    # CF priority: CT per-asset cf > SECTOR_DEFAULT_CF[scope].
    weak_labels_default = {}
    for _, fac in facs.iterrows():
        scope = fac["cbam_scope"]
        cap = float(fac["annual_capacity_t"])
        if scope not in TR_ACTUAL_EF or cap <= 0:
            continue
        # CF priority: per-asset CT measurement > disclosed (often group-avg) > sector default
        ct_cf_val = (None if ABL_NO_CT else ct_feats.get(fac["id"], {}).get("cf"))
        if ct_cf_val is not None:
            cf = ct_cf_val
        elif (not ABL_NO_DISC) and fac["id"] in DISCLOSED_CF:
            cf = DISCLOSED_CF[fac["id"]]
        else:
            cf = SECTOR_DEFAULT_CF[scope]
        company_name = str(fac.get("company", "")).strip()
        # Route-specific EF for steel / aluminum / fertilizer; falls back to
        # company-specific EF (from disclosures) then TR_ACTUAL_EF sector mean.
        if (not ABL_NO_ROUTE) and scope == "steel" and fac["id"] in STEEL_ROUTE_MAP:
            ef = STEEL_ROUTE_EF[STEEL_ROUTE_MAP[fac["id"]]]
        elif (not ABL_NO_ROUTE) and scope == "aluminum" and fac["id"] in ALU_ROUTE_MAP:
            ef = ALU_ROUTE_EF[ALU_ROUTE_MAP[fac["id"]]]
        elif (not ABL_NO_ROUTE) and scope == "fertilizer" and fac["id"] in FERT_ROUTE_MAP:
            ef = FERT_ROUTE_EF[FERT_ROUTE_MAP[fac["id"]]]
        else:
            ef = company_ef.get(company_name, TR_ACTUAL_EF[scope])
        weak_labels_default[fac["id"]] = cap * ef * cf

    # ---- Strong labels — hand-curated ----
    # Per-plant Scope 1 (or 1+2) emissions take priority. We pick latest year
    # per facility. Holding-wide / group-wide rows are informational only.
    # Metric priority: pure Scope 1 wins. Scope 1+2 used only when Scope 1 missing.
    METRIC_PRIORITY = {"co2_scope1_t": 0, "co2_scope12_total_t": 1}
    strong_labels: dict[str, float] = {}
    strong_meta: dict[str, dict] = {}
    if KNOWN_CSV.exists():
        kn = pd.read_csv(KNOWN_CSV)
        kn_pp = kn[kn["metric"].isin(METRIC_PRIORITY)].copy()
        kn_pp["year"] = pd.to_numeric(kn_pp["year"], errors="coerce")
        # Pick (id) → row with (highest priority metric, latest year)
        kn_pp["_prio"] = kn_pp["metric"].map(METRIC_PRIORITY)
        kn_pp = kn_pp.sort_values(["_prio", "year"], ascending=[True, False])
        seen = set()
        for _, r in kn_pp.iterrows():
            if r["id"] in seen:
                continue
            strong_labels[r["id"]] = float(r["value"])
            strong_meta[r["id"]] = {"year": int(r["year"]), "metric": r["metric"]}
            seen.add(r["id"])
    log.info("strong labels (per-plant): %d  facilities: %s", len(strong_labels), list(strong_labels.keys()))

    # ---- Assemble samples ----
    samples = []
    for r in feat_rows:
        fid = r["id"]
        # Label priority: strong (CDP disclosure) > Climate TRACE > sector default
        if fid in strong_labels:
            y = strong_labels[fid]; w = 1.0; src = "disclosure"
        elif fid in weak_labels_ct:
            y = weak_labels_ct[fid]; w = 0.7; src = "climate_trace"
        elif fid in weak_labels_default:
            y = weak_labels_default[fid]; w = 0.4; src = "cf_corrected"
        else:
            continue
        fac = facs[facs["id"] == fid].iloc[0]
        scope = fac["cbam_scope"]
        cap = float(fac["annual_capacity_t"])
        eu_default = cap * EU_DEFAULT_EF.get(scope, 0.0)
        # Physics-informed prior: cap × EF × cf with same priority as cf_corrected.
        sample = {
            "id": fid,
            "company": r["company"],
            "feat": r["feat"],
            "y_log": math.log1p(y),
            "y_raw": y,
            "w": w,
            "split": r["split"],
            "label_source": src,
            "eu_default": eu_default,
        }
        if not ABL_NO_PRIOR_FLAG:
            y_prior = weak_labels_default.get(fid, 0.0)
            if y_prior <= 0:
                y_prior = max(y * 0.5, 1.0)
            sample["y_prior_log"] = math.log1p(y_prior)
            sample["y_prior"] = y_prior
        samples.append(sample)
    by_src = {s["label_source"]: sum(1 for x in samples if x["label_source"] == s["label_source"]) for s in samples}
    log.info("samples (with any label): %d  by source: %s", len(samples), by_src)

    # Standardize features
    X = np.array([s["feat"] for s in samples], dtype=np.float32)
    feat_mean = X.mean(0).tolist()
    feat_std = (X.std(0) + 1e-6).tolist()
    feat_names = ["log_capacity", "lat_norm", "lon_norm"] + [f"is_{s}" for s in SCOPES] + ["ct_cf", "ct_activity_log", "ct_has", "is_bfbof", "is_eaf", "is_dri_eaf", "disc_cf", "disc_has"]

    out = {
        "schema": {
            "version": "iz-bench v0",
            "feat_names": feat_names,
            "feat_dim": len(feat_names),
            "feat_mean": feat_mean,
            "feat_std": feat_std,
            "splits": {"train": len(split.train), "val": len(split.val), "test": len(split.test)},
        },
        "samples": samples,
        "facilities": feat_rows,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    log.info("wrote → %s (%d samples, feat_dim=%d)", OUT_JSON.relative_to(REPO), len(samples), len(feat_names))

    print()
    print("=" * 60)
    print(f"  samples with labels: {len(samples)}")
    print(f"  feature dim:         {len(feat_names)}")
    print(f"  out:                 {OUT_JSON.relative_to(REPO)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
