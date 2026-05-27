"""Render site/assets/og.html → site/assets/og.png at 1200×630 via headless Chromium."""
from __future__ import annotations
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "site" / "assets" / "og.html"
OUT = REPO / "site" / "assets" / "og.png"


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1200, "height": 630}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto(SRC.as_uri(), wait_until="networkidle")
        await page.screenshot(path=str(OUT), clip={"x": 0, "y": 0, "width": 1200, "height": 630})
        await browser.close()
    print(f"wrote {OUT.relative_to(REPO)}  ({OUT.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
