"""
Headline figure: iz-1 vs EU CBAM default per-plant log-CO₂ across the 7 LODO
disclosure facilities. Outputs a self-contained SVG.

Style follows the editorial/cream aesthetic used in marketing/report_*.html.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# Prefer the aggregated (multi-outer-run) result if present.
AGG = REPO / "reports" / "lodo_aggregated.json"
SINGLE = REPO / "reports" / "lodo_results.json"
LODO = AGG if AGG.exists() else SINGLE
OUT = REPO / "reports" / "fig_iz1_vs_eu_lodo.svg"

BG = "#fbf7ee"
INK = "#14181d"
MUTED = "#6e6862"
RULE = "#d8cfbe"
IZ_GREEN = "#2d5a4c"
EU_RED = "#b85c3f"
TRUTH = "#8a7d64"


def main() -> None:
    rows = json.loads(LODO.read_text())
    if not rows:
        print("no lodo results")
        return

    # sort by truth ascending so the chart reads small→big
    rows = sorted(rows, key=lambda r: r["truth"])
    n = len(rows)

    # Layout — auto-scale width for larger n
    w = max(1100, 60 + 60 * n)
    h = 560
    pad_l = 230
    pad_r = 60
    pad_t = 90
    pad_b = 110
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b

    # log-y scale from min truth/pred/eu to max
    vals = [r["truth"] for r in rows] + [r["pred_median"] for r in rows] + [r["eu_default"] for r in rows]
    y_min = math.floor(math.log10(min(v for v in vals if v > 0)))
    y_max = math.ceil(math.log10(max(vals)))
    def y(v: float) -> float:
        if v <= 0:
            return pad_t + plot_h
        lv = math.log10(v)
        return pad_t + plot_h - (lv - y_min) / (y_max - y_min) * plot_h

    # Compute metrics
    model_log = sum(abs(math.log(r["pred_median"]) - math.log(r["truth"])) for r in rows) / n
    eu_log = sum(abs(math.log(r["eu_default"]) - math.log(r["truth"])) for r in rows) / n
    reduction = (1 - model_log / eu_log) * 100

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
           f'style="font-family:Georgia,serif;background:{BG}">']
    # frame
    svg.append(f'<rect x="0" y="0" width="{w}" height="{h}" fill="{BG}"/>')
    # title
    svg.append(f'<text x="{pad_l}" y="36" fill="{INK}" font-size="22pt" font-weight="600" letter-spacing="-0.02em">iz-1 per-plant CO₂ vs the EU CBAM default</text>')
    n_seeds = rows[0].get("n_runs", 0) * 3 if rows and "n_runs" in rows[0] else 3
    svg.append(f'<text x="{pad_l}" y="62" fill="{MUTED}" font-size="11pt" font-style="italic">Leave-one-disclosure-out · {n} audit-grade Turkish facilities · all 4 CBAM scopes · {n_seeds} seeds per plant · log-MAE reduction {reduction:.1f}% vs EU default</text>')

    # gridlines + labels
    for k in range(y_min, y_max + 1):
        yy = y(10 ** k)
        svg.append(f'<line x1="{pad_l}" x2="{w-pad_r}" y1="{yy}" y2="{yy}" stroke="{RULE}" stroke-width="0.5"/>')
        label = f'10^{k}' if k > 6 else f'{10**k:,}'
        if k == 6: label = "1M"
        elif k == 7: label = "10M"
        elif k == 5: label = "100k"
        elif k == 4: label = "10k"
        svg.append(f'<text x="{pad_l-12}" y="{yy+4}" text-anchor="end" font-size="9pt" fill="{MUTED}">{label}</text>')
    svg.append(f'<text x="{pad_l-50}" y="{pad_t + plot_h/2}" transform="rotate(-90 {pad_l-50} {pad_t+plot_h/2})" text-anchor="middle" font-size="10pt" fill="{MUTED}" letter-spacing="0.12em">tCO₂ / yr (log)</text>')

    # bars per facility
    bar_w = plot_w / n * 0.85
    gap = (plot_w / n) - bar_w
    for i, r in enumerate(rows):
        cx = pad_l + gap/2 + i * (bar_w + gap) + bar_w/2
        # EU default bar (full bar, light)
        eu_y = y(r["eu_default"])
        svg.append(f'<rect x="{cx - bar_w/2}" y="{eu_y}" width="{bar_w}" height="{pad_t + plot_h - eu_y}" fill="{EU_RED}" opacity="0.18"/>')
        # iz-1 pred bar (overlapping, deeper)
        iz_y = y(r["pred_median"])
        svg.append(f'<rect x="{cx - bar_w/2}" y="{iz_y}" width="{bar_w}" height="{pad_t + plot_h - iz_y}" fill="{IZ_GREEN}" opacity="0.55"/>')
        # truth — black tick
        tt = y(r["truth"])
        svg.append(f'<line x1="{cx - bar_w/2 - 6}" x2="{cx + bar_w/2 + 6}" y1="{tt}" y2="{tt}" stroke="{INK}" stroke-width="2"/>')
        # facility label below — shortened for legibility
        label = r["facility_id"].replace("-", " · ")
        svg.append(f'<text x="{cx}" y="{h - pad_b + 18}" text-anchor="end" font-size="8.5pt" fill="{INK}" transform="rotate(-32 {cx} {h-pad_b+18})">{label}</text>')
        # ratio annotation
        ratio = r["pred_median"] / r["truth"]
        svg.append(f'<text x="{cx}" y="{iz_y-6}" text-anchor="middle" font-size="8pt" fill="{IZ_GREEN}" font-weight="600">{ratio:.2f}×</text>')

    # legend
    lx = pad_l + 8; ly = pad_t + 14
    svg.append(f'<rect x="{lx}" y="{ly-10}" width="14" height="14" fill="{EU_RED}" opacity="0.18"/>')
    svg.append(f'<text x="{lx+22}" y="{ly}" font-size="10pt" fill="{INK}">EU CBAM default (capacity × default EF)</text>')
    ly += 20
    svg.append(f'<rect x="{lx}" y="{ly-10}" width="14" height="14" fill="{IZ_GREEN}" opacity="0.55"/>')
    svg.append(f'<text x="{lx+22}" y="{ly}" font-size="10pt" fill="{INK}">iz-1 prediction (median of 3 seeds)</text>')
    ly += 20
    svg.append(f'<line x1="{lx}" x2="{lx+14}" y1="{ly-3}" y2="{ly-3}" stroke="{INK}" stroke-width="2"/>')
    svg.append(f'<text x="{lx+22}" y="{ly}" font-size="10pt" fill="{INK}">Disclosed truth (Scope 1 from IAR / sustainability report)</text>')

    # bottom-right metric box
    bx = w - pad_r - 280; by = pad_t + 6
    svg.append(f'<rect x="{bx}" y="{by}" width="280" height="74" fill="{BG}" stroke="{RULE}"/>')
    svg.append(f'<text x="{bx+12}" y="{by+22}" font-size="9pt" letter-spacing="0.16em" fill="{MUTED}" text-transform="uppercase">PER-PLANT LOG-MAE</text>')
    svg.append(f'<text x="{bx+12}" y="{by+44}" font-size="14pt" fill="{INK}"><tspan font-weight="600" fill="{IZ_GREEN}">iz-1</tspan> {model_log:.3f}   |   <tspan fill="{EU_RED}">EU</tspan> {eu_log:.3f}</text>')
    svg.append(f'<text x="{bx+12}" y="{by+64}" font-size="13pt" fill="{IZ_GREEN}" font-weight="600">{reduction:.1f}% reduction</text>')

    svg.append('</svg>')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(svg))
    print(f"wrote {OUT.relative_to(REPO)}  ({OUT.stat().st_size} bytes)")
    print(f"  n={n}  iz-1 log-MAE={model_log:.3f}  EU log-MAE={eu_log:.3f}  reduction={reduction:.1f}%")


if __name__ == "__main__":
    main()
