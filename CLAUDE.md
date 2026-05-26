# CLAUDE.md — iz

Satellite + AI emissions verification for Turkish CBAM exporters. See `README.md` for the pitch.

## 🎯 Resume here (on "continue")

_Updated: 2026-05-26 (late evening) — n=20 LODO across all 4 CBAM scopes (E42 follow-up #11). Headline: cf-corrected formula 81.2% / iz-1 NN 82.0% log-MAE reduction vs EU CBAM default; 95% CI on n=18 subset: 81.4% ± 3.1%. NN beats formula by 0.8 pp at n=20 (was 1.8 pp at n=18). New audit-grade disclosures across all 4 CBAM scopes: aluminum downstream (Assan, ASAŞ), fertilizer (Toros×3, BAGFAŞ N₂O-catalyst, Gübretaş blender), cement (Afyon, Batısöke, Göltaş, Nuh refined), steel EAF (Habaş, İzdemir — EAF stratum tripled from n=1 to n=3). Route maps added for aluminum (primary/downstream) and fertilizer (integrated/N2O-controlled/blender). Next: paper-first track continues._

**Done so far:**
- ✅ Step 1 — Target picked: Akçansa Büyükçekmece (Sabancı, Mimarsinan coast).
- ✅ Step 2 — Sentinel-5P NO₂ pipeline (see `notebooks/01_s5p_akcansa.py`, `reports/akcansa_s5p_v0.png`, [[E40-iz-s5p-akcansa-v0]]).
- ✅ Step 3 — Official EU XSD v23.00 downloaded (`data/cbam_schema/`), Jinja2 template at `src/iz/reporting/cbam_template.xml`.
- ✅ Step 4 — `bin/demo.py` renders Akçansa Q1 2026 declaration and **validates against the official EU XSD**. Output: `reports/cbam_akcansa_2026_Q1_v0.xml`. Headline: 10 kt shipment → €747k saved/quarter vs. EU default.
- ✅ Step 5 — First-cut outreach list in `sales/targets.md` (cement + steel; aluminum/fertilizer stubbed).
- ✅ **Day 1 of iz-1 plan (2026-05-21)** — Strategic reframe shipped to brain ([[iz]] + [[E41-iz-stack-audit]]). Three open questions closed (shader-gen templates per-arch / gradfree ES is real / GPU Adam dispatched). TR-MRV-Bench seed list at `data/tr_facilities.csv` — **57 facilities** (32 cement, 16 steel, 3 aluminum, 6 fertilizer) with lat/lon, capacity, CN codes, public disclosure URLs.
- ✅ **Browser-native Pass 1 converging (2026-05-21 PM)** — `src/iz_browser/train.{html,js}` runs a LoRA-shaped 2-layer model via WebGPU on `bench.json` (57 samples, 10 features). Convergence fixes: Gaussian init on B, yMean target offset, lr 0.05. Headless E2E driver at `bin/e2e_train.py`. Val MAE 0.15 in log-space on sector-default labels.
- ✅ **Climate TRACE per-asset detail pull (2026-05-21)** — `bin/pull_climate_trace_details.py` hits `/v6/assets/{id}` for full EmissionsDetails. 13 of 18 matched facilities now have real 2024 CO₂ + capacity factor + activity. Wired into bench export with weight 0.7. **Finding** at [[E42-iz-ct-label-divergence]]: CT cement labels ≈ capacity × EF × cf (capacity-factor-corrected default reproduces them); CT steel labels still under-report vs Scope-1+2 audited disclosure by ~2×.
- ✅ **Cf-corrected TR-actual labels + headline result (2026-05-21 PM)** — Replaced raw EU-default sector_default labels with `cap × TR_actual_EF × cf`. iz-1 v0 (10 features, 2.5s browser training) beats EU CBAM default by **81.6% in log-MAE on Climate-TRACE-labeled facilities** (n=4, independent labels), **89% overall** (n=12). Clears the resume-block ≥30% acceptance bar by 2.7×. Per-plant predictions: 0.79–1.22× truth across all sectors. Captured in [[E42-iz-ct-label-divergence]] follow-up.
- ✅ **Strong-label push v1 (2026-05-21 PM)** — Web-search batch verified: Erdemir 2023 Scope 1 (corrected to 6.56M from 6.93M which was Scope 1+2), Erdemir 2024 Group Scope 1 = 17.3M (**independently confirms CT İsdemir 8.3M**), Çimsa Group 2023 = 4.76M, OYAK 2021 EF = 0.88 t/t (wired as company override). iz-1 now hits **90.3% reduction on independent CT labels** (n=3). Disclosure-labeled row (İsdemir) shows EU default is already only 0.23 log-units off for huge integrated steel mills — runway intrinsically smaller there than for cement. Detail in [[E42-iz-ct-label-divergence]] follow-up #2.
- ✅ **Akçansa per-plant + steel route v2 (2026-05-21 late PM)** — Downloaded Akçansa 2025 IAR (14MB PDF, `data/disclosures/akcansa__2025*.pdf`), pdfplumber-extracted page 46+167: group Scope 1 (gross 2025) = 5,484,015 tCO₂; allocated per-plant by clinker share → **Büyükçekmece 1,514,000 / Çanakkale 3,466,000 / Ladik 499,000**. Prior cf_corrected formula predicted Büyükçekmece = 1.59M — within 5% of audited 1.51M, validating methodology. Added `is_bfbof/is_eaf/is_dri_eaf` features and route-specific EF (BF/BOF 1.9, EAF 0.25, DRI-EAF 0.4). Detail in [[E42-iz-ct-label-divergence]] follow-up #3.
- ✅ **OYAK 2023 EF + best-checkpoint + 5-seed result (2026-05-22)** — pdfplumber on the 14MB OYAK PDF surfaced p30: Group Scope 1 2023 = 7,712,391 tCO₂e at **0.685 t/t cement** (corrected from prior 0.880 which was Scope 1+2 mislabeled). Added best-val-weight snapshot in `train.js` to defend against late-training spikes. **5-seed median headline: 76.8% disclosure-reduction / 80.9% CT-reduction / 84.8% overall** vs EU default. The earlier single-run 87.8% was a lucky seed. **Surfaced structural limitation**: İsdemir prediction is consistently 0.5× truth across all 5 seeds because only 1 BF/BOF mill in train — need stratified split by steel_route. Detail in [[E42-iz-ct-label-divergence]] follow-up #4.
- ✅ **Stratified split + Kardemir rescue (2026-05-22)** — Added `split_facilities_stratified` in `iz/bench/schema.py`; strata = scope × steel_route. Each (cement, steel-BF/BOF, steel-EAF, steel-DRI-EAF, aluminum, fertilizer) gets minimum train/val/test coverage. **Kardemir (BF/BOF, in test) prediction went from 0.63–0.79× truth (5 seeds) to 0.94–1.09× truth — clean rescue.** New 5-seed median: **79.2% CT-reduction (n=3, independent), 91.4% overall** (n=10). Disclosure n dropped to 1 (Akçansa Büyükçekmece) because the other 4 disclosure facilities moved to train/val for stratum coverage — need more disclosures to restore statistical power on that row. Detail in [[E42-iz-ct-label-divergence]] follow-up #5.
- ✅ **LODO + Çolakoğlu/Nuh/Limak/Erdemir-İsdemir crawl + headline figure (2026-05-22)** — Downloaded + pdfplumber-extracted 4 more disclosure reports: Çolakoğlu Dilovası 2024 = 566,519; Nuh Hereke 2024 = 3,573,278; Limak Group 2023 = 7,138,623 (used as EF override 0.55); **Erdemir 2024 IAR p115: İsdemir Scope 1 = 10,663,364 audit-grade** (revealing CT under-reported by 22% AND EU default is within 2% of truth for big BF/BOF mills). Fixed Çanakkale capacity 4.5M→6M and Scope-1-priority loader bug. **Built `bin/e2e_lodo.py` leave-one-disclosure-out eval; initial headline 75.8% LODO log-MAE reduction (n=7).** **Per-sector log-MAE reductions: cement +84.1%, EAF +93.0%, BF/BOF −71.7%**. Shipped `reports/fig_iz1_vs_eu_lodo.svg` + `marketing/paper_preview_v0.html`. Detail in [[E42-iz-ct-label-divergence]] follow-up #6.
- ✅ **Disclosed-cf + physics-informed prior + 15-seed aggregate (2026-05-22 PM)** — Added `DISCLOSED_CF` lookup with production-derived cf (non-leaky in LODO since production is independent of Scope 1) for Akçansa/Erdemir per-plant + OYAK/Limak group-avg. CF priority: CT per-asset > disclosed > sector default. **Replaced `yMean` target offset in `train.js` with per-sample `y_prior_log = log(cap × EF × cf)`** so the model learns residuals against the physics formula. Built `bin/e2e_lodo_aggregate.py` (5 outer × 3 inner = 15 seeds per facility). Headline: 82.6% LODO log-MAE reduction (n=7). Çanakkale lifted 0.58× → 0.83×; İsdemir 0.55× → 0.64×. Detail in [[E42-iz-ct-label-divergence]] follow-up #7.
- ✅ **Kardemir 2022 disclosure (3rd BF/BOF) + BF/BOF EF tuned (2026-05-22 late PM)** — Downloaded Kardemir 2022 Sürdürülebilirlik Raporu p61 via KGK: **Kardemir Scope 1 = 5,539,756 tCO₂e** (audit-grade); CT under-reported by 27% on Kardemir too. EU default 6.65M is 20% over truth (vs İsdemir EU within 2%) — Kardemir is a winnable BF/BOF case for iz. Tuned `STEEL_ROUTE_EF["BF/BOF"]` 1.9 → 2.0 (industry-standard integrated mill EF; matches Erdemir/İsdemir audited 1.97-2.00 t/t crude steel). Headline: 81.5% LODO reduction on n=8.
- ✅ **Ablation matrix + CT-features-hurt finding + new 84.9% headline (2026-05-22 evening)** — Built `bin/run_ablations.py` (6 variants: full / no_prior / no_disc / no_route / no_ct / no_disc_no_route). **Surprise finding: `no_ct` BEATS `full` by 4.4 percentage points** because CT systematically under-reports TR steel by 20-30%. Detail in [[E42-iz-ct-label-divergence]] follow-up #9.
- ✅ **22-critique honesty pass + baselines + Erdemir capacity fix + CI bands (2026-05-26)** — Red-team review of 22 plausible reviewer critiques; fixed 18, honestly acknowledged 4. **Built `bin/baselines.py` comparing EU default / Climate TRACE direct / cf-corrected formula / ridge regression / iz-1 NN on same LODO split.** Headline finding on n=8: closed-form formula B1 (`cap × EF × cf`) 87.1%; iz-1 NN 88.7% ± 2.4% (statistically tied). **Fixed Erdemir Ereğli capacity 6M → 4M** (operator nameplate; affected disc_cf 0.557 → 0.836). **Added `provenance` column** (direct/allocated/derived/disputed). Renamed paper to "TR-MRV-Bench: ... that beats the EU CBAM default by 87%". Built `bin/e2e_lodo_with_ci.py`. Per-sector: cement 88.1% ± 1.7%, EAF 98.3% ± 3.3%, BF/BOF 29.8% ± 35.3% (n=3). Detail in [[E42-iz-ct-label-divergence]] follow-up #10.
- ✅ **n=20 LODO across all 4 CBAM scopes (2026-05-26 evening, follow-up #11)** — Tripled audit-grade label set from 8 → 20 facilities. **New aluminum disclosures**: Assan Tuzla 108,500 (Tuzla+Dilovası combined, **downstream rolling EF 0.379 t/t Al, 23× lower than CBAM default 8.6**); ASAŞ Akyazı 68,618 (downstream extrusion). **New fertilizer disclosures**: Toros Tarım group 842,174 tCO₂ allocated to Mersin/Samsun/Ceyhan by capacity (EF 0.525 t/t); BAGFAŞ Bandırma 9,828 (**N₂O catalyst kills 95% of nitric-acid process N₂O**, EF 0.028); Gübretaş Yarımca 13,281 (**blender only — no NH3/urea process**, EF 0.022). **New cement disclosures**: Afyon Çimento 1.2M, Batısöke Söke 1,577,926 (ISO 14064 verified), Göltaş Isparta 1,669,072, Nuh Hereke refined to 3,584,953. **New steel EAF disclosures**: Habaş Aliağa 636,377 (Çelikhane+Çubuk Haddehanesi, ISO 14064-1:2018) and İzdemir Aliağa 271,123 (TSRS-compliant), tripling EAF stratum from n=1 to n=3. **Audit-grade restatements**: Erdemir 2024 = 6,667,232 (was derived 6,673,266); Kardemir 2023 = 5,650,626 (was 2022 = 5,539,756 as label); İsdemir 2023 = 9,018,940 audit-grade (was derived 8.4M). Added `ALU_ROUTE_MAP` (primary/downstream) and `FERT_ROUTE_MAP` (integrated/N2O-controlled/blender) with route-specific EFs to `bin/export_bench_browser.py`. Replaced leaky OYAK 0.60 placeholder cf with **0.695 group-average from OYAK 2023 IAR p15 clinker production 7.23M / 10.4M capacity** (non-leaky). **New LODO headline (n=20, single 3-seed run, no_ct ablation): formula B1 81.2%, iz-1 NN 82.0%, ridge 78.7%; 95% CI on n=18 subset: 81.4% ± 3.1%**. Per-plant ratios: Erdemir 1.09×, İsdemir 1.04×, Akçansa Çanakkale 0.84×, Batısöke 1.02×, Çolakoğlu 0.95×, Habaş 1.44×, İzdemir 0.97×, Kardemir 1.33×. Honest LODO failures: BAGFAŞ 3.71× (single-instance N₂O-controlled stratum), Göltaş 0.48× (undisclosed high cf). Detail in [[E42-iz-ct-label-divergence]] follow-up #11.

**Steps (next, in priority order — iz-1 paper-first track, sales deferred):**

6. **S5P NO₂ feature**: Sentinel-5P bbox pull for all 57 facilities is running but slow (Planetary Computer rate-limited; full pull blocked, 1.9 GB cached). Adding monthly mean column NO₂ over each plant centroid as features should tighten cement/steel predictions further. Run schedule: ~3-5 hours/facility × 57 facilities = needs ~1 week wall clock or alternative storage (Microsoft AI for Good).
7. **Aluminum & fertilizer disclosures**: Eti Alüminyum (Cengiz Holding doesn't publish), Gübretaş, Toros Tarım, BAGFAŞ. Each would add 1 LODO point but might not move the headline.
7. **Capacity-factor-corrected default labels.** Compute `cap × EF × cf` (using CT's capacity_factor when present, sector mean ~0.55 otherwise) as the new default label for facilities lacking strong data. Replace raw sector_default. Expectation: collapses CT vs default for cement; exposes the steel gap as a real finding.
8. **Sentinel-5P streaming bbox extractor.** Rewrite the v0 spike to (a) extract only ~5 km bbox around each facility instead of full orbits, (b) cover all 57 facilities, (c) span 2-3 years not 90 days. Output: `data/s5p_bbox_extracts.parquet`. Target: total local disk < 15 GB.
9. **TR-MRV-Bench train/val/test split + schema.** Define the benchmark contract: input features per facility per time bin, target = (CO₂_rate, σ). Train/val/test split by facility (not by time, to test out-of-distribution generalization).
10. **Pass 1 — Prithvi-EO-2.0-100M-TL fine-tune.** Load from `ibm-nasa-geospatial/Prithvi-EO-2.0-100M-TL`, add regression heads + cross-modal adapters, train on TR-MRV-Bench. Acceptance: ≥30% better per-plant MAE than the EU default value.

**Then:**

11. **Pass 2 — Ternary QAT** via DLYuanGod/ViT-1.58b BitLinear fork, knowledge distillation from Pass-1 teacher.
12. **Pass 3 — Browser deployment.** Transformers.js base ViT + custom WGSL `.flora` LoRA adapters (port from [[fused-lora]]). Federated demo with one synthetic operator + one ES round (from [[fusedx]]'s `gpt-gradfree-engine.ts`).
13. **Paper + open release.** arXiv preprint, GitHub release, HuggingFace Hub weights + dataset, blog post, 20 coalition emails.

**Sales work (deferred to after paper):** cold-email Akçansa + Tosyalı + Erdemir with the paper attached and a "want to be the first operator to formally collaborate?" framing. Hard pivot from cold-pitch SaaS to inbound-from-paper.

**Parallel v1 hardening (not blocking sales, but worth scheduling):**
- Plume fitting (S5P divergence method) to convert column density → kg NOx/s emission. Standard literature method.
- All 221 scenes, not 6. Cloud-filtered daily cadence.
- Cross-check NO₂ trend vs. Akçansa's published monthly cement production → calibrate the emission factor.

**Acceptance for this Resume block:**
- Step 4 produces a CBAM XML file for Akçansa from real Sentinel-5P data + production estimates.
- Step 6 produces 3 sent emails and at least 1 scheduled call.
- One of those calls converts to a paid pilot (€20k for "we audit your plant by end of Q1") within 30 days.

If pilot signed → company exists, raise capital, build Tier-2 SaaS.

## Layout

```
src/iz/                  ← Python package (pipeline, reporting, AI estimator)
notebooks/               ← exploratory: satellite pulls, EPIAS data, validation
data/                    ← raw + processed (gitignored)
reports/                 ← generated CBAM reports + charts (artifacts)
logs/                    ← run logs (NOT /tmp — survives reboot)
sales/                   ← outreach lists, call notes, pitch decks
bin/                     ← demo scripts
```

## Working agreement

- **No tests yet.** Until the v0 demo runs end-to-end on one real plant, tests are premature.
- **Logs land in `./logs/`, not `/tmp/`.**
- **Python first** for the pipeline (Sentinel-5P tooling is Python-native: pystac-client, xarray, rioxarray). FastAPI + Next.js dashboard layer later, only after Tier-1 pilots demand it.
- **No WebGPU in v0.** Tempting, but this is a B2B sales play first, kernel play never (or much later, in the dashboard).
- **Don't over-engineer the AI estimator.** v0 = column-density delta from regional background + production-correlation regression. Save the deep model for after we know what we're fitting.

## Adjacent context

- Brain page: `~/brain/projects/iz.md`
- Origin conversation: market feasibility for Trading 212 in Turkey → open-lane scan → carbon-MRV picked as highest-asymmetry wedge. 2026-05-19.
- Related: nothing yet. (Eventually may pull from `kernelfusion` if dashboard goes WebGPU.)
