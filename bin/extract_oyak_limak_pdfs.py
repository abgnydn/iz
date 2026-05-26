"""
Extract per-plant clinker / cement production + Scope 1 from OYAK 2023 and
Limak 2023 PDFs. We already have group totals (OYAK 7.71M tCO2 p30, Limak
7.14M tCO2 p89); we need per-plant allocation factors.

Strategy: scan all pages for lines containing both a plant name AND a number.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

REPO = Path(__file__).resolve().parent.parent
DISC = REPO / "data" / "disclosures"

OYAK_PLANTS = ["Bolu", "Ünye", "Mardin", "Adana", "Aslan", "Niğde", "Hatay",
               "Bartın", "Erkin", "Denizli", "Ergani", "Aşkale", "Modern"]
LIMAK_PLANTS = ["Ankara", "Şanlıurfa", "Kurtalan", "Trakya", "Ergani",
                "Derik", "Bitlis", "Kilis", "Gaziantep", "Balıkesir"]

NUM = r"[\d][\d.,\s]{0,12}"
SCOPE1_RE = re.compile(r"(scope\s*1|kapsam\s*1|direct emission)", re.IGNORECASE)
KLINKER_RE = re.compile(r"(klinker|clinker|çimento|cement)", re.IGNORECASE)


def scan(pdf_path: Path, plant_names: list[str], label: str) -> None:
    print(f"\n{'='*72}")
    print(f"  {label}: {pdf_path.name}  ({pdf_path.stat().st_size/1e6:.1f} MB)")
    print('='*72)
    plant_re = re.compile("(" + "|".join(plant_names) + ")", re.IGNORECASE)
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            txt = page.extract_text() or ""
            if not txt:
                continue
            for line in txt.splitlines():
                if plant_re.search(line) and re.search(NUM, line):
                    # Skip pure heading lines without context
                    if len(line.strip()) < 8:
                        continue
                    print(f"  p{i:3d} | {line.strip()[:200]}")


def main() -> None:
    oyak = sorted(DISC.glob("oyak*__2023*.pdf"))
    limak = sorted(DISC.glob("limak__2023*.pdf"))
    if oyak:
        scan(oyak[-1], OYAK_PLANTS, "OYAK 2023 IAR")
    if limak:
        scan(limak[-1], LIMAK_PLANTS, "Limak 2023 SR")


if __name__ == "__main__":
    main()
