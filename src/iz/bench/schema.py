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


def split_facilities_stratified_loo(
    facility_ids: list[str],
    strata: dict[str, str],
    holdout_id: str,
    seed: str = "iz-1-2026",
) -> BenchSplit:
    """Leave-one-out variant: force `holdout_id` into test, then stratify the rest."""
    others = [f for f in facility_ids if f != holdout_id]
    base = split_facilities_stratified(others, strata, seed)
    return BenchSplit(train=sorted(base.train + base.val[:0]), val=sorted(base.val), test=sorted(base.test + [holdout_id]))


def split_facilities_stratified(
    facility_ids: list[str],
    strata: dict[str, str],
    seed: str = "iz-1-2026",
) -> BenchSplit:
    """Deterministic stratified split.

    Within each stratum (keyed by `strata[fid]`), facilities are deterministically
    sorted by hash and round-robin-assigned to train/val/test in a 70/15/15
    fashion that respects fold minimums. Strata with <3 members all go to train
    (preserves rare-class learning signal; the rare-class facility wouldn't be
    a meaningful test point anyway). Strata with exactly 3 go 1/1/1.
    """
    by_stratum: dict[str, list[str]] = {}
    for fid in facility_ids:
        by_stratum.setdefault(strata.get(fid, "_unknown"), []).append(fid)

    train, val, test = [], [], []
    for stratum, fids in sorted(by_stratum.items()):
        # Deterministic per-stratum order via hash
        ordered = sorted(fids, key=lambda f: hashlib.sha256(f"{seed}-{stratum}-{f}".encode()).hexdigest())
        n = len(ordered)
        if n == 0:
            continue
        if n == 1:
            train.extend(ordered)
            continue
        if n == 2:
            train.append(ordered[0])
            test.append(ordered[1])
            continue
        if n == 3:
            train.append(ordered[0]); val.append(ordered[1]); test.append(ordered[2])
            continue
        # n >= 4: 70/15/15 by index, with explicit floor-then-fill
        n_test = max(1, round(n * 0.15))
        n_val = max(1, round(n * 0.15))
        n_train = n - n_test - n_val
        train.extend(ordered[:n_train])
        val.extend(ordered[n_train:n_train + n_val])
        test.extend(ordered[n_train + n_val:])
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
