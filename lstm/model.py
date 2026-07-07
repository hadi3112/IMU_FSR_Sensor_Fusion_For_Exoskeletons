from __future__ import annotations
"""
lstm/model.py

Defines the LSTM-based gait phase classifier.

Architecture:
  Input  (batch, WINDOW_SIZE, N_FEATURES)
    ↓
  BatchNorm1d  — stabilise raw sensor scale variance
    ↓
  LSTM  (2 layers, hidden=128, bidirectional, dropout=0.3)
    ↓
  LayerNorm    — normalise LSTM output
    ↓
  Attention    — learnable weighted pooling over timesteps
    ↓
  Dense  512 → ReLU → Dropout(0.4)
  Dense  256 → ReLU → Dropout(0.3)
  Dense  128 → ReLU → Dropout(0.2)
    ↓
  Linear → 4 logits  (softmax applied externally by CrossEntropyLoss)
"""

import torch
import torch.nn as nn
from lstm.data_loader import N_FEATURES, N_CLASSES, WINDOW_SIZE


class _Attention(nn.Module):
    """Additive self-attention pool over the time dimension."""

    def __init__(self, hidden_dim: int):
        super().__init__()
        self.score = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x : (B, T, H)
        scores  = self.score(x)            # (B, T, 1)
        weights = torch.softmax(scores, dim=1)   # (B, T, 1)
        pooled  = (weights * x).sum(dim=1)       # (B, H)
        return pooled


class GaitLSTM(nn.Module):
    """
    Bidirectional stacked LSTM for 4-class gait phase classification.

    Parameters
    ----------
    n_features  : int   input feature width  (default 18)
    n_classes   : int   output classes       (default 4)
    hidden_size : int   LSTM hidden units    (default 128)
    num_layers  : int   stacked LSTM layers  (default 2)
    dropout     : float LSTM inter-layer dropout (default 0.3)
    """

    def __init__(
        self,
        n_features:  int   = N_FEATURES,
        n_classes:   int   = N_CLASSES,
        hidden_size: int   = 128,
        num_layers:  int   = 2,
        dropout:     float = 0.3,
    ):
        super().__init__()

        self.n_features  = n_features
        self.hidden_size = hidden_size
        self.num_layers  = num_layers
        lstm_out_dim     = hidden_size * 2      # × 2 because bidirectional

        # ── Input normalisation ──────────────────────────────────────────
        self.input_norm = nn.BatchNorm1d(n_features)

        # ── Bidirectional stacked LSTM ───────────────────────────────────
        self.lstm = nn.LSTM(
            input_size    = n_features,
            hidden_size   = hidden_size,
            num_layers    = num_layers,
            batch_first   = True,
            bidirectional = True,
            dropout       = dropout if num_layers > 1 else 0.0,
        )

        # ── Output normalisation ─────────────────────────────────────────
        self.layer_norm = nn.LayerNorm(lstm_out_dim)

        # ── Temporal attention pooling ───────────────────────────────────
        self.attention = _Attention(lstm_out_dim)

        # ── Classifier head ──────────────────────────────────────────────
        self.classifier = nn.Sequential(
            nn.Linear(lstm_out_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.4),

            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(128, n_classes),   # raw logits — softmax via loss fn
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x : (batch, time_steps, n_features)
        returns logits : (batch, n_classes)
        """
        # BatchNorm expects (B, C, L) so transpose, norm, transpose back
        x = self.input_norm(x.permute(0, 2, 1)).permute(0, 2, 1)

        # LSTM
        out, _ = self.lstm(x)        # (B, T, lstm_out_dim)
        out     = self.layer_norm(out)

        # Attention pool  →  (B, lstm_out_dim)
        pooled  = self.attention(out)

        # Classify
        logits  = self.classifier(pooled)   # (B, n_classes)
        return logits


def build_model(device: str = "cpu") -> GaitLSTM:
    """Construct and return the model on `device`."""
    model = GaitLSTM().to(device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[MODEL] GaitLSTM  |  params: {n_params:,}  |  device: {device}")
    return model
