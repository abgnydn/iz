# iz-1 — paper outline

*Working draft. Target: arXiv preprint within 7-10 days of Pass-1 results clearing the EU-default bar by ≥30%.*

## Title (working)

**iz-1: A ternary multi-modal Earth-observation foundation model for per-facility industrial emissions verification, with browser-native federated fine-tuning**

## Abstract (~200 words target)

CBAM and emerging emissions-trading regimes require per-facility CO₂ accounting that is independently verifiable, defensible, and cheap to scale. Existing approaches either trust operator self-reports (CarbonChain, Persefoni), produce country-level aggregates that miss the facility scale (Climate TRACE), or rely on commercial methane-specialized satellites with no CBAM tie-in (GHGSat, Carbon Mapper). We introduce **iz-1**, the first ternary multi-modal Earth-observation foundation model for industrial emissions. iz-1 is a 100M-parameter ViT fine-tuned from Prithvi-EO-2.0 on TR-MRV-Bench, a new public benchmark of 57 Turkish CBAM-scope facilities with verified CDP / sustainability-disclosure labels and Climate TRACE weak supervision. We ternary-quantize iz-1 using a knowledge-distillation extension of ViT-1.58b's QAT recipe, yielding a 20 MB model that runs at native speed in any browser via WebGPU. Per-facility fine-tuning uses federated `.flora` adapters: operators train locally on their CEMS data without ever exchanging raw data or gradients (via FLASC-pruned LoRA or gradient-free ES). Across our test split, iz-1 reduces per-plant CO₂ MAE by [TBD]% relative to the EU CBAM default. iz-1, the benchmark, and the deployment code are released under Apache-2.0.

## Five contributions (paper sections)

1. **The TR-MRV-Bench benchmark.** Public per-facility emissions benchmark with hand-curated strong labels + Climate TRACE weak supervision; train/val/test split by facility for OOD generalization.
2. **Ternary multi-modal EO foundation model.** First application of BitNet-style QAT to a geospatial foundation model. Knowledge distillation from full-precision Prithvi-EO teacher.
3. **Browser-native deployment via Transformers.js + custom WGSL.** First in-browser per-facility climate ML.
4. **Federated `.flora` multi-layer adapter format.** FLASC-pruned, ~200-400 KB per facility, communication-efficient.
5. **Gradient-free federated fine-tuning protocol.** Operator-side ES — fitness scalars only leave the operator's network. No gradients, no adapters, no raw data shared. Privacy-preserving by construction.

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

### 8. Limitations
- L2 NO₂ is a combustion proxy, not direct CO₂; per-plant conversion still has factor-of-2 uncertainty without operator data
- 57 facilities is too few to draw global conclusions — TR-MRV-Bench is a starting point
- We don't yet handle plant outages, retrofits, fuel switches — these need news/filings ingestion
- Verifier accreditation is a 12-18 month process; iz-1 v0 is research-grade, not audit-grade

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
