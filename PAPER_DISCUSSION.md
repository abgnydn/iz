# iz-1 — Section 7: Discussion (draft)

## 7.1 Why log-MAE reduction is the honest metric (and not cost-savings)

There are two natural ways to compare iz-1 against the EU CBAM default per facility, and they sometimes disagree:

- **log-MAE reduction** = `(1 − iz_log_err / EU_log_err) × 100`. Positive means iz is more accurate than EU.
- **Cost-savings vs EU** = `(EU_default − iz_pred) / EU_default × 100`. Positive means the operator pays less under iz.

For cement and EAF, both metrics agree — iz is more accurate AND the operator pays less, because EU defaults dramatically overestimate. For **BF/BOF integrated steel** the metrics disagree: the cost-savings metric stays positive (iz under-predicts, operator pays less) but the accuracy metric goes negative (iz is less accurate than EU). The positive cost-savings sign there is iz-induced **payment-evasion**, not accuracy improvement, and we report log-MAE reduction as the primary metric throughout.

This distinction has policy implications. A pure cost-savings framing creates the wrong incentive for both vendors and operators — vendors get rewarded for under-predicting and operators get rewarded for picking the lowest-prediction tool. Log-MAE reduction against audited truth is the only metric that aligns vendor incentives with measurement quality.

## 7.2 EU CBAM default is sector-asymmetric — not uniformly punitive

The conventional narrative is that EU CBAM defaults are punitive overestimates designed to push operators toward verified MRV. Our findings sharpen that:

- **Cement default 1.584 t/t** vs TR cement industry average **0.643 t/t** — EU default is **2.46× reality**. Iz-1 captures most of this gap.
- **EAF steel default 1.9 t/t** vs realistic EAF ~0.25 t/t — EU default is **7.6× reality**. Iz-1's largest sector win.
- **BF/BOF steel default 1.9 t/t** vs TR audited 1.97-2.40 t/t (Erdemir 2.00, İsdemir 1.97, Kardemir 2.40). **The EU default is within ±5-25% of audited truth for big integrated mills**, and tighter than that for the largest one (İsdemir, EU within 2%).

This means the iz-1 value proposition is concentrated in cement and EAF, and there's structurally limited room to improve over the EU default for BF/BOF integrated steel. For a Turkish operator deciding whether to invest in MRV vs. paying the EU default, the calculus is:

- **Cement / EAF**: pay for verified MRV; saves €40-80 per tonne of CO₂ over default.
- **BF/BOF integrated steel**: pay the EU default; MRV verification only confirms you owe roughly what the default says anyway.

## 7.3 The cf-corrected formula as a CBAM-grade "shadow default"

Independent of the model, our `cap × EF × cf` formula reproduces the only directly-disclosed per-plant Akçansa Scope 1 (Büyükçekmece, 1,514,000 tCO₂e from 2025 IAR p46+167) within 1% (1,502,325 tCO₂e from `4.5M × 0.607 × 0.55`). The formula reads off three independently-published inputs:

- **Capacity**: operator nameplate (industry registries, KAP filings).
- **EF**: industry-association sector averages (TÜRKÇİMENTO 0.643 t/t cement) or operator-published specific emissions (OYAK 0.685 t/t).
- **CF**: Climate TRACE per-asset utilization (independent of operator self-reporting) or operator-disclosed production ÷ capacity.

This suggests a **shadow CBAM default** — a published EF×CF table that the EU could adopt with very little additional verification overhead, dropping the headline EU default from `cap × 1.584` (cement) to `cap × 0.643 × cf_sector` (≈ `cap × 0.35`), closing roughly 78% of the per-plant accuracy gap for cement without any operator MRV submission. We make no claim about EU regulatory feasibility; we observe only that the formula is sufficient and the inputs are public.

## 7.4 Climate TRACE consistently under-reports TR industrial emissions (n=5 audit-matched)

Five facilities have both a TR audit-grade disclosure and a Climate TRACE per-asset label. CT under-reports 4 of 5, mean bias −17.2%, median −22.5%:

| Facility | Sector | CT (latest) | Audited (latest) | CT bias |
|----------|--------|------------:|-----------------:|--------:|
| Erdemir Karadeniz Ereğli | steel · BF/BOF | 4,724,148 | 6,673,266 | **−29%** |
| Kardemir Karabük | steel · BF/BOF | 4,367,749 | 5,650,626 | **−23%** |
| Nuh Hereke | cement | 2,768,786 | 3,573,278 | **−23%** |
| İsdemir İskenderun | steel · BF/BOF | 8,310,166 | 10,663,364 | **−22%** |
| Göltaş Isparta | cement | 1,846,026 | 1,669,072 | **+11%** |

Earlier drafts of this paper limited the claim to BF/BOF integrated steel (the original n=3 finding). Widening to all audit-matched facilities shows the under-reporting extends into cement (Nuh, also −23%), with only Göltaş as a counter-example (over-reports by 11%). The pattern is too consistent to dismiss as sampling noise but n=5 is too small for a strong global claim.

Plausible mechanism: CT's bottom-up inventory underestimates on-site fuel mix in TR — captive coal power plants are common in TR integrated mills, and the alternative-fuel share at TR cement plants varies plant-to-plant in ways the global methodology may not capture. The audited Scope 1 includes all on-site combustion + process emissions; CT's source data may miss the captive-power and alt-fuel deltas. Worth publishing as a methodology note for the CT team.

When we use CT-derived features in our model, this systematic bias propagates — which is why our headline configuration is the `no_ct` ablation. Adding CT features to the formula prior makes per-plant predictions ~3-4 pp worse.

## 7.5 The model and the formula are essentially tied

A central honest finding of this work: across all our experiments at the bench's current data scale, our learned model and the closed-form `cap × EF × cf` formula sit within each other's seed noise. On the n=21 LODO eval (all four CBAM scopes, no_ct ablation):

| Baseline | log-MAE | Reduction vs EU |
|----------|--------:|----------------:|
| B0 EU CBAM default | 1.432 | 0.0% |
| B2 Ridge regression | 0.266 | +81.4% |
| **B1 cf-corrected formula** | **0.189** | **+85.3%** |
| iz-1 NN (5-outer median, no CT) | 0.235 | +83.6% |

The NN beat the formula by 1.8 pp at n=18-20 (before disclosed_cf for fertilizer/aluminum was added) and is statistically tied with it at n=21 once the formula has access to the same disclosed_cf signal. The honest framing: **the deliverable is the formula and the bench**. The NN is a working reference implementation; future data growth (S5P NO₂ features, more disclosures, multi-year LODO) may give it room to extract residual signal the formula cannot.

The formula wins. The 2-layer NN adds ~0.03 to the log-MAE on average. Ridge regression underperforms both. We initially trained the NN to learn residuals against the formula as a physics-informed prior (cf. Karniadakis et al.); the model successfully learns those residuals, but the residuals don't average to better predictions on held-out facilities — they average to slightly worse ones, because residual fits on 40 facilities are noisy.

The right framing of this work is therefore: **the formula and the bench are the deliverables**. The NN is a working, browser-native reference implementation that future researchers can build on once the bench has hundreds or thousands of disclosure-labeled facilities. At today's data scale, ship the formula.

Implications for the field:
- Small-data ML in emissions verification is hard for the same reason small-data ML is hard everywhere: you can't beat strong baselines without much more data than the baseline needs.
- The next investment is data, not parameters. More TR disclosure mining (Bursa, Çimsa per-plant, Tosyalı per-plant, sector expansion to aluminum / fertilizer), satellite-feature pipelines (S5P NO₂, S2 RGB, Landsat thermal), and time-series labels (multi-year disclosures we already have for Çolakoğlu, Erdemir) — these are the moves that would unlock ML over formula.
- The provenance and source-cited disclosure crawl in this paper takes ~3 days of careful PDF mining per major. That's the scarce input.

## 7.6 Why browser-native training

Three reasons we ported the training loop to WebGPU/WGSL instead of running PyTorch on a GPU:

1. **Reproducibility for non-ML reviewers.** Anyone with a 2024 laptop can open `train.html`, click Train, and get the same `lodo_results.json` we report. No CUDA versions, no `pip install`, no Colab session.

2. **Federated fine-tuning is the v1 thesis.** One operator at a time runs LoRA fine-tuning on its own CEMS data locally; only the rank-16 `.flora` adapter (~200-400 KB compressed via FLASC) is shared. The browser-native stack is the federated deployment substrate, not just a demo.

3. **Climate ML deserves to feel like climate ML.** A 14 MB model that runs in 3 seconds on a laptop is the right form factor for tools that need to be auditable, not the 100 GB GPU-cluster jobs that climate-curious data scientists currently see.

## 7.7 The paper's actual moat

The contribution isn't a new architecture, a new sensor, or a new loss function. It's the synthesis: a sector-stratified bench tied to audited operator disclosures, a physics-informed prior that makes few-shot supervised learning work, and a browser-native training stack that makes the whole thing reproducible by anyone. The headline 81.5% LODO reduction is the validation; the methodology is the contribution.
