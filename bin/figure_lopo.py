"""
Headline figure: per-plant EU CBAM default vs the cf-corrected formula's
leave-one-plant-out prediction, against audit-grade truth.

Reads reports/lopo_ef_eval.json (produced by bin/lopo_ef_eval.py) and writes
site/assets/fig_formula_vs_eu.svg. Only the 19 validatable plants are plotted;
the 2 single-plant strata are excluded from the headline by construction.

Run: uv run python bin/figure_lopo.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

REPO = Path(__file__).resolve().parent.parent
LOPO = REPO / "reports" / "lopo_ef_eval.json"
OUT = REPO / "site" / "assets" / "fig_formula_vs_eu.svg"

EU = "#b85c3f"
IZ = "#2d5a4c"
INK = "#14181d"
PAPER = "#fbf7ee"

NAME = {
    "erdemir-eregli": "Erdemir", "isdemir-iskenderun": "İsdemir",
    "kardemir-karabuk": "Kardemir", "nuh-hereke": "Nuh Hereke",
    "akcansa-canakkale": "Akçansa Çan.", "goltas-isparta": "Göltaş",
    "batisoke-soke": "Batısöke", "akcansa-buyukcekmece": "Akçansa Büy.",
    "afyon-cimento": "Afyon", "bursa-cimento": "Bursa Çim.",
    "habas-aliaga": "Habaş", "colakoglu-gebze": "Çolakoğlu",
    "akcansa-ladik": "Akçansa Ladik", "toros-mersin": "Toros Mersin",
    "izdemir-aliaga": "İzdemir", "toros-samsun": "Toros Samsun",
    "toros-ceyhan": "Toros Ceyhan", "assan-tuzla": "Assan", "asas-akyazi": "ASAŞ",
}


def main() -> None:
    d = json.loads(LOPO.read_text())
    rows = [r for r in d["per_plant"] if r.get("ratio_lopo") is not None]
    rows.sort(key=lambda r: r["truth"])

    labels = [NAME.get(r["id"], r["id"]) for r in rows]
    truth = [r["truth"] for r in rows]
    eu = [r["eu_default"] for r in rows]
    pred = [r["ratio_lopo"] * r["truth"] for r in rows]

    n = len(rows)
    x = range(n)
    w = 0.4

    fig, ax = plt.subplots(figsize=(12, 5.2))
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)

    ax.bar([i - w / 2 for i in x], eu, w, color=EU, label="EU CBAM default", zorder=2)
    ax.bar([i + w / 2 for i in x], pred, w, color=IZ,
           label="cf-corrected formula (leave-one-plant-out)", zorder=2)
    ax.scatter(list(x), truth, color=INK, marker="_", s=420, linewidths=2.4,
               label="audit-grade Scope 1 (truth)", zorder=3)

    ax.set_yscale("log")
    ax.set_ylabel("tCO₂ / year (log scale)", fontsize=10)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_title(
        "Per-plant emissions: EU CBAM default vs cf-corrected formula\n"
        f"leave-one-plant-out, +82.3% log-MAE reduction over n={n} validatable plants",
        fontsize=11.5, color=INK, pad=12,
    )
    ax.tick_params(colors=INK)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#d8cfbe")
    ax.grid(axis="y", color="#d8cfbe", linewidth=0.5, zorder=0)
    ax.legend(handles=[
        Patch(color=EU, label="EU CBAM default"),
        Patch(color=IZ, label="cf-corrected formula (leave-one-plant-out)"),
        plt.Line2D([0], [0], color=INK, marker="_", linestyle="None", markersize=12,
                   markeredgewidth=2.4, label="audit-grade Scope 1 (truth)"),
    ], fontsize=9, frameon=False, loc="upper left")

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, format="svg", facecolor=PAPER)
    print(f"wrote {OUT.relative_to(REPO)}  ({n} plants)")


if __name__ == "__main__":
    main()
