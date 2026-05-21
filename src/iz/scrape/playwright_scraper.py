"""
Playwright-based scraper for JS-rendered corporate sustainability pages.

The static-HTML scraper (src/iz/scrape/disclosures.py) fails on Akçansa /
OYAK / Çimsa / Tosyalı because their sustainability landing pages render
PDF links in JavaScript after page load. This module uses headless Chromium
to wait for the dynamic content, then extracts every PDF link visible on
the page.

Run once: `uv run playwright install chromium` to download the browser.
"""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urljoin

log = logging.getLogger(__name__)

PDF_KEYWORDS = re.compile(
    r"(sustainab|sürdürül|cdp|esg|carbon|emiss|climate|iklim|gri|integrated|annual|"
    r"faaliyet|enviro|csr|raporu)",
    re.IGNORECASE,
)


async def _render_and_collect(url: str, *, wait_ms: int = 4000) -> list[dict]:
    from playwright.async_api import async_playwright

    out: list[dict] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
            ),
            locale="tr-TR",
        )
        page = await ctx.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            log.warning("  navigation failed: %s", e)
            await browser.close()
            return out
        await page.wait_for_timeout(wait_ms)

        # Pull every anchor on the rendered page.
        anchors = await page.eval_on_selector_all(
            "a",
            """els => els.map(a => ({
                href: a.href || '',
                text: (a.innerText || a.textContent || '').trim().slice(0, 200)
            }))""",
        )
        seen: set[str] = set()
        for a in anchors:
            href = a.get("href", "")
            text = a.get("text", "")
            if not href or href in seen:
                continue
            seen.add(href)
            if not (href.lower().endswith(".pdf") or ".pdf?" in href.lower()):
                continue
            if not PDF_KEYWORDS.search(f"{text} {href}"):
                continue
            out.append({"url": urljoin(url, href), "anchor_text": text})

        await browser.close()
    return out


def collect_pdf_links(url: str, *, wait_ms: int = 4000) -> list[dict]:
    """Synchronous wrapper. Returns [{url, anchor_text}, ...]."""
    return asyncio.run(_render_and_collect(url, wait_ms=wait_ms))
