"""
TR-MRV-Bench schema.

Per-facility, per-month rows. The model maps (satellite features) → (emissions estimate).
Strong labels from CDP / sustainability disclosures (annual);
weak labels from Climate TRACE (annual, ±50%);
both broadcast across the months of their reporting year.

Train/val/test split is BY FACILITY (not by time) so that we test
out-of-distribution generalization to plants the model has not seen.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

# Feature columns from S5P + ERA5 + sentinel-2 + sentinel-3 + grid
FEATURE_COLUMNS = [
    "no2_mean",           # μmol/m² (S5P L2 NO₂ bbox mean)
    "no2_std",
    "no2_n_pixels",
    "no2_anomaly_vs_background",   # plant - rural-Thrace baseline
    "thermal_mean_k",     # Landsat / Sentinel-3 SLSTR brightness temp over kiln/furnace
    "thermal_max_k",
    "wind_speed_mps",     # ERA5 10m
    "wind_dir_deg",       # ERA5
    "pbl_height_m",       # ERA5 boundary layer height
    "temp_2m_k",          # ERA5
    "grid_co2_g_per_kwh", # EPIAS Şeffaflık Platformu monthly TR grid factor
]

# Label columns
LABEL_COLUMNS = [
    "co2_t_month",        # ground truth CO₂ in tonnes for this month
    "label_source",       # "cdp" | "sustainability" | "climate_trace" | "estimated"
    "label_confidence",   # "high" | "medium" | "low"
]

META_COLUMNS = [
    "facility_id",
    "company",
    "cbam_scope",         # cement / steel / aluminum / fertilizer
    "lat",
    "lon",
    "month",              # ISO date, first-of-month
    "split",              # "train" | "val" | "test"
]


@dataclass
class BenchSplit:
    train: list[str]
    val: list[str]
    test: list[str]


def split_facilities(facility_ids: list[str], seed: str = "iz-1-2026") -> BenchSplit:
    """Deterministic facility-level split (70 / 15 / 15) so the same facility
    always lands in the same split across runs. Hash-based so order-independent."""
    train, val, test = [], [], []
    for fid in facility_ids:
        h = int(hashlib.sha256(f"{seed}-{fid}".encode()).hexdigest()[:8], 16)
        r = (h % 100) / 100.0
        if r < 0.70:
            train.append(fid)
        elif r < 0.85:
            val.append(fid)
        else:
            test.append(fid)
    return BenchSplit(train=sorted(train), val=sorted(val), test=sorted(test))


def schema_row(facility: dict, *, month: str, features: dict, labels: dict, split: str) -> dict:
    """Canonical row factory. Keeps the contract centralized."""
    return {
        "facility_id": facility["id"],
        "company": facility.get("company", ""),
        "cbam_scope": facility.get("cbam_scope", ""),
        "lat": float(facility.get("lat", 0) or 0),
        "lon": float(facility.get("lon", 0) or 0),
        "month": month,
        "split": split,
        **{c: features.get(c, float("nan")) for c in FEATURE_COLUMNS},
        **{c: labels.get(c) for c in LABEL_COLUMNS},
    }
