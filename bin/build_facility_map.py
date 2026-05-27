"""
Build a static SVG map of all TR CBAM-scope facilities for the bench browser.

Coordinates from data/tr_facilities.csv. LODO ratio (if available) from
reports/lodo_aggregated.json. Output: site/assets/facility_map.svg.

Style:
  - Cream background, simple equirectangular projection on TR bounds
  - Soft TR outline (drawn from a hand-coded polygon — close enough for v0)
  - Each facility = colored dot, scaled by capacity (log)
  - Disclosure-labeled facilities outlined in ink
  - Hover via SVG <title> shows facility name + sector + ratio (when LODO-tested)
"""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAC = REPO / "data" / "tr_facilities.csv"
AGG = REPO / "reports" / "lodo_aggregated.json"
OUT = REPO / "site" / "assets" / "facility_map.svg"

# Palette
BG = "#fbf7ee"
INK = "#14181d"
MUTED = "#a89e90"
LAND = "#e8dec8"
SECTOR_COLOR = {
    "cement":     "#2d5a4c",  # iz-green
    "steel":      "#7a3b22",  # deep brick
    "aluminum":   "#5a4a7a",  # plum
    "fertilizer": "#7a6a2d",  # ochre
}

# TR projection bounds (slightly padded)
LON_MIN, LON_MAX = 25.5, 45.0
LAT_MIN, LAT_MAX = 35.8, 42.5

# Output canvas
W, H = 1200, 540
PAD = 30

# Hand-coded simplified TR coastline polygon (lat,lon pairs, clockwise from NW)
# Not a precise GIS file — just visually approximates the country outline at this scale.
TR_OUTLINE = [
    (41.9, 27.1), (41.5, 28.0), (41.0, 29.0), (41.2, 31.4), (41.7, 32.5),
    (41.9, 35.0), (41.4, 36.3), (41.1, 38.5), (41.0, 40.0), (41.3, 41.7),
    (40.6, 43.0), (39.5, 44.3), (38.4, 44.8), (37.3, 44.5), (37.0, 43.0),
    (37.3, 42.0), (37.1, 40.5), (36.6, 38.0), (36.2, 36.5), (36.0, 35.7),
    (36.5, 34.5), (36.7, 33.0), (36.9, 31.5), (36.2, 30.0), (36.7, 28.0),
    (37.3, 27.0), (38.4, 26.4), (39.1, 26.7), (39.7, 26.1), (40.5, 26.0),
    (41.2, 26.3), (41.7, 26.5),
]


def project(lat: float, lon: float) -> tuple[float, float]:
    x = (lon - LON_MIN) / (LON_MAX - LON_MIN) * (W - 2 * PAD) + PAD
    y = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * (H - 2 * PAD) + PAD
    return x, y


def main() -> None:
    fac_rows = list(csv.DictReader(open(FAC)))
    # LODO ratios (if file exists)
    ratio_by_id: dict[str, float] = {}
    if AGG.exists():
        for r in json.loads(AGG.read_text()):
            if r["truth"] > 0:
                ratio_by_id[r["facility_id"]] = r["pred_median"] / r["truth"]

    # Capacity bounds for radius scaling
    caps = [int(f["annual_capacity_t"]) for f in fac_rows if int(f.get("annual_capacity_t") or 0) > 0]
    log_min = math.log10(min(caps)); log_max = math.log10(max(caps))
    def radius(cap: int) -> float:
        if cap <= 0:
            return 4.0
        t = (math.log10(cap) - log_min) / (log_max - log_min)
        return 4.0 + 10.0 * t  # 4-14 px

    # ----- SVG -----
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'style="font-family:-apple-system, system-ui, sans-serif; background:{BG}; max-width:100%; height:auto;">']
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>')

    # TR coastline polygon
    pts = " ".join(f"{x:.1f},{y:.1f}" for lat, lon in TR_OUTLINE for x, y in [project(lat, lon)])
    parts.append(f'<polygon points="{pts}" fill="{LAND}" stroke="{MUTED}" stroke-width="1" stroke-linejoin="round"/>')

    # Lat/lon graticule (subtle)
    for lat in range(int(LAT_MIN) + 1, int(LAT_MAX) + 1):
        y = project(lat, LON_MIN)[1]
        parts.append(f'<line x1="{PAD}" y1="{y:.1f}" x2="{W-PAD}" y2="{y:.1f}" stroke="{MUTED}" stroke-width="0.3" opacity="0.4"/>')
    for lon in range(int(LON_MIN) + 1, int(LON_MAX) + 1, 2):
        x = project(LAT_MIN, lon)[0]
        parts.append(f'<line x1="{x:.1f}" y1="{PAD}" x2="{x:.1f}" y2="{H-PAD}" stroke="{MUTED}" stroke-width="0.3" opacity="0.4"/>')

    # Facility dots (sorted by capacity so big plants render last / on top)
    fac_rows.sort(key=lambda f: int(f.get("annual_capacity_t") or 0))
    for f in fac_rows:
        lat = float(f["lat"]); lon = float(f["lon"])
        cap = int(f.get("annual_capacity_t") or 0)
        x, y = project(lat, lon)
        r = radius(cap)
        color = SECTOR_COLOR.get(f["cbam_scope"], "#888")
        fid = f["id"]
        ratio = ratio_by_id.get(fid)
        has_label = fid in ratio_by_id
        # Stroke for disclosure-labeled facilities
        stroke = INK if has_label else "none"
        stroke_w = 1.6 if has_label else 0
        # Tooltip text
        tip = f"{f['company']} — {f['plant_name']} ({f['cbam_scope']}, cap {cap:,} t/yr)"
        if ratio:
            tip += f"; LODO ratio {ratio:.2f}× truth"
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}" '
            f'fill-opacity="0.78" stroke="{stroke}" stroke-width="{stroke_w}">'
            f'<title>{tip}</title></circle>'
        )

    # Legend
    lx, ly = PAD + 8, H - PAD - 90
    parts.append(f'<rect x="{lx}" y="{ly}" width="190" height="80" fill="{BG}" stroke="{MUTED}" stroke-width="0.5"/>')
    parts.append(f'<text x="{lx+10}" y="{ly+18}" font-size="10" letter-spacing="0.15em" fill="{INK}" font-weight="600">CBAM SECTOR</text>')
    for i, (scope, color) in enumerate(SECTOR_COLOR.items()):
        cx = lx + 18; cy = ly + 30 + i * 14
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{color}" fill-opacity="0.78"/>')
        parts.append(f'<text x="{cx+12}" y="{cy+3}" font-size="10" fill="{INK}">{scope}</text>')

    # Caption
    parts.append(
        f'<text x="{W-PAD}" y="{H-PAD-22}" text-anchor="end" font-size="10" fill="{MUTED}">'
        f'{len(fac_rows)} facilities · {len(ratio_by_id)} LODO-tested (ink outline) · dot size ∝ log(capacity)'
        '</text>'
    )
    parts.append(
        f'<text x="{W-PAD}" y="{H-PAD-8}" text-anchor="end" font-size="10" fill="{MUTED}" font-style="italic">'
        'hover a dot to inspect'
        '</text>'
    )

    parts.append('</svg>')
    OUT.write_text("\n".join(parts))
    print(f"wrote {OUT.relative_to(REPO)} ({OUT.stat().st_size} bytes)")
    print(f"  {len(fac_rows)} facilities · {len(ratio_by_id)} with LODO ratio")


if __name__ == "__main__":
    main()
