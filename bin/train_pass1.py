"""
iz Pass 1 — full-precision fine-tune of Prithvi-EO-2.0-100M-TL on TR-MRV-Bench.

Loads NASA+IBM's Prithvi-EO ViT-base (100M params, 3D temporal patch embed),
strips the MAE head, attaches a regression head per pollutant, trains with
MSE + uncertainty quantile losses on the bench.

This script is designed to run on:
  - Local M2 Pro MPS (overnight, modest batch size)
  - Free Colab T4 (faster, see notebooks/pass1_colab.ipynb)

Usage:
    uv run python bin/train_pass1.py --epochs 20 --lr 3e-4 --batch 32
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

REPO = Path(__file__).resolve().parent.parent
BENCH_DIR = REPO / "data" / "bench"
CKPT_DIR = REPO / "checkpoints"
LOG_PATH = REPO / "logs" / "10_pass1.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger("iz.pass1")

# Numeric feature columns we feed the regression head (in addition to satellite tiles)
NUMERIC_FEATS = [
    "no2_mean", "no2_std", "no2_n_pixels",
    "wind_speed_mps", "wind_dir_deg", "pbl_height_m", "temp_2m_k",
    "thermal_mean_k", "thermal_max_k", "grid_co2_g_per_kwh",
]


class BenchDataset(Dataset):
    """Loads bench parquet rows. For Pass 1, we use the tabular features only;
    Prithvi-EO image features are added once the bbox tiles are extracted (TODO)."""

    def __init__(self, parquet_path: Path):
        df = pd.read_parquet(parquet_path)
        # Drop unlabeled rows
        df = df.dropna(subset=["co2_t_month"]).reset_index(drop=True)
        # Sanitize numeric features
        feats = df[NUMERIC_FEATS].astype("float32").values
        # Fill NaNs with column means (will be replaced by proper feature pipeline)
        col_means = np.nanmean(feats, axis=0)
        col_means = np.nan_to_num(col_means, nan=0.0)
        inds = np.where(np.isnan(feats))
        feats[inds] = np.take(col_means, inds[1])
        # Standardize
        self.feat_mean = feats.mean(0)
        self.feat_std = feats.std(0) + 1e-6
        self.X = (feats - self.feat_mean) / self.feat_std

        self.y = df["co2_t_month"].astype("float32").values
        # Log-transform target (emissions span orders of magnitude)
        self.y_log = np.log1p(self.y)
        # Confidence-derived sample weight
        conf_w = df["label_confidence"].map({"high": 1.0, "medium": 0.7, "low": 0.3, "": 0.5}).fillna(0.5)
        self.weights = conf_w.astype("float32").values
        self.df = df

    def __len__(self): return len(self.X)

    def __getitem__(self, idx):
        return {
            "x": torch.from_numpy(self.X[idx]),
            "y": torch.tensor(self.y_log[idx], dtype=torch.float32),
            "w": torch.tensor(self.weights[idx], dtype=torch.float32),
        }


class TabularHead(nn.Module):
    """Stand-in for the full Prithvi-EO + cross-modal head while satellite
    tile extraction is being wired. Pure tabular MLP — predicts log(CO₂_t/month)
    + log(σ). This is the baseline the Prithvi-EO version has to beat."""

    def __init__(self, in_dim: int, hidden: int = 128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.GELU(),
            nn.Linear(hidden, hidden), nn.GELU(),
            nn.Dropout(0.1),
        )
        self.mu_head = nn.Linear(hidden, 1)
        self.logsig_head = nn.Linear(hidden, 1)

    def forward(self, x):
        h = self.trunk(x)
        return self.mu_head(h).squeeze(-1), self.logsig_head(h).squeeze(-1)


def nll_gaussian(mu, logsig, y, w):
    """Weighted Gaussian negative log-likelihood. Trains both mean and variance."""
    sig2 = torch.exp(2.0 * logsig)
    loss = 0.5 * ((y - mu) ** 2 / sig2 + 2.0 * logsig)
    return (loss * w).mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--device", default="auto")
    args = ap.parse_args()

    device = (
        "cuda" if (args.device in ("auto", "cuda") and torch.cuda.is_available())
        else "mps" if (args.device in ("auto", "mps") and torch.backends.mps.is_available())
        else "cpu"
    )
    log.info("device: %s", device)

    train_ds = BenchDataset(BENCH_DIR / "train.parquet")
    val_ds = BenchDataset(BENCH_DIR / "val.parquet")
    log.info("train rows: %d   val rows: %d", len(train_ds), len(val_ds))
    if len(train_ds) == 0:
        log.error("empty train set — wait for extract_s5p_bench.py to populate data/s5p/ and re-run build_bench.py")
        return

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch, shuffle=False)

    model = TabularHead(in_dim=len(NUMERIC_FEATS)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-3)

    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    best_val = float("inf")
    for ep in range(1, args.epochs + 1):
        model.train()
        tr_losses = []
        for batch in train_loader:
            x = batch["x"].to(device)
            y = batch["y"].to(device)
            w = batch["w"].to(device)
            mu, ls = model(x)
            loss = nll_gaussian(mu, ls, y, w)
            opt.zero_grad(); loss.backward(); opt.step()
            tr_losses.append(loss.item())

        model.eval()
        with torch.no_grad():
            val_losses = []
            val_mae = []
            for batch in val_loader:
                x = batch["x"].to(device); y = batch["y"].to(device); w = batch["w"].to(device)
                mu, ls = model(x)
                val_losses.append(nll_gaussian(mu, ls, y, w).item())
                val_mae.append((mu - y).abs().mean().item())
        v = float(np.mean(val_losses))
        mae = float(np.mean(val_mae))
        log.info("ep %2d  train_nll=%.4f  val_nll=%.4f  val_mae(log)=%.4f", ep, float(np.mean(tr_losses)), v, mae)
        if v < best_val:
            best_val = v
            torch.save({"model": model.state_dict(),
                        "feat_mean": train_ds.feat_mean,
                        "feat_std": train_ds.feat_std,
                        "epoch": ep, "val_nll": v},
                       CKPT_DIR / "pass1_best.pt")

    log.info("Pass 1 done. Best val NLL: %.4f. Checkpoint: %s", best_val, CKPT_DIR / "pass1_best.pt")


if __name__ == "__main__":
    main()
