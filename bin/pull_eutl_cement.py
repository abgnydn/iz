"""
Verifier B6 — pull EUTL verified Scope 1 emissions for all EU cement
installations via the euets.info public API (no auth needed).

Output:
    data/eutl/eutl_cement_installations.parquet — metadata (name, NACE,
        lat/lon, parent, registry) for ~372 EU cement clinker installations
    data/eutl/eutl_cement_compliance.parquet — per-installation × per-year
        verified emissions, allocated allowances, surrendered allowances
        (2005-2024+)

Why this matters:
    - Adds ~7,400 audit-grade EU plant-years to TR-MRV-Bench (n=21)
    - All verified by accredited third-party verifiers under EU ETS Article 15
    - Independent of operator IAR disclosure (different audit trail)
    - Direct external-validity test for the cf-corrected formula
"""

from __future__ import annotations

import base64
import json
import logging
import time
import zlib
from pathlib import Path

import httpx
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
LOG = REPO / "logs" / "b6_eutl_cement.log"
OUT_INST = REPO / "data" / "eutl" / "eutl_cement_installations.parquet"
OUT_COMP = REPO / "data" / "eutl" / "eutl_cement_compliance.parquet"

API = "https://2j6zr78sq1.execute-api.eu-central-1.amazonaws.com/prod"


def fetch(path: str, client: httpx.Client) -> dict | list:
    r = client.get(f"{API}/{path}", timeout=60.0)
    r.raise_for_status()
    j = r.json()
    body = j.get("body", "")
    if not body:
        return []
    return json.loads(zlib.decompress(base64.b64decode(body)))


def main() -> None:
    REPO.joinpath("logs").mkdir(exist_ok=True)
    REPO.joinpath("data", "eutl").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(LOG), logging.StreamHandler()],
    )
    log = logging.getLogger("eutl.cement")

    with httpx.Client(http2=True, headers={"user-agent": "iz-bench/0.1"}) as client:
        all_inst = pd.DataFrame(fetch("installations", client))
        log.info("total EU ETS installations: %d", len(all_inst))

        cement = all_inst[
            all_inst["activity"].str.contains("cement clinker", case=False, na=False)
        ].copy()
        log.info("cement clinker installations: %d", len(cement))

        # Pull full metadata + compliance per cement installation
        meta_rows: list[dict] = []
        comp_rows: list[dict] = []
        for i, inst_id in enumerate(cement["id"].tolist(), 1):
            try:
                inst = fetch(f"installation?id={inst_id}", client)
                if inst:
                    meta_rows.append(inst[0])
                comp = fetch(f"compliance?id={inst_id}", client)
                for row in comp:
                    comp_rows.append({"id": inst_id, **row})
                if i % 25 == 0:
                    log.info("  [%d/%d] %s", i, len(cement), inst_id)
                time.sleep(0.05)
            except Exception as e:
                log.warning("[%d/%d] %s failed: %s", i, len(cement), inst_id, e)

    inst_df = pd.DataFrame(meta_rows)
    comp_df = pd.DataFrame(comp_rows)
    log.info("meta rows: %d  compliance rows: %d", len(inst_df), len(comp_df))

    inst_df.to_parquet(OUT_INST, index=False)
    comp_df.to_parquet(OUT_COMP, index=False)
    log.info("wrote %s and %s", OUT_INST.relative_to(REPO), OUT_COMP.relative_to(REPO))

    # Summary stats
    verified = comp_df[comp_df["verified"].notna()].copy()
    verified["year"] = verified["year"].astype(int)
    latest = verified.groupby("id").apply(lambda g: g.loc[g["year"].idxmax()])
    log.info("plants with at least one verified year: %d", len(latest))
    log.info("latest-year verified emissions total: %.2f Mt", latest["verified"].sum() / 1e6)
    by_country = (
        latest.merge(inst_df[["id", "country"]], on="id")
        .groupby("country")
        .agg(plants=("id", "nunique"), total_mt=("verified", lambda s: s.sum() / 1e6))
        .sort_values("total_mt", ascending=False)
    )
    log.info("per-country summary:\n%s", by_country.head(15).to_string())


if __name__ == "__main__":
    main()
