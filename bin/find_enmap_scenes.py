"""
Scout EnMAP L2A scene coverage over our 21 audit-grade TR facilities.

Queries https://geoservice.dlr.de/eoc/ogc/stac/v1/search?collections=ENMAP_HSI_L2A
for each facility's bbox, lists all scenes with cloud_cover <= MAX_CC, saves
to data/enmap_scenes_index.csv.

EnMAP coverage is irregular (target-acquisition mode, not continuous sweep
like S5P/Sentinel-2) so coverage per facility varies wildly.

Usage:
  .venv/bin/python bin/find_enmap_scenes.py [--max-cc 25] [--bbox-deg 0.05]
"""
from __future__ import annotations
import argparse
import csv
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
FAC_CSV = REPO / "data" / "tr_facilities.csv"
KNOWN_CSV = REPO / "data" / "tr_facility_known_emissions.csv"
OUT_CSV = REPO / "data" / "enmap_scenes_index.csv"
ENDPOINT = "https://geoservice.dlr.de/eoc/ogc/stac/v1/search"


def load_audit_grade_ids() -> set[str]:
    """Return ids that have an audit-grade Scope 1 row."""
    ids = set()
    with open(KNOWN_CSV) as f:
        for r in csv.DictReader(f):
            if r["metric"] == "co2_scope1_t" and r["provenance"] in ("direct", "allocated", "composite"):
                ids.add(r["id"])
    return ids


def search_scenes(lat: float, lon: float, half: float, max_cc: float, max_scenes: int = 50):
    bbox = f"{lon-half:.4f},{lat-half:.4f},{lon+half:.4f},{lat+half:.4f}"
    params = {
        "collections": "ENMAP_HSI_L2A",
        "bbox": bbox,
        "limit": max_scenes,
    }
    headers = {
        "Accept": "application/geo+json",
        "User-Agent": "iz-tr-mrv-bench/0.1 (https://github.com/abgnydn/iz)",
    }
    try:
        resp = requests.get(ENDPOINT, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  search failed: {e}", file=sys.stderr)
        return []
    feats = data.get("features", [])
    out = []
    for f in feats:
        props = f.get("properties", {})
        cc_raw = props.get("eo:cloud_cover", 100)
        if cc_raw is None:
            cc = 100.0
        else:
            try:
                cc = float(cc_raw)
            except (ValueError, TypeError):
                cc = 100.0
        if cc > max_cc:
            continue
        out.append({
            "scene_id": f.get("id"),
            "datetime": props.get("datetime"),
            "cloud_cover": cc,
            "self_href": next((l.get("href") for l in f.get("links", []) if l.get("rel") == "self"), None),
            "data_href": next((a.get("href") for k, a in f.get("assets", {}).items() if "L2A" in k.upper() or "data" in k.lower() or "metadata" in k.lower()), None),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-cc", type=float, default=25.0, help="max cloud cover percentage")
    ap.add_argument("--bbox-deg", type=float, default=0.05, help="bbox half-width in degrees (5 km)")
    ap.add_argument("--all", action="store_true", help="search all 59 facilities (default: audit-grade only)")
    args = ap.parse_args()

    audit = load_audit_grade_ids()
    facs = list(csv.DictReader(open(FAC_CSV)))
    if not args.all:
        facs = [f for f in facs if f["id"] in audit]
    print(f"searching EnMAP for {len(facs)} facilities (max cc {args.max_cc}%, bbox ±{args.bbox_deg}°)")

    rows = []
    coverage_summary = []
    for i, f in enumerate(facs, 1):
        fid = f["id"]
        lat = float(f["lat"]); lon = float(f["lon"])
        scenes = search_scenes(lat, lon, args.bbox_deg, args.max_cc)
        n_total = len(scenes)
        n_cf = sum(1 for s in scenes if s["cloud_cover"] <= 10)
        n_clear = sum(1 for s in scenes if s["cloud_cover"] == 0)
        print(f"  [{i:2d}/{len(facs)}] {fid:32s} total={n_total:3d}  ≤10%cc={n_cf:3d}  =0%cc={n_clear:3d}")
        coverage_summary.append({
            "id": fid, "n_scenes": n_total, "n_cloud_le_10": n_cf, "n_zero_cloud": n_clear,
            "best_scene_id": scenes[0]["scene_id"] if scenes else None,
            "best_datetime": scenes[0]["datetime"] if scenes else None,
            "best_cloud_cover": scenes[0]["cloud_cover"] if scenes else None,
        })
        for s in scenes:
            s["facility_id"] = fid
            rows.append(s)
        time.sleep(0.3)  # courtesy

    # Per-scene index
    if rows:
        keys = ["facility_id", "scene_id", "datetime", "cloud_cover", "self_href", "data_href"]
        with open(OUT_CSV, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
        print(f"\nwrote {OUT_CSV.relative_to(REPO)}  ({len(rows)} rows)")

    # Per-facility summary
    print()
    print("=" * 80)
    print(f"  EnMAP coverage summary (cloud cover ≤{args.max_cc}%)")
    print("=" * 80)
    print(f"  {'facility':35s} {'n_scenes':>8s} {'≤10%cc':>8s} {'=0%cc':>7s}  best_scene_datetime")
    coverage_summary.sort(key=lambda r: -r["n_scenes"])
    for r in coverage_summary:
        dt = (r["best_datetime"] or "")[:10]
        print(f"  {r['id']:35s} {r['n_scenes']:>8d} {r['n_cloud_le_10']:>8d} {r['n_zero_cloud']:>7d}  {dt}")
    print("=" * 80)
    n_with_any = sum(1 for r in coverage_summary if r["n_scenes"] > 0)
    n_with_zero_cc = sum(1 for r in coverage_summary if r["n_zero_cloud"] > 0)
    print(f"  facilities with any cloud≤{args.max_cc}% coverage: {n_with_any}/{len(facs)}")
    print(f"  facilities with at least one 0%cc scene:        {n_with_zero_cc}/{len(facs)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
