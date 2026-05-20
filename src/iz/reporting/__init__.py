"""CBAM XML rendering + XSD validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from lxml import etree

TEMPLATE_DIR = Path(__file__).resolve().parent
XSD_DIR = Path(__file__).resolve().parents[3] / "data" / "cbam_schema"


def render(context: dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tmpl = env.get_template("cbam_template.xml")
    return tmpl.render(**context)


def validate(xml_text: str, xsd_path: Path | None = None) -> tuple[bool, list[str]]:
    """Validate XML against the CBAM QReport XSD. Returns (ok, errors)."""
    xsd_path = xsd_path or (XSD_DIR / "QReport_ver23.00.xsd")
    with open(xsd_path, "rb") as f:
        schema_doc = etree.parse(f)
    schema = etree.XMLSchema(schema_doc)
    doc = etree.fromstring(xml_text.encode("utf-8"))
    if schema.validate(doc):
        return True, []
    errs = [f"{e.line}:{e.column} — {e.message}" for e in schema.error_log]
    return False, errs
