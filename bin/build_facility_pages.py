"""
Generates one static HTML page per facility under site/bench/{id}/index.html.

The page is what an operator sees when they Google their plant name. It pulls
together:
 - identity (company / plant / city / capacity / sector / route)
 - truth (Scope 1 + provenance + assurance + source PDF)
 - iz prediction with conformal CI (when in the leave-one-plant-out disclosure subset)
 - EU CBAM default + delta vs. truth
 - Beirle 2023 v2 TROPOMI NOx flux (when within 15 km of a catalog source)
 - EnMAP scenes available (count + first 3 cloud-free dates)
 - Methodology footer: how to verify, how to correct, how to cite

Inputs (read-only):
 - site/bench/facilities.json     master per-facility join
 - data/beirle_match_audit_grade.csv
 - data/enmap_scenes_index.csv
 - reports/conformal_ci.json

Outputs:
 - site/bench/{id}/index.html     one per facility
 - site/sitemap.xml updated to include the new URLs
"""
from __future__ import annotations
import csv
import html
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAC_JSON = REPO / "site" / "bench" / "facilities.json"
BEIRLE = REPO / "data" / "beirle_match_audit_grade.csv"
ENMAP = REPO / "data" / "enmap_scenes_index.csv"
CONFORMAL = REPO / "reports" / "conformal_ci.json"
OUT_DIR = REPO / "site" / "bench"
SITEMAP = REPO / "site" / "sitemap.xml"

SITE_URL = "https://iz-b0n.pages.dev"


def load_beirle() -> dict[str, dict]:
    out = {}
    if not BEIRLE.exists():
        return out
    with BEIRLE.open() as f:
        for r in csv.DictReader(f):
            try:
                d = float(r.get("distance_km") or "nan")
                nox = float(r.get("beirle_nox_kgs") or "nan")
            except ValueError:
                continue
            if d != d or nox != nox:
                continue
            if d <= 15:
                out[r["id"]] = {
                    "nox_kgs": nox,
                    "nox_err_kgs": float(r.get("beirle_nox_err_kgs") or 0),
                    "distance_km": d,
                    "pp_match": r.get("beirle_pp_match", "") or None,
                    "city_match": r.get("beirle_city_match", "") or None,
                }
    return out


def load_enmap() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    if not ENMAP.exists():
        return out
    with ENMAP.open() as f:
        for r in csv.DictReader(f):
            fid = r.get("facility_id", "")
            if not fid:
                continue
            try:
                cc = float(r.get("cloud_cover") or 100)
            except ValueError:
                cc = 100
            out[fid].append({
                "scene_id": r.get("scene_id", ""),
                "datetime": r.get("datetime", ""),
                "cloud_cover": cc,
            })
    for fid in out:
        out[fid].sort(key=lambda s: (s["cloud_cover"], s["datetime"]))
    return out


def load_conformal() -> dict[str, dict]:
    if not CONFORMAL.exists():
        return {}
    d = json.loads(CONFORMAL.read_text())
    return {r["facility_id"]: r for r in d.get("per_facility", [])}


def fmt_int(x: float | None) -> str:
    if x is None or x != x:
        return "—"
    return f"{int(round(x)):,}"


def fmt_pct(x: float) -> str:
    return f"{x:+.0f}%" if x != x or abs(x) >= 1 else f"{x:+.1f}%"


def render_page(fac: dict, beirle: dict | None, scenes: list[dict],
                conformal: dict | None) -> str:
    def s(key: str, default: str = "") -> str:
        v = fac.get(key)
        return default if v is None else str(v)

    fid = fac["id"]
    company = s("company")
    plant = s("plant")
    sector = s("sector")
    city = s("city")
    cap = fac.get("capacity")
    truth = fac.get("truth")
    truth_year = fac.get("truth_year")
    truth_src = s("truth_src")
    provenance = s("provenance")
    assurance = s("assurance")
    notes = s("notes")
    label_source = s("label_source")
    eu_default = fac.get("eu_default")
    pred_median = fac.get("pred_median")
    n_runs = fac.get("n_runs")
    # Honest headline prediction: cf-corrected formula, leave-one-plant-out
    formula_pred = fac.get("formula_pred")
    formula_validatable = fac.get("formula_validatable")

    title_h1 = html.escape(f"{plant}") if plant else html.escape(fid)
    company_line = html.escape(company) if company else ""

    delta_eu = None
    if eu_default and truth:
        delta_eu = (eu_default - truth) / truth * 100
    delta_formula = None
    if formula_pred and truth:
        delta_formula = (formula_pred - truth) / truth * 100

    # Build truth block
    pdf_links = ""
    if "akcansa" in fid.lower():
        pdf_links = '<a href="https://www.akcansa.com.tr/en/our-company/integrated-annual-reports/" target="_blank" rel="noopener">Akçansa IAR archive</a>'
    elif "erdemir" in fid.lower() or "isdemir" in fid.lower():
        pdf_links = '<a href="https://www.erdemir.com.tr/en/investor-relations/financial-information/integrated-annual-reports" target="_blank" rel="noopener">Erdemir IAR archive</a>'
    elif "kardemir" in fid.lower():
        pdf_links = '<a href="https://www.kardemir.com/sustainability-reports.aspx" target="_blank" rel="noopener">Kardemir sustainability reports</a>'

    # Conformal CI line (global + per-stratum if available)
    ci_line = ""
    if conformal:
        ci_lo = conformal.get("ci_lo")
        ci_hi = conformal.get("ci_hi")
        cov = conformal.get("covered")
        ci_lo_s = conformal.get("ci_lo_stratum")
        ci_hi_s = conformal.get("ci_hi_stratum")
        stratum = conformal.get("stratum", "")
        is_tighter = (ci_lo_s and ci_hi_s and ci_lo and ci_hi
                      and ci_hi_s - ci_lo_s < ci_hi - ci_lo)
        if ci_lo is not None and ci_hi is not None:
            ci_line = (f'<div class="ci-line">95% conformal prediction interval (global, n=21): '
                       f'<strong>{fmt_int(ci_lo)}</strong> – '
                       f'<strong>{fmt_int(ci_hi)}</strong> tCO₂ '
                       f'<span class="muted">({"truth inside ✓" if cov else "truth outside ✗"})</span></div>')
            if is_tighter and stratum:
                cov_s = conformal.get("covered_stratum")
                ci_line += (f'<div class="ci-line" style="margin-top:4px;">95% interval restricted to '
                            f'<code>{html.escape(stratum)}</code> calibration set: '
                            f'<strong>{fmt_int(ci_lo_s)}</strong> – '
                            f'<strong>{fmt_int(ci_hi_s)}</strong> tCO₂ '
                            f'<span class="muted">({"truth inside ✓" if cov_s else "truth outside ✗"} · '
                            f'undercoverage caveat at small n)</span></div>')

    # Beirle block
    beirle_block = ""
    if beirle:
        nox = beirle["nox_kgs"]
        err = beirle["nox_err_kgs"]
        dist = beirle["distance_km"]
        pp = beirle.get("pp_match")
        city_m = beirle.get("city_match")
        ann = []
        if pp:
            ann.append(f"colocated source: {html.escape(pp)}")
        elif city_m:
            ann.append(f"city: {html.escape(city_m)}")
        ann_str = f" ({'; '.join(ann)})" if ann else ""
        beirle_block = f"""
<section>
  <h2><span class="h2-num">04</span> Satellite cross-check</h2>
  <p>The TROPOMI flux-divergence catalog of <a href="https://essd.copernicus.org/articles/15/3051/2023/" target="_blank" rel="noopener">Beirle et al. (2023, ESSD)</a> lists a NOx source within {dist:.1f} km of this plant:</p>
  <p class="metric"><strong>{nox:.3f} ± {err:.3f} kg NOx/s</strong>{ann_str}</p>
  <p class="muted">NOx is an activity proxy independent of operator disclosure. A catalog hit within 15 km
  means the plant (or its colocated captive power) is bright enough in TROPOMI to register globally.
  This row is in the <code>data/beirle_match_audit_grade.csv</code> join shipped with the bench.</p>
</section>"""

    # EnMAP block
    enmap_block = ""
    if scenes:
        cf_count = sum(1 for s in scenes if s["cloud_cover"] < 1)
        top = scenes[:5]
        top_html = "".join(
            f'<li><code>{html.escape(s["datetime"])}</code> · cloud cover {s["cloud_cover"]:.0f}% · '
            f'<code class="muted">{html.escape(s["scene_id"][:50])}…</code></li>'
            for s in top
        )
        enmap_block = f"""
<section>
  <h2><span class="h2-num">05</span> Hyperspectral coverage</h2>
  <p>{len(scenes)} EnMAP L2A scene{'s' if len(scenes) != 1 else ''} index this plant ({cf_count} with &lt;1% cloud cover).
  Source: <a href="https://geoservice.dlr.de/eoc/ogc/stac/v1" target="_blank" rel="noopener">DLR EOC STAC</a>.
  Following <a href="https://iopscience.iop.org/article/10.1088/1748-9326/adc0b1" target="_blank" rel="noopener">Borger et al. (2025)</a>,
  these scenes can yield direct CO₂ and NO₂ plume retrievals at ~30 m spatial resolution.</p>
  <p class="muted">Lowest cloud cover scenes (showing top 5):</p>
  <ul class="scene-list">{top_html}</ul>
  <p class="muted small">Downloads require a free DLR EOWEB account
  (see <a href="https://github.com/abgnydn/iz/blob/master/outreach/enmap_access_howto.md" target="_blank" rel="noopener">enmap_access_howto.md</a>).</p>
</section>"""

    # Sector / route line
    sector_label = sector
    if fac.get("is_bfbof"):
        sector_label += " (BF/BOF)"
    elif fac.get("is_eaf"):
        sector_label += " (EAF)"
    elif fac.get("is_dri_eaf"):
        sector_label += " (DRI-EAF)"

    # Provenance badge text
    PROVENANCE_DESC = {
        "direct": "Per-plant Scope 1 directly disclosed by operator.",
        "allocated": "Allocated from operator group Scope 1 by a disclosed physical share (clinker tonnage / crude steel tonnage).",
        "derived": "Derived from a published intensity × disclosed activity, or company-group EF × plant capacity.",
        "disputed": "Operator-published number that materially conflicts with other public evidence; flagged for review.",
        "": "",
    }
    prov_desc = PROVENANCE_DESC.get(provenance, "")

    ASSURANCE_DESC = {
        "iso14064": "ISO 14064-1 verified",
        "tsrs_assured": "TSRS independent assurance",
        "operator_audited": "operator-audited financial-grade",
        "derived": "derived",
        "disputed": "disputed",
        "": "",
    }
    assur = ASSURANCE_DESC.get(assurance, assurance)

    # JSON-LD structured data: schema.org Dataset for Google rich results.
    # Operators searching "{plant} CO2 emissions" should see the audit-grade Scope 1
    # surfaced in the search snippet, with the source PDF cited.
    jsonld_vars = []
    if truth:
        jsonld_vars.append({
            "@type": "PropertyValue",
            "name": f"CO2 emissions (Scope 1, {truth_year})",
            "value": int(round(truth)),
            "unitText": "tCO2 per year",
            "description": f"Audit-grade per-facility Scope 1, {provenance}, {assurance}. Source: {truth_src[:200]}",
        })
    if formula_pred:
        jsonld_vars.append({
            "@type": "PropertyValue",
            "name": "cf-corrected formula prediction (leave-one-plant-out)",
            "value": int(round(formula_pred)),
            "unitText": "tCO2 per year",
            "description": "Closed-form capacity × route-EF × cf, with the route emission-factor derived only from the other audit-grade plants (leave-one-plant-out). +82.3% log-MAE reduction vs EU default across 19 validatable plants.",
        })
    if eu_default:
        jsonld_vars.append({
            "@type": "PropertyValue",
            "name": "EU CBAM default",
            "value": int(round(eu_default)),
            "unitText": "tCO2 per year",
            "description": "EU CBAM Article 4(3) default value: nameplate capacity × sector default emission factor.",
        })
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"{plant or fid} CO2 emissions ({truth_year or '2024-25'})",
        "alternateName": [plant, company, f"{company} {plant}"],
        "description": f"Audit-grade Scope 1, cf-corrected formula prediction (leave-one-plant-out), EU CBAM default, and full source citations for {plant}, {city}, Türkiye. Industry: {sector}.",
        "url": f"{SITE_URL}/bench/{fid}/",
        "identifier": fid,
        "license": "https://www.apache.org/licenses/LICENSE-2.0",
        "creator": {
            "@type": "Person",
            "name": "Ahmet Barış Günaydın",
            "email": "hi@barisgunaydin.com",
            "url": "https://barisgunaydin.com",
        },
        "publisher": {"@type": "Organization", "name": "TR-MRV-Bench", "url": SITE_URL},
        "isAccessibleForFree": True,
        "keywords": ["CBAM", "Scope 1", "CO2 emissions", "Turkey", sector, company, plant],
        "spatialCoverage": {
            "@type": "Place",
            "name": f"{plant}, {city}, Türkiye",
            "geo": {"@type": "GeoCoordinates", "addressCountry": "TR"},
        },
        "variableMeasured": jsonld_vars,
        "citation": truth_src,
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{SITE_URL}/bench/facilities.json"},
            {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{SITE_URL}/bench/tr_bench_v0.csv"},
        ],
    }
    jsonld_script = json.dumps(jsonld, ensure_ascii=False, separators=(",", ":"))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(plant or fid)} · {html.escape(company)} · iz · TR-MRV-Bench</title>
<meta name="description" content="iz · TR-MRV-Bench page for {html.escape(plant or fid)}{(', ' + html.escape(company)) if company else ''}. Audit-grade Scope 1, cf-corrected formula prediction (leave-one-plant-out), EU CBAM default, source citations.">
<meta name="theme-color" content="#2d5a4c">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="canonical" href="{SITE_URL}/bench/{fid}/">
<meta property="og:type" content="article">
<meta property="og:site_name" content="iz · TR-MRV-Bench">
<meta property="og:title" content="{html.escape(plant or fid)} · {html.escape(company)}">
<meta property="og:description" content="Audit-grade Scope 1 + cf-corrected formula prediction + EU CBAM default. Source PDFs cited.">
<meta property="og:url" content="{SITE_URL}/bench/{fid}/">
<meta property="og:image" content="{SITE_URL}/bench/{fid}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE_URL}/bench/{fid}/og.png">
<script type="application/ld+json">{jsonld_script}</script>
<link rel="stylesheet" href="/assets/style.css">
<style>
.metric {{ font-family: var(--mono); font-size: 17px; margin: 6px 0; }}
.ci-line {{ font-family: var(--sans); font-size: 14px; color: var(--muted); margin: 8px 0 0; }}
.crumbs {{ font-family: var(--sans); font-size: 13px; color: var(--muted); margin: 12px 0; }}
.crumbs a {{ border-bottom: none; }}
.fact-grid {{ display: grid; grid-template-columns: 180px 1fr; gap: 8px 18px; font-family: var(--sans); font-size: 14px; margin: 16px 0; }}
.fact-grid dt {{ color: var(--muted); }}
.fact-grid dd {{ margin: 0; }}
.row-pred {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px; margin: 16px 0; }}
.row-pred .card {{ background: var(--paper); border: 1px solid var(--rule); padding: 14px 16px; }}
.row-pred .card .label {{ font-family: var(--sans); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }}
.row-pred .card .value {{ font-family: var(--mono); font-size: 20px; font-weight: 600; margin: 4px 0 0; }}
.row-pred .card .delta {{ font-family: var(--sans); font-size: 13px; margin-top: 4px; }}
.row-pred .card.iz .value {{ color: var(--iz-deep); }}
.row-pred .card.eu .value {{ color: var(--eu); }}
.scene-list {{ font-family: var(--mono); font-size: 12px; padding-left: 18px; }}
.scene-list li {{ margin: 2px 0; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-family: var(--sans); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }}
.badge.disclosure {{ background: var(--iz); color: white; }}
.badge.disputed {{ background: var(--eu); color: white; }}
.small {{ font-size: 12px; }}
@media (max-width: 720px) {{
  .row-pred {{ grid-template-columns: 1fr; }}
  .fact-grid {{ grid-template-columns: 1fr; }}
  .fact-grid dt {{ font-size: 11px; text-transform: uppercase; letter-spacing: .04em; margin-top: 6px; }}
}}
</style>
</head>
<body>

<div class="topbar"><div class="wrap-wide row">
  <a href="/" class="logo">iz <em>· TR-MRV-Bench</em></a>
  <nav>
    <a href="/">Home</a>
    <a href="/bench/" class="active">Bench</a>
    <a href="/use/">Use</a>
    <a href="/about/">About</a>
  </nav>
</div></div>

<div class="wrap">

<p class="crumbs"><a href="/">iz</a> · <a href="/bench/">Bench</a> · {html.escape(plant or fid)}</p>

<header class="hero">
  <p class="kicker">{html.escape(sector_label)} · {html.escape(city)}{('  ·  ' + fmt_int(cap) + ' t/y') if cap else ''}</p>
  <h1>{title_h1}</h1>
  {f'<p class="subhead"><strong>{company_line}</strong></p>' if company_line else ''}
</header>

<section>
  <h2><span class="h2-num">01</span> Snapshot</h2>
  <div class="row-pred">
    <div class="card iz">
      <div class="label">Audit-grade Scope 1{f' · {truth_year}' if truth_year else ''}</div>
      <div class="value">{fmt_int(truth)}</div>
      <div class="delta muted">tCO₂ · <span class="badge {provenance}">{html.escape(provenance)}</span>{f' · {html.escape(assur)}' if assur else ''}</div>
    </div>
    <div class="card iz">
      <div class="label">cf-corrected formula (leave-one-plant-out)</div>
      <div class="value">{fmt_int(formula_pred) if formula_pred else '—'}</div>
      <div class="delta">{('<span class="muted">' + fmt_pct(delta_formula) + ' vs. truth</span>') if delta_formula is not None else ('<span class="muted">single-plant route — not independently validatable</span>' if formula_validatable is False else '<span class="muted">not in audit-grade set</span>')}</div>
    </div>
    <div class="card eu">
      <div class="label">EU CBAM default</div>
      <div class="value">{fmt_int(eu_default)}</div>
      <div class="delta">{('<span class="muted">' + fmt_pct(delta_eu) + ' vs. truth</span>') if delta_eu is not None else ''}</div>
    </div>
  </div>
  {ci_line}
  <p style="margin-top:14px;"><a href="audit-summary/" style="display:inline-block;padding:8px 14px;background:var(--iz);color:white;border:none;border-bottom:none;font-family:var(--sans);font-size:13px;font-weight:600;">Open printable audit summary →</a>
  <span class="muted" style="font-family:var(--sans);font-size:12px;margin-left:10px;">One-page PDF you can hand to a verifier.</span></p>
</section>

<section>
  <h2><span class="h2-num">02</span> Facility data</h2>
  <dl class="fact-grid">
    <dt>Company</dt><dd>{html.escape(company)}</dd>
    <dt>Plant</dt><dd>{html.escape(plant)}</dd>
    <dt>Sector</dt><dd>{html.escape(sector_label)}</dd>
    <dt>City</dt><dd>{html.escape(city)}</dd>
    <dt>Capacity</dt><dd>{fmt_int(cap)} t/y</dd>
    <dt>Label source</dt><dd><span class="badge {label_source}">{html.escape(label_source)}</span></dd>
    <dt>Provenance</dt><dd>{html.escape(prov_desc)}</dd>
    <dt>Headline method</dt><dd>cf-corrected formula (capacity × route-EF × cf), evaluated leave-one-plant-out. +82.3% log-MAE reduction vs EU default across the 19 validatable plants.</dd>
  </dl>
</section>

<section>
  <h2><span class="h2-num">03</span> Source citation</h2>
  <p>{html.escape(truth_src)}</p>
  {f'<p>{pdf_links}</p>' if pdf_links else ''}
  {f'<p class="muted small">{html.escape(notes)}</p>' if notes else ''}
</section>
{beirle_block}
{enmap_block}

<section>
  <h2><span class="h2-num">06</span> Verify / correct</h2>
  <p>If you're an operator or analyst with a more recent disclosure than what's shown above:</p>
  <ul>
    <li>Open a pull request adding a row to <code>data/tr_facility_known_emissions.csv</code>
        (<a href="https://github.com/abgnydn/iz/blob/master/data/tr_facility_known_emissions.csv" target="_blank" rel="noopener">source</a>).</li>
    <li>Or email <a href="mailto:hi@barisgunaydin.com?subject=iz%20bench%20correction%3A%20{html.escape(plant)}">hi@barisgunaydin.com</a> with the source PDF.</li>
    <li>Or use the <a href="/bench/#claim">claim-your-facility form</a> on the bench page.</li>
  </ul>
  <p class="muted small">Corrections that include a verifiable public source land within 24 hours.
  All data is Apache-2.0 licensed; methodology at <a href="https://iz-b0n.pages.dev/paper/" target="_blank" rel="noopener">iz-b0n.pages.dev/paper</a>.</p>
</section>

<footer class="footer">
  <p>iz · TR-MRV-Bench v0.1 · per-facility page generated by <code>bin/build_facility_pages.py</code> from
  <code>site/bench/facilities.json</code>. The bench is open source and Apache-2.0 licensed.</p>
</footer>

</div>
</body>
</html>
"""


def render_audit_summary(fac: dict, beirle: dict | None,
                         conformal: dict | None) -> str:
    """One-page audit summary an operator hands to their EU-accredited verifier.

    Designed to print to a single A4 page. No images, no marketing.
    Pure typography + factual claims + source citation + verifier checklist.
    """
    def s(key: str, default: str = "") -> str:
        v = fac.get(key)
        return default if v is None else str(v)

    fid = fac["id"]
    company = s("company")
    plant = s("plant")
    sector = s("sector")
    city = s("city")
    cap = fac.get("capacity")
    truth = fac.get("truth")
    truth_year = fac.get("truth_year")
    truth_src = s("truth_src")
    provenance = s("provenance")
    assurance = s("assurance")
    label_source = s("label_source")
    eu_default = fac.get("eu_default")
    formula_pred = fac.get("formula_pred")
    formula_validatable = fac.get("formula_validatable")

    ci_text = ""
    if conformal:
        lo = conformal.get("ci_lo")
        hi = conformal.get("ci_hi")
        lo_s = conformal.get("ci_lo_stratum")
        hi_s = conformal.get("ci_hi_stratum")
        stratum = conformal.get("stratum", "")
        if lo is not None and hi is not None:
            ci_text = (f"95% conformal prediction interval (global, n=21 calibration): "
                       f"{fmt_int(lo)} – {fmt_int(hi)} tCO₂.")
        if lo is not None and hi is not None and lo_s and hi_s and stratum and (hi_s - lo_s < hi - lo):
            ci_text += (f" Restricted to {stratum} stratum: "
                        f"{fmt_int(lo_s)} – {fmt_int(hi_s)} tCO₂ (subject to small-n undercoverage).")

    delta_eu_str = ""
    if eu_default and truth:
        d = (eu_default - truth) / truth * 100
        delta_eu_str = f" (EU default overstates by {d:+.0f}%)"

    delta_formula_str = ""
    if formula_pred and truth:
        d = (formula_pred - truth) / truth * 100
        delta_formula_str = f" (formula within {d:+.1f}% of audit)"

    beirle_text = ""
    if beirle:
        beirle_text = (f"Independent satellite cross-check (Beirle et al. 2023, ESSD): "
                       f"colocated TROPOMI NOx source within {beirle['distance_km']:.1f} km, "
                       f"flux {beirle['nox_kgs']:.3f} ± {beirle['nox_err_kgs']:.3f} kg NOx/s.")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Audit summary · {html.escape(plant or fid)} · iz</title>
<style>
@page {{ size: A4; margin: 18mm 16mm; }}
body {{ font-family: Georgia, "Times New Roman", serif; font-size: 10.5pt; line-height: 1.45; color: #14181d; max-width: 178mm; margin: 0 auto; padding: 12mm 0; }}
h1 {{ font-size: 16pt; margin: 0 0 2mm; }}
h2 {{ font-size: 11pt; margin: 5mm 0 2mm; text-transform: uppercase; letter-spacing: 0.06em; border-bottom: 0.5pt solid #888; padding-bottom: 1mm; }}
.head {{ display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1pt solid #14181d; padding-bottom: 3mm; margin-bottom: 4mm; }}
.head .id {{ font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 9pt; color: #555; }}
.kv {{ display: grid; grid-template-columns: 50mm 1fr; gap: 1mm 4mm; }}
.kv dt {{ font-weight: bold; }}
.kv dd {{ margin: 0; }}
.figures {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; margin: 3mm 0; padding: 3mm 4mm; border: 0.5pt solid #888; }}
.figures .col .label {{ font-family: -apple-system, sans-serif; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.04em; color: #555; }}
.figures .col .value {{ font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 13pt; font-weight: 700; }}
.figures .col .delta {{ font-family: -apple-system, sans-serif; font-size: 8pt; color: #555; }}
.cite {{ font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 8.5pt; background: #f5f0e6; padding: 2mm 3mm; border-left: 2pt solid #2d5a4c; margin: 2mm 0; }}
.checklist {{ font-size: 10pt; line-height: 1.6; }}
.checklist li {{ margin: 1mm 0; }}
.footer {{ position: fixed; bottom: 8mm; left: 0; right: 0; text-align: center; font-family: -apple-system, sans-serif; font-size: 7.5pt; color: #777; }}
@media screen {{
  body {{ background: #f4ede2; padding: 20mm 24mm; max-width: 210mm; margin: 12mm auto; box-shadow: 0 0 24px rgba(0,0,0,0.08); background: white; }}
  .print-hint {{ position: fixed; top: 12px; right: 12px; font-family: -apple-system, sans-serif; font-size: 12px; background: #2d5a4c; color: white; padding: 8px 14px; border-radius: 3px; }}
}}
@media print {{ .print-hint {{ display: none; }} }}
</style>
</head>
<body>

<div class="print-hint">Print this page (⌘P / Ctrl+P) → save as PDF for your verifier.</div>

<div class="head">
  <div>
    <h1>{html.escape(plant or fid)}</h1>
    <div>{html.escape(company)} · {html.escape(sector)} · {html.escape(city)}</div>
  </div>
  <div class="id">iz · TR-MRV-Bench v0.1<br>{html.escape(fid)}<br>Issued: {truth_year or '—'}</div>
</div>

<h2>1 · Facility identity</h2>
<dl class="kv">
  <dt>Company / operator</dt><dd>{html.escape(company)}</dd>
  <dt>Plant name</dt><dd>{html.escape(plant)}</dd>
  <dt>Sector (CBAM scope)</dt><dd>{html.escape(sector)}</dd>
  <dt>Location</dt><dd>{html.escape(city)}, Türkiye</dd>
  <dt>Nameplate capacity</dt><dd>{fmt_int(cap)} t/y</dd>
</dl>

<h2>2 · Emission figures (tCO₂)</h2>
<div class="figures">
  <div class="col">
    <div class="label">Audit-grade Scope 1{f' · {truth_year}' if truth_year else ''}</div>
    <div class="value">{fmt_int(truth)}</div>
    <div class="delta">{html.escape(label_source)} · {html.escape(provenance)}{f' · {html.escape(assurance)}' if assurance else ''}</div>
  </div>
  <div class="col">
    <div class="label">cf-corrected formula (leave-one-plant-out)</div>
    <div class="value">{fmt_int(formula_pred) if formula_pred else '—'}</div>
    <div class="delta">{('cap × route-EF × cf' + delta_formula_str) if formula_pred else ('single-plant route — not independently validatable' if formula_validatable is False else 'not in audit-grade set')}</div>
  </div>
  <div class="col">
    <div class="label">EU CBAM default value</div>
    <div class="value">{fmt_int(eu_default)}</div>
    <div class="delta">{html.escape(delta_eu_str.strip()) if delta_eu_str else ''}</div>
  </div>
</div>
{f'<p style="margin:2mm 0;font-family: -apple-system, sans-serif; font-size:9pt;">{ci_text}</p>' if ci_text else ''}

<h2>3 · Source citation for audit-grade Scope 1</h2>
<div class="cite">{html.escape(truth_src)}</div>
{f'<p style="font-size:9pt;color:#555;margin:1mm 0;">{html.escape(s("notes"))}</p>' if s("notes") else ''}

<h2>4 · Methodology (cf-corrected formula)</h2>
<p style="font-size: 9.5pt;">The headline method is a closed-form physics baseline: Scope 1 ≈ nameplate capacity × route emission-factor × capacity factor,
using only operator-published numbers. It is evaluated <strong>leave-one-plant-out</strong>: each plant's route emission-factor
is derived only from the <em>other</em> audit-grade plants in its route, so no plant contributes to its own prediction.
Headline: <strong>+82.3% log-MAE reduction vs the EU CBAM default</strong> across the 19 validatable plants (of 21 audit-grade;
two single-plant routes — N₂O-controlled and blender fertilizer — cannot be independently validated and are excluded).
External validity: the same formula on 372 EUTL-verified EU cement installations gives a median ratio ≈1.0 vs the EU default's ≈2.5×.
An optional in-browser WebGPU model (iz) is shipped as a demo only; it does not beat this formula at current data scale.
{beirle_text}</p>

<h2>5 · Verifier checklist</h2>
<ol class="checklist">
  <li>☐ Confirm Scope 1 line item in the cited source matches the value above (tCO₂ basis; not CO₂-equivalent if different).</li>
  <li>☐ Verify operator's verification statement (ISO 14064-1 / TSRS / financial audit) attached to the source.</li>
  <li>☐ Cross-check capacity against latest published cement / steel / aluminum / fertilizer association registry.</li>
  <li>☐ If using the formula prediction as input to a CBAM Article 4(2) actual-emission declaration: it is
      a model estimate, not a measurement. Verifier must independently support the underlying activity data.</li>
  <li>☐ Confirm the conformal prediction interval covers the operator's claimed Scope 1.</li>
</ol>

<h2>6 · License and citation</h2>
<p style="font-size:8.5pt;">
TR-MRV-Bench v0 is Apache-2.0 licensed. The benchmark, methodology, and per-facility data are public at
<code>github.com/abgnydn/iz</code> and <code>iz-b0n.pages.dev</code>.
Cite: Günaydın (2026), "TR-MRV-Bench: a public per-facility emissions benchmark for Turkish CBAM-scope
industry, with a physics baseline that beats the EU CBAM default by +82.3% (leave-one-plant-out, n=19)."
</p>

<div class="footer">iz · TR-MRV-Bench v0.1 · <code>{html.escape(fid)}</code> · audit summary printed from
iz-b0n.pages.dev/bench/{html.escape(fid)}/audit-summary/ · Apache-2.0 · hi@barisgunaydin.com</div>

</body>
</html>
"""


def main() -> int:
    facs = json.loads(FAC_JSON.read_text())
    beirle = load_beirle()
    enmap = load_enmap()
    conformal = load_conformal()

    print(f"Generating {len(facs)} facility pages...")
    print(f"  Beirle hits (≤15 km): {len(beirle)}")
    print(f"  EnMAP-indexed:        {len(enmap)}")
    print(f"  Conformal CI rows:    {len(conformal)}")

    new_urls = []
    for fac in facs:
        fid = fac["id"]
        outdir = OUT_DIR / fid
        outdir.mkdir(parents=True, exist_ok=True)
        page = render_page(
            fac,
            beirle.get(fid),
            enmap.get(fid, []),
            conformal.get(fid),
        )
        (outdir / "index.html").write_text(page)
        # Audit summary one-pager for verifiers (print-stylesheet)
        summary_dir = outdir / "audit-summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        summary = render_audit_summary(fac, beirle.get(fid), conformal.get(fid))
        (summary_dir / "index.html").write_text(summary)
        new_urls.append(f"{SITE_URL}/bench/{fid}/")

    # Update sitemap
    if SITEMAP.exists():
        smap = SITEMAP.read_text()
        # Append per-facility URLs if not already present
        added = 0
        if "/bench/akcansa-buyukcekmece/" not in smap:
            entries = "\n".join(
                f'  <url><loc>{u}</loc><changefreq>weekly</changefreq></url>'
                for u in new_urls
            )
            smap = smap.replace("</urlset>", entries + "\n</urlset>")
            SITEMAP.write_text(smap)
            added = len(new_urls)
        print(f"  Sitemap entries added: {added}")

    print(f"\nWrote {len(facs)} pages under site/bench/{{id}}/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
