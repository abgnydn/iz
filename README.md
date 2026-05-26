# TR-MRV-Bench / iz-1

**A public per-facility emissions benchmark for Turkish CBAM-scope industry, plus a closed-form physics baseline that beats the EU CBAM default by 88%.**

> **Headline (v0, n=8 disclosure facilities, 95% CI from 5 outer LODO runs):**
> - **B1 — cf-corrected formula** `cap × EF × cf`: **87.1% log-MAE reduction** vs EU default (no learned parameters).
> - **iz-1 — 2-layer NN, 15 seeds median**: **88.7% ± 2.4%** (statistically indistinguishable from the formula).
> - B2 — ridge regression on same features: 80.5%.
> - B3 — Climate TRACE direct on matched subset (n=3): 37.4%.
> - Cement 88.1% ± 1.7%, EAF 98.3% ± 3.3%, BF/BOF integrated 29.8% ± 35.3% (wide CI on n=3 stratum).
>
> n=8 is small. We are honest about variance and confidence in §8. No satellite signal in v0.

[**Paper preview (1-pager)**](./marketing/paper_preview_v0.html) · [**Headline figure**](./reports/fig_iz1_vs_eu_lodo.svg) · [**Brain notes**](https://github.com/abgnydn/brain)

---

## What this is

Three artifacts shipped together — **the deliverables are the bench and the formula, not the model**:

1. **TR-MRV-Bench** — a public benchmark of 57 Turkish CBAM-scope facilities (32 cement, 16 steel, 3 aluminum, 6 fertilizer) with three-tier supervision: 8 audit-grade strong labels from operator IARs / sustainability reports, 13 Climate TRACE per-asset labels, capacity-factor-corrected default labels for the remainder. Stratified split by `(scope × steel_route)`.

2. **cf-corrected formula** — closed-form `capacity × EF × cf` with EF priority (steel-route &gt; company-specific &gt; sector-mean) and cf priority (Climate TRACE per-asset &gt; disclosed-production-ratio &gt; sector-mean). **This is the headline result and the actual deliverable.** Predicts Akçansa Büyükçekmece audited Scope 1 within 1% from capacity + sector EF + sector-default cf, no facility-specific tuning.

3. **iz-1 (the model)** — a 2-layer LoRA-shaped MLP trained against the formula as a baseline subtraction. Browser-native via WebGPU; trains in 3 seconds. With 40 training facilities and 15 features it does not meaningfully improve on the formula — a useful negative result for future small-data ML on emissions benchmarks. We ship it as a working-and-honest reference implementation, not as a state-of-the-art model.

## Result

Three baselines + the model, all evaluated on the same leave-one-disclosure-out (LODO) split over 8 audit-grade Turkish facilities:

| Baseline | log-MAE | Reduction vs EU |
|----------|--------:|----------------:|
| B0 EU CBAM default | 0.967 | 0.0% |
| B3 Climate TRACE direct (n=3 matched) | 0.247 | +37.4% (subset only) |
| **B1 cf-corrected formula** | **0.124** | **+87.1%** |
| B2 Ridge regression | 0.189 | +80.5% |
| **iz-1 NN (15-seed median)** | **0.114** | **+88.2%** (95% CI: 88.7% ± 2.4%) |

Per-facility numbers for the iz-1 NN (closest analog to "what an operator gets if they query the model"):

| Facility | Sector / route | Truth (tCO₂) | iz-1 (median) | Ratio | EU default |
|----------|----------------|-------------:|--------------:|------:|-----------:|
| Akçansa Büyükçekmece | cement | 1,514,000 | 1,399,178 | 0.92× | 7,128,000 |
| Akçansa Çanakkale | cement | 3,466,000 | 2,937,231 | 0.85× | 9,504,000 |
| Akçansa Ladik | cement | 499,000 | 553,145 | 1.11× | 2,376,000 |
| Çolakoğlu Dilovası | steel · EAF | 566,519 | 451,144 | 0.80× | 5,700,000 |
| Erdemir Ereğli | steel · BF/BOF | 6,673,266 | 7,324,325 | 1.10× | 11,400,000 |
| İsdemir İskenderun | steel · BF/BOF | 10,663,364 | 6,791,772 | 0.64× | 10,450,000 |
| Kardemir Karabük | steel · BF/BOF | 5,539,756 | 4,471,521 | 0.81× | 6,650,000 |
| Nuh Hereke | cement | 3,573,278 | 3,014,967 | 0.84× | 9,504,000 |

**Per-sector log-MAE reductions vs EU default:**

| Sector | n | iz-1 log-MAE | EU log-MAE | Reduction |
|--------|---|-------------:|-----------:|----------:|
| Cement | 4 | 0.129 | 1.274 | **+89.9%** |
| Steel · EAF | 1 | 0.228 | 2.309 | **+90.1%** |
| Steel · BF/BOF | 3 | 0.253 | 0.246 | −2.7% |
| **Overall** | **8** | **0.188** | **1.018** | **+81.5%** |

The cement and EAF wins are clean. For BF/BOF integrated mills the EU CBAM default value (1.9 t/t crude steel) happens to be within 2-20% of TR audited reality (1.97-2.40 t/t) so the model can only match — not meaningfully beat — the EU baseline.

## Limitations (paper §8 honest version)

1. **n=8 is tiny.** Eight audit-grade test facilities is one paper's worth of grit, not a serious benchmark. Anything we claim has wide CIs.
2. **No satellite signal in v0.** The S5P NO₂ pipeline runs but didn't make it into the model. We dropped the "Earth-observation foundation model" framing earlier drafts had — it isn't one.
3. **It's not a foundation model.** iz-1 is a 2-layer MLP with ~500 parameters trained from scratch on 40 samples. Calling it a foundation model is overclaiming. We call it a model.
4. **The formula wins.** Our closed-form `cap × EF × cf` baseline (B1) outperforms iz-1 ML (84.9%) at 87.8%. The actionable deliverable is the formula and the bench. The ML model is a reference implementation, not state-of-the-art.
5. **Operator-self-reported truths.** Strong labels come from operator IARs / sustainability reports (mostly Big4-audited, one ISO 14064-1 verified). Not third-party-verified. This is the same trust problem Climate TRACE tries to bypass.
6. **Climate TRACE under-reporting claim is sample-size 3.** We see CT under-reports İsdemir −22%, Kardemir −27%, Erdemir-derived −22% on the three TR BF/BOF mills. We do *not* claim CT is wrong globally — only that in our 3-mill TR sample it consistently underestimates.
7. **BF/BOF stratum (n=3) is trivially partitioned under LODO.** With only 3 BF/BOF mills in TR, leave-one-out is "predict from the other 2". Not a real generalization test on this stratum.
8. **No temporal generalization.** All labels are within one window (2022-2025). We can't claim the model holds for future years.
9. **Akçansa per-plant labels are allocated from group total** by clinker-production share (also from operator IAR). Erdemir Ereğli is derived by subtraction from group total. Several "audit-grade" labels are derived numbers anchored to audited group totals, not directly disclosed per-plant.
10. **Some capacities in `tr_facilities.csv` were corrected mid-session** (Çanakkale 4.5M → 6M). Other facilities may have similar nameplate errors we haven't audited.

## Reproducibility

```bash
# Setup (requires uv, playwright, an internet connection for the disclosure PDFs)
git clone https://github.com/abgnydn/iz
cd iz
uv sync
uv run playwright install chromium

# Build the bench (downloads Climate TRACE data; reads cached PDFs from data/disclosures/)
uv run python bin/pull_climate_trace_details.py
uv run python bin/export_bench_browser.py

# Start the browser-training server
python3 -m http.server 8765 --bind 127.0.0.1 --directory src/iz_browser &

# Single LODO run with 15 seeds aggregated (5 outer × 3 inner)
uv run python bin/e2e_lodo_aggregate.py 5
uv run python bin/figure_lodo.py    # writes reports/fig_iz1_vs_eu_lodo.svg

# Full ablation matrix
uv run python bin/run_ablations.py 3
```

Or open `src/iz_browser/train.html` in any browser to train interactively (3s on Apple GPU).

## Methodology highlights

- **Stratified split** by `(scope × steel_route)` — critical because TR has only 3 BF/BOF mills; hash split leaves them maldistributed across train/test.
- **Capacity-factor-corrected labels** — replace raw `capacity × EU_default_EF` with `capacity × TR_actual_EF × cf` where `cf` is per-asset Climate TRACE measurement when available, sector-mean otherwise. The cf-corrected formula independently matches Akçansa Büyükçekmece audited Scope 1 within 1% (1.502M vs 1.514M disclosed).
- **Steel route feature** (`is_bfbof / is_eaf / is_dri_eaf`) — EAF mills emit 5-10× less Scope 1 per tonne than BF/BOF; without this feature the model massively over-predicts EAF emissions.
- **Disclosed-cf table** — production/capacity derived from IAR text (non-leaky in LODO because production data is independent of Scope 1).
- **Physics-informed prior** — model trains against `y_log − log(cap × EF × cf)` so it only learns residuals against the formula. Generalizes much better than learning the full target magnitude with 40 training samples.
- **Best-val checkpoint** — `src/iz_browser/train.js` snapshots A,B at lowest val MAE and restores before test predictions to defend against late-training gradient spikes.
- **Leave-one-disclosure-out** — each of 8 audit-grade facilities takes a turn being the test point. 5 outer × 3 inner = 15 seeds per facility for variance reduction.

## Data sources

All raw disclosure PDFs live under `data/disclosures/` (gitignored by default for size; download links and pages cited inline):

| Company | Year | Number | Source |
|---------|------|--------|--------|
| Akçansa group | 2025 | 5,484,015 tCO₂e + per-plant clinker | [2025 IAR p46+167](https://www.akcansa.com.tr/wp-content/uploads/2026/04/Akcansa_EFR_EN-21-nisan-v2.pdf) |
| Çolakoğlu Dilovası | 2024 | 566,519 | [2024 SR p82](https://www.colakoglu.com.tr/uploads/file/colakoglu-sr-24-en-08.pdf) |
| Çolakoğlu Dilovası | 2021–2023 | 517 / 493 / 495 kt | 2024 SR p82 time-series |
| Erdemir Group | 2024 | 17,336,630 | [2024 Entegre IAR p103 (KGK)](https://www.kgk.gov.tr/Portalv2Uploads/files/Duyurular/v2/Surdurulebilirlik/Raporlar/ERDEMIR2024EntegreFaaliyetRaporu.pdf) |
| İsdemir | 2024 | 10,663,364 | Erdemir 2024 IAR p115 |
| Erdemir Ereğli | 2024 | 6,673,266 | Derived: Group − İsdemir |
| Erdemir Ereğli | 2023 | 6,559,030 | [Tracenable](https://tracenable.com/company/erdemir/ghg-emissions) |
| Kardemir Karabük | 2022 | 5,539,756 | [2022 SR p61 (KGK)](https://www.kgk.gov.tr/Portalv2Uploads/files/Duyurular/v2/Surdurulebilirlik/Raporlar/Kardemir%202022%20y%C4%B1l%C4%B1%20S%C3%BCrd%C3%BCr%C3%BClebilirlik%20Raporu.pdf) |
| Nuh Hereke | 2024 | 3,573,278 (ISO 14064 verified) | [2024 IAR p59](https://www.nuhcimento.com.tr/wp-content/uploads/Nuh-Cimento-2024-Integrated-Annual-Report-1.pdf) |
| OYAK Çimento group | 2023 | 7,712,391 | [2023 Integrated Report p30](https://assets.oyakcimento.com/contents/pdf/2024255/85591726125090012652.pdf) |
| Limak Çimento group | 2023 | 7,138,623 | [2023 SR p89](https://www.limakcimento.com/assets/images/dosya/sustainability-report-2023_1751267090.pdf) |
| Climate TRACE per-asset | 2024 | 13 TR facilities | api.climatetrace.org `/v6/assets/{id}` |
| TR Cement industry avg EF | 2023 | 0.643 t/t cement | TÜRKÇİMENTO 2023 Sürdürülebilirlik Raporu |

## Limitations (paper Section 8)

- **N=8 disclosure facilities is small.** Bigger benchmarks would let us run real cross-validation rather than LODO.
- **BF/BOF integrated steel is structurally hard for any model.** TR has only 3 BF/BOF mills (Erdemir, İsdemir, Kardemir) and EU CBAM's 1.9 t/t is already close to the audited 1.97-2.40 range. iz-1 matches but does not meaningfully beat EU default on this stratum.
- **No satellite signal yet.** S5P NO₂ feature pipeline is rate-limited by Microsoft Planetary Computer; full 57-facility pull blocked.
- **İsdemir 0.64×** is the largest outlier. The cf_corrected formula gets it within 6% of truth (10.24M vs 10.66M) but the trained model under-predicts. Root cause: only 2 other BF/BOF mills in train under LODO, and one of them (Erdemir) has very different cf.

## Layout

```
src/iz/               ← Python package (bench schema, scrapers, CT client, etc.)
src/iz_browser/       ← WebGPU training UI (train.html / train.js / bench.json / shaders)
bin/                  ← Reproducibility scripts: pull / export / train / eval / figures
data/                 ← raw + processed (mostly gitignored)
data/tr_facilities.csv                 ← 57 TR CBAM-scope facilities
data/tr_facility_known_emissions.csv   ← 17 hand-curated strong-label rows
data/disclosures/     ← downloaded IAR / sustainability PDFs (gitignored)
reports/              ← Generated artifacts: lodo_aggregated.json, fig_iz1_vs_eu_lodo.svg, ablations/
marketing/            ← paper_preview_v0.html (1-page paper summary)
PAPER_OUTLINE.md      ← Full paper outline
CLAUDE.md             ← Development log + resume block
```

## Cite

```bibtex
@misc{gunaydin2026iz,
  title = {iz-1: A per-facility industrial emissions model with browser-native fine-tuning},
  author = {Ahmet Baris Gunaydin},
  year = {2026},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/abgnydn/iz}},
  note = {Apache-2.0; TR-MRV-Bench v0}
}
```

## License

Code + bench + weights all Apache-2.0 (cite-us).
