"""
Extract Scope 1 emissions and per-plant numbers from the Akçansa 2025 IAR PDF.
Looks for: 'Scope 1', 'Kapsam 1', 'Direct emissions', 'Büyükçekmece', 'Çanakkale',
'Ladik' near tCO2 / ton numbers.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

REPO = Path(__file__).resolve().parent.parent
PDF = sorted((REPO / "data" / "disclosures").glob("akcansa__2025*.pdf"))[-1]

KEYWORDS = [
    r"Scope\s*1", r"Kapsam\s*1", r"Direct\s+emissions",
    r"Büyükçekmece", r"Çanakkale", r"Ladik",
    r"tCO\s*2\s*e?", r"tCO₂", r"ton CO2", r"emission\w* intensity",
    r"specific\s+emission",
]
KW_RE = re.compile("|".join(KEYWORDS), re.IGNORECASE)
NUM_RE = re.compile(r"([\d.,]{3,15})\s*(t?CO\s*2\s*e?|ton(?:nes)?(?:\s+of\s+CO2)?|kg\s*CO2|tCO₂e?)?", re.IGNORECASE)


def main() -> None:
    print(f"opening {PDF.name}  ({PDF.stat().st_size/1e6:.1f} MB)")
    with pdfplumber.open(PDF) as pdf:
        n = len(pdf.pages)
        print(f"  {n} pages")
        hits = []
        for i, page in enumerate(pdf.pages, 1):
            txt = page.extract_text() or ""
            if not KW_RE.search(txt):
                continue
            # Take lines containing scope-1 hints
            for line in txt.splitlines():
                if re.search(r"Scope\s*1|Kapsam\s*1|Direct emission", line, re.IGNORECASE):
                    hits.append((i, line.strip()))
                elif re.search(r"Büyükçekmece|Çanakkale|Ladik", line) and re.search(r"\d", line):
                    hits.append((i, line.strip()))
    print()
    print(f"=== {len(hits)} candidate lines ===")
    for page, line in hits[:80]:
        print(f"  p{page:3d} | {line[:160]}")


if __name__ == "__main__":
    main()
