"""
Build a static SVG map of all TR CBAM-scope facilities for the bench browser.

Geography:
  - Coastline from Natural Earth 1:50m admin_0_countries (data/geo/turkey.geojson),
    cached locally so this script is offline-safe after first fetch.
  - Mainland + European Türkiye (Trakya) + the major Aegean islands all rendered.
  - Web Mercator projection (EPSG:3857), auto-fit to the Türkiye bounding box,
    so the country looks like a country instead of a stretched lat/lon rectangle.

Data:
  - Facility coordinates from data/tr_facilities.csv.
  - LODO ratio (if available) from reports/lodo_aggregated.json.

Output: site/assets/facility_map.svg
"""
from __future__ import annotations
import csv
import json
import math
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAC = REPO / "data" / "tr_facilities.csv"
AGG = REPO / "reports" / "lodo_aggregated.json"
GEO = REPO / "data" / "geo" / "turkey.geojson"
NE_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
          "master/geojson/ne_50m_admin_0_countries.geojson")
OUT = REPO / "site" / "assets" / "facility_map.svg"

# Palette
BG = "#fbf7ee"
INK = "#14181d"
MUTED = "#a89e90"
LAND = "#e8dec8"
SEA = BG
SECTOR_COLOR = {
    "cement":     "#2d5a4c",
    "steel":      "#7a3b22",
    "aluminum":   "#5a4a7a",
    "fertilizer": "#7a6a2d",
}

# Output canvas
W, H = 1200, 540
PAD = 30


def web_mercator(lon: float, lat: float) -> tuple[float, float]:
    """EPSG:3857 forward. Returns radians-scaled meters, but we only use
    the ratios, so the units don't matter — only that the proportions are right.
    """
    x = math.radians(lon)
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


def ensure_geojson() -> dict:
    """Cache Turkey-only GeoJSON locally."""
    if GEO.exists():
        return json.loads(GEO.read_text())
    GEO.parent.mkdir(parents=True, exist_ok=True)
    print(f"Fetching Natural Earth 50m countries → {GEO}…")
    with urllib.request.urlopen(NE_URL, timeout=30) as r:
        gj = json.loads(r.read().decode("utf-8"))
    for feat in gj["features"]:
        p = feat["properties"]
        iso = p.get("ISO_A3") or p.get("ISO_A2", "")
        name = (p.get("NAME_EN") or p.get("NAME") or "").lower()
        if iso == "TUR" or "turkey" in name or "rkiye" in name:
            out = {"type": "Feature",
                   "properties": {"name": "Türkiye"},
                   "geometry": feat["geometry"]}
            GEO.write_text(json.dumps(out, separators=(",", ":")))
            return out
    raise RuntimeError("Türkiye polygon not found in Natural Earth dataset")


def main() -> None:
    geo = ensure_geojson()
    rings = geo["geometry"]["coordinates"]
    # rings is a list of polygons, each polygon is [outer_ring, hole_ring_1, ...]

    # Keep coastline rings in lon/lat; Mercator-project the bbox.
    coastline_rings: list[list[tuple[float, float]]] = []
    all_xy = []
    for poly in rings:
        outer = poly[0]
        coastline_rings.append([(lon, lat) for lon, lat in outer])
        all_xy.extend(web_mercator(lon, lat) for lon, lat in outer)

    xs = [p[0] for p in all_xy]; ys = [p[1] for p in all_xy]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    # Compute uniform scale so that Türkiye fits in the canvas-with-padding,
    # preserving aspect ratio.
    span_x = x_max - x_min
    span_y = y_max - y_min
    target_w = W - 2 * PAD
    target_h = H - 2 * PAD - 26  # leave room for caption
    sx = target_w / span_x
    sy = target_h / span_y
    s = min(sx, sy)
    drawn_w = span_x * s
    drawn_h = span_y * s
    # Center horizontally and vertically
    off_x = PAD + (target_w - drawn_w) / 2
    off_y = PAD + (target_h - drawn_h) / 2

    def proj(lon: float, lat: float) -> tuple[float, float]:
        x_m, y_m = web_mercator(lon, lat)
        x = (x_m - x_min) * s + off_x
        # SVG y goes down → flip Mercator y
        y = (y_max - y_m) * s + off_y
        return x, y

    # ----- SVG -----
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'style="font-family:-apple-system, system-ui, sans-serif; '
        f'background:{BG}; max-width:100%; height:auto;" '
        f'role="img" aria-label="Map of {{n}} Turkish CBAM-scope facilities">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SEA}"/>',
    ]

    # Build path covering all rings of Türkiye (one <path> with multiple "M…Z" subpaths)
    path_d = []
    for ring in coastline_rings:
        coords = [proj(lon, lat) for lon, lat in ring]
        if not coords:
            continue
        x0, y0 = coords[0]
        path_d.append(f"M{x0:.1f},{y0:.1f}")
        for x, y in coords[1:]:
            path_d.append(f"L{x:.1f},{y:.1f}")
        path_d.append("Z")
    parts.append(
        f'<path d="{" ".join(path_d)}" fill="{LAND}" stroke="{MUTED}" '
        f'stroke-width="0.8" stroke-linejoin="round" fill-rule="evenodd"/>'
    )

    # Subtle graticule labels (integer-degree ticks in lat/lon, projected)
    # — covers 36–42°N and 26–44°E roughly
    for lat in range(36, 43, 2):
        x_l, y_l = proj(26.0, lat)
        x_r, y_r = proj(44.0, lat)
        parts.append(
            f'<line x1="{x_l:.1f}" y1="{y_l:.1f}" x2="{x_r:.1f}" y2="{y_r:.1f}" '
            f'stroke="{MUTED}" stroke-width="0.3" opacity="0.25"/>'
        )
    for lon in range(26, 45, 4):
        x_t, y_t = proj(lon, 42.5)
        x_b, y_b = proj(lon, 35.5)
        parts.append(
            f'<line x1="{x_t:.1f}" y1="{y_t:.1f}" x2="{x_b:.1f}" y2="{y_b:.1f}" '
            f'stroke="{MUTED}" stroke-width="0.3" opacity="0.25"/>'
        )

    # ----- Facility dots -----
    fac_rows = list(csv.DictReader(open(FAC)))
    ratio_by_id: dict[str, float] = {}
    if AGG.exists():
        for r in json.loads(AGG.read_text()):
            if r["truth"] > 0:
                ratio_by_id[r["facility_id"]] = r["pred_median"] / r["truth"]

    caps = [int(f["annual_capacity_t"]) for f in fac_rows
            if int(f.get("annual_capacity_t") or 0) > 0]
    log_min = math.log10(min(caps)); log_max = math.log10(max(caps))

    def radius(cap: int) -> float:
        if cap <= 0:
            return 4.0
        t = (math.log10(cap) - log_min) / (log_max - log_min)
        return 4.0 + 10.0 * t

    fac_rows.sort(key=lambda f: int(f.get("annual_capacity_t") or 0))
    for f in fac_rows:
        lat = float(f["lat"]); lon = float(f["lon"])
        cap = int(f.get("annual_capacity_t") or 0)
        x, y = proj(lon, lat)
        r = radius(cap)
        color = SECTOR_COLOR.get(f["cbam_scope"], "#888")
        fid = f["id"]
        ratio = ratio_by_id.get(fid)
        has_label = fid in ratio_by_id
        stroke = INK if has_label else "none"
        stroke_w = 1.6 if has_label else 0
        tip = f"{f['company']} — {f['plant_name']} ({f['cbam_scope']}, cap {cap:,} t/yr)"
        if ratio:
            tip += f"; LODO ratio {ratio:.2f}× truth"
        parts.append(
            f'<a href="/bench/{fid}/" target="_top">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}" '
            f'fill-opacity="0.78" stroke="{stroke}" stroke-width="{stroke_w}">'
            f'<title>{tip}</title></circle></a>'
        )

    # Legend
    lx, ly = PAD + 8, H - PAD - 90
    parts.append(
        f'<rect x="{lx}" y="{ly}" width="190" height="80" fill="{BG}" '
        f'stroke="{MUTED}" stroke-width="0.5"/>'
    )
    parts.append(
        f'<text x="{lx+10}" y="{ly+18}" font-size="10" letter-spacing="0.15em" '
        f'fill="{INK}" font-weight="600">CBAM SECTOR</text>'
    )
    for i, (scope, color) in enumerate(SECTOR_COLOR.items()):
        cx = lx + 18; cy = ly + 30 + i * 14
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="5" fill="{color}" fill-opacity="0.78"/>'
        )
        parts.append(
            f'<text x="{cx+12}" y="{cy+3}" font-size="10" fill="{INK}">{scope}</text>'
        )

    # Caption
    parts.append(
        f'<text x="{W-PAD}" y="{H-PAD-22}" text-anchor="end" font-size="10" fill="{MUTED}">'
        f'{len(fac_rows)} facilities · {len(ratio_by_id)} LODO-tested (ink outline) · '
        f'dot size ∝ log(capacity)'
        '</text>'
    )
    parts.append(
        f'<text x="{W-PAD}" y="{H-PAD-8}" text-anchor="end" font-size="10" fill="{MUTED}" font-style="italic">'
        f'Web Mercator · coastline: Natural Earth 1:50m · click a dot for details'
        '</text>'
    )

    parts.append('</svg>')

    OUT.write_text("\n".join(parts).replace("{n}", str(len(fac_rows))))
    print(f"wrote {OUT.relative_to(REPO)} ({OUT.stat().st_size:,} bytes)")
    print(f"  {len(fac_rows)} facilities · {len(ratio_by_id)} with LODO ratio")
    print(f"  coastline: {sum(len(r) for r in coastline_rings)} vertices across "
          f"{len(coastline_rings)} rings")


if __name__ == "__main__":
    main()
