# Verifier B6 — EUTL EU Aluminum External Validation

*Generated 2026-06-01 from EUTL via euets.info. n=71 EU aluminum installations × ~20 years = 724 audit-grade verified Scope 1 facility-years.*

## Lens 1 — Time-series YoY consistency

- Median |ΔYoY|: 5.7%
- P90 |ΔYoY|: 32.3%
- Share within ±10% YoY: 60%
- Share within ±25% YoY: 78%

## Lens 2 — Country coverage (latest year per plant)

| Country | Plants | Mt/yr |
|---|---:|---:|
| Norway | 8 | 2.21 |
| Iceland | 3 | 1.41 |
| Germany | 17 | 1.05 |
| France | 3 | 0.74 |
| Spain | 5 | 0.42 |
| Sweden | 1 | 0.21 |
| Romania | 1 | 0.16 |
| United Kingdom | 4 | 0.14 |
| Greece | 1 | 0.12 |
| Italy | 5 | 0.12 |
| Netherlands | 4 | 0.08 |
| Slovenia | 2 | 0.07 |
| Austria | 1 | 0.06 |
| Hungary | 1 | 0.06 |
| Luxembourg | 2 | 0.03 |

## Lens 3 — Operator group rollup

| Operator | EU plants | EUTL EU sum (Mt) | Disclosed group (Mt) | EU share |
|---|---:|---:|---:|---:|
| Aluminium Dunkerque | 1 | 0.48 | 1.80 | 27% |
| Norsk Hydro | 5 | 1.43 | 12.00 | 12% |
| Speira | 3 | 0.08 | 1.00 | 8% |
| Rio Tinto | 1 | 0.32 | 30.00 | 1% |
| Trimet | 3 | 0.27 | 0.80 | 34% |
| Alcoa | 3 | 1.13 | 23.00 | 5% |
| Mytilineos | 0 | 0.00 | 1.60 | 0% |
| Aluminij Mostar | 0 | 0.00 | 0.90 | 0% |
| San Ciprián | 2 | 0.40 | 0.80 | 50% |

## Lens 4 — Direct formula test (n=18)

Applied `cap × route-EF × EU_cf (0.68)` to 18 EU plants with operator-published capacity.

- **log-MAE formula vs EUTL: 0.399**
- **log-MAE EU CBAM default vs EUTL: 0.567**
- **Reduction vs EU default: 29.7%**
- **Plants within ±15%: 4/18**

| Plant | Route | Capacity (Mt) | EUTL verified (Mt) | Formula (Mt) | Ratio | EU default (Mt) | EU/verified |
|---|---|---:|---:|---:|---:|---:|---:|
| Aluminium Dunkerque (FR) | primary | 0.30 | 0.48 | 0.41 | 0.84× | 0.30 | 0.62× |
| Trimet Saint-Jean (FR) | primary | 0.13 | 0.21 | 0.18 | 0.84× | 0.13 | 0.62× |
| Trimet Essen (DE) | primary | 0.16 | 0.08 | 0.22 | 2.70× | 0.16 | 1.99× |
| Trimet Hamburg (DE) | primary | 0.13 | 0.08 | 0.18 | 2.19× | 0.13 | 1.61× |
| San Ciprián Aluminio (ES) | primary | 0.23 | 0.40 | 0.31 | 0.78× | 0.23 | 0.57× |
| ALRO Slatina (RO) | primary | 0.27 | 0.16 | 0.36 | 2.28× | 0.27 | 1.67× |
| Hydro Sunndal (NO) | primary | 0.39 | 0.66 | 0.53 | 0.80× | 0.39 | 0.59× |
| Hydro Karmøy (NO) | primary | 0.18 | 0.32 | 0.24 | 0.75× | 0.18 | 0.55× |
| Hydro Årdal (NO) | primary | 0.18 | 0.32 | 0.24 | 0.77× | 0.18 | 0.57× |
| Hydro Høyanger (NO) | primary | 0.07 | 0.11 | 0.09 | 0.88× | 0.07 | 0.64× |
| Alcoa Mosjøen (NO) | primary | 0.19 | 0.44 | 0.26 | 0.58× | 0.19 | 0.43× |
| Alcoa Lista (NO) | primary | 0.09 | 0.12 | 0.12 | 1.02× | 0.09 | 0.75× |
| Alcoa Fjarðaál (IS) | primary | 0.34 | 0.57 | 0.46 | 0.80× | 0.34 | 0.59× |
| Norðurál Grundartangi (IS) | primary | 0.32 | 0.52 | 0.43 | 0.84× | 0.32 | 0.62× |
| Rio Tinto ISAL (IS) | primary | 0.21 | 0.32 | 0.28 | 0.89× | 0.21 | 0.65× |
| Lochaber Smelter (UK) | primary | 0.04 | 0.06 | 0.05 | 0.94× | 0.04 | 0.69× |
| Aluminij Mostar (SK) | primary | 0.10 | 0.02 | 0.14 | 5.72× | 0.10 | 4.20× |
| Kubikenborg (SE) | primary | 0.13 | 0.21 | 0.18 | 0.83× | 0.13 | 0.61× |

## Lens 5 — Sector aggregate

| Estimator | Predicted Mt/yr | EUTL truth (Mt/yr) | Ratio |
|---|---:|---:|---:|
| Formula at `primary` route EF × EU cf | 5.4 | 5.8 | 0.94× |
| EU CBAM default | 4.0 | 5.8 | 0.69× |

## Sources

- [EUTL via euets.info](https://www.euets.info)
- Operator IARs and industry-body data for capacity