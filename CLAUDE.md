# CLAUDE.md — iz

Satellite + AI emissions verification for Turkish CBAM exporters. See `README.md` for the pitch.

## 🎯 Resume here (on "continue")

_Updated: 2026-05-19 (evening) — v0 spike shipped (E40). Plant signal 1.9–18.7× rural background NO₂ on 4 clean scenes via Sentinel-5P + MPC. Next: get from "satellite signal exists" to "draft CBAM declaration in EU format" + first sales call._

**Done so far:**
- ✅ Step 1 — Target picked: Akçansa Büyükçekmece (Sabancı, Mimarsinan coast).
- ✅ Step 2 — Sentinel-5P NO₂ pipeline (see `notebooks/01_s5p_akcansa.py`, `reports/akcansa_s5p_v0.png`, [[E40-iz-s5p-akcansa-v0]]).
- ✅ Step 5 — First-cut outreach list in `sales/targets.md` (cement + steel; aluminum/fertilizer stubbed).

**Steps (next, in priority order):**

3. **EU CBAM report schema.** Download the official EU CBAM XML schema + reporting template (Implementing Regulation 2023/1773 annex). Stub a Jinja2 template in `src/iz/reporting/cbam_template.xml` that takes `(plant_id, period, embedded_emissions_t_co2, verification_method, electricity_consumed_mwh, …)` and emits a syntactically valid CBAM declaration.
4. **End-to-end fake demo.** Script `bin/demo.py` that wires v0 NO₂ → production-tonnes-derived CO₂ estimate → CBAM XML: "given Akçansa, here's a draft CBAM report." Numbers don't need to be production-quality yet — it just needs to *render* in the EU's format. **Acceptance:** `uv run python bin/demo.py --plant akcansa` produces a CBAM XML that opens in EU's validator without schema errors.
6. **First 3 sales calls.** Pick 3 from `sales/targets.md`. Cold-email the sustainability director with the v0 chart attached. Goal isn't a sale — it's *listening* to what scares them about January 2026.

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
