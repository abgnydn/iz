"""Screenshot the paper preview HTML for quick visual verification."""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

REPO = Path(__file__).resolve().parent.parent
URL = "http://127.0.0.1:8770/marketing/paper_preview_v0.html"
OUT = REPO / "reports" / "paper_preview_v0.png"


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1100, "height": 900}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(OUT), full_page=True)
        await browser.close()
        print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
