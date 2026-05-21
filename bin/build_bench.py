"""
iz Step 9 — build TR-MRV-Bench from the shards.

Joins per-facility S5P parquets + Climate TRACE labels + hand-curated
disclosure ground truth into a single training/val/test parquet.

Usage:
    uv run python bin/build_bench.py
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from iz.bench.schema import FEATURE_COLUMNS, LABEL_COLUMNS, META_COLUMNS, split_facilities

REPO = Path(__file__).resolve().parent.parent
FACS_CSV = REPO / "data" / "tr_facilities.csv"
S5P_DIR = REPO / "data" / "s5p"
CT_PARQUET = REPO / "reports" / "climate_trace_tr_joined.parquet"
DISCLOSURES_CSV = REPO / "data" / "tr_facility_known_emissions.csv"
BENCH_DIR = REPO / "data" / "bench"
LOG_PATH = REPO / "logs" / "09_build_bench.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger("iz.bench")


def load_facilities() -> pd.DataFrame:
    with open(FACS_CSV, encoding="utf-8") as f:
        return pd.DataFrame(csv.DictReader(f))


def main():
    facs = load_facilities()
    log.info("facilities: %d", len(facs))
    ids = facs["id"].tolist()
    split = split_facilities(ids)
    split_lookup = {**{i: "train" for i in split.train},
                    **{i: "val" for i in split.val},
                    **{i: "test" for i in split.test}}
    log.info("split: train=%d val=%d test=%d", len(split.train), len(split.val), len(split.test))

    # --- 1) S5P features per facility, aggregated to monthly ---
    rows: list[dict] = []
    for _, fac in facs.iterrows():
        fid = fac["id"]
        shard = S5P_DIR / f"{fid}.parquet"
        if not shard.exists():
            continue
        df_s = pd.read_parquet(shard)
        df_s["month"] = pd.to_datetime(df_s["datetime"]).dt.to_period("M").dt.to_timestamp()
        monthly = (
            df_s.groupby("month")
            .agg(
                no2_mean=("no2_mean", "mean"),
                no2_std=("no2_mean", "std"),
                no2_n_pixels=("no2_n_pixels", "mean"),
            )
            .reset_index()
        )
        for _, r in monthly.iterrows():
            rows.append({
                "facility_id": fid,
                "company": fac["company"],
                "cbam_scope": fac["cbam_scope"],
                "lat": float(fac["lat"]),
                "lon": float(fac["lon"]),
                "month": str(r["month"].date()),
                "split": split_lookup[fid],
                "no2_mean": float(r["no2_mean"]),
                "no2_std": float(r["no2_std"]) if pd.notna(r["no2_std"]) else float("nan"),
                "no2_n_pixels": int(r["no2_n_pixels"]),
                # placeholders for features we'll fill later
                "no2_anomaly_vs_background": float("nan"),
                "thermal_mean_k": float("nan"),
                "thermal_max_k": float("nan"),
                "wind_speed_mps": float("nan"),
                "wind_dir_deg": float("nan"),
                "pbl_height_m": float("nan"),
                "temp_2m_k": float("nan"),
                "grid_co2_g_per_kwh": float("nan"),
                "co2_t_month": float("nan"),
                "label_source": "",
                "label_confidence": "",
            })
    if not rows:
        log.warning("no S5P shards found yet — bench will be empty until extract_s5p_bench.py finishes")
        return
    df = pd.DataFrame(rows)
    log.info("monthly feature rows: %d", len(df))

    # --- 2) Strong labels from hand-curated disclosures ---
    if DISCLOSURES_CSV.exists():
        dis = pd.read_csv(DISCLOSURES_CSV)
        # Only annual totals — broadcast across the 12 months of that year.
        for _, r in dis.iterrows():
            metric = r["metric"]
            if not metric.startswith("co2_scope1") and metric != "co2_scope12_total_t":
                continue
            fid = r["id"]
            year = int(r["year"])
            annual_t = float(r["value"])
            monthly_t = annual_t / 12.0
            mask = (df["facility_id"] == fid) & df["month"].str.startswith(str(year))
            df.loc[mask, "co2_t_month"] = monthly_t
            df.loc[mask, "label_source"] = "disclosure"
            df.loc[mask, "label_confidence"] = r.get("confidence", "high")
            log.info("  strong label  %s  %d  %.0f t/year (×12 broadcast)", fid, year, annual_t)

    # --- 3) Weak labels from Climate TRACE ---
    if CT_PARQUET.exists():
        ct = pd.read_parquet(CT_PARQUET)
        # Climate TRACE rows already include iz_id from the proximity join.
        for fid, g in ct.groupby("iz_id"):
            if fid not in set(df["facility_id"]):
                continue
            co2_rows = g[g["gas"] == "co2e_100yr"]
            if co2_rows.empty:
                continue
            # Annual aggregate at the asset level — take the median across matched assets
            annual = co2_rows.groupby("year")["emissions"].sum()
            for year_str, annual_t in annual.items():
                if year_str is None:
                    continue
                year = int(year_str)
                mask = (
                    (df["facility_id"] == fid)
                    & df["month"].str.startswith(str(year))
                    & df["co2_t_month"].isna()
                )
                if mask.any():
                    df.loc[mask, "co2_t_month"] = float(annual_t) / 12.0
                    df.loc[mask, "label_source"] = "climate_trace"
                    df.loc[mask, "label_confidence"] = "low"

    n_labeled = df["co2_t_month"].notna().sum()
    log.info("rows with any label: %d / %d", n_labeled, len(df))

    # --- 4) Write splits ---
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    for s in ["train", "val", "test"]:
        out = BENCH_DIR / f"{s}.parquet"
        df[df["split"] == s].to_parquet(out, index=False)
        log.info("  %s → %s (%d rows)", s, out.relative_to(REPO), (df["split"] == s).sum())

    # Summary
    print()
    print("=" * 60)
    print(f"  facilities w/ S5P shards:   {df['facility_id'].nunique()}")
    print(f"  total monthly rows:         {len(df)}")
    print(f"  rows with any label:        {n_labeled}")
    print(f"  train / val / test rows:    "
          f"{(df['split']=='train').sum()} / {(df['split']=='val').sum()} / {(df['split']=='test').sum()}")
    print(f"  output:                     {BENCH_DIR.relative_to(REPO)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
