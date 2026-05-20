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

**Steps (next, in priority order):**

6. **First 3 sales calls.** Cold-email Akçansa + Tosyalı + Erdemir sustainability directors with the v0 chart + sample CBAM XML attached. Pitch line: "We just validated a CBAM declaration for your plant from free satellite data. Want to see it?" Goal: 1 reply, 1 call scheduled.
7. **Production-data calibration.** Pull Akçansa's published quarterly clinker output (CDP/sustainability report). Correlate against the satellite NO₂ trend. This is what makes the 0.65 tCO₂/t number defensible to an EU auditor instead of "iz's best guess."
8. **Plume fitting v1.** Replace the bbox-mean with a proper S5P divergence-method emission estimate. Standard literature; converts the 4-pixel bbox into a kg NOx/s number with uncertainty bounds.

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
