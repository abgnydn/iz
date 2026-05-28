# EnMAP access how-to (v0.2 blocker)

The DLR EOC Geoservice STAC catalog is **auth-free** for metadata
(we already use this in `bin/find_enmap_scenes.py` to build the 103-scene
index over our 21 facilities). But all actual data downloads
(L2A spectral COG, VNIR/SWIR quicklooks, even thumbnails) redirect to
`sso.eoc.dlr.de/eoc/auth/login`. DLR registration is required.

This file documents how to get past the wall and what to do once you have
credentials.

---

## Step 1 — Register for EnMAP data access

1. Go to <https://www.enmap.org/data_access/>.
2. Click "Data Access via EOWEB® GeoPortal (EGP)" or "Instrument Planning
   Portal (IPP)".
3. Create a DLR EOWEB account: <https://eoweb.dlr.de/egp/main>.
4. Verify your email; account is approved in 1-3 days (per DLR FAQ).
5. After approval, log in to EOWEB and complete the EnMAP Terms of Use
   acceptance (one-time).

Cost: free. Account is good for many other DLR missions too
(TanDEM-X, TerraSAR-X, etc.).

---

## Step 2 — Configure credentials for programmatic download

Once you have a DLR account, the simplest path is a `.netrc` file:

```bash
cat >> ~/.netrc <<'EOF'
machine sso.eoc.dlr.de
  login YOUR_EOWEB_USERNAME
  password YOUR_EOWEB_PASSWORD
machine download.geoservice.dlr.de
  login YOUR_EOWEB_USERNAME
  password YOUR_EOWEB_PASSWORD
EOF
chmod 600 ~/.netrc
```

`requests` (Python) and `curl` both honor `.netrc` automatically.

Alternative: pass `auth=("user","pass")` explicitly in your Python code.
**Do not commit credentials to git** — `.netrc` is the standard location.

---

## Step 3 — Smoke-test download

```bash
# Pick a scene from our index (Akçansa Büyükçekmece 2026-05-25, cc=1%):
URL="https://download.geoservice.dlr.de/ENMAP/files/L2A/2026/05/25/DT0000196528/04/ENMAP01-____L2A-DT0000196528_20260525T093246Z_004_V010506_20260526T153030Z/ENMAP01-____L2A-DT0000196528_20260525T093246Z_004_V010506_20260526T153030Z-SPECTRAL_IMAGE_COG.TIF"
curl -L --netrc -O "$URL"
```

If you get the file (~3-5 GB COG with 224 bands), you're in. If you get
a redirect loop, the credentials are wrong or the SSO cookie scope is
narrower than expected — check the DLR FAQ.

**Disk budget**: each L2A scene is 3-5 GB. The 103-scene index is
~400-500 GB if you download everything. For v0.2 you'd realistically
want ~10-20 scenes (a few cloud-free per facility, total ~50-100 GB).

---

## Step 4 — What to do once you have data

The v0.2 hero feature is **direct CO₂ + NO₂ plume retrieval** following
Borger et al. (2025, ERL, doi:10.1088/1748-9326/adc0b1).

Pipeline pieces:

1. **Atmospheric correction**: EnMAP L2A is already CARD4L
   (CEOS Analysis-Ready Data), surface reflectance. No additional
   correction needed for v0.2 first-pass.

2. **DOAS retrieval for NO₂**: 425-470 nm window, NO₂ absorption
   cross-section from Vandaele et al. (or HITRAN). EnMAP's VNIR
   spectral resolution (~6.5 nm) may be marginal for NO₂; Borger's
   approach uses additional smoothing.

3. **CO₂ retrieval**: 2.0 μm and 1.6 μm SWIR windows. Requires
   RemoTeC-style full radiative transfer (line-by-line, atmospheric
   profile, surface reflectance prior). This is the multi-week step.
   Open-source code:
   - **6ABOS** (Atmospheric correction for EnMAP):
     <https://arxiv.org/pdf/2603.10856>
   - **EnMAP-Box** plugins: <https://enmap-box.readthedocs.io>
   - **DLR's SICOR**: <https://gitext.gfz-potsdam.de/EnMAP/sicor>

4. **Plume identification**: difference between plant pixels and a
   downwind/upwind background. Threshold + connected-component on the
   retrieved CO₂ excess (Δ XCO₂).

5. **Emission flux estimation**: cross-sectional integration (CSI) or
   Gaussian plume fit using ERA5 wind at hub height. Borger uses CSI.

For v0.2 first-pass, **start with steps 1-3 over one cloud-free
Akçansa Büyükçekmece scene** (2026-05-25, cc=1%) and just produce a
single-day CO₂ map. That alone is a publishable wedge:
"first direct EnMAP CO₂ retrieval over a Turkish CBAM facility."

---

## Step 5 — Cite Borger 2025 as methodology source

```bibtex
@article{borger2025enmap,
  title = {High-resolution observations of NO2 and CO2 emission plumes from EnMAP satellite measurements},
  author = {Borger, C. and Beirle, S. and Butz, A. and Scheidweiler, L. and Wagner, T.},
  journal = {Environmental Research Letters},
  year = {2025},
  doi = {10.1088/1748-9326/adc0b1}
}
```

---

## What is already done (and committed) in v0.1

- `bin/find_enmap_scenes.py` — STAC scout, auth-free.
- `data/enmap_scenes_index.csv` — 103 scenes across 21 audit-grade
  facilities, cloud cover ≤ 25%, sortable by date.
- 18 of 21 facilities have at least one zero-cloud-cover scene.

The scene index is the v0.1 deliverable. The retrieval is v0.2.
