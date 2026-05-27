"""
Reduce per-scene S5P NO₂ observations to per-facility aggregate features.

Input:  data/s5p_no2_per_facility.parquet  (long: facility × scene)
Output: data/s5p_no2_aggregated.csv         (one row per facility)

Aggregate features per facility:
  no2_plant_mean    : mean of plant_no2_mean across all scenes where the
                       plant bbox had ≥1 valid pixel
  no2_plant_std     : std of the same
  no2_bg_mean       : mean of background_no2_mean
  no2_delta_mean    : mean of (plant - background) — the "excess" attributed
                       to the plant. Positive = plant emits NO₂ above local
                       background.
  no2_delta_std     : std of the delta
  no2_n_obs         : number of scenes with ≥1 plant pixel
  no2_n_obs_bg      : number of scenes with ≥1 background pixel
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
IN_PARQUET = REPO / "data" / "s5p_no2_per_facility.parquet"
OUT_CSV = REPO / "data" / "s5p_no2_aggregated.csv"


def main() -> int:
    if not IN_PARQUET.exists():
        print(f"no input: {IN_PARQUET}", file=sys.stderr)
        return 1

    df = pd.read_parquet(IN_PARQUET)
    print(f"loaded {len(df)} rows, {df.facility_id.nunique()} facilities, {df.scene_id.nunique()} scenes")
    print(f"window: {df.datetime.min()} → {df.datetime.max()}")

    # Filter to rows where at least one of plant/background had pixels
    df_plant = df[df["plant_n_pixels"] > 0]
    df_bg = df[df["background_n_pixels"] > 0]

    g_plant = df_plant.groupby("facility_id").agg(
        no2_plant_mean=("plant_no2_mean", "mean"),
        no2_plant_std=("plant_no2_mean", "std"),
        no2_n_obs=("plant_no2_mean", "count"),
    )
    g_bg = df_bg.groupby("facility_id").agg(
        no2_bg_mean=("background_no2_mean", "mean"),
        no2_n_obs_bg=("background_no2_mean", "count"),
    )

    # delta: per-row plant - background where both exist
    both = df[(df["plant_n_pixels"] > 0) & (df["background_n_pixels"] > 0)].copy()
    both["delta"] = both["plant_no2_mean"] - both["background_no2_mean"]
    g_delta = both.groupby("facility_id").agg(
        no2_delta_mean=("delta", "mean"),
        no2_delta_std=("delta", "std"),
        no2_n_obs_both=("delta", "count"),
    )

    out = g_plant.join(g_bg, how="outer").join(g_delta, how="outer")
    out = out.reset_index()
    # Fill NaN with 0 for std with n=1, leave means as NaN
    out["no2_plant_std"] = out["no2_plant_std"].fillna(0)
    out["no2_delta_std"] = out["no2_delta_std"].fillna(0)
    out["no2_n_obs"] = out["no2_n_obs"].fillna(0).astype(int)
    out["no2_n_obs_bg"] = out["no2_n_obs_bg"].fillna(0).astype(int)
    out["no2_n_obs_both"] = out["no2_n_obs_both"].fillna(0).astype(int)

    out.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV.relative_to(REPO)}  ({len(out)} facilities)")
    print()
    # Quick sanity: largest plant_no2 facilities
    top = out.nlargest(10, "no2_plant_mean")
    print("Top 10 facilities by mean plant NO₂:")
    for _, r in top.iterrows():
        print(f"  {r.facility_id:30s} plant={r.no2_plant_mean:.2e}  delta={r.no2_delta_mean:.2e}  n={int(r.no2_n_obs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
