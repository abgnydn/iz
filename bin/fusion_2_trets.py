"""
Fusion #2 — TR-ETS pilot allocation modeled from disclosure data.

Per the July 2025 draft regulation, the TR-ETS pilot (2026-2027) covers
installations emitting >50,000 tCO₂/yr in cement, steel, aluminum, fertilizer
(and ceramics, chemicals, refining — out of our scope). Allocation: 100% free,
based on historical Scope 1 baseline. Carbon-credit offset use is not allowed.

We use our 21 audit-grade Scope 1 disclosures (latest year, direct or anchored
to direct) as the BASELINE the Carbon Market Board is most likely to use when
issuing 2026 allowances. Output: per-facility predicted allowance, threshold
status (above/below 50kt), and per-operator group total.

Sources:
  - https://gmk.center/en/news/turkey-outlines-structure-of-future-emissions-trading-system/
  - https://icapcarbonaction.com/en/ets/turkish-emission-trading-system
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
KNOWN = REPO / "data" / "tr_facility_known_emissions.csv"
FACS = REPO / "data" / "tr_facilities.csv"
OUT_DIR = REPO / "reports" / "fusion"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / "trets_allocations.json"
OUT_MD = OUT_DIR / "trets_allocations.md"

THRESHOLD = 50_000   # tCO₂/yr — TR-ETS pilot coverage floor


def latest_scope1():
    df = pd.read_csv(KNOWN)
    pp = df[df["metric"] == "co2_scope1_t"].copy()
    pp["year"] = pd.to_numeric(pp["year"], errors="coerce")
    return pp.sort_values("year", ascending=False).drop_duplicates("id")


def main():
    facs = pd.read_csv(FACS)
    s1 = latest_scope1()

    rows = []
    for _, fac in facs.iterrows():
        d = s1[s1["id"] == fac["id"]]
        if d.empty:
            continue
        sc1 = float(d["value"].iloc[0])
        year = int(d["year"].iloc[0])
        prov = d["provenance"].iloc[0]
        rows.append({
            "facility_id": fac["id"],
            "company": fac["company"],
            "sector": fac["cbam_scope"],
            "year": year,
            "scope1_t": sc1,
            "provenance": prov,
            "above_50kt": sc1 >= THRESHOLD,
            "allowance_2026": sc1,   # under draft 100% free + historical baseline
        })

    out = sorted(rows, key=lambda r: -r["scope1_t"])

    above = [r for r in out if r["above_50kt"]]
    below = [r for r in out if not r["above_50kt"]]
    total_allowances = sum(r["allowance_2026"] for r in above)

    # Group by operator parent (company column)
    by_company = {}
    for r in above:
        by_company.setdefault(r["company"], []).append(r)

    OUT_JSON.write_text(json.dumps({
        "rules": {
            "threshold_t": THRESHOLD,
            "allocation_method": "100% free, historical baseline (draft pilot 2026-2027)",
            "covered_sectors": ["cement", "steel", "aluminum", "fertilizer"],
            "source": "TR-ETS draft regulation July 2025; ICAP factsheet",
        },
        "summary": {
            "n_facilities_audit_grade": len(out),
            "n_above_50kt": len(above),
            "n_below_50kt": len(below),
            "total_allowance_t_per_yr": total_allowances,
        },
        "per_facility": out,
    }, indent=2))

    # Markdown report
    md = [f"# TR-ETS Pilot 2026-2027 — Modeled Allocations"]
    md.append(f"\n*Source: TR-ETS draft regulation (July 2025) — 100% free allocation in pilot phase, baseline = historical Scope 1, threshold = {THRESHOLD:,} tCO₂/yr.*\n")
    md.append(f"## Summary\n")
    md.append(f"- {len(out)} TR-MRV-Bench facilities with audit-grade Scope 1\n- {len(above)} above the 50 kt threshold (in scope)\n- {len(below)} below the threshold (excluded from pilot)\n- **Total modeled allowances**: {total_allowances:,.0f} tCO₂/yr\n")
    md.append(f"## Per-operator (covered facilities only)\n")
    md.append("| Operator | Plants | Total allowance (tCO₂/yr) |\n|---|---|---|")
    for comp, plants in sorted(by_company.items(), key=lambda kv: -sum(p["scope1_t"] for p in kv[1])):
        tot = sum(p["scope1_t"] for p in plants)
        md.append(f"| {comp} | {len(plants)} | {tot:>15,.0f} |")
    md.append(f"\n## Per-facility detail\n")
    md.append("| Facility | Sector | Scope 1 (tCO₂/yr) | In scope? | Year | Provenance |\n|---|---|---|---|---|---|")
    for r in out:
        scope = "✓" if r["above_50kt"] else "—"
        md.append(f"| {r['facility_id']} | {r['sector']} | {r['scope1_t']:>14,.0f} | {scope} | {r['year']} | {r['provenance']} |")
    md.append(f"\n## Sub-threshold facilities (excluded from TR-ETS pilot)\n")
    for r in below:
        md.append(f"- **{r['facility_id']}** ({r['company']}, {r['sector']}): {r['scope1_t']:,.0f} tCO₂ — below the 50 kt threshold. {'(BAGFAŞ has N₂O catalyst; Gübretaş is blender-only — both sub-threshold by design)' if r['facility_id'] in ('bagfas-bandirma', 'gubretas-izmit') else ''}")

    OUT_MD.write_text("\n".join(md))

    print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print(f"wrote {OUT_MD.relative_to(REPO)}")
    print()
    print(f"Summary: {len(above)}/{len(out)} above 50kt; total modeled allowances {total_allowances:,.0f} tCO₂/yr")
    print()
    print("Top-10 facilities by modeled allowance:")
    for r in out[:10]:
        print(f"  {r['facility_id']:32s} {r['scope1_t']:>12,.0f} tCO₂  ({r['sector']})")


if __name__ == "__main__":
    main()
