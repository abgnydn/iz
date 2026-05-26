# TR-MRV-Bench — paper outline

*Working draft v0.2 (2026-05-26). Tightened from earlier "foundation model" framing after baseline analysis showed the closed-form formula outperforms the learned model.*

## Title (working)

**TR-MRV-Bench: A public per-facility emissions benchmark for Turkish CBAM-scope industry, with a physics baseline that beats the EU CBAM default by 85% across all four CBAM scopes**

## Abstract (~200 words)

CBAM and emerging emissions-trading regimes require per-facility CO₂ accounting that is independently verifiable. Existing per-facility data sources have known gaps: Climate TRACE under-reports the three Turkish BF/BOF steel mills in our sample by 20-30%; operator self-reports trust the operator; satellite tools (GHGSat, Carbon Mapper) focus on methane with no CBAM tie-in. We release **TR-MRV-Bench**, a public benchmark of 59 Turkish CBAM-scope facilities with three-tier supervision (**20 audit-grade strong labels** across all four CBAM scopes — cement, steel, aluminum, fertilizer — from operator IARs, TSRS-compliant sustainability reports, and KGK-verified ISO 14064-1 statements; 8 Climate TRACE per-asset labels; capacity-factor-corrected default labels for the rest). On this bench we evaluate a closed-form physics baseline — `capacity × emission-factor × capacity-factor`, with route-aware EF priorities (steel BF/BOF / EAF / DRI-EAF; aluminum primary / downstream; fertilizer integrated / N₂O-controlled / blender) and cf priorities (Climate-TRACE per-asset > operator-disclosed-production / capacity > sector-mean default) defined in §3 — and find it reduces per-plant log-MAE by **85.9% vs the EU CBAM default** in leave-one-disclosure-out evaluation across the 20 audit-grade test facilities. A 2-layer neural network trained on the bench's residuals against this prior reaches **+84.5% ± 0.3% (95% CI across 5 outer LODO runs)** — statistically tied with the closed-form formula. Ridge regression on the same features lags both at 81.7%. Per-sector confidence intervals: cement +73.8% ± 1.7%, EAF steel +98.3% ± 2.2%, BF/BOF steel −7.3% ± 71.0% (n=3 stratum, very wide), aluminum downstream +86.0% ± 5.1%, fertilizer integrated +79.3% ± 8.4%, fertilizer N₂O-controlled +84.7% ± 2.2%, fertilizer blender +99.3% ± 1.1%. The actionable artifacts are the bench, the formula, and the source-cited disclosure crawl. Most BF/BOF mills (Erdemir, İsdemir, Kardemir) sit within ±15% of the EU default because the EU integrated-steel default 1.9 t/t is already close to TR audited reality; cement and EAF are where the formula's value is concentrated. n=20 is still small and we are explicit about that in §8. The bench and code are released under Apache-2.0.

## Contributions (paper sections)

1. **TR-MRV-Bench (§4).** Public per-facility emissions benchmark with three-tier supervision (audit-grade / Climate TRACE / cf-corrected default), provenance-tagged labels (direct / allocated / derived / disputed), and stratified train/val/test split by `(scope × route)` covering steel BF/BOF / EAF / DRI-EAF, aluminum primary / downstream, fertilizer integrated / N₂O-controlled / blender. 18 audit-grade test facilities across all four CBAM scopes.
2. **cf-corrected formula baseline (§3, §5).** Closed-form `cap × EF × cf` with explicit route-aware EF and cf priority rules. **85.9% log-MAE reduction vs EU default on n=20 LODO** — predicts all 13 big-emitter facilities (steel + cement) within ±20% of audit. NN ties at 84.5% ± 0.3%.
3. **EU CBAM default is route-asymmetric (§5.1).** The default over-estimates cement by 2-5×, EAF steel by 10×, downstream aluminum by 4× (CBAM applies primary-Al EF 8.6 to downstream rolling at actual 0.38), and fertilizer blenders by 90×. It is within 5% of audited reality only for big BF/BOF integrated mills. The mismatch is the gap iz-1 closes.
4. **Climate TRACE under-reports TR integrated steel (§5.2).** Verified across 3 mills (İsdemir −22%, Kardemir −27%, Erdemir Ereğli-derived −22%). Adding CT cf as a model feature worsens LODO accuracy by ~4 percentage points; this is why the no_ct ablation is the headline configuration.
5. **The formula and the model are statistically tied (§6).** A LoRA-shaped MLP achieves +84.5% ± 0.3% vs the closed-form formula's 85.9% on n=20 LODO. Ridge regression on the same features lags at 81.7%. **The actionable shipped baseline is the formula**; the NN is a working reference implementation that opens room for future signal extraction (satellite features, multi-year LODO). At this data scale (~39 training samples after LODO holdout), parameter growth offers no meaningful gain over data growth.

## Sections

### 1. Introduction
- Why per-facility emissions verification is the bottleneck for climate action + compliance regimes
- The four kinds of existing player (compliance SaaS / satellite intelligence / verifier / advisory) and what each misses
- Our four-bet thesis: open methodology + bench + ternary backbone + federated deployment

### 2. Related work
- **Earth-observation foundation models**: Prithvi (Jakubik et al., 2023; 2024), Clay, SatMAE, ScaleMAE, SpectralGPT
- **Ternary/1-bit ViT**: Q-ViT (NeurIPS 2022), ViT-1.58b (Yuan et al., 2024), BitMedViT (2025), BitVLA (2025)
- **Industrial emissions tracking**: Climate TRACE, Carbon Mapper Tanager-1, GHGSat Vanguard, MethaneSAT, Kayrros
- **Federated fine-tuning + sparse adapters**: FLASC (Kuo & Raje, 2024), Sparse-BitNet (2026), classical FedAvg

### 3. Method
#### 3.1 Backbone + multi-modal heads
- Prithvi-EO-2.0-100M-TL initialization
- Cross-modal patch tokenizers per sensor (S5P NO₂ + S2 RGB+NIR + S3 thermal + Landsat TIRS + S1 SAR + tabular ERA5 / grid)
- Per-pollutant regression heads with Gaussian NLL (mean + variance) for calibrated uncertainty

#### 3.2 Loss + supervision
- Strong labels (CDP, audited sustainability reports): weight 1.0
- Medium labels (industry-association sector averages): weight 0.5-0.7
- Weak labels (Climate TRACE): weight 0.3
- Physics-informed soft penalty: per-plant emissions × 12 months ≥ a fraction of capacity (mass balance sanity check)

#### 3.3 Ternary QAT (Pass 2)
- BitLinear swap in attention + FFN (skip patch embed + regression heads)
- Multi-query attention swap-in for stability (BitMedViT pattern)
- Knowledge distillation: KL between student and teacher Gaussians + ground-truth NLL

#### 3.4 Federated fine-tuning
- `.flora` v2: multi-layer adapter format, list of (layer_name, A, B) tuples
- FLASC-pruned top-K B serialization: ~200-400 KB compressed
- Gradient-free ES variant: operator returns scalar fitness, never gradients

#### 3.5 Browser deployment
- Transformers.js + ONNX Runtime WebGPU base inference
- Custom fused WGSL kernels for LoRA delta (ported from `fused-lora`)
- End-to-end: any laptop loads facility + `.flora`, predicts CO₂, audits provenance

### 4. The TR-MRV-Bench dataset
- 57 facilities (32 cement, 16 steel, 3 aluminum, 6 fertilizer)
- 3-year monthly time series per facility
- Strong labels for [N]/57 facilities; Climate TRACE labels for [N]/57
- Test split: 12 facilities held out (≈21%); val: 5 facilities; train: 40
- Split is BY FACILITY, not by time, to test OOD generalization

### 5. Experiments
#### 5.1 Pass 1: full-precision baseline
- iz-1-fp vs (Climate TRACE direct) vs (EU CBAM default value)
- per-plant MAE
- annual aggregate MAE
- uncertainty calibration: CRPS, coverage at 90% / 95% intervals

#### 5.2 Pass 2: ternary
- iz-1-ternary vs iz-1-fp
- accuracy gap as a function of layers quantized
- memory + inference latency

#### 5.3 Federated fine-tuning
- Synthetic operator: simulate one operator's CEMS data
- `.flora`-based: how many local steps to converge
- ES-based: number of forward passes per fitness improvement

### 6. Ablations
- backbone size: Prithvi-100M vs 300M vs 600M
- multi-modal: each modality dropped one at a time
- ternary scope: FFN only / attention only / all
- LoRA rank: 4 / 8 / 16 / 32

### 7. Discussion
- What we got right, what we didn't, what we'd do differently
- The provenance receipt as a primitive (cryptographic signing planned)
- Why open methodology is the actual moat for climate measurement

### 8. Limitations (honest version)

**Statistical:**
- **n=8 audit-grade test facilities is small.** Confidence intervals around the 87.1% headline are wide; we report mean ± 2σ across N outer LODO runs (see `reports/lodo_ci.json`) but the right answer for tight CIs needs n≫8.
- **No held-out year.** All labels are in a single window (mostly 2022-2025). Split is by facility, not by time. We cannot claim temporal generalization.
- **BF/BOF stratum has n=3 globally** (Erdemir, İsdemir, Kardemir — the only TR integrated mills). LODO over n=3 is trivially "predict from the other 2"; not a real generalization test on this stratum.

**Methodological:**
- **Operator-self-reported truths.** Audit-grade ≠ third-party-verified. Disclosures come from operator IARs / sustainability reports — mostly Big4-audited, one ISO 14064-1 verified — but this is the same trust problem Climate TRACE was meant to bypass.
- **The formula beats the model.** Our learned NN at n=40 train samples produces slightly worse predictions than the closed-form formula it tries to residual-correct. The deliverable is the formula and the bench, not the model. Future work should target data scale before parameter scale.
- **The Climate TRACE under-reporting claim is sample-size 3.** We see CT under-report İsdemir −22%, Kardemir −27%, Erdemir-derived −22% on the three TR BF/BOF mills. We do not claim CT is wrong globally — only that in our 3-mill TR sample it consistently underestimates.

**Data:**
- **Akçansa per-plant labels are allocated from group total**, not directly disclosed per-plant. Group total is audited (5,484,015 tCO₂e from 2025 IAR p46); per-plant split is by disclosed clinker production share (p167). Erdemir Ereğli 2024 = Group 17.34M − İsdemir 10.66M; derived by subtraction.
- **Some capacities in `tr_facilities.csv` were corrected mid-development** (Çanakkale 4.5M → 6M; Erdemir Ereğli 6M → 4M). We don't claim every other capacity is perfectly verified.
- **The Tosyalı Holding 425k 2022 Scope 1 is implausibly low** for a ~3M t/yr EAF operator and we flag it as `provenance=disputed` in the bench. It is not used as supervision for the headline metric (Tosyalı facilities are not in the disclosure LODO set).
- **No satellite signal in v0.** S5P NO₂ pipeline exists but is rate-limited by Microsoft Planetary Computer; full 57-facility pull blocked at ~1.9 GB cached. We dropped the "Earth-observation foundation model" framing from earlier drafts to match what we actually shipped.

**Scope:**
- **Turkey-only.** The bench is Turkish CBAM-scope facilities. The methodology should port to other countries but we have not demonstrated this.
- **No verifier-accreditation pathway in v0.** Audit-grade is research-grade, not regulator-acceptable. Production deployment for actual CBAM submission needs a 12-18 month accreditation process we have not started.

### 9. Conclusion + future work

## Author block

- Ahmet Baris Gunaydin (sole author for v0; coauthors welcome via PRs to the open codebase)

## Code + data release

- Code: github.com/abgnydn/iz (Apache-2.0)
- Weights: huggingface.co/abgnydn/iz-1 (Apache-2.0)
- Dataset: huggingface.co/datasets/abgnydn/tr-mrv-bench (Apache-2.0 + cite-us)
- Browser demo: huggingface.co/spaces/abgnydn/iz-1 (Zero-GPU)

## Distribution plan (post-arXiv)

- Climate TRACE coalition lead
- Carbon Mapper science team (Aubrey, Duren)
- GHGSat (Germain)
- EDF (Hamburg)
- ESA CO2M
- DG-CLIMA EU
- TR Ministry of Environment, Urbanization & Climate Change
- 2-3 TR sustainability journalists
- HN / r/MachineLearning / climate-Twitter coordinated drop
