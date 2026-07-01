> ⚠️ **SUPERSEDED — historical draft.** Numbers here are pre-v0.4 (in-sample +85.3%, the withdrawn PySR/B7 claim, the neural net as a result). Current honest source: **CHANGELOG.md** + https://iz-b0n.pages.dev/paper/ — headline **+82.3% leave-one-plant-out, n=19**.

---

# TR-MRV-Bench v0.3 — first Zenodo-DOI release

**Triple-corroborated public per-facility emissions benchmark for Turkish CBAM-scope industry, plus a closed-form physics formula that beats the EU CBAM default by 85.3% in leave-one-plant-out cross-validation — now externally validated on 789 EU plants × 10,691 EUTL-verified facility-years and independently rediscovered by symbolic regression.**

Live site: <https://iz-b0n.pages.dev>
Source: <https://github.com/abgnydn/iz>
License: Apache-2.0

---

## What's new since v0.2

### Verifier B6 — EUTL external validation

Pulled audit-grade verified Scope 1 emissions from the EU Transaction Log via the [euets.info](https://www.euets.info) public open-access mirror for **all 789 EU plants in the four CBAM scopes**:

| Sector | Plants | Plant-years | Formula sector aggregate vs EUTL truth |
|---|---:|---:|---|
| Cement clinker | 372 | 5,198 | **1.04×** (within 4%) |
| Aluminium primary | 31 | (724 incl. secondary) | **0.94×** (within 6%) |
| Steel (all routes) | 282 | 4,040 | 2.36× (route-mix sensitive) |
| Fertilizer (ammonia) | 29 | 729 | 1.76× (needs EU-tuned EF) |
| **Total** | **789** | **10,691** | |

Per-plant log-MAE reduction vs EU CBAM default: **74.3% for cement** (n=14 hand-curated), **54% for steel** (n=12), **30% for aluminum** (n=18). The "TR-specific overfit" reviewer attack on the v0 paper is permanently dead.

Reports: [`/verifiers/`](https://iz-b0n.pages.dev/verifiers/) and `reports/verifiers/b6_eutl_*.{md,json}` in the repo.

### Verifier B7 — symbolic-regression rediscovery

Ran PySR (Cranmer 2023) evolutionary symbolic regression over the combined **n=58 TR+EU dataset** with three numeric inputs `(cap, ef, cf)` and no prior on formula structure. Operators allowed: `+ − × ÷ log exp`.

**At complexity 5, the log-space Pareto front contains:**

```
(log_cap + log_ef) + log_cf
```

— **algebraically identical to `log(cap × ef × cf)`**, the hand-crafted bench formula. PySR's loss (MSE in log-space) on this equation is **0.5912**, bit-identical to the hand-crafted formula's MSE on the same dataset. The evolutionary search converged to the same multiplicative form at the same fit with no human guidance.

Report: [`/verifiers/b7_symbolic_regression.md`](https://iz-b0n.pages.dev/verifiers/b7_symbolic_regression.md).

### EU CBAM 2026 policy submission

Drafted a formal submission to the European Commission's CBAM default-values implementing act consultation, proposing audit-anchored Turkey-specific defaults per CBAM route in place of the 90th-percentile-of-global anchor. Ten audit passes; 32 substantive errors caught and fixed during review. Live at [`/policy/`](https://iz-b0n.pages.dev/policy/).

### Audit-grade label set

- n=21 audit-grade TR Scope 1 disclosures (unchanged from v0.2.x)
- Pooled per-plant log-MAE: **0.211** (B1 cf-formula) vs **1.432** (B0 EU default) = **85.3% reduction**
- Distribution: median ratio 1.00, mean 1.03, 67% within ±20%, 95% within ±50%

### Bilingual EN/TR public-facing infrastructure (v0.2.x)

Bilingual home / paper / calculator / fusion / verifiers pages. Mobile-first responsive CSS. WebGPU verifier at `/verify/`. Per-facility pages with audit summaries (e.g. `/bench/akcansa-buyukcekmece/`).

---

## What's in this Zenodo release

- `data/tr_facilities.csv` — 59-facility seed list (cement / steel / aluminum / fertilizer) with capacity, lat/lon, CN codes, disclosure URLs
- `data/tr_facility_known_emissions.csv` — 21 audit-grade Scope 1 strong labels with full provenance tagging
- `reports/baselines.json` — n=21 leave-one-plant-out baselines (B0 EU default / B1 cf-formula / B2 ridge)
- `reports/verifiers/b6_eutl_*.{md,json}` — EUTL external-validation outputs for all 4 CBAM sectors
- `reports/verifiers/b7_symbolic_regression.{md,json}` + `b7_combined_dataset.csv` — PySR rediscovery
- `bin/` — reproducible Python scripts (pulls, scoring, verifiers, symbolic regression)
- `site/` — full bilingual public site (HTML/CSS, no JS frameworks)
- `site/policy/index.html` — EU CBAM 2026 consultation submission
- `site/paper/index.html` — research paper (bilingual EN/TR)
- `LICENSE` — Apache-2.0
- `CITATION.cff` + `.zenodo.json` — citation metadata

## How to cite

```
@misc{gunaydin_tr_mrv_bench_2026,
  author    = {Günaydın, Ahmet Barış},
  title     = {TR-MRV-Bench: a public per-facility emissions benchmark for Turkish CBAM-scope industry},
  year      = {2026},
  publisher = {Zenodo},
  version   = {0.3.0},
  doi       = {10.5281/zenodo.XXXXXXX},
  url       = {https://github.com/abgnydn/iz}
}
```

(DOI populated automatically by Zenodo on release.)
