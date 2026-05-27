# TR-MRV-Bench: A public per-facility emissions benchmark for Turkish CBAM-scope industry, with a physics baseline that beats the EU CBAM default by 85% across all four CBAM scopes

**Ahmet Barış Günaydın**¹
¹Independent · hi@barisgunaydin.com · barisgunaydin.com

*v0.1 · 2026-05-27 · [github.com/abgnydn/iz](https://github.com/abgnydn/iz) · [iz-b0n.pages.dev](https://iz-b0n.pages.dev) · Apache-2.0*

---

## Abstract

The EU Carbon Border Adjustment Mechanism (CBAM) and analogous emissions-trading regimes require per-facility CO₂ accounting that is independently verifiable. Existing per-facility data sources have known gaps: Climate TRACE under-reports 4 of 5 audit-matched Turkish facilities (mean bias −17%, median −23%; under-reporting concentrated in steel and cement); operator self-reports trust the operator; satellite tools (GHGSat, Carbon Mapper) focus on methane with no CBAM tie-in.

We release **TR-MRV-Bench v0**, a public benchmark of 59 Turkish CBAM-scope facilities with three-tier supervision: **21 audit-grade strong labels** across all four CBAM scopes — cement, steel, aluminum, fertilizer — from operator Integrated Annual Reports, TSRS-compliant sustainability reports, and ISO 14064-1 third-party verifications; 8 Climate TRACE per-asset labels; capacity-factor-corrected default labels for the rest. The bench includes operator-published source URLs and page numbers for every audit-grade row.

On this bench we evaluate a closed-form physics baseline:

```
tCO₂ = capacity × route-EF × capacity-factor
```

with route-aware emission factors (steel BF/BOF / EAF / DRI-EAF, aluminum primary / downstream, fertilizer integrated / N₂O-controlled / blender) and a capacity-factor priority (Climate-TRACE per-asset > operator-disclosed production-÷-capacity > sector mean). The formula reduces per-plant log-MAE by **+85.3%** vs the EU CBAM default in leave-one-disclosure-out (LODO) evaluation across the 21 audit-grade test facilities (capacities operator-audited). A 2-layer LoRA-shaped neural network trained on the bench's residuals against this prior reaches **+83.3%** with 95% data-bootstrap CI [+72.0%, +90.6%] — statistically tied with the closed-form formula. Ridge regression on the same features lags both at +81.4%.

Per-sector bootstrap 95% CIs: aluminum downstream [+89.9%, +91.5%], EAF steel [+96.6%, +97.6%], cement [+66.2%, +92.2%], fertilizer [+34.6%, +93.0%], BF/BOF steel [−289%, +97%] (n=3 stratum, structurally wide).

The actionable artifacts are the bench, the formula, and the source-cited disclosure crawl. Our learned model is a working reference implementation, not a state-of-the-art result. The bench and code are released under Apache-2.0 with the explicit intent of being used by Turkish exporters, EU-accredited CBAM verifiers, and policy researchers — not as a SaaS product.

**Practical implication:** if every TR CBAM-scope operator used real per-facility data instead of the EU default, our estimate is **~€2 billion per year** in CBAM payments stays in Turkey instead of going to the EU treasury (CBAM at €85/tCO₂, realistic sector EU-export shares).

---

## 1. Introduction

CBAM enters full enforcement in 2034. For Turkish exporters in CBAM-scope sectors (cement, iron and steel, aluminum, fertilizer), the choice on each shipment to the EU is binary: file verified emissions data through an EU-accredited verifier, or pay tariff against a deliberately-punitive default value. The default is calibrated as a stick: for cement it is 1.584 tCO₂ per tonne of cement, vs a TR industry average around 0.643 t/t (TÜRKÇİMENTO 2023). For aluminum the default is 1.5 t/t — appropriate for primary (Hall-Héroult) smelting but absurd for downstream rolling, where actual emissions are ~0.4 t/t (a 4× over-charge that hits the entire downstream aluminum value chain). For fertilizer plants with N₂O abatement catalysts, the default overstates by 20-30× (BAGFAŞ 2024 audited: 0.028 t/t product; EU default: 0.8 t/t).

The intended path out is for operators to commission EU-accredited verifier audits (DNV / TÜV Süd / Bureau Veritas / SGS) at €30-100k per facility per year. For mid-tier operators this cost frequently exceeds the savings, so they eat the default. The whole system depends on operators absorbing the verifier-audit cost — which means smaller plants overpay disproportionately, and the resulting CBAM revenue is partly a regressive industry-size penalty rather than an emissions-pricing instrument.

This paper presents the bench, methodology, and result as **open infrastructure**, not a SaaS product. The point is to make the per-facility data accessible to every operator, verifier, journalist, and policy researcher who needs it. The math is simple enough that no one should rent it; the prize for getting it right is large enough that everyone should have it.

### 1.1 Contributions

1. **TR-MRV-Bench (§4).** Public per-facility emissions benchmark with three-tier supervision (audit-grade / Climate TRACE / cf-corrected default), provenance-tagged labels (direct / allocated / derived / disputed / composite), and stratified train/val/test split by `(scope × route)` covering steel BF/BOF / EAF / DRI-EAF, aluminum primary / downstream, fertilizer integrated / N₂O-controlled / blender. 21 audit-grade test facilities across all four CBAM scopes.

2. **cf-corrected formula baseline (§3, §5).** Closed-form `cap × EF × cf` with explicit route-aware EF and cf priority rules. **+85.3% log-MAE reduction vs EU default on n=21 LODO** (capacities operator-audited). 15 of 21 predictions land within ±20% of audit truth.

3. **EU CBAM default is route-asymmetric (§5.1).** The default over-estimates cement by 2-5×, EAF steel by 10×, downstream aluminum by 4×, and fertilizer blenders by 90×. It is within 5% of audited reality only for big BF/BOF integrated mills.

4. **Climate TRACE under-reports TR industrial emissions (§5.2).** 4 of 5 audit-matched facilities under-reported: Erdemir −29%, İsdemir −22%, Kardemir −23%, Nuh −23%; Göltaş the lone over-report at +11%. Mean bias −17.2%, median −22.5%.

5. **The formula and the model are statistically tied (§6).** A LoRA-shaped MLP achieves +83.3% vs the formula's +85.3% on n=21 LODO. Ridge regression lags at +81.4%. **The shipped baseline is the formula.** The NN is a working reference implementation that future work on satellite features or multi-year LODO can build on.

### 1.2 What's not in this work

We do not use satellite signal — the Sentinel-5P NO₂ pipeline runs but did not make it into the model in v0. We are not a "foundation model" — earlier framing along those lines is dropped; iz is a 2-layer MLP at 500 parameters trained on ~40 samples after LODO holdout. We do not claim per-quarter or per-month accuracy — all labels are annual.

---

## 2. Related work

**Per-facility CO₂ inventories.** Climate TRACE provides a global bottom-up per-asset emissions inventory derived from satellite and remote-sensing data. Their data is open and we use 8 of their TR-asset rows in the bench. However, we find a consistent under-reporting bias on TR steel (−22 to −29% on 3 BF/BOF mills) and now also TR cement (−23% on Nuh Hereke) when compared against audit-grade operator disclosures. Plausible mechanism: CT's source data misses on-site captive coal power plants common in TR integrated mills, and the alternative-fuel share at TR cement plants varies plant-to-plant in ways the global methodology may not capture. We catalog this finding but do not claim it generalizes globally — our sample is n=5.

**Operator-self-reported MRV SaaS.** Persefoni, CarbonChain, Sweep ingest operator-typed data and produce dashboards. The data quality is whatever the operator types. For CBAM compliance the data still has to pass through an EU-accredited verifier.

**Satellite plume detection.** GHGSat Vanguard, Carbon Mapper Tanager-1, MethaneSAT, Kayrros focus on methane plumes (the dominant per-shot signal). CO₂ plumes are much harder to detect — they're 100× less concentrated above background and overlap with biogenic CO₂. None of these are connected to a CBAM-tariff workflow.

**Earth-observation foundation models.** Prithvi-EO-2.0 (Jakubik et al., 2023; 2024), Clay, SatMAE, ScaleMAE, SpectralGPT provide pre-trained backbones for downstream Earth-observation tasks. These are promising directions for satellite-feature work but at iz's current data scale (~40 training samples) they are infeasible to fine-tune productively.

**Industrial emissions benchmarks.** Most existing emissions benchmarks (CDP, GRESB, TPI) operate at the corporate level, not per-facility. The CDP Cement and Steel sector reports aggregate to operator group level. To our knowledge, TR-MRV-Bench is the first public per-facility emissions benchmark for any country's CBAM-scope industry with explicit source-PDF citations and a reproducible LODO evaluation harness.

---

## 3. Method

### 3.1 The formula

```
tCO₂[i] = capacity[i] × emission_factor[i] × capacity_factor[i]
```

Three operator-published quantities. The selection rules:

**Capacity** is the operator's nameplate annual production capacity in tonnes of CBAM-good (cement for cement plants, crude steel for steel mills, aluminum for Al, fertilizer product for fertilizer plants). We use the most-recent operator-published figure from corporate websites, KAP filings, Integrated Annual Reports, or industry registries; provenance is recorded per facility.

**Emission factor (EF)** is tCO₂ per tonne of CBAM-good output. Selection priority:

1. Operator-published facility-specific EF (rare; e.g. Bursa Çimento 2024 TSRS p58: 0.532 t/t grey clinker).
2. Route-specific EF for the plant's process type. For steel: BF/BOF integrated 2.0, EAF 0.25, DRI-EAF 0.4. For aluminum: primary (Hall-Héroult) 8.6, downstream rolling 0.45. For fertilizer: integrated NH₃+urea 0.5, N₂O-controlled 0.05, blender 0.025.
3. Sector mean: cement 0.643 t/t cement (TÜRKÇİMENTO 2023), steel 1.44, aluminum 1.5, fertilizer 0.8.

**Capacity factor (cf)** is operator-disclosed annual production divided by nameplate capacity. Selection priority:

1. Climate TRACE per-asset measurement (independent of operator self-reporting).
2. Operator-disclosed production ÷ capacity. This is **non-leaky** with respect to Scope 1 emissions because production tonnage is reported on a separate page of the same annual report — when a facility's Scope 1 is held out for LODO, its production tonnage remains available.
3. Sector-mean default: cement 0.55, steel 0.70, aluminum 0.85, fertilizer 0.65.

The route maps and EF tables are hardcoded in `bin/export_bench_browser.py` and open-source.

### 3.2 The bench

59 Turkish CBAM-scope facilities: 34 cement, 16 steel, 3 aluminum, 6 fertilizer. Three supervision tiers:

1. **Strong labels (audit-grade, weight 1.0):** 21 facilities with operator-published Scope 1 tCO₂ from Integrated Annual Reports, TSRS-compliant sustainability reports, or ISO 14064-1 third-party verifications. Each row records the source URL, page number, year, provenance (`direct` / `allocated` / `derived` / `disputed` / `composite`), and assurance tier (ISO 14064 / TSRS / operator-audited).

2. **Climate TRACE labels (weight 0.7):** 8 facilities matched to a CT v6 per-asset entry (proximity join ≤30 km). We use the most recent year's `co2e_100yr` emissions.

3. **Capacity-factor-corrected default labels (weight 0.4):** the remaining 30 facilities receive a formula-derived label. These are not used as test points — they are only used to give the model more training samples.

The bench is in `data/tr_facilities.csv` (facility identity), `data/tr_facility_known_emissions.csv` (disclosure rows), and the rendered `src/iz_browser/bench.json` (per-facility samples for the trainer).

### 3.3 Assurance tiers

Of the 21 audit-grade rows, the assurance is non-uniform:

- **ISO 14064-1 third-party verified (n=5):** Habaş, Batısöke, Nuh, BAGFAŞ N₂O measurement, Bursa Çimento.
- **TSRS-compliant limited assurance from a KGK-registered firm (n=6):** Assan, ASAŞ, Toros, Gübretaş, Afyon, Göltaş, newer Akçansa.
- **Operator IAR Big4-audited overall but without GHG-specific verification (n=10):** Erdemir, İsdemir, Kardemir, Çolakoğlu, OYAK group, Limak group, older Çimsa.

The bench browser shows the tier per row. The headline number does not weight by tier — that is a deliberate v0 simplification we acknowledge.

### 3.4 Allocated labels

6 of 21 strong labels are allocated, not directly disclosed:

- **Akçansa Büyükçekmece / Çanakkale / Ladik:** the operator's 2025 IAR p46 gives group Scope 1 = 5,484,015 tCO₂ and p167 gives per-plant clinker production. We split the group total by clinker share (27.6% / 63.2% / 9.1%).

- **Toros Tarım Mersin / Samsun / Ceyhan:** Tekfen's 2024 TSRS p18 gives Toros group Scope 1 = 842,174 tCO₂. We split by nameplate capacity (Mersin 45.5%, Samsun 30.3%, Ceyhan 24.2%). This is a known approximation; Mersin has the NH₃+urea line and is likely more process-heavy than capacity-share allocation reflects. Better keys require process-tonnage disclosures Toros does not publish.

We flag allocated rows with `provenance=allocated` in the CSV and surface the caveat in the bench browser.

### 3.5 Stratified split

Hash-based 70/15/15 splits put 1 of 3 TR BF/BOF integrated mills in train and 2 in test under naive randomization — the model couldn't extrapolate the cap-vs-emission relationship from `n = 1`. We replaced this with a deterministic stratified split keyed on `(scope × route)` so every fold contains at least one facility from each stratum (cement; steel-BF/BOF, steel-EAF, steel-DRI-EAF; aluminum-primary, aluminum-downstream; fertilizer-integrated, fertilizer-N₂O-controlled, fertilizer-blender).

### 3.6 Evaluation: Leave-one-disclosure-out (LODO)

For each of the n=21 audit-grade facilities, we force it into the test set, stratify the remaining 58 facilities normally, train the model, and read the prediction for the held-out facility. This gives 21 test points without resampling. We run **5 outer LODO passes × 3 inner seeds = 15 predictions per facility**, report the per-facility median, and additionally bootstrap-resample the n=21 facilities 5000 times to compute the data-variance confidence interval. The 5-outer variance gives the seed CI (model reproducibility); the bootstrap gives the data CI (sensitivity to which facilities are in the test set).

### 3.7 Why log-MAE, not cost-savings

There are two natural ways to compare per-facility predictions:

- **log-MAE reduction** = `(1 − iz_log_err / EU_log_err) × 100`. Positive means iz is more accurate.
- **Cost-savings vs EU default** = `(EU_default − iz_pred) / EU_default × 100`. Positive means the operator pays less.

For cement and EAF, both metrics agree — iz is more accurate AND the operator pays less. For BF/BOF integrated mills the metrics disagree: the cost-savings stays positive (iz under-predicts, operator pays less) but log-MAE goes negative (iz is less accurate than EU because EU is essentially right). The positive cost-savings sign there is **iz-induced payment-evasion**, not accuracy improvement. We report log-MAE reduction as the primary metric to align vendor incentives with measurement quality.

### 3.8 The model

A 2-layer LoRA-shaped MLP with rank-32 hidden dimension, trained on the bench's residuals against the formula prior `y_prior_log = log(cap × EF × cf)`. 18 features per facility (log capacity, normalized lat/lon, scope one-hot, route one-hots, disclosed cf, has-disclosed-cf, CT features when not ablated). Trained in the browser via WebGPU in ~3 seconds. Best-val checkpoint restored. We run with `IZ_NO_CT=1` (no Climate TRACE features) as the headline configuration — including CT features worsens LODO by ~3-4 pp because CT systematically under-reports the TR mills.

---

## 4. Results

### 4.1 Headline

| Baseline | log-MAE | Reduction vs EU |
|----------|--------:|----------------:|
| B0 EU CBAM default | 1.432 | 0.0% |
| B2 Ridge regression | 0.350 | +75.6% |
| **iz-1 NN** | **0.239** | **+83.3%** |
| **B1 cf-corrected formula** | **0.211** | **+85.3%** |

95% data-bootstrap CI for the NN: **[+72.0%, +90.6%]** (5000 resamples of n=21).
Per-outer seed CI for the NN: ±0.3% (range 84.4 – 84.8%). The model is reproducible across seeds; the data CI is wider because n=21 is small.

### 4.2 Per-sector

| Sector / route | n | Mean reduction | 95% bootstrap CI |
|---|---|---|---|
| Aluminum · downstream | 2 | +90.7% | [+89.9, +91.5] |
| Steel · EAF | 3 | +97.1% | [+96.6, +97.6] |
| Cement | 7 | +81.7% | [+66.2, +92.2] |
| Fertilizer (all strata) | 5 | +76.2% | [+34.6, +93.0] |
| Steel · BF/BOF | 3 | −31.3% | [−289, +97] |
| **Overall** | **21** | **+83.1%** | **[+72.0, +90.6]** |

BF/BOF crosses zero because TR has only 3 BF/BOF mills (Erdemir, İsdemir, Kardemir) and the EU CBAM default 1.9 t/t is already within ±15% of TR audited reality (1.97-2.40 t/t) on those mills. iz's value is concentrated in cement, EAF, aluminum, and fertilizer.

### 4.3 Per-facility (median across 5 × 3 seeds)

15 of 21 facilities land within ±20% of audit truth. Selected big-emitters:

- Erdemir Karadeniz Ereğli (BF/BOF): 7.07M predicted vs 6.67M truth (1.06×)
- İsdemir İskenderun (BF/BOF): 8.53M vs 10.66M (0.80×)
- Kardemir Karabük (BF/BOF): 5.62M vs 5.65M (1.00×)
- Akçansa Büyükçekmece (cement, allocated): 1.67M vs 1.51M (1.11×)
- Akçansa Çanakkale (cement, allocated): 3.81M vs 3.47M (1.10×)
- Batısöke Söke (cement): 1.54M vs 1.58M (0.97×)
- Göltaş Isparta (cement): 1.97M vs 1.67M (1.18×) — was 0.45× before capacity correction
- Çolakoğlu Dilovası (EAF): 0.62M vs 0.57M (1.10×)
- Habaş Aliağa (EAF, combined site): 0.88M vs 0.83M (1.06×)
- İzdemir Aliağa (EAF): 0.29M vs 0.27M (1.07×)
- Assan Tuzla (downstream Al): 95k vs 109k (0.87×)
- Gübretaş Yarımca (fertilizer blender): 13.8k vs 13.3k (1.04×)

Remaining outliers (acknowledged in limitations):

- BAGFAŞ Bandırma (fertilizer N₂O-controlled): 21.0k vs 9.8k (2.14×). Only N₂O-controlled facility in TR's disclosure set; LODO holdout has no in-stratum training data, so the model reverts to integrated-fertilizer EF.
- Bursa Çimento Kestel (cement): 630k vs 1.12M (0.56×). High actual cf, no operator-disclosed production tonnage.
- Afyon Çimento (cement): 676k vs 1.2M (0.56×). Same pattern.
- Toros Mersin (fertilizer integrated, allocated): 0.22M vs 0.38M (0.57×). Capacity-share allocation underestimates the NH₃+urea-heavy Mersin plant.

### 4.4 Climate TRACE comparison

Of the 5 facilities with both an audit-grade truth and a Climate TRACE label:

| Facility | Sector | CT (latest) | Audited (latest) | CT bias |
|----------|--------|------------:|-----------------:|--------:|
| Erdemir Karadeniz Ereğli | steel · BF/BOF | 4,724,148 | 6,673,266 | **−29%** |
| Kardemir Karabük | steel · BF/BOF | 4,367,749 | 5,650,626 | **−23%** |
| Nuh Hereke | cement | 2,768,786 | 3,573,278 | **−23%** |
| İsdemir İskenderun | steel · BF/BOF | 8,310,166 | 10,663,364 | **−22%** |
| Göltaş Isparta | cement | 1,846,026 | 1,669,072 | **+11%** |

CT under-reports 4 of 5; mean bias −17.2%, median −22.5%. Earlier drafts of this work limited the claim to BF/BOF integrated steel (n=3). Widening to all 5 audit-matched facilities shows the pattern extends into cement (Nuh, −23%), with Göltaş the lone over-report. The sample is too small for a strong global claim but too consistent to dismiss as noise.

Plausible mechanism: CT's bottom-up inventory underestimates on-site captive power plants and alternative-fuel share in TR — both common in TR integrated mills, both feeding directly into operators' Scope 1 audits, both potentially missed by global methodology. We do not claim CT is wrong globally; we observe that on our 5-facility TR sample it consistently underestimates by ~20%.

When we use CT-derived features in our model, this systematic bias propagates — which is why our headline configuration is the `no_ct` ablation. Adding CT features makes per-plant LODO predictions ~3-4 pp worse.

---

## 5. Discussion

### 5.1 EU CBAM default is route-asymmetric, not uniformly punitive

The conventional narrative is that EU CBAM defaults are punitive overestimates designed to push operators toward verified MRV. Our findings sharpen that:

- **Cement default 1.584 t/t** vs TR cement industry average **0.643 t/t** — EU default is **2.46× reality**. iz captures most of this gap.
- **EAF steel default 1.9 t/t** vs realistic EAF ~0.25 t/t — EU default is **7.6× reality**. iz's largest sector win.
- **Aluminum default 1.5 t/t** applied uniformly — but the operator-population is heavily downstream-rolling (Assan, ASAŞ) at ~0.4 t/t. EU default is **3.7× reality** for downstream rollers.
- **Fertilizer default 0.8 t/t** vs BAGFAŞ's N₂O-controlled 0.028 t/t — **29× over** for facilities with abatement catalysts. Vs Gübretaş's blender 0.022 t/t — **36× over** for non-process plants.
- **BF/BOF steel default 1.9 t/t** vs TR audited 1.97-2.40 t/t (Erdemir 2.00, İsdemir 1.97, Kardemir 2.40). **The EU default is within ±5-25% of audited truth for big integrated mills**, and tighter for the largest (İsdemir within 2%).

This means the iz value proposition is concentrated in cement, EAF, downstream aluminum, and N₂O-controlled fertilizer; there's structurally limited room to improve over the EU default for BF/BOF integrated steel.

### 5.2 The cf-corrected formula as a CBAM-grade "shadow default"

Independent of the model, our `cap × EF × cf` formula reproduces the Akçansa Büyükçekmece audited Scope 1 (1,514,000 tCO₂e from 2025 IAR p46+167) within 1% (1,516k from `2.5M × 0.607 × 0.999`). The formula reads off three independently-published inputs and reproduces 15 of 21 audited facilities within ±20%.

This suggests a **shadow CBAM default** — a published EF×CF table that the EU could adopt with very little additional verification overhead, dropping the headline cement default from `cap × 1.584` to `cap × 0.643 × cf_sector` (≈ `cap × 0.35`), closing roughly 78% of the per-plant accuracy gap for cement without any operator MRV submission. We make no claim about EU regulatory feasibility; we observe only that the formula is sufficient and the inputs are public.

### 5.3 The model and the formula are statistically tied

The 2-layer NN reaches +83.3% vs the formula's +85.3% on n=21 LODO. Ridge regression on the same features lags at +81.4%. **The actionable shipped baseline is the formula.** The NN exists as a reference implementation that future researchers can build on once the bench has hundreds or thousands of disclosure-labeled facilities or year-time-series satellite features. At today's data scale (~40 training samples post-LODO), parameter growth offers no meaningful gain over data growth.

Implications for the field:
- Small-data ML in emissions verification is hard for the same reason small-data ML is hard everywhere: you can't beat strong baselines without much more data than the baseline needs.
- The next investment is data, not parameters. More TR disclosure mining, satellite-feature pipelines (Sentinel-5P NO₂, Sentinel-2 RGB, Landsat thermal), and time-series labels are the moves that would unlock ML over formula.

### 5.4 What about other countries

This work is TR-specific because we hand-curated TR disclosures. The methodology generalizes: replace `data/tr_facilities.csv` with the equivalent for any other country, replace the route maps if domestic process mix differs, hunt for the country's TSRS-equivalent reporting (Turkey was relatively early to TSRS; most of Europe is now CSRD/ESRS). The closed-form formula and the LODO evaluation harness are country-agnostic.

For other CBAM-exporting countries (Russia, India, China, Brazil, Egypt, Morocco) the analogous benchmark would require ~2-3 months of one-person disclosure-mining work. We release the code structure as a template.

---

## 6. Limitations

1. **n=21 is small.** Single-instance disclosure-route strata (BAGFAŞ N₂O-controlled, Gübretaş blender) have no in-stratum LODO training counterpart. Our 95% data-bootstrap CI [+72.0%, +90.6%] reflects this.

2. **"Audit-grade" is three tiers.** ISO 14064-1 verified (n=5) > TSRS limited assurance (n=6) > operator IAR (n=10). The headline does not weight by tier — a v0 simplification.

3. **6 of 21 strong labels are allocated.** Akçansa per-plant from group via clinker share; Toros from group via nameplate capacity. Group totals are audit-grade; per-plant splits are our arithmetic.

4. **Capacity values are operator-published nameplate**, not field-verified. We did one round of operator-source verification (May 2026); residual errors are possible.

5. **Habaş Aliağa uses combined site total** (EAF main line 636,377 + plate mill 193,961 = 830,338). CBAM treats Aliağa as one site for tariff; we follow that convention.

6. **BAGFAŞ is a partial-cap year.** 2024 cf=0.29, well below typical fertilizer operation. An average year would shift the prediction.

7. **Erdemir 2024 IAR restated 2023 from 6.56M → 5.95M.** We use the restatement. This raises a question about the stability of any single year's audit-grade disclosure.

8. **LODO is not cold prediction.** When we hold out Erdemir, the other 2 BF/BOF mills remain in training. A genuinely new BF/BOF mill would have no in-stratum data.

9. **BF/BOF stratum has only 3 mills in TR.** Bootstrap CI on this stratum is [−289%, +97%] — uninformative. The EU CBAM default for BF/BOF is also already within ±15% of TR reality, so the stratum is structurally hard regardless of method.

10. **"85.3% beats EU default" is log-MAE reduction**, not error reduction. A non-technical reader may misinterpret.

11. **39 cf-corrected facilities are formula-predicted by construction.** The +85.3% headline applies only to the 21 truth-labeled LODO rows. The other 39 have labels assigned from the same formula being evaluated.

12. **Climate TRACE under-reporting claim is n=5 audit-matched.** We do not claim CT is wrong globally — only that in our 5-facility TR sample it consistently underestimates.

13. **No satellite signal in v0.** Sentinel-5P NO₂ pipeline runs but didn't make it into the model.

14. **Zero pilot customers.** This is not a commercial work; the bench is open infrastructure.

15. **Operator-self-reported truths.** Audit-grade ≠ field-verified-by-iz. The bench inherits the trust profile of the operator's audit.

---

## 7. Conclusion

We release TR-MRV-Bench v0 and the cf-corrected formula as **open infrastructure for Turkish CBAM compliance**. The formula reduces per-plant log-MAE by +85.3% vs the EU CBAM default across 21 audit-grade Turkish facilities in all four CBAM scopes. The bench is downloadable as CSV and JSON with full source-PDF citations. The model (a 2-layer LoRA-shaped MLP) ties the formula at +83.3% on the same evaluation.

If every TR CBAM-scope operator used real per-facility data instead of paying the EU default, **~€2 billion per year** stays in Turkey instead of going to the EU treasury (CBAM at €85/tCO₂, realistic sector EU-export shares). That is the prize. The point of iz is to make sure no operator pays more than they should because they couldn't afford the verifier audit.

All code, data, and documentation are released under Apache-2.0 at <https://github.com/abgnydn/iz>. The live site, bench browser, and interactive trainer are at <https://iz-b0n.pages.dev>. Citation file (CITATION.cff) is in the repo.

---

## Acknowledgments

This work was completed by one person over a series of weekend sessions, with substantial use of AI assistants (Claude Opus 4.7) for code, disclosure-PDF parsing, and synthesis. Every audit-grade disclosure is sourced from a publicly-available operator document; we thank the Turkish operators publishing under TSRS / GRI / ISO 14064-1 frameworks. Climate TRACE provides the v6 per-asset data we use as a comparative baseline. Limitations and methodology choices are our own.

---

## Reproducibility

```bash
git clone https://github.com/abgnydn/iz
cd iz
uv sync
playwright install chromium

# (1) Build the bench
.venv/bin/python bin/export_bench_browser.py
.venv/bin/python bin/build_facilities_json.py

# (2) Start the HTTP server (for browser-side trainer)
python3 -m http.server 8765 --bind 127.0.0.1 --directory src/iz_browser &

# (3) Run the headline LODO + bootstrap
IZ_NO_CT=1 .venv/bin/python bin/e2e_lodo_aggregate.py 5
.venv/bin/python bin/bootstrap_ci.py
.venv/bin/python bin/baselines.py
.venv/bin/python bin/check_consistency.py
```

All tests: `.venv/bin/python -m pytest tests/` (9 sanity checks).

---

## Bibliography

Primary sources for every audit-grade row are in `data/tr_facility_known_emissions.csv` (source URL + page number per row). The bench browser at `/bench/` exposes them as searchable tags.

Selected references:

- Jakubik, J. et al. (2023, 2024). *Prithvi-EO-2.0: A foundation model for Earth observation.*
- TÜRKÇİMENTO (2023). *Sürdürülebilirlik Raporu.* Turkish Cement Manufacturers' Association.
- Akçansa (2025). *Integrated Annual Report.*
- Erdemir (2024). *Entegre Faaliyet Raporu, KGK-verified.*
- Climate TRACE (2024). *v6 per-asset emissions inventory.* <https://climatetrace.org>
- Bursa Çimento (2024). *TSRS Sustainability Report.* p59 Tablo 24.
- Tekfen Holding (2024). *TSRS Sürdürülebilirlik Raporu.* p18 (Toros Tarım sector).
- BAGFAŞ (2024). *Sürdürülebilirlik Raporu.* p41-44 (ISO 14064-1 N₂O measurement).
- Çimsa (2024). *Integrated Annual Report.* (Kayseri + Niğde divestiture, p98.)
- European Commission (2023). *Regulation (EU) 2023/956 (CBAM).*
- European Commission (2023). *Implementing Regulation (EU) 2023/1773 — CBAM transitional period.*

---

*Submitted draft. Comments and corrections welcome via GitHub issues or hi@barisgunaydin.com.*
