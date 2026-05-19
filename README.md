# iz

**Karbon izi.** Satellite + AI emissions verification for Turkish industrial exporters facing the EU's CBAM carbon tax.

## What this is

Starting **January 2026**, the EU charges Turkish steel, cement, aluminum, and fertilizer exporters **€70–100 per ton of embedded CO₂**. A mid-size cement plant pays ~€80/t — more than the cement itself costs. A mid-size steel mill exporting to the EU pays **~€58M/year**. Total TR industry exposure: **€138M in 2027 → €2.5B/year by 2032**.

Factories can lower the bill by **proving their actual emissions are below the EU's punitive default values**. To prove it they need MRV (Measurement, Reporting, Verification) software in a format the EU will accept. Nobody sells this in Turkey yet.

**iz is that vendor.**

## The product (v0)

A web app where a factory uploads production records + energy bills + plant GPS. iz:

1. Pulls **Sentinel-5P** satellite imagery over the plant (free, ESA Copernicus).
2. Pulls **EPIAS** grid-emissions data for the plant's region.
3. Runs an **AI emissions estimator** that infers actual CO₂ from imagery + production + grid mix.
4. Cross-checks vs. the factory's self-reported numbers.
5. Outputs a **CBAM-compliant XML report** in the EU's required schema.

Replaces a €500k / 6-month consultancy engagement with €30–80k / 2-week SaaS.

## Money shape

| Tier | Product | Price | Path to scale |
|------|---------|-------|---------------|
| **1** | One-shot CBAM report | €30–80k / facility / yr | 20 customers → €600k–1.6M |
| **2** | Continuous MRV subscription (forced by TR-ETS 2026) | €50–150k / facility / yr | 50 customers → €3–7M ARR |
| **3** | Carbon credit origination on verified abatement | 10–20% of credit value | 9-figure exit shape (cf. Pachama) |

## Why now

- **CBAM bites Jan 2026** — exporters are panicking *this quarter*.
- **TR-ETS pilot 2026** — Turkish factories also forced into a domestic carbon market.
- **EPIAS** runs the carbon market (energy regulator), **not SPK** — no securities-license headache.
- Global MRV players (Pachama just sold to Carbon Direct; Climate TRACE is a free non-profit) don't have Turkish sales or factory access.
- **12–18 month land-grab window** before pricing commoditizes.

## Why us

- Satellite-data + AI inference + fast compute is the technical core. That's our stack.
- Local: Turkish-language sales, factory visits, EPIAS relationships.
- Zero financial-regulator exposure — we're a vendor, not a market participant.

## Status

**2026-05-19** — Project init. No code yet. First task is a single-plant Sentinel-5P spike to validate the satellite-to-emissions estimator. See `CLAUDE.md` for current step.
