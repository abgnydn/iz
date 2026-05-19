# CLAUDE.md — iz

Satellite + AI emissions verification for Turkish CBAM exporters. See `README.md` for the pitch.

## 🎯 Resume here (on "continue")

_Updated: 2026-05-19 — fresh init. No code yet. Folders + scope only._

**Steps (next, in priority order):**

1. **Pick one real Turkish cement plant as the v0 target.** Candidates in `sales/targets.md` — Akçansa Büyükçekmece is the obvious one (largest TR cement exporter, Sabancı-owned, EU-export-heavy, public emissions data exists). Confirm GPS + production capacity + recent EU shipment volumes.
2. **Sentinel-5P spike.** Write `notebooks/01_s5p_akcansa.py` (or `.ipynb`):
   - Pull last 90 days of Sentinel-5P **NO₂** Level-2 product over the plant footprint (S5P doesn't measure CO₂ — NO₂ is the standard industry activity proxy for cement/power, correlates with combustion intensity; CO₂ comes later via production-tonnes × emission factor).
   - Optionally pull SO₂ + CO as secondary proxies.
   - Spatial-mean column density over plant bbox; subtract a rural-Thrace background bbox as a baseline.
   - Sanity-check trend vs. seasonal expectation + plant outage records (if findable).
   - **Acceptance:** one chart showing satellite-inferred NO₂ trend over the plant vs. rural background, written to `reports/akcansa_s5p_v0.png` and `logs/01_s5p_akcansa.log`.
3. **EU CBAM report schema.** Download the official EU CBAM XML schema + reporting template. Stub a Jinja2 template in `src/iz/reporting/cbam_template.xml` that takes `(plant_id, period, emissions_t_co2, verification_method)` and emits a syntactically valid CBAM declaration.
4. **End-to-end fake demo.** Script `bin/demo.py` that wires (2) → (3): "given Akçansa, here's a draft CBAM report." Numbers don't need to be production-quality yet — it just needs to *render* in the EU's format. **Acceptance:** in 2 minutes a non-engineer can run `python bin/demo.py --plant akcansa` and get a CBAM XML they can open.
5. **Outreach list.** Fill `sales/targets.md` with top-20 TR CBAM exporters (cement, steel, aluminum, fertilizer). Pull from public TR customs / TÜİK data. For each: company, plant, contact pattern, last public emissions number, est. annual EU shipment volume.
6. **First 3 sales calls.** Pick 3 from the top-20. Cold-email the sustainability director. Goal isn't a sale — it's *listening* to what scares them about January 2026.

**Acceptance for this Resume block:**
- Step 4 produces a CBAM XML file for one real plant from real Sentinel-5P data.
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
