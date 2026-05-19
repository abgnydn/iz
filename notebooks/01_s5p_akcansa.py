"""
E40-prep — Sentinel-5P NO₂ over Akçansa Büyükçekmece cement plant.

v0 spike for the iz CBAM MRV product. Goal: prove we can pull S5P data,
spatial-mean it over a plant bbox, subtract a rural background, and plot a
defensible 90-day trend. Numbers are NOT production-quality — this is the
first end-to-end pipe test.

Why NO₂: Sentinel-5P does not measure CO₂. NO₂ (NOx) is the standard
satellite activity proxy for cement / power-plant combustion intensity.
Cement clinker kilns emit ~1–3 kg NOx per ton of clinker; tropospheric
NO₂ column density correlates with throughput at the plant scale.

CO₂ itself is reconstructed downstream from production tonnes × cement-
specific emission factor, with NO₂ as the activity sanity check.
"""

import logging
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import planetary_computer as pc
import xarray as xr
from pystac_client import Client

REPO = Path(__file__).resolve().parent.parent
LOG_PATH = REPO / "logs" / "01_s5p_akcansa.log"
PNG_PATH = REPO / "reports" / "akcansa_s5p_v0.png"
CSV_PATH = REPO / "reports" / "akcansa_s5p_v0.csv"
S5P_DIR = REPO / "data" / "s5p"
S5P_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger("iz.s5p")

# --- target bounding boxes -----------------------------------------------
# Akçansa Büyükçekmece plant (Mimarsinan coastal cement complex)
PLANT_BBOX = (28.50, 40.99, 28.62, 41.07)   # (lon_min, lat_min, lon_max, lat_max)
# Rural Thrace background — interior, low-industrial, ~70 km NW
RURAL_BBOX = (27.00, 41.50, 27.20, 41.65)
WINDOW_DAYS = 90
MAX_SCENES = 6  # bandwidth cap for v0; raise once pipeline is stable

END = datetime.now(timezone.utc)
START = END - timedelta(days=WINDOW_DAYS)

log.info("plant bbox  : %s", PLANT_BBOX)
log.info("rural bbox  : %s", RURAL_BBOX)
log.info("window      : %s → %s", START.date(), END.date())
log.info("max scenes  : %d", MAX_SCENES)

# --- STAC query ----------------------------------------------------------
cat = Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=pc.sign_inplace,
)

plant_aoi = {
    "type": "Polygon",
    "coordinates": [[
        [PLANT_BBOX[0], PLANT_BBOX[1]],
        [PLANT_BBOX[2], PLANT_BBOX[1]],
        [PLANT_BBOX[2], PLANT_BBOX[3]],
        [PLANT_BBOX[0], PLANT_BBOX[3]],
        [PLANT_BBOX[0], PLANT_BBOX[1]],
    ]],
}


def stac_search(with_filter: bool):
    kwargs = dict(
        collections=["sentinel-5p-l2-netcdf"],
        intersects=plant_aoi,
        datetime=f"{START.isoformat()}/{END.isoformat()}",
    )
    if with_filter:
        kwargs["query"] = {"s5p:product_type": {"eq": "L2__NO2___"}}
    return list(cat.search(**kwargs).items())


items = stac_search(with_filter=True)
if not items:
    log.warning("filter returned 0 items; retrying without product_type filter")
    items = stac_search(with_filter=False)
    items = [
        it for it in items
        if "no2" in it.id.lower() or it.properties.get("s5p:product_type") == "L2__NO2___"
    ]

log.info("STAC returned %d S5P NO₂ items", len(items))
if not items:
    log.error("no items — bail")
    sys.exit(1)

# Subsample evenly over the window
items.sort(key=lambda it: it.datetime)
if len(items) > MAX_SCENES:
    step = len(items) // MAX_SCENES
    items = items[::step][:MAX_SCENES]
log.info("processing %d scenes", len(items))


# --- per-scene processing -----------------------------------------------
def find_nc_asset(item):
    """S5P MPC items have one NetCDF; find it without assuming the key name."""
    for key, a in item.assets.items():
        href = a.href.lower()
        if href.endswith(".nc") or "netcdf" in (a.media_type or "").lower():
            return key, a
    # fallback: first asset
    key = next(iter(item.assets))
    return key, item.assets[key]


def download(url: str, dst: Path) -> Path:
    if dst.exists() and dst.stat().st_size > 0:
        log.info("  cached: %s (%.1f MB)", dst.name, dst.stat().st_size / 1e6)
        return dst
    log.info("  downloading %s …", dst.name)
    tmp = dst.with_suffix(dst.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dst)
    log.info("  done: %.1f MB", dst.stat().st_size / 1e6)
    return dst


def bbox_mean(prod: xr.Dataset, bbox):
    lo, la, hi, ha = bbox
    no2 = prod["nitrogendioxide_tropospheric_column"]
    qa = prod["qa_value"]
    lon = prod["longitude"]
    lat = prod["latitude"]
    mask = (
        (lon >= lo) & (lon <= hi)
        & (lat >= la) & (lat <= ha)
        & (qa >= 0.75)
    )
    vals = no2.where(mask).values
    flat = vals[~np.isnan(vals)]
    return (float(flat.mean()), int(flat.size)) if flat.size else (float("nan"), 0)


rows = []
for i, item in enumerate(items, 1):
    asset_key, asset = find_nc_asset(item)
    when = item.datetime
    log.info("[%d/%d] %s | %s | asset=%s", i, len(items), when.strftime("%Y-%m-%d"), item.id, asset_key)

    local = S5P_DIR / f"{item.id}.nc"
    try:
        download(asset.href, local)
    except Exception as e:
        log.error("  download failed: %s", e)
        continue

    try:
        # S5P NetCDFs use a group hierarchy; PRODUCT group holds the science vars
        prod = xr.open_dataset(local, group="PRODUCT", engine="h5netcdf")
    except Exception as e:
        log.error("  open_dataset failed: %s", e)
        continue

    try:
        p_mean, p_n = bbox_mean(prod, PLANT_BBOX)
        r_mean, r_n = bbox_mean(prod, RURAL_BBOX)
    finally:
        prod.close()

    delta = p_mean - r_mean if not (np.isnan(p_mean) or np.isnan(r_mean)) else float("nan")
    rows.append({
        "datetime": when,
        "plant_no2": p_mean,
        "plant_n": p_n,
        "rural_no2": r_mean,
        "rural_n": r_n,
        "delta": delta,
    })
    log.info(
        "  plant=%.3e (n=%d), rural=%.3e (n=%d), Δ=%.3e",
        p_mean, p_n, r_mean, r_n, delta,
    )

if not rows:
    log.error("no rows — abort")
    sys.exit(2)

df = pd.DataFrame(rows)
df.to_csv(CSV_PATH, index=False)
log.info("wrote %d rows → %s", len(df), CSV_PATH.relative_to(REPO))

# --- plot ----------------------------------------------------------------
df_plot = df.dropna(subset=["plant_no2", "rural_no2"])
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.plot(df_plot["datetime"], df_plot["plant_no2"] * 1e6, "o-", label="Akçansa Büyükçekmece (plant bbox)")
ax.plot(df_plot["datetime"], df_plot["rural_no2"] * 1e6, "o-", label="Rural Thrace (background bbox)", alpha=0.65)
ax.plot(df_plot["datetime"], df_plot["delta"] * 1e6, "s--", label="Plant − Background", color="crimson")
ax.set_ylabel(r"Tropospheric NO$_2$ column ($\mu$mol/m²)")
ax.set_xlabel("Date (UTC)")
ax.set_title(f"Sentinel-5P NO₂ — Akçansa Büyükçekmece vs. rural Thrace, last {WINDOW_DAYS}d  (v0 spike, n={len(df_plot)})")
ax.legend(loc="best")
ax.grid(alpha=0.3)
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(PNG_PATH, dpi=120)
log.info("wrote chart → %s", PNG_PATH.relative_to(REPO))
print(f"\n✓ done: {len(df_plot)} scenes plotted → {PNG_PATH.relative_to(REPO)}")
