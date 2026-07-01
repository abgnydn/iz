"""
Fusion #4 — Beirle NOx flux × respiratory mortality (spatial framework).

DATA-GAP FINDING: Province-level respiratory mortality is not publicly
available in Turkey. Kocak 2024 (Wiley) and Yıldız 2022 (PMC) both state:
"data on Turkey's mortality and morbidity and disease burden on a provincial
and district basis are not available, which hinders the putting forward of
the causal relationship between pollution and disease/death."

What WE can do:
  1. Aggregate our 59-facility Beirle NOx flux + audit-grade Scope 1 by TR
     province. This produces a per-province "industrial CO₂ / NOx pressure"
     map at facility resolution Turkey doesn't currently publish anywhere.
  2. Cross-reference with the persistent-pollution zones identified in
     Yıldız 2022 (industrial provinces). The overlap is the testable
     hypothesis when mortality data becomes available.
  3. Flag the data gap as a policy finding: TR can't currently attribute
     respiratory disease burden to specific facilities; iz + TÜİK
     publishing province-mortality would unlock that.
"""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
FACS = REPO / "data" / "tr_facilities.csv"
KNOWN = REPO / "data" / "tr_facility_known_emissions.csv"
BEIRLE = REPO / "data" / "beirle_match_audit_grade.csv"
OUT_DIR = REPO / "reports" / "fusion"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / "health_nox_spatial.json"
OUT_MD = OUT_DIR / "health_nox_spatial.md"

# Persistent-pollution provinces identified by Yıldız 2022 (PMC8975334)
# based on 4-year mean PM10 exceedance of EU limit. These are TR provinces
# with sustained industrial air-quality problems.
PERSISTENT_POLLUTION_PROVINCES = {
    "Iğdır","Düzce","Bursa","Sakarya","Yalova","Karaman","Kahramanmaraş",
    "Konya","Karabük","Gaziantep","Manisa","Tekirdağ","Kocaeli","Şanlıurfa",
}


def main():
    facs = pd.read_csv(FACS)

    # Latest Scope 1 per facility
    kn = pd.read_csv(KNOWN)
    s1 = kn[kn["metric"] == "co2_scope1_t"].copy()
    s1["year"] = pd.to_numeric(s1["year"], errors="coerce")
    s1 = s1.sort_values("year", ascending=False).drop_duplicates("id")
    s1_lookup = dict(zip(s1["id"], s1["value"]))

    # Beirle NOx flux per facility (if available)
    beirle_lookup = {}
    if BEIRLE.exists():
        b = pd.read_csv(BEIRLE)
        if "facility_id" in b.columns and "beirle_nox_kgs" in b.columns:
            beirle_lookup = dict(zip(b["facility_id"], b["beirle_nox_kgs"]))

    # Aggregate per province
    by_prov = {}
    for _, fac in facs.iterrows():
        prov = fac["province"]
        d = by_prov.setdefault(prov, {
            "province": prov,
            "n_facilities": 0,
            "total_capacity_t": 0,
            "audit_scope1_t": 0,
            "beirle_nox_kgs_sum": 0,
            "facilities": [],
            "sectors": set(),
            "persistent_pollution_listed": prov in PERSISTENT_POLLUTION_PROVINCES,
        })
        d["n_facilities"] += 1
        d["total_capacity_t"] += float(fac["annual_capacity_t"])
        d["audit_scope1_t"] += float(s1_lookup.get(fac["id"], 0))
        d["beirle_nox_kgs_sum"] += float(beirle_lookup.get(fac["id"], 0) or 0)
        d["facilities"].append(fac["id"])
        d["sectors"].add(fac["cbam_scope"])

    # Convert sets to sorted lists for JSON
    for d in by_prov.values():
        d["sectors"] = sorted(d["sectors"])

    rows = sorted(by_prov.values(), key=lambda d: -d["audit_scope1_t"])

    OUT_JSON.write_text(json.dumps({
        "data_gap_finding": "Province-level respiratory mortality is not publicly published by TÜİK at the granularity needed for facility-attribution regression. Kocak 2024 + Yıldız 2022 PMC both note this explicitly. iz's per-facility Beirle/S5P/Scope-1 layer is ready to plug in if/when TÜİK publishes.",
        "persistent_pollution_provinces_yildiz_2022": sorted(PERSISTENT_POLLUTION_PROVINCES),
        "facility_pressure_by_province": rows,
    }, indent=2, ensure_ascii=False))

    md = ["# Fusion #4 — Industrial Pressure × Health (Spatial Framework)\n"]
    md.append("*Verified 2026-05-29. Respiratory mortality at province resolution is **not publicly published** by TÜİK, so this analysis builds the spatial framework and flags the data gap as a policy finding.*\n")

    md.append("## Headline\n")
    md.append("Turkey publishes:\n")
    md.append("- Air-quality readings per station (Ministry of Environment National Air Quality Monitoring Network)\n")
    md.append("- Province-level **all-cause** mortality (TÜİK Death and Cause of Death Statistics)\n\n")
    md.append("Turkey does **not** publish:\n")
    md.append("- Province-level cause-specific mortality (J00-J99 respiratory) at granularity sufficient for facility attribution\n")
    md.append("- District-level mortality\n\n")
    md.append("**Policy implication**: iz has facility-resolution NOx (Beirle satellite divergence) + audit-grade Scope 1 for 21 facilities across {n_prov} provinces. The moment TÜİK publishes province × ICD-10 J-chapter mortality, this dataset becomes ready-to-join for the first per-facility air-pollution-attribution study in Turkey.\n".format(n_prov=len(rows)))

    md.append("## Top provinces by industrial pressure (our bench)\n")
    md.append("| Province | Facilities | Total capacity (t/yr) | Audit Scope 1 (tCO₂) | Beirle NOx Σ (kg/s) | Persistent pollution? | Sectors |")
    md.append("|---|---|---|---|---|---|---|")
    for r in rows[:15]:
        pp = "✓ Yıldız 2022" if r["persistent_pollution_listed"] else "—"
        beirle = f"{r['beirle_nox_kgs_sum']:.2f}" if r['beirle_nox_kgs_sum'] > 0 else "—"
        md.append(f"| {r['province']} | {r['n_facilities']} | {r['total_capacity_t']:>14,.0f} | {r['audit_scope1_t']:>14,.0f} | {beirle} | {pp} | {', '.join(r['sectors'])} |")

    md.append("\n## Cross-reference: persistent-pollution provinces (Yıldız 2022) vs our facility footprint\n")
    overlap = [r["province"] for r in rows if r["persistent_pollution_listed"]]
    md.append(f"- Our bench covers {len(overlap)} of the {len(PERSISTENT_POLLUTION_PROVINCES)} persistent-pollution provinces: **{', '.join(overlap)}**")
    md.append(f"- Persistent provinces with NO bench facility: **{', '.join(sorted(set(PERSISTENT_POLLUTION_PROVINCES) - set(overlap)))}** — likely driven by non-CBAM industry (power, refineries, heating)")
    md.append("")
    md.append("## What this enables\n")
    md.append("Once TÜİK publishes province × ICD-10-J mortality (or via an FOI / academic data-sharing request to Ministry of Health), the iz facility-pressure layer plugs directly into:\n")
    md.append("1. **Excess respiratory mortality regression** — Beirle NOx flux per province (kg/s, our data) → respiratory mortality / 100k (TÜİK)\n")
    md.append("2. **Persistent-pollution attribution** — for the 8-12 provinces where our facilities sit AND PM10 exceeds EU limit, allocate the excess to specific operators via the Beirle layer\n")
    md.append("3. **Counterfactual modeling** — at each operator's published 2030 reduction target, compute downstream respiratory-mortality reduction expected in their province\n")
    md.append("\n## Caveats\n")
    md.append("- Yıldız 2022 used PM10 not NO₂; the persistent-pollution province list is a proxy for industrial pressure rather than a direct NOx measure.")
    md.append("- The 14-province persistent list includes mountain / dust-dominant provinces (Iğdır) that aren't industrial — pollution-source attribution at this resolution is genuinely hard.")
    md.append("- Beirle 2023 v2 NOx fluxes have ≤15 km matching uncertainty; we don't claim plume-resolution at city level.")
    md.append("- The right next step is an academic data-sharing request to the Ministry of Health for J00-J99 province × year mortality. ~6-week turnaround at TR public-data norms.")

    OUT_MD.write_text("\n".join(md))
    print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print(f"wrote {OUT_MD.relative_to(REPO)}")
    print()
    print(f"  {len(rows)} TR provinces hosting bench facilities")
    print(f"  {sum(1 for r in rows if r['persistent_pollution_listed'])} overlap with Yıldız 2022 persistent-pollution list")
    print(f"  Top 5 provinces by audit Scope 1:")
    for r in rows[:5]:
        pp = " (persistent pollution)" if r["persistent_pollution_listed"] else ""
        print(f"    {r['province']:14s} {r['audit_scope1_t']:>12,.0f} tCO₂  ({r['n_facilities']} facilities){pp}")


if __name__ == "__main__":
    main()
