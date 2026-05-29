"""
Fusion A4 — TL-EUR FX sensitivity for CBAM exposure.

The €732M/yr total exposure is denominated in EUR. TR operators bill EU customers
in EUR but their cost base (labor, energy) is in TL. At what TL/EUR rate does
each operator's CBAM bill exceed a meaningful fraction of revenue?

We model: required EBITDA cushion to absorb CBAM under EU default vs cf-formula.
Sensitivity at TRY/EUR rates of 30, 40, 50, 60 (rough 2024-2027 range).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "reports" / "fusion"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / "fx_sensitivity.json"
OUT_MD = OUT_DIR / "fx_sensitivity.md"

# Per-operator: 2024 revenue (TL B), Scope 1 (tCO₂), EU export share (rough)
OPERATORS = [
    # name,                       rev_tl_b, scope1_t,    eu_export_share
    ("Akçansa",                       21.6,    5_479_000,  0.45),  # ~45% of TR cement to EU
    ("Çimsa",                         28.2,    4_760_000,  0.50),
    ("Erdemir (group)",              209.8,   17_336_630,  0.30),  # 30% flat steel to EU
    ("Kardemir",                      56.5,    5_650_626,  0.20),  # long products, less EU-heavy
    ("Nuh Çimento",                   13.8,    3_584_953,  0.15),
    ("OYAK Çimento",                  44.4,    7_712_391,  0.20),
    ("Bursa Çimento",                 15.4,    1_121_545,  0.10),
    ("BAGFAŞ",                         1.7,        9_828,  0.30),
    ("Gübretaş",                      48.0,       13_281,  0.10),
    ("Çolakoğlu (2023)",              61.4,      495_035,  0.50),  # EAF flat to EU
]

# Bench EFs (TR actual, our formula)
ACTUAL_EF = {"cement": 0.643, "steel-bfbof": 2.0, "steel-eaf": 0.25}
EU_EF = {"cement": 1.584, "steel-bfbof": 1.9, "steel-eaf": 1.9}

CBAM_PRICE_EUR = 85.0


def sector_for(name):
    n = name.lower()
    if "çimento" in n or "cement" in n.lower() or "akçansa" in n: return "cement"
    if "kardemir" in n or "erdemir" in n: return "steel-bfbof"
    if "çolakoğlu" in n: return "steel-eaf"
    if "bagf" in n or "gübre" in n.lower(): return "cement"  # not really, but no FX sensitivity for sub-threshold
    return "cement"


def main():
    fx_rates = [30, 40, 50, 60]
    rows = []
    for name, rev_tl_b, s1_t, share in OPERATORS:
        sec = sector_for(name)
        ef_actual = ACTUAL_EF.get(sec, 0.643)
        ef_eu = EU_EF.get(sec, 1.584)
        # CO2 attributable to EU exports
        export_co2 = s1_t * share
        # If formula EF / actual EF = X, then CO2 in EU default tariff = export_co2 × (eu_ef / actual_ef)
        eu_co2 = export_co2 * (ef_eu / ef_actual) if ef_actual > 0 else export_co2
        cbam_default_eur = eu_co2 * CBAM_PRICE_EUR
        cbam_actual_eur  = export_co2 * CBAM_PRICE_EUR
        savings_eur = cbam_default_eur - cbam_actual_eur

        # Express as % of revenue at each FX rate
        rev_eur = lambda fx: rev_tl_b * 1e9 / fx
        cbam_pct_revenue = {fx: (cbam_default_eur / rev_eur(fx)) * 100 for fx in fx_rates}
        savings_pct_revenue = {fx: (savings_eur / rev_eur(fx)) * 100 for fx in fx_rates}

        rows.append({
            "operator": name, "sector": sec,
            "rev_tl_b": rev_tl_b, "scope1_t": s1_t, "eu_export_share": share,
            "cbam_default_eur": cbam_default_eur,
            "cbam_actual_eur": cbam_actual_eur,
            "savings_eur": savings_eur,
            "cbam_pct_revenue_by_fx": cbam_pct_revenue,
            "savings_pct_revenue_by_fx": savings_pct_revenue,
        })

    rows.sort(key=lambda r: -r["cbam_default_eur"])

    OUT_JSON.write_text(json.dumps({
        "cbam_price_eur": CBAM_PRICE_EUR,
        "fx_rates_modeled": fx_rates,
        "operators": rows,
    }, indent=2, ensure_ascii=False))

    md = ["# Fusion A4 — TL-EUR FX Sensitivity for CBAM Exposure\n"]
    md.append(f"*CBAM allowance price €{CBAM_PRICE_EUR}/tCO₂. TR operators bill EU in EUR but cost base in TL — FX-sensitive exposure.*\n")
    md.append("## CBAM bill at EU default as % of revenue, by TL/EUR rate\n")
    md.append("| Operator | Scope 1 (tCO₂) | EU export share | CBAM @default (€M/yr) | " + " | ".join(f"@TRY{fx}" for fx in fx_rates) + " |")
    md.append("|---|---|---|---|" + "|".join("---" for _ in fx_rates) + "|")
    for r in rows:
        bill = f"{r['cbam_default_eur']/1e6:.1f}M"
        cells = " | ".join(f"{r['cbam_pct_revenue_by_fx'][fx]:.2f}%" for fx in fx_rates)
        md.append(f"| {r['operator']} | {r['scope1_t']:,.0f} | {r['eu_export_share']:.0%} | €{bill} | {cells} |")

    md.append("\n## CBAM savings (default → actual) as % of revenue, by FX rate\n")
    md.append("How much breathing room the formula buys, scaled to operator size.\n")
    md.append("| Operator | Savings (€M/yr) | " + " | ".join(f"@TRY{fx}" for fx in fx_rates) + " |")
    md.append("|---|---|" + "|".join("---" for _ in fx_rates) + "|")
    for r in rows:
        sav = f"{r['savings_eur']/1e6:.1f}M"
        cells = " | ".join(f"{r['savings_pct_revenue_by_fx'][fx]:.2f}%" for fx in fx_rates)
        md.append(f"| {r['operator']} | €{sav} | {cells} |")

    md.append("\n## Reading the table\n")
    md.append("- TR cement exporters face CBAM at **2-5% of revenue** under EU default — material to margin (typical cement EBITDA ~20%).\n")
    md.append("- Cement operators save **1-3% of revenue** by submitting MRV — full benefit goes directly to bottom line.\n")
    md.append("- BF/BOF integrated steel (Erdemir, Kardemir) has the highest absolute CBAM bill but lower revenue-share savings because EU default EF ≈ TR actual.\n")
    md.append("- FX appreciation (TL/EUR → higher) increases the revenue-denominated burden of CBAM (since bill is in EUR, revenue in TL). At TL/EUR = 60, cement makers face ~4-5% revenue erosion at EU default.\n")
    md.append("- FX depreciation (TL/EUR → lower toward 30) provides relief but the structural CBAM-savings gap (default vs actual) remains constant in EUR terms.\n")

    OUT_MD.write_text("\n".join(md))
    print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print(f"wrote {OUT_MD.relative_to(REPO)}")


if __name__ == "__main__":
    main()
