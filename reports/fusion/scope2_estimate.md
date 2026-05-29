# Fusion A1 — Scope 2 Estimation from TR Grid Intensity

*TR grid CO₂ factor: 0.4243 kgCO₂/kWh (Climatiq 2023 reference; EPİAŞ Şeffaflık serves hourly real-time updates).*

## Headline

- Bench total Scope 1 (audit-grade, where available): **40,324,095 tCO₂/yr**
- Bench total Scope 2 (this estimate): **8,816,115 tCO₂/yr**
- **Total Scope 1+2: 49,140,210 tCO₂/yr**

## Top-15 facilities by Scope 1+2

| Facility | Sector | Scope 1 (t) | Scope 2 est. (t) | Total | Scope 2 share |
|---|---|---|---|---|---|
| isdemir-iskenderun | steel | 10,663,364 | 539,710 | 11,203,074 | 5% |
| erdemir-eregli | steel | 6,667,232 | 407,328 | 7,074,560 | 6% |
| kardemir-karabuk | steel | 5,650,626 | 356,412 | 6,007,038 | 6% |
| nuh-hereke | cement | 3,584,953 | 159,622 | 3,744,575 | 4% |
| akcansa-canakkale | cement | 3,466,000 | 154,021 | 3,620,021 | 4% |
| goltas-isparta | cement | 1,669,072 | 140,019 | 1,809,091 | 8% |
| batisoke-soke | cement | 1,577,926 | 112,015 | 1,689,941 | 7% |
| akcansa-buyukcekmece | cement | 1,514,000 | 70,010 | 1,584,010 | 4% |
| habas-aliaga | steel | 830,338 | 687,366 | 1,517,704 | 45% |
| colakoglu-gebze | steel | 566,519 | 687,366 | 1,253,885 | 55% |
| afyon-cimento | cement | 1,200,000 | 50,407 | 1,250,407 | 4% |
| bursa-cimento | cement | 1,121,545 | 56,008 | 1,177,553 | 5% |
| tosyali-osmaniye | steel | 0 | 712,824 | 712,824 | 100% |
| icdas-biga | steel | 0 | 534,618 | 534,618 | 100% |
| akcansa-ladik | cement | 499,000 | 28,004 | 527,004 | 5% |

## Sector pattern

**Primary aluminum (Eti Seydişehir)** dominates Scope 2: Hall-Héroult electrolysis at 14,000 kWh/t × TR grid = ~6 tCO₂/t Al Scope 2 — orders of magnitude above Scope 1 (which is just anode + auxiliary). Tail of CBAM exposure.

**Cement** has low Scope 2 (~110 kWh/t × grid = 47 kgCO₂/t) compared to Scope 1 (660 kgCO₂/t). Scope 1 dominates the cement story.

**EAF steel** has high Scope 2 (600 kWh/t × grid = 255 kgCO₂/t) and low Scope 1 (250 kgCO₂/t process). **For EAF mills, Scope 2 is roughly equal to Scope 1** — the bench's previous EAF-wins-big finding under-counted total carbon exposure.

**Fertilizer** Scope 2 is small relative to Scope 1 — the chemistry dominates.


## Caveats

- Single grid factor (0.4243 kg/kWh) is national average; coastal industrial provinces (Kocaeli, İzmir) have higher grid intensity due to coal-heavy generation mix. EPİAŞ hourly intensity by region is the v1 input.

- Electricity intensity per tonne is a literature value, not operator-specific. Operators with captive cogen (Erdemir, İsdemir have own power plants) draw less from grid; their Scope 2 is lower than this estimate.

- Production estimate uses sector-default cf=0.6 when audit cf isn't disclosed; for the 21 disclosure facilities we have audit cf — use that in v1.


## Sources

- [Climatiq TR grid emission factor](https://www.climatiq.io/data/emission-factor/d56e798f-2094-40af-9ab2-1367f9c98b1f)
- [EPİAŞ Şeffaflık Platformu — real-time TR electricity data](https://seffaflik.epias.com.tr/)
- [eptr2 Python wrapper for EPİAŞ Şeffaflık 2.0 API](https://github.com/Tideseed/eptr2)