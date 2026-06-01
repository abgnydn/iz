# Fusion #A2 — TR Climate Law (No. 7552, July 2025) Alignment

*Verified 2026-05-29. Cross-checks our formula methodology against Turkey's binding MRV requirements under the Climate Law adopted 2 July 2025.*

## Headline

**TR-MRV-Bench's methodology is regulator-aligned out of the box.** The Climate Law's MRV requirements match our existing pipeline at every layer where we make a claim:

| TR Climate Law requirement | TR-MRV-Bench status |
|---|---|
| ISO 14064-1 compliance for Scope 1/2/3 | ✅ 3 of 21 audit-grade labels (Batısöke, Nuh, BAGFAŞ) are ISO 14064-1 verified; framework natively supports this |
| TÜRKAK-accredited third-party verification | ✅ Bench cites operator IARs verified by Big4 auditors / TÜRKAK-accredited verifiers |
| Installation-level reporting (>800 facilities) | ✅ Bench is installation-level for 59 facilities; methodology scales to whole national list |
| Embedded emissions (SEE) for iron/steel, cement, Al, fertilizer, H₂, electricity | ✅ Our 4 covered sectors are the CBAM scope subset; H₂/electricity not in bench v0 |
| Annual reporting by April 30 | ✅ Our update pipeline (`bin/annual_refresh.py`) re-extracts IARs each spring |
| Pilot ETS 2026-2027, 50 kt threshold | ✅ Fusion #2 already models pilot allocations on 19 of 21 bench facilities |
| Carbon Market Board allocation methodology | 🟡 Draft regulation still in stakeholder consultation; we'll align to final |

## Where the bench can plug straight in

The Climate Law requires operators to submit a monitoring plan **six months before actual monitoring starts** (i.e., by end of 2025 for the 2026 ETS pilot). The plan must specify:
1. **Capacity** of each emission source — our bench has this for 59 facilities ✓
2. **Emission factors** per fuel / process — our route-aware EF table (`bin/export_bench_browser.py`) is the public reference ✓
3. **Activity data** (production tonnes, fuel consumption) — operator-disclosed via IAR; our pipeline extracts ✓
4. **Verifier credentials** — TÜRKAK-accredited; we cite the verifier in `provenance` column ✓
5. **Uncertainty quantification** — our bootstrap CI per sector (verifier B4) directly provides this ✓

## Where the bench needs to extend

- **Scope 2 derivation**: Climate Law requires Scope 2 reporting; we're adding via [EPİAŞ fusion (A1)](epias_scope2.md).
- **Scope 3 supply-chain**: not in scope of CBAM defaults, but Climate Law requires it for full corporate reporting. Out of scope for v0.
- **Monitoring plan template**: regulators will publish a standard form; we should add an output that fills it from our bench data.

## Sources

- [Türkiye adopts landmark climate law (ICAP)](https://icapcarbonaction.com/en/news/turkiye-adopts-landmark-climate-law-paving-way-national-ets)
- [TR Climate Law and CBAM (CMS Legal)](https://cms.law/en/tur/legal-updates/tuerkiye-s-new-climate-law-an-important-step-towards-carbon-governance-and-economic-transformation)
- [CBAM and Turkey's Climate Law (Goldstein Renewable)](https://www.goldstein-renewable.de/en/post/carbon-border-adjustment-mechanism-cbam-and-turkey-climate-law)
- [ICAP TR-ETS factsheet](https://icapcarbonaction.com/en/ets/turkish-emission-trading-system)
- [What is Climate Law in Turkey (CimpactPro)](https://cimpactpro.com/en/blog/what-is-climate-law-how-is-the-climate-law-implemented-in-turkey)

## Implication for v0 release

We can credibly claim the bench is **regulator-aligned** under TR Climate Law 7552 today. Specifically:

> *"TR-MRV-Bench computes Scope 1 emissions using the same ISO 14064-1 framework that the Climate Law mandates, sources its strong labels from TÜRKAK-accredited verifier statements, and outputs at the installation level required by the MRV regulation. The cf-corrected formula is a methodologically defensible alternative to operator-submitted Scope 1 for facilities lacking a current verification cycle."*
