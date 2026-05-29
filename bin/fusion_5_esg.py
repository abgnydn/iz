"""
Fusion #5 — Public ESG rating coverage table.

Honest output: Sustainalytics + MSCI per-operator rating data is paywalled.
What IS public:
  - Sustainalytics page existence (URL slug confirms covered)
  - One-line summaries cached in Google snippets ("High Exposure", "Average
    Management") — these are pre-2024 cached fragments, not current
  - BIST Sustainability 25 index (XSD25) membership — LSEG-scored TR ESG proxy
  - BIST Sustainability Index (XUSRD) — broader ~80-stock TR ESG proxy
  - Operators' own disclosed ESG targets and methodologies

We tabulate what's publicly observable, flag the gaps, and recommend
subscription channels for the data we can't reach.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "reports" / "fusion"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / "esg_coverage.json"
OUT_MD = OUT_DIR / "esg_coverage.md"

# What's publicly observable per operator. Cross-referenced with:
#  - sustainalytics.com page slugs (existence ≠ free score access)
#  - Borsa Istanbul XSD25 membership (LSEG-scored ESG threshold ≥70)
#  - Press / IR mentions of ESG ratings, ISSB / TSRS compliance
ESG_COVERAGE = {
    "akcansa-buyukcekmece": {
        "operator": "Akçansa",
        "bist_ticker": "AKCNS",
        "sustainalytics_page": True,
        "bist_xsd25": False,   # not visible in top traded of XSD25
        "rating_visible": False,
        "notes": "Sustainalytics covered (page exists); rating data subscription-only. Parent SAHOL is in XSD25. Past Google snippet: 'High Exposure / Average Management'.",
    },
    "akcansa-canakkale":  {"operator":"Akçansa","bist_ticker":"AKCNS","sustainalytics_page":True,"bist_xsd25":False,"rating_visible":False,"notes":"Same parent as Büyükçekmece"},
    "akcansa-ladik":      {"operator":"Akçansa","bist_ticker":"AKCNS","sustainalytics_page":True,"bist_xsd25":False,"rating_visible":False,"notes":"Same parent"},
    "cimsa-mersin": {
        "operator":"Çimsa","bist_ticker":"CIMSA","sustainalytics_page":True,"bist_xsd25":True,"rating_visible":False,
        "notes":"In BIST Sustainability 25 — implies LSEG ESG score ≥70. Sustainalytics page slug exists.",
    },
    "erdemir-eregli": {
        "operator":"Erdemir","bist_ticker":"EREGL","sustainalytics_page":True,"bist_xsd25":False,"rating_visible":False,
        "notes":"Largest BIST steel; ISSB-aligned TSRS sustainability report; Tracenable data feed. Sustainalytics covered.",
    },
    "isdemir-iskenderun": {
        "operator":"İsdemir","bist_ticker":"ISDMR","sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,
        "notes":"Sub-entity of Erdemir Group; consolidated in EREGL ESG profile.",
    },
    "kardemir-karabuk": {
        "operator":"Kardemir","bist_ticker":"KRDMA/KRDMB/KRDMD","sustainalytics_page":True,"bist_xsd25":False,"rating_visible":True,
        "esg_snapshot":"Exposure: High; Management of ESG Material Risk: Average",
        "notes":"Sustainalytics page returns risk band in Google snippet (cached). 2024 TSRS sustainability report published.",
    },
    "nuh-hereke": {
        "operator":"Nuh Çimento","bist_ticker":"NUHCM","sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,
        "notes":"ISO 14064-1 verified 2024 disclosure. No public ESG rating found.",
    },
    "bursa-cimento": {
        "operator":"Bursa Çimento","bist_ticker":"BUCIM","sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,
        "notes":"2024 TSRS report ISO 14064-verified. Small-cap; ESG coverage thin.",
    },
    "afyon-cimento":   {"operator":"Afyon Çimento","bist_ticker":"AFYON","sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"Çimsa subsidiary; consolidated into CIMSA ESG profile"},
    "batisoke-soke":   {"operator":"Batısöke","bist_ticker":"BSOKE","sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"ISO 14064 verified disclosure; thin ESG coverage"},
    "goltas-isparta":  {"operator":"Göltaş","bist_ticker":"GOLTS","sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"TSRS disclosure; small-cap"},
    "oyak-bolu":       {"operator":"OYAK Çimento","bist_ticker":"OYAKC","sustainalytics_page":True,"bist_xsd25":True,"rating_visible":False,"notes":"Press: OYAK Çimento joined XSD25 with strong ESG performance (CemenTürk Dec 2024). 28.6% alt-fuel mix, 2× TR avg."},
    "oyak-unye":       {"operator":"OYAK Çimento","bist_ticker":"OYAKC","sustainalytics_page":True,"bist_xsd25":True,"rating_visible":False,"notes":"Same parent"},
    "oyak-mardin":     {"operator":"OYAK Çimento","bist_ticker":"OYAKC","sustainalytics_page":True,"bist_xsd25":True,"rating_visible":False,"notes":"Same parent"},
    "oyak-adana":      {"operator":"OYAK Çimento","bist_ticker":"OYAKC","sustainalytics_page":True,"bist_xsd25":True,"rating_visible":False,"notes":"Same parent"},
    "oyak-aslan":      {"operator":"OYAK Çimento","bist_ticker":"OYAKC","sustainalytics_page":True,"bist_xsd25":True,"rating_visible":False,"notes":"Same parent"},
    "colakoglu-gebze": {"operator":"Çolakoğlu","bist_ticker":None,"sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"Private; 2024 SR with 2030/2050 ESG targets. No public rating."},
    "habas-aliaga":    {"operator":"Habaş","bist_ticker":None,"sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"Private EAF; ISO 14064-1 verified; no public rating."},
    "izdemir-aliaga":  {"operator":"İzdemir","bist_ticker":None,"sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"Private; TSRS-compliant SR"},
    "assan-tuzla":     {"operator":"Assan Alüminyum","bist_ticker":None,"sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"Kibar Holding subsidiary; private"},
    "asas-akyazi":     {"operator":"Asaş","bist_ticker":None,"sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"Private"},
    "toros-mersin":    {"operator":"Toros Tarım","bist_ticker":"TKFEN","sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"Tekfen Holding (TKFEN) subsidiary; TSRS disclosed at group level"},
    "toros-samsun":    {"operator":"Toros Tarım","bist_ticker":"TKFEN","sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"Same parent"},
    "toros-ceyhan":    {"operator":"Toros Tarım","bist_ticker":"TKFEN","sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"Same parent"},
    "bagfas-bandirma": {"operator":"BAGFAŞ","bist_ticker":"BAGFS","sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"BIST-listed but small-cap; N₂O catalyst is implicit best-in-class ESG signal"},
    "gubretas-izmit":  {"operator":"Gübretaş","bist_ticker":"GUBRF","sustainalytics_page":False,"bist_xsd25":False,"rating_visible":False,"notes":"BIST-listed; blender-only operation"},
}


def main():
    n_total = len(ESG_COVERAGE)
    n_sustainalytics = sum(1 for v in ESG_COVERAGE.values() if v["sustainalytics_page"])
    n_xsd25 = sum(1 for v in ESG_COVERAGE.values() if v["bist_xsd25"])
    n_rated_visible = sum(1 for v in ESG_COVERAGE.values() if v.get("rating_visible"))
    n_private = sum(1 for v in ESG_COVERAGE.values() if v["bist_ticker"] is None)

    OUT_JSON.write_text(json.dumps({
        "summary": {
            "n_facilities": n_total,
            "n_sustainalytics_page_exists": n_sustainalytics,
            "n_in_bist_xsd25": n_xsd25,
            "n_public_rating_visible": n_rated_visible,
            "n_private_operators": n_private,
        },
        "per_facility": ESG_COVERAGE,
    }, indent=2, ensure_ascii=False))

    md = ["# Public ESG Coverage of TR-MRV-Bench Facilities\n"]
    md.append(f"*Verified 2026-05-29. Sustainalytics/MSCI specific scores require subscription; this table reports what's publicly observable.*\n")
    md.append(f"## Summary\n")
    md.append(f"- {n_total} bench facilities (across {len(set(v['operator'] for v in ESG_COVERAGE.values()))} operators)")
    md.append(f"- {n_sustainalytics} have a Sustainalytics page slug (covered but data paywalled)")
    md.append(f"- {n_xsd25} in BIST Sustainability 25 (LSEG ESG ≥70 threshold)")
    md.append(f"- {n_rated_visible} have a publicly-cached rating fragment")
    md.append(f"- {n_private} are private companies (no BIST ESG signal)")
    md.append(f"\n**Honest take:** of 5 fusion bets, this is the thinnest. Public ESG data for TR mid-caps is paywalled. The XSD25 membership signal is binary (in/out) and only 6/27 of our facilities' operators clear it. Operator-level ESG depth needs a Sustainalytics or MSCI subscription.\n")
    md.append(f"## Per-facility table\n")
    md.append(f"| Facility | Operator | BIST ticker | Sustainalytics page | XSD25 member | Public rating | Notes |")
    md.append(f"|---|---|---|---|---|---|---|")
    for fid, v in ESG_COVERAGE.items():
        sp = "✓" if v["sustainalytics_page"] else "—"
        xs = "✓" if v["bist_xsd25"] else "—"
        rv = "✓" if v.get("rating_visible") else "—"
        ticker = v["bist_ticker"] or "private"
        md.append(f"| {fid} | {v['operator']} | {ticker} | {sp} | {xs} | {rv} | {v['notes']} |")

    OUT_MD.write_text("\n".join(md))
    print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print(f"wrote {OUT_MD.relative_to(REPO)}")
    print()
    print(f"  facilities: {n_total} | Sustainalytics pages: {n_sustainalytics} | XSD25 members: {n_xsd25} | public ratings: {n_rated_visible} | private: {n_private}")


if __name__ == "__main__":
    main()
