"""
Emit a flat per-facility CSV at site/bench/tr_bench_v0.csv that operators
can grep, import to Excel, or feed into their CBAM filing prep.

Joins facilities + audit-grade disclosures + LODO predictions + EU default.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "site" / "bench" / "facilities.json"
OUT = REPO / "site" / "bench" / "tr_bench_v0.csv"


def main() -> None:
    rows = json.loads(SRC.read_text())

    fieldnames = [
        "id", "company", "plant", "sector", "city",
        "capacity_t_per_yr",
        "audit_grade_truth_tCO2", "truth_year", "provenance", "assurance",
        "formula_lopo_tCO2", "formula_lopo_ratio_vs_truth", "formula_validatable",
        "eu_cbam_default_tCO2",
        "saving_vs_eu_default_pct",
        "label_source", "truth_source_pdf", "notes",
    ]

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            truth = r.get("truth")
            pred = r.get("formula_pred")  # cf-corrected formula, leave-one-plant-out
            eu = r.get("eu_default")
            ratio = r.get("formula_ratio")
            saving_pct = (((eu - (truth or pred or 0)) / eu) * 100) if eu else None
            w.writerow({
                "id": r["id"],
                "company": r["company"],
                "plant": r["plant"],
                "sector": r["sector"],
                "city": r["city"],
                "capacity_t_per_yr": r["capacity"],
                "audit_grade_truth_tCO2": int(truth) if truth else "",
                "truth_year": r.get("truth_year") or "",
                "provenance": r.get("provenance") or "",
                "assurance": r.get("assurance") or "",
                "formula_lopo_tCO2": int(pred) if pred else "",
                "formula_lopo_ratio_vs_truth": f"{ratio:.3f}" if ratio else "",
                "formula_validatable": r.get("formula_validatable"),
                "eu_cbam_default_tCO2": int(eu) if eu else "",
                "saving_vs_eu_default_pct": f"{saving_pct:.1f}" if saving_pct is not None else "",
                "label_source": r.get("label_source") or "",
                "truth_source_pdf": r.get("truth_src") or "",
                "notes": r.get("notes") or "",
            })

    print(f"wrote {OUT.relative_to(REPO)}  ({OUT.stat().st_size:,} bytes, {len(rows)} rows)")


if __name__ == "__main__":
    main()
