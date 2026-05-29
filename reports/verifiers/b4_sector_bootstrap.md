# Verifier B4 — Per-Sector Bootstrap CI

*Resamples facility indices with replacement 5000× per sector. Reports the formula's log-MAE reduction vs EU default, with 95% CI from the bootstrap distribution.*

## Per-sector formula reduction (95% bootstrap CI)

| Sector | n | Formula log-MAE | EU log-MAE | Reduction | 95% CI |
|---|---|---|---|---|---|
| cement | 8 | 0.223 | 1.102 | **+79.7%** | [+61.1%, +93.6%] |
| steel-BF/BOF | 3 | 0.057 | 0.117 | **+51.1%** | [+12.5%, +97.6%] |
| steel-EAF | 3 | 0.139 | 2.466 | **+94.4%** | [+93.1%, +96.1%] |
| aluminum-downstream | 2 | 0.252 | 1.652 | **+84.8%** | [+80.5%, +89.3%] |
| fertilizer-integrated | 3 | 0.282 | 0.762 | **+63.0%** | [+49.6%, +67.5%] |
| fertilizer-N2O | 1 | 0.575 | 4.043 | **+85.8%** | n=1 |
| fertilizer-blender | 1 | 0.128 | 3.875 | **+96.7%** | n=1 |

## What survives resampling

**Sectors where the entire 95% CI is positive** (formula reliably beats EU): cement, steel-BF/BOF, steel-EAF, aluminum-downstream, fertilizer-integrated

**Sectors where the CI crosses zero** (formula advantage is not significant): none

**Single-facility strata (no CI possible at n=1)**: fertilizer-N2O, fertilizer-blender