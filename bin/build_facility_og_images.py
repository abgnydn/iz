"""
Per-facility Open Graph images: 1200×630 PNG cards rendered by Playwright.

When operators share /bench/{id}/ on LinkedIn / X / Slack / WhatsApp the
preview card needs to be specific to that plant, not the generic iz og.png.

Each card shows:
 - company + plant + sector + city (top)
 - three figures: audit-grade Scope 1 · iz-1 prediction · EU CBAM default
 - one-line provenance + delta vs truth
 - iz brand footer

Output: site/bench/{id}/og.png

Run after bin/build_facility_pages.py. Needs a local HTTP server up on
:8771 serving the repo root (auto-spawned by this script).
"""
from __future__ import annotations
import asyncio
import http.server
import json
import socketserver
import threading
from pathlib import Path

from playwright.async_api import async_playwright

REPO = Path(__file__).resolve().parent.parent
FAC_JSON = REPO / "site" / "bench" / "facilities.json"
OUT_BASE = REPO / "site" / "bench"
PORT = 8771


def fmt_int(x):
    if x is None:
        return "—"
    return f"{int(round(x)):,}"


def fmt_pct(x):
    return f"{x:+.0f}%" if abs(x) >= 1 else f"{x:+.1f}%"


def render_card_html(fac: dict) -> str:
    plant = fac.get("plant") or fac["id"]
    company = fac.get("company") or ""
    sector = fac.get("sector") or ""
    city = fac.get("city") or ""
    truth = fac.get("truth")
    truth_year = fac.get("truth_year")
    eu_default = fac.get("eu_default")
    pred_median = fac.get("pred_median")
    label_source = fac.get("label_source") or ""

    delta_eu = (eu_default - truth) / truth * 100 if (eu_default and truth) else None
    delta_iz = (pred_median - truth) / truth * 100 if (pred_median and truth) else None

    truth_card = ""
    if truth:
        truth_card = f"""
        <div class="card iz">
          <div class="lab">Audit-grade Scope 1{f' · {truth_year}' if truth_year else ''}</div>
          <div class="val">{fmt_int(truth)}</div>
          <div class="sub">tCO₂ · {label_source}</div>
        </div>"""
    pred_card = ""
    if pred_median:
        pred_card = f"""
        <div class="card iz2">
          <div class="lab">iz-1 prediction</div>
          <div class="val">{fmt_int(pred_median)}</div>
          <div class="sub">{fmt_pct(delta_iz) + " vs truth" if delta_iz is not None else "held-out"}</div>
        </div>"""
    eu_card = ""
    if eu_default:
        eu_card = f"""
        <div class="card eu">
          <div class="lab">EU CBAM default</div>
          <div class="val">{fmt_int(eu_default)}</div>
          <div class="sub">{(fmt_pct(delta_eu) + " vs truth") if delta_eu is not None else ''}</div>
        </div>"""

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Source+Serif+4:wght@400;700&display=swap');
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ width: 1200px; height: 630px; background: #f4ede2; color: #14181d;
       font-family: 'Source Serif 4', Georgia, serif; padding: 56px 64px; display: flex; flex-direction: column; }}
.head .kick {{ font-family: 'Inter', sans-serif; font-size: 18px; letter-spacing: 0.08em; text-transform: uppercase; color: #2d5a4c; font-weight: 600; }}
.head h1 {{ font-size: 60px; line-height: 1.08; font-weight: 700; margin-top: 8px; max-width: 1080px; }}
.head .co {{ font-family: 'Inter', sans-serif; font-size: 22px; color: #6e6862; margin-top: 12px; }}
.cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; margin-top: 42px; flex: 1; align-items: stretch; }}
.card {{ background: #fbf7ee; border: 1.5px solid #d8cfbe; padding: 22px 24px; display: flex; flex-direction: column; justify-content: space-between; }}
.card .lab {{ font-family: 'Inter', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; color: #6e6862; font-weight: 600; }}
.card .val {{ font-family: 'Inter', sans-serif; font-size: 50px; font-weight: 800; margin-top: 8px; line-height: 1; }}
.card .sub {{ font-family: 'Inter', sans-serif; font-size: 16px; color: #6e6862; margin-top: 12px; }}
.card.iz {{ border-color: #2d5a4c; border-width: 3px; }}
.card.iz .val {{ color: #1e3f33; }}
.card.iz2 .val {{ color: #2d5a4c; }}
.card.eu .val {{ color: #b85c3f; }}
.foot {{ display: flex; justify-content: space-between; align-items: center; margin-top: 32px; padding-top: 22px; border-top: 1px solid #d8cfbe; font-family: 'Inter', sans-serif; font-size: 18px; color: #6e6862; }}
.foot .brand {{ font-weight: 700; color: #2d5a4c; font-size: 22px; }}
.foot .brand em {{ font-style: normal; color: #6e6862; font-weight: 400; font-size: 16px; margin-left: 6px; }}
</style></head>
<body>
  <div class="head">
    <p class="kick">{sector} · {city} · Türkiye</p>
    <h1>{plant}</h1>
    <p class="co">{company}</p>
  </div>
  <div class="cards">{truth_card}{pred_card}{eu_card}</div>
  <div class="foot">
    <div class="brand">iz <em>· TR-MRV-Bench · open under Apache-2.0</em></div>
    <div>iz-b0n.pages.dev/bench/{fac['id']}/</div>
  </div>
</body></html>"""


def serve(stop_event: threading.Event) -> None:
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", PORT), handler) as httpd:
        httpd.timeout = 0.5
        while not stop_event.is_set():
            httpd.handle_request()


async def main() -> None:
    facs = json.loads(FAC_JSON.read_text())
    print(f"Generating {len(facs)} OG cards (1200×630)…")

    # Write rendering HTML files into a tmp dir served by HTTP
    tmp_dir = REPO / ".og_tmp"
    tmp_dir.mkdir(exist_ok=True)
    for fac in facs:
        (tmp_dir / f"{fac['id']}.html").write_text(render_card_html(fac))

    # Spawn a small static server scoped to repo root
    import os
    os.chdir(REPO)
    stop = threading.Event()
    t = threading.Thread(target=serve, args=(stop,), daemon=True)
    t.start()
    await asyncio.sleep(0.5)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for i, fac in enumerate(facs):
            page = await browser.new_page(viewport={"width": 1200, "height": 630})
            await page.goto(f"http://127.0.0.1:{PORT}/.og_tmp/{fac['id']}.html",
                            wait_until="networkidle")
            out_path = OUT_BASE / fac["id"] / "og.png"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(out_path), full_page=False,
                                  clip={"x": 0, "y": 0, "width": 1200, "height": 630})
            await page.close()
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(facs)}")
        await browser.close()

    stop.set()

    # Clean up tmp HTML files (keep them for debugging only if env set)
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"Wrote {len(facs)} OG cards under site/bench/{{id}}/og.png")


if __name__ == "__main__":
    asyncio.run(main())
