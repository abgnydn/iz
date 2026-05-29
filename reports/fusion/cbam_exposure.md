# Fusion #1 — TR CBAM Exposure: EU Default vs Bench Actuals

*Verified 2026-05-29. Assumes EU ETS allowance price €85.0/tCO₂ (2026 Q1 reference).*

## Headline

- **Total CBAM bill at EU default values: €1.43B/yr**
- Total CBAM bill at bench-actual EFs (cf-corrected formula): €702.3M/yr
- **Savings if operators submit verified MRV instead of paying default: €732.0M/yr (51.0% reduction)**

That is the headline number for the formula's value to TR industry. Each year TR exporters stay on EU default pricing instead of MRV-verified submission costs them this much. Cement alone is the bulk because TR is the EU's largest cement-import source.

## Per-sector breakdown

| Sector | EU exports (t) | EU default EF | Actual EF | Cost @ default | Cost @ actual | Saved |
|---|---|---|---|---|---|---|
| Cement / clinker | 4,000,000 | 1.55 | 0.64 | €527.3M | €218.6M | €308.7M (59%) |
| Steel (mixed BF/BOF + EAF) | 4,500,000 | 1.90 | 1.20 | €726.8M | €459.0M | €267.8M (37%) |
| Aluminum (downstream-heavy) | 200,000 | 8.60 | 0.45 | €146.2M | €7.7M | €138.6M (95%) |
| Fertilizer (NPK + AN + nitric acid) | 500,000 | 0.80 | 0.40 | €34.0M | €17.0M | €17.0M (50%) |

## Sources

- **Cement / clinker**: S&P Global: TR clinker exports 2024 = 5.22Mt total; ~3.3-4.8M to EU. EU CBAM default 1.551 t/t.
- **Steel (mixed BF/BOF + EAF)**: gmk.center: TR top-3 EU supplier of HS 7208/7210. EU CBAM default 1.9 t/t.
- **Aluminum (downstream-heavy)**: WITS: TR aluminum exports 2024. CBAM default 8.6 — calibrated for Hall-Héroult, dramatically overstates downstream.
- **Fertilizer (NPK + AN + nitric acid)**: tradingeconomics.com: TR fertilizer exports 2024 = $533.47M. CBAM default 0.8.

## Caveats

- Export volumes are 2024 anchors; granular HS-6 monthly data is in TÜİK at `data.tuik.gov.tr/Kategori/GetKategori?p=dis-ticaret-104`, fetch as follow-up.
- Sector-level actual EFs are bench weighted averages; per-operator the variance is large (Gübretaş 0.022 to BAGFAŞ 0.028 to Erdemir 2.05 — orders of magnitude).
- CBAM transitional phase 2023-2025 uses reported (or default if not reported) emissions × free-allocation phase-out × ETS price. From 2026 the financial obligation kicks in. Numbers here are steady-state.