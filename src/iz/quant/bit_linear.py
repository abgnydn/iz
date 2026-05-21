"""
BitLinear — ternary {-1, 0, +1} weight linear layer for Pass 2.

Adapted from DLYuanGod/ViT-1.58b's BitLinear, simplified for our regression
use case. Weights are stored f32 but quantized at forward time via absmean
binarization. Activations are 8-bit per-token absmax quantized.

Gradients flow through the quantizer via straight-through estimator (STE).

Usage in a model:

    from iz.quant.bit_linear import BitLinear, replace_linear_with_bit_linear

    # Build full-precision model first
    model = build_pass1_model()
    # Then swap every nn.Linear in attention/FFN with a BitLinear
    replace_linear_with_bit_linear(model)
"""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


def absmean_ternary_quantize(w: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Per-tensor absmean ternarization: scale = mean(|w|), q = round(clip(w/scale, -1, 1))."""
    eps = 1e-5
    scale = w.abs().mean().clamp(min=eps)
    q = (w / scale).round().clamp(-1.0, 1.0)
    return q, scale


def per_token_int8_quantize(x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Per-last-token-dim absmax int8 quantization."""
    eps = 1e-5
    scale = x.abs().amax(dim=-1, keepdim=True).clamp(min=eps) / 127.0
    q = (x / scale).round().clamp(-128, 127)
    return q, scale


class BitLinear(nn.Linear):
    """nn.Linear-compatible drop-in with ternary forward + STE backward.

    Forward (training): quantize -> matmul -> dequantize, gradients via STE.
    Forward (eval): same, but skip the STE — quantized weights are the
                    authoritative weights.
    """

    def __init__(self, in_features: int, out_features: int, bias: bool = True):
        super().__init__(in_features, out_features, bias=bias)
        # cache the latest quantized weights for inference export
        self.register_buffer("_q_cache_w", torch.zeros_like(self.weight), persistent=False)
        self.register_buffer("_q_cache_s", torch.tensor(1.0), persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Quantize weights (ternary) and activations (int8). STE: pass gradient straight through.
        w_q, w_s = absmean_ternary_quantize(self.weight)
        w_eff = self.weight + (w_q * w_s - self.weight).detach()  # STE on the difference
        x_q, x_s = per_token_int8_quantize(x)
        x_eff = x + (x_q * x_s - x).detach()
        self._q_cache_w = w_q.detach()
        self._q_cache_s = w_s.detach()
        return F.linear(x_eff, w_eff, self.bias)

    @torch.no_grad()
    def export_ternary(self) -> dict:
        """Return ternary weight + scale for inference deployment."""
        q, s = absmean_ternary_quantize(self.weight)
        return {
            "q_weight_int8": q.to(torch.int8),  # values in {-1, 0, +1}
            "scale": s.item(),
            "bias": None if self.bias is None else self.bias.detach().cpu(),
        }


def replace_linear_with_bit_linear(
    module: nn.Module,
    *,
    skip_names: Optional[set[str]] = None,
) -> int:
    """Recursively swap every nn.Linear with BitLinear in-place.
    Returns the count of swapped layers. Skips names matching skip_names
    (typically the final regression head + first patch embedding)."""
    skip = skip_names or set()
    swapped = 0
    for name, child in list(module.named_children()):
        full = name
        if isinstance(child, nn.Linear) and full not in skip:
            bl = BitLinear(child.in_features, child.out_features, bias=child.bias is not None)
            bl.weight = child.weight  # share the existing fp32 weights
            if child.bias is not None:
                bl.bias = child.bias
            setattr(module, name, bl)
            swapped += 1
        else:
            swapped += replace_linear_with_bit_linear(child, skip_names=skip)
    return swapped
