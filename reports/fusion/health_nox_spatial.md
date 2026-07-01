# Fusion #4 — Industrial Pressure × Health (Spatial Framework)

*Verified 2026-05-29. Respiratory mortality at province resolution is **not publicly published** by TÜİK, so this analysis builds the spatial framework and flags the data gap as a policy finding.*

## Headline

Turkey publishes:

- Air-quality readings per station (Ministry of Environment National Air Quality Monitoring Network)

- Province-level **all-cause** mortality (TÜİK Death and Cause of Death Statistics)


Turkey does **not** publish:

- Province-level cause-specific mortality (J00-J99 respiratory) at granularity sufficient for facility attribution

- District-level mortality


**Policy implication**: iz has facility-resolution NOx (Beirle satellite divergence) + audit-grade Scope 1 for 21 facilities across 36 provinces. The moment TÜİK publishes province × ICD-10 J-chapter mortality, this dataset becomes ready-to-join for the first per-facility air-pollution-attribution study in Turkey.

## Top provinces by industrial pressure (our bench)

| Province | Facilities | Total capacity (t/yr) | Audit Scope 1 (tCO₂) | Beirle NOx Σ (kg/s) | Persistent pollution? | Sectors |
|---|---|---|---|---|---|---|
| Hatay | 4 |     11,300,000 |     10,663,364 | — | — | steel |
| Zonguldak | 1 |      4,000,000 |      6,667,232 | — | — | steel |
| Karabük | 1 |      3,500,000 |      5,650,626 | — | ✓ Yıldız 2022 | steel |
| Kocaeli | 5 |     13,000,000 |      4,164,753 | — | ✓ Yıldız 2022 | cement, fertilizer, steel |
| Çanakkale | 2 |      9,000,000 |      3,466,000 | — | — | cement, steel |
| Isparta | 1 |      5,000,000 |      1,669,072 | — | — | cement |
| İstanbul | 2 |      2,860,000 |      1,622,500 | — | — | aluminum, cement |
| Aydın | 1 |      4,000,000 |      1,577,926 | — | — | cement |
| Afyonkarahisar | 1 |      1,800,000 |      1,200,000 | — | — | cement |
| Bursa | 3 |      3,500,000 |      1,121,545 | — | ✓ Yıldız 2022 | cement, fertilizer, steel |
| İzmir | 5 |     12,500,000 |      1,101,461 | — | — | cement, steel |
| Samsun | 2 |      1,575,000 |        754,180 | — | — | cement, fertilizer |
| Mersin | 2 |      3,210,000 |        383,150 | — | — | cement, fertilizer |
| Adana | 3 |      7,821,700 |        203,840 | — | — | cement, fertilizer |
| Sakarya | 1 |        250,000 |         68,618 | — | ✓ Yıldız 2022 | aluminum |

## Cross-reference: persistent-pollution provinces (Yıldız 2022) vs our facility footprint

- Our bench covers 7 of the 14 persistent-pollution provinces: **Karabük, Kocaeli, Bursa, Sakarya, Şanlıurfa, Tekirdağ, Konya**
- Persistent provinces with NO bench facility: **Düzce, Gaziantep, Iğdır, Kahramanmaraş, Karaman, Manisa, Yalova** — likely driven by non-CBAM industry (power, refineries, heating)

## What this enables

Once TÜİK publishes province × ICD-10-J mortality (or via an FOI / academic data-sharing request to Ministry of Health), the iz facility-pressure layer plugs directly into:

1. **Excess respiratory mortality regression** — Beirle NOx flux per province (kg/s, our data) → respiratory mortality / 100k (TÜİK)

2. **Persistent-pollution attribution** — for the 8-12 provinces where our facilities sit AND PM10 exceeds EU limit, allocate the excess to specific operators via the Beirle layer

3. **Counterfactual modeling** — at each operator's published 2030 reduction target, compute downstream respiratory-mortality reduction expected in their province


## Caveats

- Yıldız 2022 used PM10 not NO₂; the persistent-pollution province list is a proxy for industrial pressure rather than a direct NOx measure.
- The 14-province persistent list includes mountain / dust-dominant provinces (Iğdır) that aren't industrial — pollution-source attribution at this resolution is genuinely hard.
- Beirle 2023 v2 NOx fluxes have ≤15 km matching uncertainty; we don't claim plume-resolution at city level.
- The right next step is an academic data-sharing request to the Ministry of Health for J00-J99 province × year mortality. ~6-week turnaround at TR public-data norms.