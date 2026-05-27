# iz-1 — Section 3: Method (draft)

> Draft of paper Section 3. Captures the design decisions that took the model from a sector-averaged baseline to per-facility predictions within ±30% of audited Scope 1 truth across 18 leave-one-disclosure-out test points covering all four CBAM scopes.

## 3.1 Bench construction (TR-MRV-Bench v0)

The bench is 59 Turkish CBAM-scope facilities: 34 cement (including Afyon Çimento and Batısöke Söke), 16 steel, 3 aluminum, 6 fertilizer. Each row carries (a) facility identity (`id`, `company`, `cbam_scope`, `lat`, `lon`, `annual_capacity_t`), (b) a route tag for steel (`BF/BOF`, `EAF`, `DRI-EAF`), aluminum (`primary`, `downstream`), and fertilizer (`integrated`, `integrated-n2o-controlled`, `blender`), and (c) a CBAM customs-codes column for tariff bookkeeping.

We assemble three tiers of supervision:

1. **Strong labels (disclosure-grade, weight = 1.0)** — per-plant Scope 1 tCO₂e from operator integrated reports / sustainability disclosures / TSRS-compliant reports. Audit-grade; `n = 18`: cement (Akçansa Büyükçekmece / Çanakkale / Ladik allocated from 2025 group total by clinker share; Nuh Hereke 2024 cement-only; Afyon Çimento 2024 standalone TSRS; Batısöke Söke 2024 ISO 14064-verified; Göltaş Isparta 2024 TSRS); steel (Çolakoğlu Dilovası 2024 EAF; Erdemir Ereğli 2024 IAR p79; İsdemir İskenderun 2024 IAR p115; Kardemir Karabük 2022 SR); aluminum (Assan Tuzla+Dilovası combined 2024; ASAŞ Akyazı 2024); fertilizer (Toros Mersin / Samsun / Ceyhan allocated from 2024 Tekfen TSRS group 842,174 by capacity; BAGFAŞ Bandırma 2024 TSRS; Gübretaş Yarımca 2024 TSRS). Source PDFs are cached under `data/disclosures/` and cited in `data/tr_facility_known_emissions.csv`.

2. **Climate TRACE per-asset labels (weight = 0.7)** — pulled from `https://api.climatetrace.org/v6/assets/{id}` for the 13 facilities our list matched to a CT asset (proximity join, ≤30 km). The `/v6/assets` list endpoint returns null `Emissions`; the per-asset detail endpoint returns full `EmissionsDetails` with per-gas / per-year `EmissionsQuantity`, `Activity`, `CapacityFactor`. We take the latest year (2024) `co2e_100yr` and sum across multiple CT-assets that match the same iz facility.

3. **Capacity-factor-corrected default labels (weight = 0.4)** — for facilities with no direct disclosure and no CT match, we compute `y_default = capacity × EF × cf`. The two terms are:
   - **EF** — sector-specific, with three refinements applied in priority order: (i) a steel-route lookup (`BF/BOF = 2.0`, `EAF = 0.25`, `DRI-EAF = 0.4` t/t crude steel); (ii) an aluminum-route lookup (`primary = 8.6`, `downstream = 0.45` t/t Al) — the EU CBAM default 8.6 is calibrated for Hall-Héroult and overstates downstream rolling by ~23×; (iii) a fertilizer-route lookup (`integrated = 0.5`, `integrated-n2o-controlled = 0.05`, `blender = 0.025`) — BAGFAŞ's N₂O catalyst on nitric acid cuts process N₂O by ~95%, putting it 10× below ordinary integrated fertilizer; (iv) a company-level override when the company published a specific factor (OYAK 0.685 t/t cement Scope 1; Akçansa 0.607; Limak 0.55; Toros 0.525; BAGFAŞ 0.028; Assan 0.379; Gübretaş 0.022). Fallbacks: `TR_actual` table (cement 0.643 per TÜRKÇİMENTO 2023; steel 1.44 per Erdemir 2023 Scope 1+2; fertilizer 0.8; aluminum 1.5).
   - **cf** — priority is per-asset Climate TRACE measurement > disclosed (production / capacity from IAR text — non-leaky in LODO because production tonnes are reported independently of Scope 1; e.g. OYAK group 0.695 from 2023 IAR p15 clinker 7.23M / 10.4M capacity) > sector-mean default (cement 0.55, steel 0.70, aluminum 0.85, fertilizer 0.65).

**Why three tiers?** Tier 1 alone would give us 18 training samples — still too few for serious ML, but adequate as a LODO test set. Tier 2 adds 8 more independent labels with known ±50% accuracy. Tier 3 fills the rest of the bench with a deterministic route-aware formula whose error is bounded by the EF and cf inputs. Each sample carries its label source and a confidence weight; the loss is weighted MSE on `log1p(Scope 1)` per Section 3.4.

### Stratified split

Hash-based 70/15/15 splits put 1 of the 3 TR BF/BOF integrated mills in train and 2 in test — the model couldn't extrapolate the cap-vs-emission relationship from `n = 1`. We replaced it with a deterministic stratified split keyed on `(scope × route)` so every fold contains at least one facility from each stratum:

```
Stratum               n   train   val   test
────────────────────────────────────────────
cement              34    23     6     5
steel-BF/BOF         3     1     1     1
steel-EAF           12     8     2     2
steel-DRI-EAF        1     1     0     0
aluminum             3     1     1     1
fertilizer           6     4     1     1
```

The DRI-EAF stratum has `n = 1` (Tosyalı Osmaniye) so it stays in train; the others are split with floor minimums per fold. **Single-instance disclosure-route strata** (BAGFAŞ N₂O-controlled fertilizer; Gübretaş blender) remain a known LODO limitation — when held out, the model has never seen another facility in their route and reverts to integrated-fertilizer EF, producing predicted/truth ratios of 3.46× and 1.27× respectively. Both ratios are honest LODO failures the bench reports openly.

## 3.2 Features

15 tabular features per facility (no satellite signal in v0):

| Group | Features | Source |
|-------|----------|--------|
| Identity | `log_capacity`, `lat_norm`, `lon_norm` | facility CSV |
| Sector one-hot | `is_cement`, `is_steel`, `is_aluminum`, `is_fertilizer` | facility CSV |
| Climate TRACE | `ct_cf`, `ct_activity_log`, `ct_has` | CT `/v6/assets/{id}` |
| Steel route | `is_bfbof`, `is_eaf`, `is_dri_eaf` | hand-coded from operator notes |
| Disclosed cf | `disc_cf`, `disc_has` | production / capacity from IAR text |

Normalization is per-feature `(x - μ) / σ` over the training set. The disclosed-cf feature is **non-leaky in LODO** because production tonnes are reported in IAR text independently of Scope 1 — when a facility's Scope 1 is held out, its production tonnage and therefore its `disc_cf` are still available.

## 3.3 Model

The model is a **LoRA-shaped two-layer MLP** with rank-32 hidden dim:
```
y = (x @ A^T) @ B^T
```
where `A ∈ R^{32×15}` and `B ∈ R^{1×32}` are both initialized with small Gaussian noise (`std_A = 1/√15, std_B = 1/√32`). The standard "LoRA-on-frozen-base" zero-init for `B` is incorrect here because we have no frozen base — `B = 0` would freeze `A`'s gradient on step 0 (the chain rule gives `dL/dtemp = dy × B = 0`). Both being small Gaussian breaks symmetry while keeping init magnitudes well below numerical-stability ceilings.

Training uses AdamW (`β1=0.9, β2=0.999, ε=1e-8`) at `lr=0.02` for 120 epochs, batch size 8. Implemented in WGSL shaders ported from [fused-lora](https://github.com/abgnydn/fused-lora) (5 compute pipelines: `lora_down`, `lora_up`, `lora_down_bwd_A`, `lora_up_bwd_T`, `lora_up_bwd_B`, `adam_lora`). Whole training loop runs at native speed in any browser via WebGPU on f16 storage; one full training takes ~3 seconds on a 2024 Apple GPU.

### Best-val checkpoint

Late-training (~ep 90-110) we occasionally observe gradient spikes with `vMAE` shooting from ~0.2 to >1.0 and only partially recovering by ep 120. To defend against these, we snapshot the (A, B) state to CPU at every epoch where validation MAE is the lowest seen so far (after a 10-epoch warmup), and restore the best snapshot before test-set predictions. Reduces test variance roughly 2× without otherwise changing training dynamics.

## 3.4 Physics-informed prior (the key contribution)

The loss is **weighted MSE on log-Scope-1 residuals against a physics-informed prior**:

```
ŷ_raw = model(x_normalized)
target_residual = log1p(y_true) − log1p(y_prior)
loss = 0.5 × w × (ŷ_raw − target_residual)^2
prediction = exp(ŷ_raw + log1p(y_prior)) − 1
```

The prior `y_prior` is the cf-corrected formula `cap × EF × cf` computed with the same EF/cf priority described in §3.1 tier 3 (route-EF > company override > sector EF; CT cf > disc cf > sector cf). When the prior is unavailable for a sample (rare; falls back to training-set mean), the loss reduces to the standard mean-centered target.

The effect of the prior is dramatic. Without it, the model has to learn the full magnitude of log-Scope-1 (~14-17) from `~40` training samples — slow, unstable, and prone to over-fitting whichever sector dominates the train set. With the prior, the model only has to learn residuals (typically `|r| < 0.5` in log-space), which generalizes from very few examples. The prior also bakes in known physics: emissions scale with capacity, change linearly with the route-specific EF, and modulate with cf — relationships that would otherwise need to be re-learned per training run.

The prior is **leak-safe under LODO** because:
- `cap` comes from operator nameplate (public, not Scope 1).
- `EF` is per-route or per-company average — the route value (e.g. BF/BOF 2.0) is the industry standard and matches the global average, so it isn't derived from the held-out facility's disclosure.
- `cf` comes from CT measurement OR from disclosed production tonnage — neither is the Scope 1 label.

Section 6 ablations show that removing the prior drops overall LODO log-MAE reduction by ~8 percentage points.

## 3.5 Evaluation: Leave-one-disclosure-out (LODO)

Standard random or stratified test splits put too few disclosure-labeled facilities in test for a meaningful per-source metric. We instead evaluate each of the **n=21 audit-grade facilities** by forcing it into the test set, stratifying the remaining 58 facilities normally, training the model, and reading the prediction for the held-out facility. This gives n=21 test points without resampling. We run 5 outer LODO passes × 3 inner seeds (15 predictions per facility), report the per-facility median, and additionally bootstrap-resample the n=21 facilities 5000 times to compute the data-variance confidence interval.

**Headline result: iz-1 NN +83.3% log-MAE reduction vs EU CBAM default; closed-form formula +85.3%; ridge regression +81.4%; 95% data-bootstrap CI [+72.0%, +90.6%].** The formula and the NN are statistically tied at this data scale; the deliverable is the formula and the bench.

Each LODO iteration is run for 3 seeds (random model init + shuffle order). We then wrap the whole LODO evaluation in an **outer aggregator** that repeats it 5 times, taking the per-facility median across all 5 × 3 = 15 seeds. The outer aggregation reduces variance on the headline metric from ~7 percentage points (single LODO run) to ~1-2 percentage points (15-seed median).

## 3.6 Two metrics, two stories

We report two metrics:

- **log-MAE reduction** — the model's accuracy improvement vs the EU CBAM default value, computed in log space. This is the metric we optimize and report in the headline.
- **Δ vs EU** = `(EU − iz_pred) / EU` — the operator's cost savings if they use the iz prediction instead of the EU default. Positive means the operator pays less.

These two metrics agree when the EU default is a wild overestimate (cement, EAF — both metrics positive). They **disagree for big BF/BOF integrated mills**, where the EU default 1.9 t/t happens to be close to TR audited reality (1.97-2.40 t/t): the operator's cost-saving metric stays positive (iz predicts low, operator pays less) but the log-MAE accuracy metric is *negative* (iz is less accurate than EU because EU is essentially right). The cost-savings positive sign there is iz-induced **payment-evasion**, not accuracy improvement — and the paper foregrounds log-MAE reduction as the honest metric.
