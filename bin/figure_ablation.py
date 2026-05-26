"""
Ablation figure — what each component contributes to the LODO headline.

Reads reports/ablations/summary.json (produced by bin/run_ablations.py) and
draws a horizontal bar chart with overall reduction + per-sector breakdown.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "reports" / "ablations" / "summary.json"
OUT = REPO / "reports" / "fig_ablation.svg"

BG = "#fbf7ee"
INK = "#14181d"
MUTED = "#6e6862"
RULE = "#d8cfbe"
IZ = "#2d5a4c"
EU = "#b85c3f"


def main() -> None:
    if not SRC.exists():
        print(f"no ablation summary at {SRC}; run bin/run_ablations.py first")
        return
    rows = json.loads(SRC.read_text())

    w, h = 1000, 80 + len(rows) * 56 + 60
    pad_l = 240; pad_r = 320; pad_t = 70

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
           f'style="font-family:Georgia,serif;background:{BG}">']
    svg.append(f'<rect x="0" y="0" width="{w}" height="{h}" fill="{BG}"/>')
    svg.append(f'<text x="{pad_l}" y="36" font-size="20pt" font-weight="600" letter-spacing="-0.02em" fill="{INK}">iz-1 component ablations</text>')
    svg.append(f'<text x="{pad_l}" y="58" font-size="11pt" fill="{MUTED}" font-style="italic">Per-plant log-MAE reduction vs EU CBAM default (LODO, n=8, 9 seeds per facility)</text>')

    plot_w = w - pad_l - pad_r
    max_red = max(80, max(abs(r["reduction"]) for r in rows) + 5)
    x0 = pad_l + plot_w * (max_red / (2 * max_red))   # x=0 line in middle? actually want all positive
    # Use 0-100 scale for bar; negative values draw left of 0 axis
    x0 = pad_l   # x = 0 at left
    bar_unit = plot_w / max_red

    for i, r in enumerate(rows):
        y = pad_t + i * 56 + 20
        red = r["reduction"]
        bar_w = abs(red) * bar_unit
        bar_x = x0 if red >= 0 else x0 - bar_w   # always start at left, since red mostly positive
        color = IZ if red >= 0 else EU
        svg.append(f'<rect x="{x0}" y="{y-12}" width="{bar_w}" height="24" fill="{color}" opacity="0.5"/>')
        svg.append(f'<text x="{pad_l - 16}" y="{y+5}" text-anchor="end" font-size="11pt" fill="{INK}">{r["name"]}</text>')
        svg.append(f'<text x="{x0 + bar_w + 8}" y="{y+5}" font-size="10pt" fill="{INK}" font-weight="600">{red:+.1f}%</text>')

        # per-sector mini-chips on right
        cx = pad_l + plot_w + 20
        for j, (sec, key) in enumerate([("cement", "cement"), ("BF/BOF", "BF/BOF"), ("EAF", "EAF")]):
            v = r["per_sector"].get(key)
            if v is None: continue
            c = IZ if v >= 0 else EU
            svg.append(f'<rect x="{cx + j * 90}" y="{y - 10}" width="80" height="20" fill="{c}" opacity="0.16" stroke="{c}" stroke-width="0.7"/>')
            svg.append(f'<text x="{cx + j * 90 + 40}" y="{y + 4}" text-anchor="middle" font-size="9pt" fill="{INK}">{sec} {v:+.0f}%</text>')

    # axis tick at 100%
    svg.append(f'<line x1="{x0 + 100 * bar_unit}" x2="{x0 + 100 * bar_unit}" y1="{pad_t-8}" y2="{h - 30}" stroke="{RULE}" stroke-dasharray="3 3"/>')
    svg.append(f'<text x="{x0 + 100 * bar_unit + 4}" y="{pad_t-2}" font-size="9pt" fill="{MUTED}">100% (perfect vs EU)</text>')

    svg.append('</svg>')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(svg))
    print(f"wrote {OUT.relative_to(REPO)}  ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
