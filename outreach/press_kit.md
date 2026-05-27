# Press kit — TR-MRV-Bench / iz

For journalists writing about CBAM, Turkish industry, climate compliance, or
public-good data infrastructure.

---

## One-line description

A public per-facility emissions benchmark for Turkish CBAM-scope industry, built by one
person, released under Apache-2.0, with a closed-form formula that beats the EU CBAM
default by 85% on 21 audit-grade Turkish plants.

## Headline numbers

- **+85.3%** log-MAE reduction vs the EU CBAM default value (closed-form formula, n=21 LODO)
- **+83.6%** for the 2-layer LoRA-shaped neural network (statistically tied with the formula)
- **95% data-bootstrap CI: [+73.5%, +90.4%]** (5000 resamples of n=21)
- **~€2 billion/year** in CBAM payments that could stay in Turkey instead of going to the
  EU treasury if every TR CBAM-scope operator used real per-facility data (assumptions:
  CBAM at €85/tCO₂, realistic sector EU-export shares — see methodology)
- **21 audit-grade Turkish facilities** across all four CBAM scopes (cement, steel, aluminum,
  fertilizer), with operator-published source PDFs cited per row
- **Open under Apache-2.0**, no SaaS, no fundraising, no NDA

## Who built it

[Ahmet Barış Günaydın](https://barisgunaydin.com), independent. One person, a few weekends.
Contact: hi@barisgunaydin.com.

## Why this matters for journalists

1. **It's a counter-example to the "climate compliance is a black box" narrative.** The math
   is one line. Every input is publicly downloadable from operator annual reports. Anyone
   can verify by clicking a button on the live site.

2. **The €2B/year number is a story.** That's roughly what the EU CBAM treasury would
   over-collect from Turkish exporters at full enforcement if every TR operator pays the
   default instead of filing accurate data. The mid-tier operators (Afyon, Göltaş, Bursa,
   Toros, BAGFAŞ, Batısöke, Gübretaş) are the ones at most risk because EU-accredited
   verifier audits run €30-100k per facility per year.

3. **It's a Turkey-specific contribution.** Most CBAM coverage is EU-side ("how will CBAM
   raise revenue", "what will it cost steel?"). This is the rare TR-side public analysis.

4. **Open infrastructure done right.** No SaaS pitch, no behind-paywall pivot, no fundraising
   round. Apache-2.0 license, source-cited dataset, browser-native trainer. Cite-it-and-go.

5. **The audit story is sharper than expected.** Climate TRACE under-reports 4 of 5
   audit-matched TR facilities (mean bias −17%). The EU default over-charges by 2-10× on
   most plants but is correct within ±15% on BF/BOF integrated mills. The story isn't
   "default bad" — it's "default works for big-integrated, fails for everyone else."

## Suggested story angles

**Headline-grade:**
- "Turkish entrepreneur publishes free CBAM benchmark, says €2bn/yr at stake"
- "One-person open-source project beats EU's default emissions formula by 85% across Turkish industry"
- "Climate TRACE under-reports Turkish industrial emissions, audit-data shows"

**Long-form:**
- The mid-tier Turkish operator's CBAM dilemma: pay punitive default or pay €50k+ for verifier audit
- Why Turkey publishes more granular per-facility ESG data than most of Europe (TSRS rollout 2024-25)
- The economics of "open infrastructure for compliance": when public-good data outcompetes SaaS
- Climate TRACE's TR-specific bias: methodological lessons from a 5-facility audit cross-check

## Key quotes (use as-is or paraphrase)

- "If every Turkish CBAM-scope operator used real per-facility data instead of paying the EU
  default, our estimate is roughly €2 billion per year stays in Turkey instead of going to the
  EU treasury. That's the entire point. Charging for the bench would defeat it." — Ahmet Barış
  Günaydın

- "The EU default is calibrated as a stick: pay this or pay your verifier. For mid-tier
  operators the stick exceeds the savings, so they eat it. The system depends on operators
  absorbing the audit cost, which means smaller plants overpay disproportionately. The default
  becomes a regressive industry-size penalty instead of an emissions-pricing instrument."

- "The math is one line: capacity × emission-factor × capacity-factor. Every input is
  operator-published. If the EU adopted this as a 'shadow default', they'd close 78% of the
  per-plant accuracy gap for cement without any operator MRV submission."

- "Climate TRACE is the closest thing to an open per-facility CO₂ inventory globally, and we
  use 8 of their TR rows. But on the 5 facilities where we have both their estimate and an
  audit-grade truth, they under-report 4 of 5 — Erdemir −29%, İsdemir −22%, Kardemir −23%,
  Nuh −23%. We don't claim CT is wrong globally; we observe that on TR they consistently
  underestimate by ~20%. Likely because TR integrated mills run captive coal power their
  global methodology may not catch."

## Visual assets

All Apache-2.0, free to reproduce with attribution.

- **OG share card** ([assets/og.png](https://iz-b0n.pages.dev/assets/og.png), 1200×630 PNG):
  the formula + −85.3% callout + brand mark
- **Headline figure** ([reports/fig_iz1_vs_eu_lodo.svg](https://iz-b0n.pages.dev/assets/fig_iz1_vs_eu_lodo.svg)):
  per-plant bars showing iz vs EU default vs audited truth across all 21 LODO test facilities
- **TR facility map** ([assets/facility_map.svg](https://iz-b0n.pages.dev/assets/facility_map.svg)):
  all 59 facilities sized by capacity, colored by sector, ink-outlined for the 21 audit-grade ones
- **Per-facility CSV** ([bench/tr_bench_v0.csv](https://iz-b0n.pages.dev/bench/tr_bench_v0.csv)):
  flat data for any chart you want to build

## Methodology notes for fact-checkers

- The €2B/year estimate uses CBAM at €85/tCO₂ (ETS-linked, current price band) and
  realistic sector EU-export shares (cement 10%, steel 25%, aluminum 30%, fertilizer 5%).
  These are conservative; the theoretical maximum (100% to EU) is ~€5.7B/year. See
  `bin/compute_savings.py` in the repo and the about page §4.
- CBAM is currently in transitional reporting only (2023-2025); full enforcement begins
  2026 and ramps to 2034. The €2B/year is the steady-state.
- Some TR operators (Erdemir, Akçansa) almost certainly already file verified data through
  their existing MRV; for them iz adds no value. The €2B/year is primarily a mid-tier
  opportunity.
- The bench has 6 of 21 "allocated" labels (group total split by clinker or capacity share);
  these are flagged explicitly. Group totals are audit-grade; per-plant splits are arithmetic.
- BF/BOF integrated steel (n=3 in TR) is structurally hard: the EU default 1.9 t/t is
  already within ±15% of TR audited reality. iz adds value in cement, EAF, downstream
  aluminum, and N₂O-controlled fertilizer; not in big integrated steel.

## Counter-narratives to be ready for

If a critic argues...
- "n=21 is too small": ✓ acknowledged in §6 limitations; the 95% data-bootstrap CI [+73.5%, +90.4%] is the honest publication number.
- "you can't actually save Turkey €2B": ✓ assumes 100% adoption + 100% pass-through; realistic 3-year adoption is 30-50% of mid-tier plants → €200-500M/yr captured. Still meaningful.
- "operators already file accurate data through verifiers": ✓ big operators do (Erdemir, Akçansa). The mid-tier currently eats the default because the verifier fee exceeds perceived savings. The bench changes the audit cost calculus, not whether operators "need" the data.
- "Apache-2.0 means a Big4 can fork and resell": ✓ true, but Big4 sales effort vs operator trust is the real moat, not the license. License keeps the data accessible to small operators.
- "Climate TRACE pushback": ✓ we're n=5 and don't claim global. The pattern is consistent enough to be worth investigating — a methodology note for CT, not an attack.

## Repository / live site

- **Live site:** [iz-b0n.pages.dev](https://iz-b0n.pages.dev)
- **GitHub:** [github.com/abgnydn/iz](https://github.com/abgnydn/iz)
- **Citation file:** [CITATION.cff](https://github.com/abgnydn/iz/blob/master/CITATION.cff)
- **arXiv preprint draft:** [paper/iz_v0.md](https://github.com/abgnydn/iz/blob/master/paper/iz_v0.md)

## Contact

Ahmet Barış Günaydın
hi@barisgunaydin.com
barisgunaydin.com

Available for: methodology questions, fact-checking, virtual interviews (TR/EN),
quotes by email. **No exclusivity**, no embargo. Use as you find useful.
