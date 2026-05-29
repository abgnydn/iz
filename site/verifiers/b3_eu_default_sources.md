# Verifier B3 — EU CBAM Default EF Source Documentation

*Verified 2026-05-29. Provides the authoritative origin of each EU CBAM default value we benchmark against, so any reviewer can audit the comparison.*

## What we claim vs the EU default

| Sector | Our formula EF | EU CBAM default EF | Source of EU default |
|---|---|---|---|
| Cement / clinker | 0.643 t/t (TÜRKÇİMENTO 2023 TR avg) | **1.584 t/t** (Portland cement, transitional) | [EU Commission "Default values transitional period" 2023](https://taxation-customs.ec.europa.eu/system/files/2023-12/Default%20values%20transitional%20period.pdf), updated under IR 2025/2621 |
| Steel BF/BOF | 2.00 t/t (industry std + Erdemir-audited) | **1.90 t/t** | EU CBAM Implementing Regulation 2025/486, route-specific default |
| Steel EAF | 0.25 t/t (Çolakoğlu-audited + literature) | 1.90 t/t (same as BF/BOF — EU doesn't disaggregate by route in CBAM default) | EU CBAM IR 2025/486 |
| Aluminum primary | 8.60 t/t (Hall-Héroult + captive coal) | **8.60 t/t** (matches EU value) | EU CBAM IR — calibrated for primary smelting |
| Aluminum downstream | 0.45 t/t (rolling/extrusion, no electrolysis) | 8.60 t/t (EU doesn't disaggregate route) | EU CBAM IR — same default applied to all CN codes 7601-7616 |
| Fertilizer integrated | 0.50 t/t (Toros-audited, NH3+urea chain) | **0.80 t/t** | EU CBAM IR — nitric acid + AN baseline |
| Fertilizer N₂O-controlled | 0.05 t/t (BAGFAŞ audited 0.028) | 0.80 t/t (same default) | EU CBAM IR — no route disaggregation |
| Fertilizer blender | 0.025 t/t (Gübretaş audited 0.022) | 0.80 t/t | EU CBAM IR |

## How the EU set these values (JRC methodology)

The European Commission's Joint Research Centre (JRC) estimated CBAM emission intensities through publicly available data, using:

- **For cement**: IPCC 2006 Guidelines for National Greenhouse Gas Inventories — Volume 3 Chapter 2 (Mineral Industry Emissions); clinker factor of 0.95 assumed; sector mean emissions across EU producers.
- **For steel**: Worldsteel sustainability indicators + IEA Iron and Steel Technology Roadmap; weighted by EU production share of BF/BOF.
- **For aluminum**: International Aluminium Institute (IAI) global average for primary smelters with grid-mix Scope 2 included.
- **For fertilizer**: Fertilizers Europe sector baseline; assumes integrated NH₃ + nitric acid + AN/CAN production with industry-average abatement (no N₂O catalyst).

JRC primary document: [Marmier, A. — *Decarbonisation options for the cement industry* (JRC131246, 2023)](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC131246/JRC131246_01.pdf) and parallel sector studies.

## Why the EU defaults bias toward worst-case

- **Geographic conservatism**: defaults are calibrated for plants outside EU (i.e., presumed dirtier than EU best practice). Setting them lower than actual would let importers pay too little.
- **Route insensitivity**: a single default per CN code per sector means EAF gets penalized at BF/BOF intensity (7.6× over reality); downstream Al at primary-smelting intensity (19× over reality); N₂O-controlled fertilizer at integrated-without-abatement intensity (16× over reality).
- **Static data**: defaults set in 2023 don't update as global industry decarbonizes; the gap to actual TR emissions grows over time.

## The arbitrage we expose

For TR cement specifically:
> *"The default value for Turkish Portland cement under IR 2025/2621 is approximately 1.584 tCO2e per tonne, which is roughly 80% higher than Turkey's actual average of approximately 0.88 tCO2 per tonne."* — Sandbag policy brief, August 2025

That 80% number is the headline of the bench: every exporter who pays the default instead of submitting MRV-verified emissions pays ~80% more carbon tax than their actual emissions justify. We compute the total at €732M/yr in [fusion #1](../fusion/cbam_exposure.md).

## Reviewer checklist

If a reviewer asks "where did 1.584 come from?" — point them to:
1. [EU Commission default-values PDF (Dec 2023)](https://taxation-customs.ec.europa.eu/system/files/2023-12/Default%20values%20transitional%20period.pdf)
2. [IR 2025/2621 implementing regulation](https://eur-lex.europa.eu/) (post-transitional defaults)
3. [JRC131246 cement decarbonization study](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC131246/JRC131246_01.pdf) (methodology)
4. [Sandbag August 2025 brief — "Strengthening the CBAM by Default"](https://sandbag.be/2025/08/06/strengthening-the-cbam-by-default/)
5. [EMEP/EEA Guidebook 2.A.1 cement production](https://www.eea.europa.eu/publications/emep-eea-guidebook-2023/part-b-sectoral-guidance-chapters/2-industrial-processes-and-product-use/2-a-mineral-products/2-a-1-cement-production-2023) (IPCC method reference)
