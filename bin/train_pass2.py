"""
iz Pass 2 — ternary QAT via BitLinear + knowledge distillation.

Loads the Pass-1 full-precision teacher, swaps every Linear in the trunk
with iz.quant.bit_linear.BitLinear, trains the student on the same data
with a KD loss = α * KL(student||teacher) + (1-α) * NLL.

Usage:
    uv run python bin/train_pass2.py --epochs 15 --kd-alpha 0.5
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from iz.quant.bit_linear import BitLinear, replace_linear_with_bit_linear

# Reuse Pass 1's data + model
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_pass1 import BenchDataset, TabularHead, nll_gaussian, NUMERIC_FEATS

REPO = Path(__file__).resolve().parent.parent
BENCH_DIR = REPO / "data" / "bench"
CKPT_DIR = REPO / "checkpoints"
LOG_PATH = REPO / "logs" / "11_pass2.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger("iz.pass2")


def kd_distill_loss(s_mu, s_ls, t_mu, t_ls, alpha: float = 0.5):
    """KL divergence between two diagonal Gaussians + sample weighting handled outside."""
    s_var = torch.exp(2.0 * s_ls)
    t_var = torch.exp(2.0 * t_ls)
    return 0.5 * ((s_mu - t_mu) ** 2 / s_var + s_var / t_var + 2 * (s_ls - t_ls)).mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--kd-alpha", type=float, default=0.5)
    ap.add_argument("--teacher", default=str(CKPT_DIR / "pass1_best.pt"))
    args = ap.parse_args()

    device = (
        "cuda" if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available()
        else "cpu"
    )
    log.info("device: %s", device)

    teacher = TabularHead(in_dim=len(NUMERIC_FEATS)).to(device)
    state = torch.load(args.teacher, map_location=device)
    teacher.load_state_dict(state["model"])
    teacher.eval()
    for p in teacher.parameters():
        p.requires_grad_(False)
    log.info("teacher loaded from %s (epoch %s, val_nll %.4f)", args.teacher, state.get("epoch"), state.get("val_nll", float("nan")))

    student = TabularHead(in_dim=len(NUMERIC_FEATS)).to(device)
    student.load_state_dict(state["model"])
    n_swapped = replace_linear_with_bit_linear(
        student,
        skip_names={"mu_head", "logsig_head"},  # keep regression heads fp32
    )
    log.info("swapped %d Linear → BitLinear in student", n_swapped)

    train_ds = BenchDataset(BENCH_DIR / "train.parquet")
    val_ds = BenchDataset(BENCH_DIR / "val.parquet")
    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch, shuffle=False)

    opt = torch.optim.AdamW(student.parameters(), lr=args.lr, weight_decay=1e-3)
    best_val = float("inf")
    for ep in range(1, args.epochs + 1):
        student.train()
        for batch in train_loader:
            x = batch["x"].to(device); y = batch["y"].to(device); w = batch["w"].to(device)
            with torch.no_grad():
                t_mu, t_ls = teacher(x)
            s_mu, s_ls = student(x)
            loss = (
                args.kd_alpha * kd_distill_loss(s_mu, s_ls, t_mu, t_ls)
                + (1 - args.kd_alpha) * nll_gaussian(s_mu, s_ls, y, w)
            )
            opt.zero_grad(); loss.backward(); opt.step()

        student.eval()
        with torch.no_grad():
            val_losses = []
            for batch in val_loader:
                x = batch["x"].to(device); y = batch["y"].to(device); w = batch["w"].to(device)
                mu, ls = student(x)
                val_losses.append(nll_gaussian(mu, ls, y, w).item())
        v = float(np.mean(val_losses))
        log.info("ep %2d  val_nll=%.4f", ep, v)
        if v < best_val:
            best_val = v
            torch.save({"model": student.state_dict(), "epoch": ep, "val_nll": v, "ternary_skip": ["mu_head", "logsig_head"]},
                       CKPT_DIR / "pass2_best.pt")

    log.info("Pass 2 done. Best val NLL: %.4f. Checkpoint: %s", best_val, CKPT_DIR / "pass2_best.pt")

    # Export ternary weights for browser deployment
    export_path = CKPT_DIR / "pass2_ternary_export.pt"
    export = {}
    for name, mod in student.named_modules():
        if isinstance(mod, BitLinear):
            export[name] = mod.export_ternary()
    torch.save(export, export_path)
    log.info("ternary export → %s (%d BitLinear layers)", export_path, len(export))


if __name__ == "__main__":
    main()
