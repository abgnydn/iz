# Verifier B6 — EUTL EU Steel External Validation

*Generated 2026-06-01 from EUTL via euets.info. n=282 EU steel installations × ~20 years = 4,040 audit-grade verified Scope 1 facility-years.*

## Lens 1 — Time-series YoY consistency

- Median |ΔYoY|: 9.8%
- P90 |ΔYoY|: 51.7%
- Share within ±10% YoY: 46%
- Share within ±25% YoY: 71%

## Lens 2 — Country coverage (latest year per plant)

| Country | Plants | Mt/yr |
|---|---:|---:|
| Germany | 44 | 26.28 |
| Austria | 5 | 11.59 |
| France | 21 | 11.51 |
| Belgium | 7 | 7.55 |
| Italy | 33 | 7.23 |
| United Kingdom | 4 | 6.22 |
| Spain | 20 | 5.34 |
| Sweden | 13 | 5.26 |
| Netherlands | 2 | 4.62 |
| Finland | 3 | 4.41 |
| Czech Republic | 4 | 2.60 |
| Poland | 10 | 2.04 |
| Romania | 7 | 1.54 |
| Luxembourg | 2 | 0.30 |
| Hungary | 2 | 0.23 |

## Lens 3 — Operator group rollup

| Operator | EU plants | EUTL EU sum (Mt) | Disclosed group (Mt) | EU share |
|---|---:|---:|---:|---:|
| ArcelorMittal | 14 | 24.17 | 165.00 | 15% |
| Tata Steel | 2 | 4.62 | 31.00 | 15% |
| ThyssenKrupp | 0 | 0.00 | 18.50 | 0% |
| Salzgitter | 1 | 3.34 | 8.00 | 42% |
| Voestalpine | 2 | 11.41 | 13.50 | 85% |
| Liberty Steel | 2 | 1.49 | 24.00 | 6% |
| SSAB | 2 | 4.74 | 8.00 | 59% |
| Acerinox | 1 | 0.18 | 1.50 | 12% |
| Outokumpu | 1 | 0.03 | 2.70 | 1% |
| U.S. Steel Kosice | 0 | 0.00 | 5.50 | 0% |

## Lens 4 — Direct formula test (n=12)

Applied `cap × route-EF × EU_cf (0.51)` to 12 EU plants with operator-published capacity.

- **log-MAE formula vs EUTL: 0.407**
- **log-MAE EU CBAM default vs EUTL: 0.886**
- **Reduction vs EU default: 54.1%**
- **Plants within ±15%: 3/12**

| Plant | Route | Capacity (Mt) | EUTL verified (Mt) | Formula (Mt) | Ratio | EU default (Mt) | EU/verified |
|---|---|---:|---:|---:|---:|---:|---:|
| ArcelorMittal Dunkirk (FR) | BF/BOF | 7.00 | 5.17 | 7.16 | 1.38× | 6.80 | 1.31× |
| ArcelorMittal Gent (BE) | BF/BOF | 5.00 | 3.69 | 5.11 | 1.39× | 4.86 | 1.32× |
| ArcelorMittal Bremen (DE) | BF/BOF | 4.00 | 2.27 | 4.09 | 1.80× | 3.88 | 1.71× |
| Voestalpine Linz (AT) | BF/BOF | 5.50 | 8.67 | 5.62 | 0.65× | 5.34 | 0.62× |
| Salzgitter Flachstahl (DE) | BF/BOF | 4.50 | 3.34 | 4.60 | 1.38× | 4.37 | 1.31× |
| ThyssenKrupp Duisburg (DE) | BF/BOF | 11.00 | 12.31 | 11.24 | 0.91× | 10.68 | 0.87× |
| Tata Steel IJmuiden (NL) | BF/BOF | 7.00 | 4.54 | 7.16 | 1.57× | 6.80 | 1.50× |
| SSAB Raahe (FI) | BF/BOF | 2.50 | 3.74 | 2.56 | 0.68× | 2.43 | 0.65× |
| Outokumpu Tornio (FI) | EAF | 1.60 | 0.63 | 0.20 | 0.32× | 1.55 | 2.46× |
| Riva Verona (IT) | EAF | 1.40 | 0.16 | 0.18 | 1.14× | 1.36 | 8.63× |
| Feralpi Lonato (IT) | EAF | 1.20 | 0.09 | 0.15 | 1.79× | 1.17 | 13.58× |
| Sidenor Basauri (ES) | EAF | 1.00 | 0.11 | 0.13 | 1.14× | 0.97 | 8.66× |

## Lens 5 — Sector aggregate

| Estimator | Predicted Mt/yr | EUTL truth (Mt/yr) | Ratio |
|---|---:|---:|---:|
| Formula at `BF/BOF` route EF × EU cf | 230.0 | 97.4 | 2.36× |
| EU CBAM default | 218.5 | 97.4 | 2.24× |

## Sources

- [EUTL via euets.info](https://www.euets.info)
- Operator IARs and industry-body data for capacity