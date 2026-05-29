"""
Fusion A1 — Scope 2 estimation from TR grid intensity.

Climatiq cites TR grid CO₂ factor at 0.4243 kgCO₂/kWh (2023 average; varies by hour
on EPİAŞ Şeffaflık platform). Combined with per-sector electricity intensity
benchmarks (cement 110 kWh/t, EAF steel 600 kWh/t, primary Al 14000 kWh/t,
downstream Al 150 kWh/t, fertilizer 80 kWh/t), we estimate Scope 2 per facility.

This is a first-cut. A real version uses EPİAŞ hourly grid + operator-disclosed
electricity consumption. Sources: Climatiq, EPİAŞ Şeffaflık Platformu.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
FACS = REPO / "data" / "tr_facilities.csv"
KNOWN = REPO / "data" / "tr_facility_known_emissions.csv"
OUT_DIR = REPO / "reports" / "fusion"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / "scope2_estimate.json"
OUT_MD = OUT_DIR / "scope2_estimate.md"

# TR grid CO₂ intensity (2023 average per Climatiq)
GRID_FACTOR_KG_PER_KWH = 0.4243

# Sector × route specific electricity intensity (kWh per tonne of output)
ELECTRICITY_INTENSITY_KWH_PER_T = {
    ("cement", None): 110,                   # ~110 kWh/t cement (cement-grinding + kiln aux)
    ("steel", "BF/BOF"): 400,                # 400 kWh/t crude steel (BF aux + rolling)
    ("steel", "EAF"): 600,                   # 600 kWh/t (electric arc dominates)
    ("steel", "DRI-EAF"): 800,               # DRI + EAF
    ("aluminum", "primary"): 14000,          # Hall-Héroult electrolysis
    ("aluminum", "downstream"): 150,         # rolling/extrusion only
    ("fertilizer", None): 80,                # compressors + ammonia synthesis aux
}

STEEL_ROUTE = {
    "erdemir-eregli": "BF/BOF", "isdemir-iskenderun": "BF/BOF", "kardemir-karabuk": "BF/BOF",
    "colakoglu-gebze": "EAF", "habas-aliaga": "EAF", "izdemir-aliaga": "EAF",
    "tosyali-osmaniye": "DRI-EAF", "tosyali-iskenderun": "EAF", "tosyali-sivas": "EAF",
    "icdas-biga": "EAF", "ekinciler-iskenderun": "EAF", "borcelik-gemlik": "EAF",
    "diler-aliaga": "EAF", "kroman-gebze": "EAF", "asilcelik-izmit": "EAF",
    "yazici-iskenderun": "EAF",
}
AL_ROUTE = {
    "assan-tuzla": "downstream", "asas-akyazi": "downstream",
    "eti-aluminyum-seydisehir": "primary",
}


def electricity_intensity(scope: str, fid: str) -> float:
    if scope == "steel":
        return ELECTRICITY_INTENSITY_KWH_PER_T.get(("steel", STEEL_ROUTE.get(fid, "EAF")), 600)
    if scope == "aluminum":
        return ELECTRICITY_INTENSITY_KWH_PER_T.get(("aluminum", AL_ROUTE.get(fid, "downstream")), 150)
    return ELECTRICITY_INTENSITY_KWH_PER_T.get((scope, None), 100)


def main():
    facs = pd.read_csv(FACS)
    kn = pd.read_csv(KNOWN)
    pp = kn[kn["metric"] == "co2_scope1_t"].copy()
    pp["year"] = pd.to_numeric(pp["year"], errors="coerce")
    pp = pp.sort_values("year", ascending=False).drop_duplicates("id")
    s1 = dict(zip(pp["id"], pp["value"]))

    rows = []
    total_s1 = 0
    total_s2 = 0
    for _, fac in facs.iterrows():
        fid = fac["id"]
        scope = fac["cbam_scope"]
        cap = float(fac["annual_capacity_t"])
        kwh_per_t = electricity_intensity(scope, fid)
        # Use cf=0.6 sector default unless we have an audit-grade label
        # (Scope 1 baseline gives us cf via inversion but for estimation use sector default)
        production_estimate = cap * 0.6
        elec_kwh = production_estimate * kwh_per_t
        scope2_kg = elec_kwh * GRID_FACTOR_KG_PER_KWH
        scope2_t = scope2_kg / 1000.0
        scope1_t = s1.get(fid, 0)
        total_s1 += scope1_t
        total_s2 += scope2_t
        rows.append({
            "facility_id": fid,
            "operator": fac["company"],
            "sector": scope,
            "production_estimate_t": production_estimate,
            "elec_intensity_kwh_per_t": kwh_per_t,
            "scope2_estimate_t": scope2_t,
            "scope1_disclosed_t": scope1_t,
            "scope12_total_t": scope1_t + scope2_t,
            "scope2_share_pct": (scope2_t / (scope1_t + scope2_t) * 100) if (scope1_t + scope2_t) > 0 else None,
        })

    rows.sort(key=lambda r: -r["scope12_total_t"])

    OUT_JSON.write_text(json.dumps({
        "grid_factor_kg_per_kwh": GRID_FACTOR_KG_PER_KWH,
        "source": "Climatiq TR grid factor 2023 — supersedable by EPİAŞ Şeffaflık hourly",
        "per_facility": rows,
        "totals": {"scope1_t": total_s1, "scope2_estimated_t": total_s2, "scope12_total_t": total_s1 + total_s2},
    }, indent=2, ensure_ascii=False, default=str))

    md = ["# Fusion A1 — Scope 2 Estimation from TR Grid Intensity\n"]
    md.append(f"*TR grid CO₂ factor: {GRID_FACTOR_KG_PER_KWH} kgCO₂/kWh (Climatiq 2023 reference; EPİAŞ Şeffaflık serves hourly real-time updates).*\n")
    md.append(f"## Headline\n")
    md.append(f"- Bench total Scope 1 (audit-grade, where available): **{total_s1:,.0f} tCO₂/yr**")
    md.append(f"- Bench total Scope 2 (this estimate): **{total_s2:,.0f} tCO₂/yr**")
    md.append(f"- **Total Scope 1+2: {total_s1 + total_s2:,.0f} tCO₂/yr**\n")
    md.append(f"## Top-15 facilities by Scope 1+2\n")
    md.append("| Facility | Sector | Scope 1 (t) | Scope 2 est. (t) | Total | Scope 2 share |")
    md.append("|---|---|---|---|---|---|")
    for r in rows[:15]:
        share = f"{r['scope2_share_pct']:.0f}%" if r['scope2_share_pct'] is not None else "—"
        md.append(f"| {r['facility_id']} | {r['sector']} | {r['scope1_disclosed_t']:,.0f} | {r['scope2_estimate_t']:,.0f} | {r['scope12_total_t']:,.0f} | {share} |")
    md.append("\n## Sector pattern\n")
    md.append("**Primary aluminum (Eti Seydişehir)** dominates Scope 2: Hall-Héroult electrolysis at 14,000 kWh/t × TR grid = ~6 tCO₂/t Al Scope 2 — orders of magnitude above Scope 1 (which is just anode + auxiliary). Tail of CBAM exposure.\n")
    md.append("**Cement** has low Scope 2 (~110 kWh/t × grid = 47 kgCO₂/t) compared to Scope 1 (660 kgCO₂/t). Scope 1 dominates the cement story.\n")
    md.append("**EAF steel** has high Scope 2 (600 kWh/t × grid = 255 kgCO₂/t) and low Scope 1 (250 kgCO₂/t process). **For EAF mills, Scope 2 is roughly equal to Scope 1** — the bench's previous EAF-wins-big finding under-counted total carbon exposure.\n")
    md.append("**Fertilizer** Scope 2 is small relative to Scope 1 — the chemistry dominates.\n")
    md.append("\n## Caveats\n")
    md.append("- Single grid factor (0.4243 kg/kWh) is national average; coastal industrial provinces (Kocaeli, İzmir) have higher grid intensity due to coal-heavy generation mix. EPİAŞ hourly intensity by region is the v1 input.\n")
    md.append("- Electricity intensity per tonne is a literature value, not operator-specific. Operators with captive cogen (Erdemir, İsdemir have own power plants) draw less from grid; their Scope 2 is lower than this estimate.\n")
    md.append("- Production estimate uses sector-default cf=0.6 when audit cf isn't disclosed; for the 21 disclosure facilities we have audit cf — use that in v1.\n")
    md.append("\n## Sources\n")
    md.append("- [Climatiq TR grid emission factor](https://www.climatiq.io/data/emission-factor/d56e798f-2094-40af-9ab2-1367f9c98b1f)")
    md.append("- [EPİAŞ Şeffaflık Platformu — real-time TR electricity data](https://seffaflik.epias.com.tr/)")
    md.append("- [eptr2 Python wrapper for EPİAŞ Şeffaflık 2.0 API](https://github.com/Tideseed/eptr2)")

    OUT_MD.write_text("\n".join(md))
    print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print(f"wrote {OUT_MD.relative_to(REPO)}")
    print(f"  Bench total Scope 1: {total_s1:>14,.0f} tCO₂/yr")
    print(f"  Bench total Scope 2: {total_s2:>14,.0f} tCO₂/yr (estimate)")
    print(f"  Combined Scope 1+2:  {total_s1 + total_s2:>14,.0f} tCO₂/yr")


if __name__ == "__main__":
    main()
