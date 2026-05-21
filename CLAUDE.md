# CLAUDE.md — iz

Satellite + AI emissions verification for Turkish CBAM exporters. See `README.md` for the pitch.

## 🎯 Resume here (on "continue")

_Updated: 2026-05-19 (evening) — v0 spike shipped (E40). Plant signal 1.9–18.7× rural background NO₂ on 4 clean scenes via Sentinel-5P + MPC. Next: get from "satellite signal exists" to "draft CBAM declaration in EU format" + first sales call._

**Done so far:**
- ✅ Step 1 — Target picked: Akçansa Büyükçekmece (Sabancı, Mimarsinan coast).
- ✅ Step 2 — Sentinel-5P NO₂ pipeline (see `notebooks/01_s5p_akcansa.py`, `reports/akcansa_s5p_v0.png`, [[E40-iz-s5p-akcansa-v0]]).
- ✅ Step 3 — Official EU XSD v23.00 downloaded (`data/cbam_schema/`), Jinja2 template at `src/iz/reporting/cbam_template.xml`.
- ✅ Step 4 — `bin/demo.py` renders Akçansa Q1 2026 declaration and **validates against the official EU XSD**. Output: `reports/cbam_akcansa_2026_Q1_v0.xml`. Headline: 10 kt shipment → €747k saved/quarter vs. EU default.
- ✅ Step 5 — First-cut outreach list in `sales/targets.md` (cement + steel; aluminum/fertilizer stubbed).
- ✅ **Day 1 of iz-1 plan (2026-05-21)** — Strategic reframe shipped to brain ([[iz]] + [[E41-iz-stack-audit]]). Three open questions closed (shader-gen templates per-arch / gradfree ES is real / GPU Adam dispatched). TR-MRV-Bench seed list at `data/tr_facilities.csv` — **57 facilities** (32 cement, 16 steel, 3 aluminum, 6 fertilizer) with lat/lon, capacity, CN codes, public disclosure URLs.

**Steps (next, in priority order — iz-1 paper-first track, sales deferred):**

6. **CDP / sustainability disclosure scrape.** For each facility in `data/tr_facilities.csv`, pull last 5-7 years of public emissions from the URL in column `public_disclosure_url`. Targets: Scope 1 tCO₂, cement/steel tonnes produced, clinker tonnes, fuel mix, specific emission factor. Output: `data/tr_facility_disclosures.parquet` keyed on `(id, year)`. Mostly text scraping, low bandwidth.
7. **Climate TRACE label join.** Pull `https://api.climatetrace.org/v6/...` per-facility emissions for the same 57 facilities. These are weak supervision labels (±50%) vs. CDP's strong labels (±10%). Output: `data/climate_trace_labels.parquet`.
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
