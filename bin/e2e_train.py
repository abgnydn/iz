"""
Headless E2E: load train.html, click Train, capture logs + final metrics.

Runs Chromium with WebGPU enabled (Apple GPU on this Mac). Mirrors what a user
would do manually — wait for the button to enable, click it, scrape the status
log + metric cards + predictions table.
"""

from __future__ import annotations

import asyncio
import sys

from playwright.async_api import async_playwright

URL = "http://localhost:8765/train.html"
TIMEOUT_MS = 5 * 60 * 1000  # 5 minutes wall clock for training


async def main() -> int:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--enable-unsafe-webgpu",
                "--enable-features=Vulkan,UseSkiaRenderer",
                "--use-angle=metal",
                "--disable-vulkan-fallback-to-gl-for-testing",
            ],
        )
        ctx = await browser.new_context()
        page = await ctx.new_page()

        console_lines: list[str] = []
        page.on("console", lambda msg: console_lines.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda exc: console_lines.append(f"[pageerror] {exc}"))

        print(f"→ loading {URL}")
        await page.goto(URL, wait_until="networkidle")

        # Wait for WebGPU init + bench load to enable the Train button.
        print("→ waiting for Train button to enable…")
        await page.wait_for_function(
            "() => !document.querySelector('#train-btn').disabled",
            timeout=60_000,
        )
        print("→ Train button ready, status:", await page.locator("#status").inner_text())

        # Force smaller config for faster e2e signal
        await page.fill("#epochs", "120")
        await page.fill("#lr", "0.02")
        await page.fill("#rank", "32")
        await page.fill("#batch", "8")

        print("→ clicking Train")
        await page.click("#train-btn")

        # Wait until button re-enables (training finished).
        await page.wait_for_function(
            "() => !document.querySelector('#train-btn').disabled",
            timeout=TIMEOUT_MS,
        )

        train_loss = await page.locator("#train-loss").inner_text()
        val_mae = await page.locator("#val-mae").inner_text()
        step = await page.locator("#step").inner_text()
        status = await page.locator("#status").inner_text()

        # Pull predictions table rows.
        rows = await page.locator("#preds-body tr").all()
        pred_rows = []
        for r in rows:
            cells = await r.locator("td").all_inner_texts()
            pred_rows.append(cells)

        print()
        print("=" * 68)
        print(f"  train loss : {train_loss}")
        print(f"  val MAE    : {val_mae}")
        print(f"  step       : {step}")
        print("=" * 68)
        print()
        print("STATUS TAIL:")
        for line in status.splitlines()[-12:]:
            print(f"  {line}")
        print()
        print(f"TEST PREDICTIONS ({len(pred_rows)} rows):")
        # Parse numeric columns once to compute baselines.
        import math, re
        def num(s: str) -> float:
            return float(re.sub(r"[^0-9.\-]", "", s) or 0)
        by_src: dict[str, list[tuple[float, float, float]]] = {}
        for cells in pred_rows[:12]:
            if len(cells) >= 8:
                fac, scope, src, truth, pred, ratio, eu, vs_eu = cells[:8]
                print(f"  {fac[:24]:24s} {scope:10s} {src:13s} truth={truth:>13s}  pred={pred:>13s}  r={ratio:>6s}  EU={eu:>13s}  Δ={vs_eu}")
                t, p, e = num(truth), num(pred), num(eu)
                if t > 0 and p > 0 and e > 0:
                    by_src.setdefault(src.strip(), []).append(
                        (abs(math.log(p) - math.log(t)), abs(math.log(e) - math.log(t)), t)
                    )
            elif len(cells) >= 6:
                fac, scope, src, truth, pred, ratio = cells[:6]
                print(f"  {fac[:24]:24s} {scope:10s} {src:13s} truth={truth:>13s}  pred={pred:>13s}  r={ratio}")
        if by_src:
            print()
            print("=" * 76)
            print(f"  Per-plant log-MAE   {'iz-1':>8s}  {'EU default':>10s}  {'reduction':>10s}  n")
            print("=" * 76)
            for src, trips in by_src.items():
                mm = sum(t[0] for t in trips) / len(trips)
                em = sum(t[1] for t in trips) / len(trips)
                red = (1 - mm/em) * 100 if em > 0 else 0
                print(f"  {src:18s}  {mm:8.3f}  {em:10.3f}  {red:9.1f}%  {len(trips)}")
            all_trips = [t for v in by_src.values() for t in v]
            mm = sum(t[0] for t in all_trips) / len(all_trips)
            em = sum(t[1] for t in all_trips) / len(all_trips)
            print(f"  {'overall':18s}  {mm:8.3f}  {em:10.3f}  {(1-mm/em)*100:9.1f}%  {len(all_trips)}")
            print("=" * 76)

        if console_lines:
            print()
            print(f"CONSOLE ({len(console_lines)} lines):")
            for line in console_lines[-20:]:
                print(f"  {line}")

        await browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
