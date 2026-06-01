# Verifier B6 — EUTL EU Fertilizer External Validation

*Generated 2026-06-01 from EUTL via euets.info. n=64 EU fertilizer installations × ~20 years = 729 audit-grade verified Scope 1 facility-years.*

## Lens 1 — Time-series YoY consistency

- Median |ΔYoY|: 15.7%
- P90 |ΔYoY|: 62.5%
- Share within ±10% YoY: 29%
- Share within ±25% YoY: 57%

## Lens 2 — Country coverage (latest year per plant)

| Country | Plants | Mt/yr |
|---|---:|---:|
| Netherlands | 6 | 5.41 |
| Germany | 13 | 3.05 |
| Poland | 5 | 1.74 |
| United Kingdom | 2 | 1.70 |
| Lithuania | 1 | 1.36 |
| Spain | 5 | 0.92 |
| France | 9 | 0.84 |
| Austria | 2 | 0.83 |
| Slovakia | 2 | 0.80 |
| Hungary | 1 | 0.71 |
| Belgium | 4 | 0.58 |
| Bulgaria | 2 | 0.58 |
| Croatia | 1 | 0.34 |
| Greece | 1 | 0.15 |
| Czech Republic | 1 | 0.12 |

## Lens 3 — Operator group rollup

| Operator | EU plants | EUTL EU sum (Mt) | Disclosed group (Mt) | EU share |
|---|---:|---:|---:|---:|
| Yara | 10 | 5.85 | 15.00 | 39% |
| BASF | 0 | 0.00 | 12.00 | 0% |
| Borealis | 2 | 0.69 | 4.50 | 15% |
| OCI | 0 | 0.00 | 5.00 | 0% |
| Grupa Azoty | 0 | 0.00 | 5.00 | 0% |
| Achema | 0 | 0.00 | 1.50 | 0% |
| Nitrogénművek | 1 | 0.71 | 0.80 | 89% |
| Lifosa | 0 | 0.00 | 0.60 | 0% |
| Anwil | 0 | 0.00 | 0.80 | 0% |

## Lens 4 — Direct formula test (n=2)

Applied `cap × route-EF × EU_cf (0.83)` to 2 EU plants with operator-published capacity.

- **log-MAE formula vs EUTL: 0.045**
- **log-MAE EU CBAM default vs EUTL: 0.045**
- **Reduction vs EU default: 0.0%**
- **Plants within ±15%: 2/2**

| Plant | Route | Capacity (Mt) | EUTL verified (Mt) | Formula (Mt) | Ratio | EU default (Mt) | EU/verified |
|---|---|---:|---:|---:|---:|---:|---:|
| Yara Sluiskil (NL) | integrated | 1.80 | 2.75 | 3.00 | 1.09× | 3.00 | 1.09× |
| Borealis Linz (AT) | integrated | 0.50 | 0.83 | 0.83 | 1.00× | 0.83 | 1.00× |

## Lens 5 — Sector aggregate

| Estimator | Predicted Mt/yr | EUTL truth (Mt/yr) | Ratio |
|---|---:|---:|---:|
| Formula at `integrated` route EF × EU cf | 30.0 | 17.1 | 1.76× |
| EU CBAM default | 30.0 | 17.1 | 1.76× |

## Sources

- [EUTL via euets.info](https://www.euets.info)
- Operator IARs and industry-body data for capacity