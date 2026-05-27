"""
Multi-facility S5P NO₂ batch extractor for TR-MRV-Bench.

Strategy: each Sentinel-5P TROPOMI orbit covers a ~2600km swath. Multiple
TR facilities can be inside the same orbit. So we:

  for each scene in (time range, intersects TR bbox):
      download once
      for each facility in scene's coverage:
          extract NO₂ over a 0.06° bbox centered on the plant
          extract NO₂ over a "background" bbox 70km offset to compute Δ
      cache the per-facility NO₂ row to parquet
      delete the scene file (free disk)

Output: data/s5p_no2_per_facility.parquet
  columns: facility_id, scene_id, datetime, plant_no2_mean, plant_n_pixels,
           background_no2_mean, background_n_pixels, delta_no2

Then bin/aggregate_s5p.py reduces to per-facility mean over the time window
for use as a model feature.

Usage:
  .venv/bin/python bin/extract_s5p_no2_all.py --days 30 --max-scenes 20

  --days       : days back from today to query (default 30)
  --max-scenes : maximum scenes to process (cost/time bound)
"""
from __future__ import annotations
import argparse
import logging
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import planetary_computer as pc
import xarray as xr
from pystac_client import Client

REPO = Path(__file__).resolve().parent.parent
FAC_CSV = REPO / "data" / "tr_facilities.csv"
S5P_DIR = REPO / "data" / "s5p"
OUT_PARQUET = REPO / "data" / "s5p_no2_per_facility.parquet"
LOG = REPO / "logs" / "extract_s5p_no2_all.log"

S5P_DIR.mkdir(parents=True, exist_ok=True)
LOG.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG, mode="a"), logging.StreamHandler()],
)
log = logging.getLogger("iz.s5p.all")

# Plant bbox half-width (degrees); ~0.06° ≈ 5-6 km at TR latitudes
PLANT_HALF = 0.06
# Background bbox is offset 0.6° to the north (or whatever wind-upwind direction
# would be); ~70 km. For v0 we just pick a fixed offset; future work could rotate
# upwind based on ERA5.
BACKGROUND_OFFSET = (0.6, 0.0)  # (dlat, dlon)
# TR bounding box for the STAC search (slightly padded)
TR_BBOX = (25.5, 35.8, 45.0, 42.5)  # (lon_min, lat_min, lon_max, lat_max)


def stac_search(start: datetime, end: datetime, with_filter: bool = True):
    cat = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=pc.sign_inplace,
    )
    tr_aoi = {
        "type": "Polygon",
        "coordinates": [[
            [TR_BBOX[0], TR_BBOX[1]],
            [TR_BBOX[2], TR_BBOX[1]],
            [TR_BBOX[2], TR_BBOX[3]],
            [TR_BBOX[0], TR_BBOX[3]],
            [TR_BBOX[0], TR_BBOX[1]],
        ]],
    }
    kwargs = dict(
        collections=["sentinel-5p-l2-netcdf"],
        intersects=tr_aoi,
        datetime=f"{start.isoformat()}/{end.isoformat()}",
    )
    if with_filter:
        kwargs["query"] = {"s5p:product_type": {"eq": "L2__NO2___"}}
    return list(cat.search(**kwargs).items())


def find_nc_asset(item):
    for key, a in item.assets.items():
        href = a.href.lower()
        if href.endswith(".nc") or "netcdf" in (a.media_type or "").lower():
            return key, a
    key = next(iter(item.assets))
    return key, item.assets[key]


def bbox_mean(no2, qa, lon, lat, bbox: tuple[float, float, float, float]) -> tuple[float, int]:
    lo, la, hi, ha = bbox
    mask = (lon >= lo) & (lon <= hi) & (lat >= la) & (lat <= ha) & (qa >= 0.75)
    vals = no2.where(mask).values
    flat = vals[~np.isnan(vals)]
    return (float(flat.mean()), int(flat.size)) if flat.size else (float("nan"), 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30, help="rolling window from today (ignored if --start/--end given)")
    ap.add_argument("--start", type=str, default=None, help="absolute start date YYYY-MM-DD")
    ap.add_argument("--end", type=str, default=None, help="absolute end date YYYY-MM-DD")
    ap.add_argument("--max-scenes", type=int, default=20)
    ap.add_argument("--keep-files", action="store_true", help="don't delete scene files after processing")
    args = ap.parse_args()

    facs = pd.read_csv(FAC_CSV)
    log.info("facilities: %d", len(facs))

    # Pre-compute per-facility bboxes
    bboxes = {}
    bg_bboxes = {}
    for _, f in facs.iterrows():
        lat, lon = float(f["lat"]), float(f["lon"])
        bboxes[f["id"]] = (lon - PLANT_HALF, lat - PLANT_HALF, lon + PLANT_HALF, lat + PLANT_HALF)
        bg_lat = lat + BACKGROUND_OFFSET[0]
        bg_lon = lon + BACKGROUND_OFFSET[1]
        bg_bboxes[f["id"]] = (bg_lon - PLANT_HALF, bg_lat - PLANT_HALF,
                              bg_lon + PLANT_HALF, bg_lat + PLANT_HALF)

    if args.start and args.end:
        start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=args.days)
    log.info("window: %s → %s  max-scenes: %d", start.date(), end.date(), args.max_scenes)

    items = stac_search(start, end, with_filter=True)
    if not items:
        log.warning("no items with L2__NO2___ filter, retrying without")
        items = stac_search(start, end, with_filter=False)
        items = [
            it for it in items
            if "no2" in it.id.lower() or it.properties.get("s5p:product_type") == "L2__NO2___"
        ]
    log.info("STAC returned %d items", len(items))

    items.sort(key=lambda it: it.datetime, reverse=True)
    items = items[: args.max_scenes]
    log.info("processing %d scenes (most recent first)", len(items))

    # Resume support: read existing parquet and skip scene_ids already done
    done_scene_ids: set[str] = set()
    existing_df = None
    if OUT_PARQUET.exists():
        existing_df = pd.read_parquet(OUT_PARQUET)
        done_scene_ids = set(existing_df["scene_id"].unique())
        log.info("resume: %d scenes already in parquet", len(done_scene_ids))

    new_rows = []
    for idx, item in enumerate(items, 1):
        if item.id in done_scene_ids:
            log.info("[%d/%d] %s — already done, skip", idx, len(items), item.id)
            continue

        asset_key, asset = find_nc_asset(item)
        when = item.datetime
        log.info("[%d/%d] %s | %s | asset=%s", idx, len(items), when.strftime("%Y-%m-%d %H:%M"), item.id, asset_key)

        local = S5P_DIR / f"{item.id}.nc"
        try:
            if local.exists() and local.stat().st_size > 0:
                log.info("  cached: %.1f MB", local.stat().st_size / 1e6)
            else:
                tmp = local.with_suffix(local.suffix + ".part")
                log.info("  downloading…")
                urllib.request.urlretrieve(asset.href, tmp)
                tmp.rename(local)
                log.info("  done: %.1f MB", local.stat().st_size / 1e6)
        except Exception as e:
            log.error("  download failed: %s", e)
            continue

        try:
            prod = xr.open_dataset(local, group="PRODUCT", engine="h5netcdf")
            no2 = prod["nitrogendioxide_tropospheric_column"]
            qa = prod["qa_value"]
            lon = prod["longitude"]
            lat = prod["latitude"]
        except Exception as e:
            log.error("  open_dataset failed: %s", e)
            if not args.keep_files:
                local.unlink(missing_ok=True)
            continue

        try:
            # Per-facility extraction
            per_fac_rows = []
            for fid, plant_bb in bboxes.items():
                p_mean, p_n = bbox_mean(no2, qa, lon, lat, plant_bb)
                bg_mean, bg_n = bbox_mean(no2, qa, lon, lat, bg_bboxes[fid])
                if p_n > 0 or bg_n > 0:  # only record if any pixel hit
                    per_fac_rows.append({
                        "facility_id": fid,
                        "scene_id": item.id,
                        "datetime": when,
                        "plant_no2_mean": p_mean,
                        "plant_n_pixels": p_n,
                        "background_no2_mean": bg_mean,
                        "background_n_pixels": bg_n,
                        "delta_no2": (p_mean - bg_mean) if (not np.isnan(p_mean) and not np.isnan(bg_mean)) else float("nan"),
                    })
            log.info("  %d facilities hit", len(per_fac_rows))
            new_rows.extend(per_fac_rows)

            # Incremental save every 5 scenes so we don't lose work
            if len(new_rows) > 0 and idx % 5 == 0:
                df_so_far = pd.DataFrame(new_rows)
                if existing_df is not None:
                    combined = pd.concat([existing_df, df_so_far], ignore_index=True)
                else:
                    combined = df_so_far
                combined.to_parquet(OUT_PARQUET, index=False)
                log.info("  ← checkpoint saved (%d rows total)", len(combined))
        except Exception as e:
            log.error("  extraction failed: %s", e)
        finally:
            prod.close()
            if not args.keep_files:
                local.unlink(missing_ok=True)

    # Final save
    if new_rows:
        df_new = pd.DataFrame(new_rows)
        if existing_df is not None:
            df_out = pd.concat([existing_df, df_new], ignore_index=True)
        else:
            df_out = df_new
        df_out.to_parquet(OUT_PARQUET, index=False)
        log.info("wrote %d new rows (%d total) → %s", len(new_rows), len(df_out), OUT_PARQUET.relative_to(REPO))
    else:
        log.info("no new rows")

    return 0


if __name__ == "__main__":
    sys.exit(main())
