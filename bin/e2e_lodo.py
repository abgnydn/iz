"""
Leave-one-disclosure-out evaluation.

For each facility with a per-plant Scope 1 disclosure label, force it into
test, re-export the bench (stratified split for the others), run training,
and capture the model's prediction for that single held-out plant. Aggregate
across all disclosure facilities to get N test points instead of 1.

Runs N_SEEDS per facility (default 3) and uses the median ratio. The whole
thing is ~7 facilities × 3 seeds × ~3s training = ~60s wall clock.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from statistics import median

import pandas as pd
from playwright.async_api import async_playwright

REPO = Path(__file__).resolve().parent.parent
KNOWN_CSV = REPO / "data" / "tr_facility_known_emissions.csv"
URL = "http://localhost:8765/train.html"
N_SEEDS = 3
EPOCHS = 120
LR = 0.02

PER_PLANT_METRICS = {"co2_scope1_t", "co2_scope12_total_t"}


def disclosure_facilities() -> list[tuple[str, float]]:
    """Latest-year per-plant disclosure for each facility."""
    kn = pd.read_csv(KNOWN_CSV)
    pp = kn[kn["metric"].isin(PER_PLANT_METRICS)].copy()
    pp["year"] = pd.to_numeric(pp["year"], errors="coerce")
    pp = pp.sort_values("year")
    out: dict[str, float] = {}
    for _, r in pp.iterrows():
        out[r["id"]] = float(r["value"])
    return sorted(out.items())


async def run_one_seed(playwright, facility_id: str, truth: float) -> dict:
    """Single training run with the bench preloaded; returns prediction for facility_id."""
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--enable-unsafe-webgpu", "--use-angle=metal"],
    )
    ctx = await browser.new_context()
    page = await ctx.new_page()
    await page.goto(URL, wait_until="networkidle")
    await page.wait_for_function("() => !document.querySelector('#train-btn').disabled", timeout=60_000)
    await page.fill("#epochs", str(EPOCHS))
    await page.fill("#lr", str(LR))
    await page.click("#train-btn")
    await page.wait_for_function(
        "() => !document.querySelector('#train-btn').disabled",
        timeout=5 * 60 * 1000,
    )
    rows = await page.locator("#preds-body tr").all()
    pred_for_holdout = None
    for r in rows:
        cells = await r.locator("td").all_inner_texts()
        if len(cells) < 6:
            continue
        if facility_id in cells[0]:  # "Company (facility_id)" — id is in the small tag
            t = float(re.sub(r"[^0-9.]", "", cells[3]) or 0)
            p = float(re.sub(r"[^0-9.]", "", cells[4]) or 0)
            eu = float(re.sub(r"[^0-9.]", "", cells[6]) or 0) if len(cells) > 6 else 0
            pred_for_holdout = (t, p, eu)
            break
    await browser.close()
    if pred_for_holdout is None:
        return {"facility_id": facility_id, "truth": truth, "pred": None}
    t, p, eu = pred_for_holdout
    return {"facility_id": facility_id, "truth": t, "pred": p, "eu_default": eu}


def export_bench_for_holdout(facility_id: str) -> None:
    env = {**os.environ, "IZ_HOLDOUT": facility_id}
    subprocess.run(
        ["uv", "run", "python", "bin/export_bench_browser.py"],
        cwd=str(REPO), env=env, check=True, capture_output=True,
    )


async def main() -> None:
    discs = disclosure_facilities()
    print(f"LODO eval over {len(discs)} disclosure facilities")
    print("=" * 80)

    all_runs: list[dict] = []
    async with async_playwright() as p:
        for fid, truth in discs:
            print(f"\n→ holdout = {fid}  truth = {truth:,.0f} tCO2")
            export_bench_for_holdout(fid)
            seeds_for_fid = []
            for seed in range(N_SEEDS):
                result = await run_one_seed(p, fid, truth)
                if result.get("pred") is None:
                    print(f"   seed {seed}: <facility not in test — skipping>")
                    continue
                seeds_for_fid.append(result)
                ratio = result["pred"] / max(result["truth"], 1)
                print(f"   seed {seed}: pred={result['pred']:>12,.0f}  ratio={ratio:.2f}×")
            if seeds_for_fid:
                preds = [s["pred"] for s in seeds_for_fid]
                med_pred = median(preds)
                t = seeds_for_fid[0]["truth"]
                eu = seeds_for_fid[0]["eu_default"]
                all_runs.append({
                    "facility_id": fid,
                    "truth": t,
                    "pred_median": med_pred,
                    "eu_default": eu,
                    "ratio_median": med_pred / max(t, 1),
                })

    # Reset bench export
    subprocess.run(["uv", "run", "python", "bin/export_bench_browser.py"], cwd=str(REPO), check=True, capture_output=True)

    print()
    print("=" * 80)
    print("  LODO disclosure-facility results (median over seeds)")
    print("=" * 80)
    print(f"  {'facility':30s} {'truth':>14s} {'pred (med)':>14s} {'ratio':>7s} {'EU default':>14s} {'Δ EU':>8s}")
    print("-" * 80)
    model_log_err = []
    eu_log_err = []
    for r in all_runs:
        t, p, eu = r["truth"], r["pred_median"], r["eu_default"]
        d_eu = (eu - p) / eu * 100 if eu else 0
        print(f"  {r['facility_id']:30s} {t:>14,.0f} {p:>14,.0f} {r['ratio_median']:>6.2f}× {eu:>14,.0f} {d_eu:>+7.0f}%")
        if t > 0 and p > 0 and eu > 0:
            model_log_err.append(abs(math.log(p) - math.log(t)))
            eu_log_err.append(abs(math.log(eu) - math.log(t)))
    print("-" * 80)
    if model_log_err and eu_log_err:
        mm = sum(model_log_err) / len(model_log_err)
        em = sum(eu_log_err) / len(eu_log_err)
        red = (1 - mm / em) * 100
        print(f"  log-MAE:  iz-1 {mm:.3f}    EU default {em:.3f}    reduction {red:.1f}%   n={len(model_log_err)}")
    print("=" * 80)

    with open(REPO / "reports" / "lodo_results.json", "w") as f:
        json.dump(all_runs, f, indent=2)
    print(f"\n→ wrote reports/lodo_results.json")


if __name__ == "__main__":
    asyncio.run(main())
