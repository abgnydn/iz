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

from iz.bench.schema import split_facilities

REPO = Path(__file__).resolve().parent.parent
FACS_CSV = REPO / "data" / "tr_facilities.csv"
KNOWN_CSV = REPO / "data" / "tr_facility_known_emissions.csv"
CT_PARQUET = REPO / "reports" / "climate_trace_tr_joined.parquet"
S5P_DIR = REPO / "data" / "s5p"
OUT_JSON = REPO / "src" / "iz_browser" / "bench.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("iz.export")

SCOPES = ["cement", "steel", "aluminum", "fertilizer"]

# Sector-default annual specific emissions (tCO₂ per ton of product), from
# EU CBAM Implementing Regulation 2023/1773 Annex IV defaults — used as weak
# labels for facilities lacking direct disclosures. Operators beat these
# defaults with verified measurements.
SECTOR_DEFAULT_EF = {
    "cement": 1.584,      # tCO2 / t cement (EU default for Portland cement)
    "steel": 1.900,       # tCO2 / t crude steel (BF/BOF route)
    "aluminum": 1.500,    # tCO2 / t primary aluminum (Scope 1 direct only)
    "fertilizer": 0.800,  # tCO2 / t ammonia-equivalent
}


def main():
    facs = pd.read_csv(FACS_CSV)
    log.info("facilities: %d", len(facs))
    split = split_facilities(facs["id"].tolist())
    split_lookup = {**{i: "train" for i in split.train},
                    **{i: "val" for i in split.val},
                    **{i: "test" for i in split.test}}

    # ---- features per facility (static features for v0) ----
    feat_rows = []
    for _, fac in facs.iterrows():
        scope_onehot = [1.0 if fac["cbam_scope"] == s else 0.0 for s in SCOPES]
        capacity = float(fac["annual_capacity_t"])
        feat = [
            math.log1p(capacity) / 20.0,   # log-capacity, roughly [0, 1]
            (float(fac["lat"]) - 38.0) / 5.0,  # lat normalized (TR is 36-42°N)
            (float(fac["lon"]) - 33.0) / 10.0, # lon normalized (TR is 26-44°E)
            *scope_onehot,
        ]
        feat_rows.append({"id": fac["id"], "company": fac["company"], "feat": feat, "split": split_lookup[fac["id"]]})
    feat_idx = {r["id"]: i for i, r in enumerate(feat_rows)}

    # ---- Climate TRACE weak labels ----
    # NOTE: the /v6/assets endpoint returns EmissionsSummary with Emissions=null
    # in the current API response; need /v6/emissions for actual values.
    # TODO: pull emissions from /v6/emissions/assets?asset_ids=... in a follow-up.
    weak_labels_ct = {}
    if CT_PARQUET.exists():
        ct = pd.read_parquet(CT_PARQUET)
        co2 = ct[ct["gas"] == "co2e_100yr"].dropna(subset=["emissions"])
        for iz_id, g in co2.groupby("iz_id"):
            total = float(g["emissions"].sum())
            if total > 0 and total < 1e8:
                weak_labels_ct[iz_id] = total
    log.info("Climate TRACE weak labels with emissions: %d", len(weak_labels_ct))

    # ---- Sector-default weak labels (capacity × EU default EF) ----
    # Coarse but reproducible — gives every facility a starting label.
    weak_labels_default = {}
    for _, fac in facs.iterrows():
        scope = fac["cbam_scope"]
        cap = float(fac["annual_capacity_t"])
        if scope in SECTOR_DEFAULT_EF and cap > 0:
            weak_labels_default[fac["id"]] = cap * SECTOR_DEFAULT_EF[scope]

    # ---- Strong labels — hand-curated ----
    strong_labels = {}
    if KNOWN_CSV.exists():
        kn = pd.read_csv(KNOWN_CSV)
        for _, r in kn.iterrows():
            metric = r["metric"]
            if not (metric.startswith("co2_scope1") or metric == "co2_scope12_total_t"):
                continue
            strong_labels[r["id"]] = float(r["value"])

    # ---- Assemble samples ----
    samples = []
    for r in feat_rows:
        fid = r["id"]
        # Label priority: strong (CDP disclosure) > Climate TRACE > sector default
        if fid in strong_labels:
            y = strong_labels[fid]; w = 1.0; src = "disclosure"
        elif fid in weak_labels_ct:
            y = weak_labels_ct[fid]; w = 0.5; src = "climate_trace"
        elif fid in weak_labels_default:
            y = weak_labels_default[fid]; w = 0.25; src = "sector_default"
        else:
            continue
        samples.append({
            "id": fid,
            "company": r["company"],
            "feat": r["feat"],
            "y_log": math.log1p(y),
            "y_raw": y,
            "w": w,
            "split": r["split"],
            "label_source": src,
        })
    by_src = {s["label_source"]: sum(1 for x in samples if x["label_source"] == s["label_source"]) for s in samples}
    log.info("samples (with any label): %d  by source: %s", len(samples), by_src)

    # Standardize features
    X = np.array([s["feat"] for s in samples], dtype=np.float32)
    feat_mean = X.mean(0).tolist()
    feat_std = (X.std(0) + 1e-6).tolist()
    feat_names = ["log_capacity", "lat_norm", "lon_norm"] + [f"is_{s}" for s in SCOPES]

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
