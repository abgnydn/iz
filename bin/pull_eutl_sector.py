"""
Generalised EUTL pull — fetches metadata + per-year verified emissions for
EU ETS installations matching a sector activity pattern.

Usage:
    uv run python bin/pull_eutl_sector.py steel
    uv run python bin/pull_eutl_sector.py aluminum
    uv run python bin/pull_eutl_sector.py fertilizer

Adds:
    data/eutl/eutl_<sector>_installations.parquet
    data/eutl/eutl_<sector>_compliance.parquet
"""

from __future__ import annotations

import base64
import json
import logging
import sys
import time
import zlib
from pathlib import Path

import httpx
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
API = "https://2j6zr78sq1.execute-api.eu-central-1.amazonaws.com/prod"

SECTOR_FILTERS = {
    "steel": {
        # "Production or processing of ferrous metals" (262) is too broad —
        # includes rolling mills, foundries, downstream. Stick to primary
        # / secondary fusion (pig iron + steel) to match TR-bench BF/BOF + EAF
        # scope.
        "activity_contains": ["pig iron or steel"],
        "exclude": [],
    },
    "aluminum": {
        "activity_contains": ["primary aluminium", "secondary aluminium"],
        "exclude": [],
    },
    "fertilizer": {
        "activity_contains": ["nitric acid", "ammonia"],
        "exclude": [],
    },
}


def fetch(path: str, client: httpx.Client) -> list | dict:
    r = client.get(f"{API}/{path}", timeout=60.0)
    r.raise_for_status()
    j = r.json()
    body = j.get("body", "")
    if not body:
        return []
    return json.loads(zlib.decompress(base64.b64decode(body)))


def main(sector: str) -> None:
    REPO.joinpath("logs").mkdir(exist_ok=True)
    REPO.joinpath("data", "eutl").mkdir(parents=True, exist_ok=True)
    out_inst = REPO / "data" / "eutl" / f"eutl_{sector}_installations.parquet"
    out_comp = REPO / "data" / "eutl" / f"eutl_{sector}_compliance.parquet"
    log_path = REPO / "logs" / f"b6_eutl_{sector}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(log_path, mode="w"), logging.StreamHandler()],
        force=True,
    )
    log = logging.getLogger(f"eutl.{sector}")

    flt = SECTOR_FILTERS[sector]
    includes = [s.lower() for s in flt["activity_contains"]]
    excludes = [s.lower() for s in flt["exclude"]]

    with httpx.Client(http2=True, headers={"user-agent": "iz-bench/0.1"}) as client:
        all_inst = pd.DataFrame(fetch("installations", client))
        log.info("total EU ETS installations: %d", len(all_inst))

        def matches(activity: str | None) -> bool:
            if not activity:
                return False
            al = activity.lower()
            if any(x in al for x in excludes):
                return False
            return any(x in al for x in includes)

        sel = all_inst[all_inst["activity"].apply(matches)].copy()
        log.info("%s installations matched: %d", sector, len(sel))
        log.info("activity breakdown:\n%s", sel["activity"].value_counts().to_string())

        meta_rows: list[dict] = []
        comp_rows: list[dict] = []
        for i, inst_id in enumerate(sel["id"].tolist(), 1):
            try:
                inst = fetch(f"installation?id={inst_id}", client)
                if inst:
                    meta_rows.append(inst[0])
                comp = fetch(f"compliance?id={inst_id}", client)
                for row in comp:
                    comp_rows.append({"id": inst_id, **row})
                if i % 25 == 0:
                    log.info("  [%d/%d] %s", i, len(sel), inst_id)
                time.sleep(0.05)
            except Exception as e:
                log.warning("[%d/%d] %s failed: %s", i, len(sel), inst_id, e)

    inst_df = pd.DataFrame(meta_rows)
    comp_df = pd.DataFrame(comp_rows)
    log.info("meta rows: %d  compliance rows: %d", len(inst_df), len(comp_df))

    inst_df.to_parquet(out_inst, index=False)
    comp_df.to_parquet(out_comp, index=False)
    log.info("wrote %s and %s", out_inst.relative_to(REPO), out_comp.relative_to(REPO))

    verified = comp_df[comp_df["verified"].notna()].copy()
    verified["year"] = verified["year"].astype(int)
    latest = verified.groupby("id").apply(lambda g: g.loc[g["year"].idxmax()])
    log.info("plants with at least one verified year: %d", len(latest))
    log.info("latest-year total: %.2f Mt", latest["verified"].sum() / 1e6)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in SECTOR_FILTERS:
        print(f"usage: {sys.argv[0]} {{{'|'.join(SECTOR_FILTERS)}}}")
        sys.exit(1)
    main(sys.argv[1])
