"""
LLM-assisted structured emissions extraction from sustainability-report PDFs.

The regex text-grep approach in disclosures.py produces 1 real row per 5
noise rows. This module replaces it with a Claude call that takes a PDF's
text content and a JSON schema, returns a structured array of emissions
metrics with confidence + source-page citations.

Requires: ANTHROPIC_API_KEY env var. Cost: ~$0.01-0.05 per report.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

EXTRACTION_PROMPT = """\
You are extracting emissions and production data from a corporate sustainability
report for a Turkish industrial facility (CBAM-scope: cement, steel, aluminum, or
fertilizer). Return ONLY a JSON array of records. Each record:

  {{
    "year": <int>,                       # reporting year (4 digits)
    "metric": <str>,                     # one of: co2_scope1_t, co2_scope2_t,
                                         #   co2_scope3_t, co2_specific_t_per_t,
                                         #   cement_produced_t, clinker_produced_t,
                                         #   crude_steel_t, electricity_consumed_mwh,
                                         #   nox_emitted_t, sox_emitted_t,
                                         #   thermal_energy_intensity_mj_per_t,
                                         #   alternative_fuel_pct, clinker_factor_pct
    "value": <float>,                    # numeric value
    "unit": <str>,                       # e.g. "tCO2", "tCO2e", "t", "MWh", "%", "MJ/t"
    "confidence": "high" | "medium" | "low",  # high = table cell with clear label;
                                              # medium = inferred from narrative; low = ambiguous
    "source_quote": <str>,               # short verbatim quote from the report (≤120 chars)
    "scope": <str>                       # which plant or "group" if consolidated
  }}

Rules:
- DO NOT invent values. If the report does not state a metric, omit it.
- Prefer table cells over narrative numbers.
- For consolidated group reports (e.g. OYAK Çimento covering 5 plants),
  set scope="group" unless the data is broken out per-plant.
- Output a JSON array even if empty: [].
- No commentary, no markdown — JSON only.

Facility hint: company={company}, scope={cbam_scope}, plant={plant_name}.

The PDF text (truncated to most-relevant pages) follows.
==========
{pdf_text}
"""


def extract_with_llm(
    pdf_text: str,
    *,
    company: str,
    cbam_scope: str,
    plant_name: str,
    model: str = "claude-sonnet-4-6",
    max_chars: int = 50_000,
) -> list[dict[str, Any]]:
    """Send PDF text to Claude and parse a structured emissions array.
    Returns [] if API key is missing or the response is unparseable."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY not set; skipping LLM extraction")
        return []
    try:
        import anthropic
    except ImportError:
        log.warning("anthropic SDK not installed")
        return []

    text = pdf_text[:max_chars]
    prompt = EXTRACTION_PROMPT.format(
        company=company, cbam_scope=cbam_scope, plant_name=plant_name, pdf_text=text
    )
    client = anthropic.Anthropic(api_key=api_key)
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        log.warning("Anthropic API call failed: %s", e)
        return []

    raw = "".join(b.text for b in msg.content if hasattr(b, "text"))
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning("LLM returned non-JSON: %s", e)
        return []
    if not isinstance(parsed, list):
        return []
    return parsed


def extract_emissions_from_pdf(
    pdf_path: Path, *, company: str, cbam_scope: str, plant_name: str = "",
) -> list[dict[str, Any]]:
    """Read PDF text with pdfplumber, send to Claude, return structured rows."""
    import pdfplumber

    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_text = []
            for i, page in enumerate(pdf.pages, 1):
                t = page.extract_text() or ""
                if not t.strip():
                    continue
                pages_text.append(f"\n[page {i}]\n{t}")
            full_text = "\n".join(pages_text)
    except Exception as e:
        log.warning("pdfplumber failed on %s: %s", pdf_path.name, e)
        return []

    rows = extract_with_llm(
        full_text,
        company=company,
        cbam_scope=cbam_scope,
        plant_name=plant_name,
    )
    for r in rows:
        r["source_doc"] = pdf_path.name
    return rows
