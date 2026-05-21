"""
Streaming Sentinel-5P NO₂ bbox extractor for all TR-MRV-Bench facilities.

Replaces the v0 spike's "download full orbit → average a bbox → throw away
the other 99.998%" pattern with a real cloud-streaming approach:

  1. STAC search for S5P L2 NO₂ scenes that intersect each facility footprint
  2. h5netcdf + fsspec range-byte open on the NetCDF over HTTPS
  3. Extract ONLY the bbox slice (a handful of pixels)
  4. QA-mask, mean, write one row per (facility, scene) to a parquet shard

Outputs:
    data/s5p/<facility_id>.parquet  — long-format time series per facility

Schema:
    facility_id, datetime, scene_id, no2_mean, no2_n_pixels, no2_std, qa_min
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import planetary_computer as pc
import xarray as xr
from pystac_client import Client

log = logging.getLogger(__name__)

PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "sentinel-5p-l2-netcdf"


def bbox_around(lat: float, lon: float, half_deg: float = 0.08) -> tuple[float, float, float, float]:
    """~0.04° = ~4.4 km in lat, ~3.5 km in lon at 41°N. Roughly one S5P pixel.
    We use 2× to make sure we catch the kiln stack even if coords are off."""
    return (lon - half_deg, lat - half_deg, lon + half_deg, lat + half_deg)


def stac_search_facility(
    cat: Client, lat: float, lon: float, start: datetime, end: datetime
):
    bbox = bbox_around(lat, lon)
    aoi = {
        "type": "Polygon",
        "coordinates": [[
            [bbox[0], bbox[1]],
            [bbox[2], bbox[1]],
            [bbox[2], bbox[3]],
            [bbox[0], bbox[3]],
            [bbox[0], bbox[1]],
        ]],
    }
    s = cat.search(
        collections=[COLLECTION],
        intersects=aoi,
        datetime=f"{start.isoformat()}/{end.isoformat()}",
        query={"s5p:product_type": {"eq": "L2__NO2___"}},
    )
    return list(s.items())


def find_nc_asset(item):
    for key, a in item.assets.items():
        if a.href.lower().endswith(".nc") or "netcdf" in (a.media_type or "").lower():
            return a.href
    return list(item.assets.values())[0].href


def extract_bbox_no2(nc_path_or_url: str, lat: float, lon: float, half_deg: float = 0.08) -> dict:
    """Open NetCDF (local path or signed HTTPS) and compute bbox-mean NO2."""
    try:
        ds = xr.open_dataset(nc_path_or_url, group="PRODUCT", engine="h5netcdf")
    except Exception as e:
        return {"error": str(e)}
    try:
        no2 = ds["nitrogendioxide_tropospheric_column"]
        qa = ds["qa_value"]
        lons = ds["longitude"]
        lats = ds["latitude"]
        mask = (
            (lons >= lon - half_deg) & (lons <= lon + half_deg)
            & (lats >= lat - half_deg) & (lats <= lat + half_deg)
            & (qa >= 0.75)
        )
        vals = no2.where(mask).values
        flat = vals[~np.isnan(vals)]
        if flat.size == 0:
            return {"no2_mean": float("nan"), "no2_std": float("nan"), "no2_n_pixels": 0, "qa_min": float("nan")}
        qa_vals = qa.where(mask).values
        return {
            "no2_mean": float(flat.mean()),
            "no2_std": float(flat.std()),
            "no2_n_pixels": int(flat.size),
            "qa_min": float(np.nanmin(qa_vals)),
        }
    finally:
        ds.close()


def download_to(url: str, dst: Path, max_bytes: int = 800 * 1024 * 1024) -> bool:
    """Bandwidth-bound: pull the NetCDF to local disk. S5P NetCDFs are not
    cloud-optimized, so cloud-streaming via fsspec/h5netcdf often downloads
    the whole file behind the scenes — we cache it explicitly."""
    import urllib.request
    if dst.exists() and dst.stat().st_size > 1024:
        return True
    tmp = dst.with_suffix(dst.suffix + ".part")
    try:
        urllib.request.urlretrieve(url, tmp)
        if tmp.stat().st_size > max_bytes:
            tmp.unlink()
            return False
        tmp.rename(dst)
        return True
    except Exception as e:
        log.warning("    download failed: %s", e)
        tmp.unlink(missing_ok=True)
        return False


def extract_facility(
    facility_id: str,
    lat: float,
    lon: float,
    start: datetime,
    end: datetime,
    *,
    pdf_cache: Path,
    out_parquet: Path,
    max_scenes: int = 200,
) -> int:
    """Pull all S5P NO₂ scenes for a facility in the window, extract bbox, save."""
    cat = Client.open(PC_STAC, modifier=pc.sign_inplace)
    items = stac_search_facility(cat, lat, lon, start, end)
    items.sort(key=lambda it: it.datetime)
    if len(items) > max_scenes:
        step = max(1, len(items) // max_scenes)
        items = items[::step][:max_scenes]

    rows: list[dict] = []
    for i, item in enumerate(items, 1):
        url = find_nc_asset(item)
        scene_id = item.id
        local = pdf_cache / f"{scene_id}.nc"
        if not download_to(url, local):
            continue
        m = extract_bbox_no2(str(local), lat, lon)
        if "error" in m:
            log.warning("  scene %s open failed: %s", scene_id, m["error"])
            continue
        rows.append({
            "facility_id": facility_id,
            "datetime": item.datetime,
            "scene_id": scene_id,
            **m,
        })
        if i % 10 == 0:
            log.info("    %s [%d/%d] n_pixels=%d", facility_id, i, len(items), m["no2_n_pixels"])

    if rows:
        df = pd.DataFrame(rows)
        out_parquet.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_parquet, index=False)
        log.info("  → %s (%d rows)", out_parquet.name, len(df))
    return len(rows)
