"""Resume ablation matrix — skip variants whose lodo_<name>.json was
written today (N=5 already completed), run the rest sequentially with
one retry per variant on failure."""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "reports" / "ablations"

VARIANTS = [
    ("full",       {}),
    ("no_prior",   {"IZ_NO_PRIOR": "1"}),
    ("no_disc",    {"IZ_NO_DISC_CF": "1"}),
    ("no_route",   {"IZ_NO_ROUTE": "1"}),
    ("no_ct",      {"IZ_NO_CT": "1"}),
    ("no_s5p",     {"IZ_NO_S5P": "1"}),
    ("no_beirle",  {"IZ_NO_BEIRLE": "1"}),
    ("no_sat",     {"IZ_NO_S5P": "1", "IZ_NO_BEIRLE": "1"}),
    ("no_disc_no_route", {"IZ_NO_DISC_CF": "1", "IZ_NO_ROUTE": "1"}),
]

N_OUTER = int(sys.argv[1]) if len(sys.argv) > 1 else 5

# A file "completed at N=5" if it was modified within the last 24h AND
# its first row has n_runs == N_OUTER.
def already_done(name: str) -> bool:
    f = OUT_DIR / f"lodo_{name}.json"
    if not f.exists():
        return False
    try:
        rows = json.loads(f.read_text())
        if rows and rows[0].get("n_runs") == N_OUTER:
            age = datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)
            return age < timedelta(hours=24)
    except Exception:
        pass
    return False


def run_variant(name: str, env_vars: dict, attempt: int = 1) -> bool:
    env = {**os.environ, **env_vars}
    print(f"\n=== {name}  attempt {attempt}  ({env_vars}) ===", flush=True)
    try:
        subprocess.run(
            ["uv", "run", "python", "bin/e2e_lodo_aggregate.py", str(N_OUTER)],
            cwd=str(REPO), env=env, check=True,
        )
        # Copy the result
        src = REPO / "reports" / "lodo_aggregated.json"
        (OUT_DIR / f"lodo_{name}.json").write_text(src.read_text())
        return True
    except subprocess.CalledProcessError as e:
        print(f"  FAILED with code {e.returncode}", flush=True)
        return False


def main():
    todo = []
    for name, env in VARIANTS:
        if already_done(name):
            print(f"skip  {name}  (already completed at N={N_OUTER})")
        else:
            todo.append((name, env))
    print(f"\nrunning {len(todo)} variants at N_OUTER={N_OUTER}\n")

    failed = []
    for name, env in todo:
        if not run_variant(name, env, 1):
            print(f"  retrying {name}...", flush=True)
            if not run_variant(name, env, 2):
                failed.append(name)
                print(f"  giving up on {name}", flush=True)

    # Rebuild summary from all lodo_<name>.json files
    rows_out = []
    sectors = {
        "cement": ["akcansa-buyukcekmece","akcansa-canakkale","akcansa-ladik","nuh-hereke",
                   "afyon-cimento","batisoke-soke","goltas-isparta","bursa-cimento"],
        "BF/BOF": ["erdemir-eregli","isdemir-iskenderun","kardemir-karabuk"],
        "EAF": ["colakoglu-gebze","habas-aliaga","izdemir-aliaga"],
        "aluminum": ["assan-tuzla","asas-akyazi"],
        "fertilizer": ["bagfas-bandirma","gubretas-izmit","toros-mersin","toros-samsun","toros-ceyhan"],
    }
    for name, _ in VARIANTS:
        f = OUT_DIR / f"lodo_{name}.json"
        if not f.exists():
            continue
        rows = json.loads(f.read_text())
        ml = [abs(math.log(r["pred_median"]) - math.log(r["truth"])) for r in rows if r["pred_median"] > 0]
        el = [abs(math.log(r["eu_default"]) - math.log(r["truth"])) for r in rows if r["eu_default"] > 0]
        sec_red = {}
        for sec, fids in sectors.items():
            rs = [r for r in rows if r["facility_id"] in fids]
            if not rs:
                continue
            mm = sum(abs(math.log(r["pred_median"]) - math.log(r["truth"])) for r in rs)/len(rs)
            em = sum(abs(math.log(r["eu_default"]) - math.log(r["truth"])) for r in rs)/len(rs)
            sec_red[sec] = (1 - mm/em) * 100 if em > 0 else 0
        rows_out.append({
            "name": name, "n": len(ml),
            "n_runs": rows[0].get("n_runs", N_OUTER),
            "iz_log_mae": sum(ml)/len(ml), "eu_log_mae": sum(el)/len(el),
            "reduction": (1 - sum(ml)/len(ml) / (sum(el)/len(el))) * 100,
            "per_sector": sec_red,
        })
    (OUT_DIR / "summary.json").write_text(json.dumps(rows_out, indent=2))

    print("\n" + "=" * 90)
    print(f"  ABLATION MATRIX  (N_OUTER per variant; n=21 LODO holdouts)")
    print("=" * 90)
    print(f"  {'variant':24s} {'N':>3s}  {'log-MAE':>8s}  {'reduction':>10s}   {'cement':>7s} {'BF/BOF':>8s} {'EAF':>7s} {'AL':>7s} {'FERT':>7s}")
    print("-" * 90)
    for r in rows_out:
        sec = r["per_sector"]
        cm = sec.get("cement", float("nan"))
        bf = sec.get("BF/BOF", float("nan"))
        ef = sec.get("EAF", float("nan"))
        al = sec.get("aluminum", float("nan"))
        ft = sec.get("fertilizer", float("nan"))
        print(f"  {r['name']:24s} {r['n_runs']:>3d}  {r['iz_log_mae']:>8.3f}  {r['reduction']:>9.1f}%   {cm:>+6.1f}% {bf:>+7.1f}% {ef:>+6.1f}% {al:>+6.1f}% {ft:>+6.1f}%")
    print("=" * 90)
    if failed:
        print(f"\nFailed variants: {failed}")


if __name__ == "__main__":
    main()
