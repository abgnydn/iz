"""
Climate TRACE v6 API client.

Pulls Turkish CBAM-scope facility-level emissions for use as weak supervision
labels in TR-MRV-Bench. Per the audit (E41-iz-stack-audit), Climate TRACE
labels are ±50% accuracy — used as soft targets in regression training,
weighted lower than CDP / direct-disclosure ground truth.

API base: https://api.climatetrace.org/v6
"""

from __future__ import annotations

import logging
from typing import Iterable

import httpx
import pandas as pd

API = "https://api.climatetrace.org/v6"
INDUSTRIAL_SECTORS = [
    "cement",
    "iron-and-steel",
    "aluminum",
    "fertilizer",            # may map to chemicals; we filter result-side too
    "chemicals",
    "petrochemicals",
    "lime",
    "glass",
    "pulp-and-paper",
]
log = logging.getLogger(__name__)


def fetch_tr_assets(
    *,
    countries: Iterable[str] = ("TUR",),
    sectors: Iterable[str] | None = None,
    timeout: float = 60.0,
) -> pd.DataFrame:
    """Pull all Turkish CBAM-scope facility-level assets from Climate TRACE v6.

    Returns a long-format DataFrame with columns:
        ct_asset_id, name, native_id, country, sector, asset_type,
        reporting_entity, lat, lon, year, month, gas, activity, activity_units,
        emissions, ef, ef_units, capacity, capacity_units, capacity_factor
    """
    base_params = {"countries": ",".join(countries), "limit": 1000}
    if sectors:
        base_params["sectors"] = ",".join(sectors)

    all_assets: list = []
    with httpx.Client(http2=True, timeout=timeout) as client:
        offset = 0
        while True:
            params = {**base_params, "offset": offset}
            log.info("GET %s/assets %s", API, params)
            r = client.get(f"{API}/assets", params=params)
            r.raise_for_status()
            page = r.json()
            page_assets = page.get("assets", []) or []
            all_assets.extend(page_assets)
            if len(page_assets) < base_params["limit"]:
                break
            offset += len(page_assets)
            if offset > 50000:
                log.warning("pagination ceiling hit; stopping")
                break
        payload = {"assets": all_assets}

    rows: list[dict] = []
    assets = payload.get("assets", [])
    log.info("  received %d assets", len(assets))
    for a in assets:
        # Geographic centroid lives in different keys depending on asset shape.
        centroid = a.get("Centroid") or {}
        lat = centroid.get("Geometry", [None, None])[1] if isinstance(centroid.get("Geometry"), list) else None
        lon = centroid.get("Geometry", [None, None])[0] if isinstance(centroid.get("Geometry"), list) else None

        base = {
            "ct_asset_id": a.get("Id"),
            "name": a.get("Name"),
            "native_id": a.get("NativeId"),
            "country": a.get("Country"),
            "sector": a.get("Sector"),
            "asset_type": a.get("AssetType"),
            "reporting_entity": a.get("ReportingEntity"),
            "lat": lat,
            "lon": lon,
        }
        emissions_list = a.get("EmissionsSummary") or []
        if not emissions_list:
            rows.append({**base, "year": None, "month": None, "gas": None, "emissions": None})
            continue
        for em in emissions_list:
            rows.append(
                {
                    **base,
                    "year": em.get("StartTime", "")[:4] if em.get("StartTime") else None,
                    "month": em.get("StartTime", "")[5:7] if em.get("StartTime") else None,
                    "gas": em.get("Gas"),
                    "activity": em.get("Activity"),
                    "activity_units": em.get("ActivityUnits"),
                    "emissions": em.get("Emissions"),
                    "ef": em.get("EmissionsFactor"),
                    "ef_units": em.get("EmissionsFactorUnits"),
                    "capacity": em.get("Capacity"),
                    "capacity_units": em.get("CapacityUnits"),
                    "capacity_factor": em.get("CapacityFactor"),
                }
            )

    df = pd.DataFrame(rows)
    log.info("  flattened to %d rows over %d unique assets", len(df), df["ct_asset_id"].nunique())
    return df


def filter_industrial(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to CBAM-relevant sectors only."""
    return df[df["sector"].isin(INDUSTRIAL_SECTORS)].copy()
