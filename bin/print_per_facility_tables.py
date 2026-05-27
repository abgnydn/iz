"""
Emit per-facility tables for the home page, README, and paper preview from
the aggregated LODO predictions.

Output:
 - sections/per_facility.html.frag     HTML rows for site/index.html
 - sections/per_facility.md.frag       Markdown rows for README.md
"""
from __future__ import annotations
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AGG = REPO / "reports" / "lodo_aggregated.json"
FAC = REPO / "site" / "bench" / "facilities.json"
OUT_DIR = REPO / "logs" / "sections"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PRETTY_NAME = {
    "afyon-cimento": ("Afyon Çimento", "cement"),
    "akcansa-buyukcekmece": ("Akçansa Büyükçekmece", "cement"),
    "akcansa-canakkale": ("Akçansa Çanakkale", "cement"),
    "akcansa-ladik": ("Akçansa Ladik", "cement"),
    "batisoke-soke": ("Batısöke Söke", "cement"),
    "goltas-isparta": ("Göltaş Isparta", "cement"),
    "nuh-hereke": ("Nuh Hereke", "cement"),
    "colakoglu-gebze": ("Çolakoğlu Dilovası", "steel · EAF"),
    "habas-aliaga": ("Habaş Aliağa", "steel · EAF"),
    "izdemir-aliaga": ("İzdemir Aliağa", "steel · EAF"),
    "erdemir-eregli": ("Erdemir Karadeniz Ereğli", "steel · BF/BOF"),
    "isdemir-iskenderun": ("İsdemir İskenderun", "steel · BF/BOF"),
    "kardemir-karabuk": ("Kardemir Karabük", "steel · BF/BOF"),
    "assan-tuzla": ("Assan Tuzla", "aluminum · downstream"),
    "asas-akyazi": ("ASAŞ Akyazı", "aluminum · downstream"),
    "toros-mersin": ("Toros Mersin", "fertilizer · integrated"),
    "toros-samsun": ("Toros Samsun", "fertilizer · integrated"),
    "toros-ceyhan": ("Toros Ceyhan", "fertilizer · integrated"),
    "bagfas-bandirma": ("BAGFAŞ Bandırma", "fertilizer · N₂O-controlled"),
    "gubretas-izmit": ("Gübretaş Yarımca", "fertilizer · blender"),
}


def ratio_class(r: float) -> str:
    if abs(math.log(r)) < 0.18:
        return "ratio-good"
    if abs(math.log(r)) < 0.4:
        return "ratio-warn"
    return "ratio-bad"


def fmt(n: float) -> str:
    return f"{n:,.0f}"


def main() -> None:
    rows = json.loads(AGG.read_text())
    by_id = {r["facility_id"]: r for r in rows}

    # Sort by truth descending (biggest emitters first)
    ordered = sorted(by_id.values(), key=lambda r: -r["truth"])

    # Print HTML for home page (full 20)
    html_lines = []
    for r in ordered:
        fid = r["facility_id"]
        name, sector = PRETTY_NAME.get(fid, (fid, ""))
        truth = r["truth"]
        pred = r["pred_median"]
        eu = r["eu_default"]
        ratio = pred / truth
        cls = ratio_class(ratio)
        n_runs = r.get("n_runs", 0)
        rng_min = min(r.get("preds_all", [pred]))
        rng_max = max(r.get("preds_all", [pred]))
        html_lines.append(
            f'      <tr><td>{name}</td><td>{sector}</td>'
            f'<td class="num">{fmt(truth)}</td>'
            f'<td class="num">{fmt(pred)}<br><span class="muted" style="font-size:10px;">n={n_runs}: {fmt(rng_min)}–{fmt(rng_max)}</span></td>'
            f'<td class="num {cls}">{ratio:.2f}×</td>'
            f'<td class="num">{fmt(eu)}</td></tr>'
        )
    (OUT_DIR / "per_facility.html.frag").write_text("\n".join(html_lines) + "\n")

    # Markdown for README
    md_lines = ["| Facility | Sector / route | Truth (tCO₂) | iz-1 (5-run median) | Ratio | EU default |",
                "|----------|----------------|-------------:|--------------------:|------:|-----------:|"]
    for r in ordered:
        fid = r["facility_id"]
        name, sector = PRETTY_NAME.get(fid, (fid, ""))
        truth = r["truth"]
        pred = r["pred_median"]
        eu = r["eu_default"]
        ratio = pred / truth
        md_lines.append(
            f"| {name} | {sector} | {fmt(truth)} | {fmt(pred)} | {ratio:.2f}× | {fmt(eu)} |"
        )
    (OUT_DIR / "per_facility.md.frag").write_text("\n".join(md_lines) + "\n")

    # Recompute headline
    ml = [abs(math.log(r["pred_median"]) - math.log(r["truth"])) for r in rows]
    el = [abs(math.log(r["eu_default"]) - math.log(r["truth"])) for r in rows]
    mm = sum(ml) / len(ml); em = sum(el) / len(el)
    red = (1 - mm / em) * 100

    print(f"n = {len(rows)}")
    print(f"iz-1 NN headline reduction (median across 5 outer runs): {red:.2f}%")
    print(f"per-plant log-MAE (NN): {mm:.3f}  EU default: {em:.3f}")
    print()
    print(f"Wrote {OUT_DIR}/per_facility.html.frag and per_facility.md.frag")


if __name__ == "__main__":
    main()
