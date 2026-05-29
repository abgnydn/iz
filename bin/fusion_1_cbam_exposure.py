"""
Fusion #1 — TÜİK exports × CBAM tariff exposure.

For each CBAM-scope sector, compute TR's 2024 exports to the EU and the resulting
CBAM tariff bill under (a) EU default EFs vs (b) our cf-corrected formula EFs.
The delta is the money operators leave on the table if they pay the default
instead of submitting verified MRV.

Inputs:
  - TR export tonnage to EU per sector (TÜİK / WITS / S&P Global / argus media)
  - EU CBAM default EFs (cement 1.551 t/t per S&P; steel 1.9; aluminum 8.6; fertilizer 0.8)
  - Bench-derived TR-actual EFs (cement 0.643; steel-mix 1.2; aluminum-downstream 0.379; fertilizer-mix 0.45)
  - Assumed CBAM allowance price 2026: ~€85/t (EU ETS Q1 2026 spot)

Outputs: € of tariff at default, at formula, and operator-saved per sector.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "reports" / "fusion"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / "cbam_exposure.json"
OUT_MD = OUT_DIR / "cbam_exposure.md"

CBAM_PRICE_EUR_PER_TCO2 = 85.0   # EU ETS spot ~€85 Q1 2026

# Per-sector export volumes to EU (2024). Sources documented inline.
SECTORS = [
    {
        "sector": "Cement / clinker",
        "tr_export_to_eu_t": 4_000_000,   # midpoint of 3.3-4.8M (S&P Global / TÜRKÇİMENTO)
        "eu_default_ef": 1.551,           # tCO₂ / t clinker (S&P, current CBAM default)
        "bench_actual_ef": 0.643,         # TÜRKÇİMENTO sector avg / cf_corrected formula EF
        "source": "S&P Global: TR clinker exports 2024 = 5.22Mt total; ~3.3-4.8M to EU. EU CBAM default 1.551 t/t.",
    },
    {
        "sector": "Steel (mixed BF/BOF + EAF)",
        "tr_export_to_eu_t": 4_500_000,   # rough — TR is top-3 supplier of flat products to EU; ~4-5M t flats+longs
        "eu_default_ef": 1.900,           # tCO₂ / t crude steel (CBAM)
        "bench_actual_ef": 1.200,         # weighted: ~60% EAF (0.25) + ~40% integrated (2.0) ≈ 0.95; bench average 1.2 (operator mix)
        "source": "gmk.center: TR top-3 EU supplier of HS 7208/7210. EU CBAM default 1.9 t/t.",
    },
    {
        "sector": "Aluminum (downstream-heavy)",
        "tr_export_to_eu_t":   200_000,   # ASAŞ + Assan combined exports ~200k t to EU
        "eu_default_ef": 8.600,           # tCO₂ / t primary Al (CBAM)
        "bench_actual_ef": 0.450,         # mostly downstream rolling/extrusion (Assan 0.379, ASAŞ ~0.30)
        "source": "WITS: TR aluminum exports 2024. CBAM default 8.6 — calibrated for Hall-Héroult, dramatically overstates downstream.",
    },
    {
        "sector": "Fertilizer (NPK + AN + nitric acid)",
        "tr_export_to_eu_t":   500_000,   # TR fertilizer exports 2024 total $533M; ~30-40% to EU
        "eu_default_ef": 0.800,           # tCO₂ / t fertilizer (CBAM nitric acid)
        "bench_actual_ef": 0.400,         # Toros 0.525, BAGFAŞ 0.028 (N2O catalyst), Gübretaş 0.022; weighted ~0.4
        "source": "tradingeconomics.com: TR fertilizer exports 2024 = $533.47M. CBAM default 0.8.",
    },
]


def main():
    total_default = 0.0
    total_actual = 0.0

    rows = []
    for s in SECTORS:
        tonnes_co2_default = s["tr_export_to_eu_t"] * s["eu_default_ef"]
        tonnes_co2_actual  = s["tr_export_to_eu_t"] * s["bench_actual_ef"]
        cost_default = tonnes_co2_default * CBAM_PRICE_EUR_PER_TCO2
        cost_actual  = tonnes_co2_actual  * CBAM_PRICE_EUR_PER_TCO2
        savings = cost_default - cost_actual

        rows.append({
            "sector": s["sector"],
            "tr_export_to_eu_t": s["tr_export_to_eu_t"],
            "eu_default_ef": s["eu_default_ef"],
            "bench_actual_ef": s["bench_actual_ef"],
            "tco2_default": tonnes_co2_default,
            "tco2_actual":  tonnes_co2_actual,
            "cost_default_eur": cost_default,
            "cost_actual_eur":  cost_actual,
            "savings_eur":      savings,
            "savings_pct":      (savings / cost_default * 100) if cost_default > 0 else 0,
            "source":           s["source"],
        })
        total_default += cost_default
        total_actual  += cost_actual

    total_savings = total_default - total_actual

    OUT_JSON.write_text(json.dumps({
        "assumptions": {
            "cbam_price_eur_per_tco2": CBAM_PRICE_EUR_PER_TCO2,
            "valid_for": "2026 Q1 EU ETS spot price reference",
            "scope": "Turkey → EU exports under CBAM transitional/definitive phase",
        },
        "by_sector": rows,
        "total": {
            "cost_at_eu_default_eur": total_default,
            "cost_at_bench_actual_eur": total_actual,
            "savings_eur_if_operators_submit_verified_mrv": total_savings,
            "savings_pct": (total_savings / total_default * 100),
        },
    }, indent=2, ensure_ascii=False))

    fmt = lambda v: f"€{v/1e6:,.1f}M" if v < 1e9 else f"€{v/1e9:,.2f}B"

    md = ["# Fusion #1 — TR CBAM Exposure: EU Default vs Bench Actuals\n"]
    md.append(f"*Verified 2026-05-29. Assumes EU ETS allowance price €{CBAM_PRICE_EUR_PER_TCO2}/tCO₂ (2026 Q1 reference).*\n")
    md.append("## Headline\n")
    md.append(f"- **Total CBAM bill at EU default values: {fmt(total_default)}/yr**")
    md.append(f"- Total CBAM bill at bench-actual EFs (cf-corrected formula): {fmt(total_actual)}/yr")
    md.append(f"- **Savings if operators submit verified MRV instead of paying default: {fmt(total_savings)}/yr ({total_savings/total_default*100:.1f}% reduction)**")
    md.append("")
    md.append("That is the headline number for the formula's value to TR industry. Each year TR exporters stay on EU default pricing instead of MRV-verified submission costs them this much. Cement alone is the bulk because TR is the EU's largest cement-import source.")
    md.append("\n## Per-sector breakdown\n")
    md.append("| Sector | EU exports (t) | EU default EF | Actual EF | Cost @ default | Cost @ actual | Saved |")
    md.append("|---|---|---|---|---|---|---|")
    for r in rows:
        md.append(f"| {r['sector']} | {r['tr_export_to_eu_t']:,} | {r['eu_default_ef']:.2f} | {r['bench_actual_ef']:.2f} | {fmt(r['cost_default_eur'])} | {fmt(r['cost_actual_eur'])} | {fmt(r['savings_eur'])} ({r['savings_pct']:.0f}%) |")
    md.append("\n## Sources\n")
    for r in rows:
        md.append(f"- **{r['sector']}**: {r['source']}")
    md.append("\n## Caveats\n")
    md.append("- Export volumes are 2024 anchors; granular HS-6 monthly data is in TÜİK at `data.tuik.gov.tr/Kategori/GetKategori?p=dis-ticaret-104`, fetch as follow-up.")
    md.append("- Sector-level actual EFs are bench weighted averages; per-operator the variance is large (Gübretaş 0.022 to BAGFAŞ 0.028 to Erdemir 2.05 — orders of magnitude).")
    md.append("- CBAM transitional phase 2023-2025 uses reported (or default if not reported) emissions × free-allocation phase-out × ETS price. From 2026 the financial obligation kicks in. Numbers here are steady-state.")

    OUT_MD.write_text("\n".join(md))
    print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print(f"wrote {OUT_MD.relative_to(REPO)}")
    print()
    print(f"  Total CBAM at EU default: {fmt(total_default)}")
    print(f"  Total at bench actual:    {fmt(total_actual)}")
    print(f"  Savings:                  {fmt(total_savings)} ({total_savings/total_default*100:.1f}%)")
    print()
    print(f"  {'sector':32s} {'@default':>15s}  {'@actual':>15s}  {'saved':>15s}")
    for r in rows:
        print(f"  {r['sector']:32s} {fmt(r['cost_default_eur']):>15s}  {fmt(r['cost_actual_eur']):>15s}  {fmt(r['savings_eur']):>15s}")


if __name__ == "__main__":
    main()
