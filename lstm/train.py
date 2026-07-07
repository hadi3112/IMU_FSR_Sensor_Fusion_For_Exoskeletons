from __future__ import annotations
"""
lstm/train.py

Entry point for training the GaitLSTM classifier.

Usage:
    python -m lstm.train                        # default settings
    python -m lstm.train --epochs 100 --lr 1e-3
    python -m lstm.train --batch 64 --no-gpu

Full CLI options:
    --epochs   N     training epochs                    (default 60)
    --batch    N     mini-batch size                    (default 32)
    --lr       F     initial learning rate              (default 5e-4)
    --wd       F     L2 weight decay                    (default 1e-4)
    --patience N     early-stopping patience (epochs)   (default 15)
    --val-split F    fraction of data used for val      (default 0.2)
    --seed     N     random seed                        (default 42)
    --no-gpu        disable GPU even if available
    --out      PATH  directory for saved checkpoints    (default ./lstm/checkpoints)
"""

import argparse
import os
import sys
import time
import random

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset, random_split
from sklearn.preprocessing import StandardScaler

# ── add project root to sys.path so imports work from any cwd ───────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from lstm.data_loader import load_dataset, N_CLASSES, WINDOW_SIZE, N_FEATURES
from lstm.model import build_model


# ─────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train GaitLSTM classifier")
    p.add_argument("--epochs",    type=int,   default=60)
    p.add_argument("--batch",     type=int,   default=32)
    p.add_argument("--lr",        type=float, default=5e-4)
    p.add_argument("--wd",        type=float, default=1e-4)
    p.add_argument("--patience",  type=int,   default=15)
    p.add_argument("--val-split", type=float, default=0.20)
    p.add_argument("--seed",      type=int,   default=42)
    p.add_argument("--no-gpu",    action="store_true")
    p.add_argument("--out",       type=str,   default=os.path.join(_ROOT, "lstm", "checkpoints"))
    return p.parse_args()


# ─────────────────────────────────────────────────────────────────────────
# REPRODUCIBILITY
# ─────────────────────────────────────────────────────────────────────────

def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ─────────────────────────────────────────────────────────────────────────
# NORMALISATION
# ─────────────────────────────────────────────────────────────────────────

def fit_scaler(X_train: np.ndarray) -> StandardScaler:
    """
    Fit a StandardScaler on the training windows.
    X_train : (N, T, F) — reshape to (N*T, F), fit, reshape back.
    """
    N, T, F = X_train.shape
    scaler = StandardScaler()
    scaler.fit(X_train.reshape(-1, F))
    return scaler


def apply_scaler(X: np.ndarray, scaler: StandardScaler) -> np.ndarray:
    N, T, F = X.shape
    return scaler.transform(X.reshape(-1, F)).reshape(N, T, F).astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────
# TRAIN / EVAL LOOPS
# ─────────────────────────────────────────────────────────────────────────

def run_epoch(model:     nn.Module,
              loader:    DataLoader,
              criterion: nn.Module,
              optimizer: torch.optim.Optimizer | None,
              device:    str,
              train:     bool) -> tuple[float, float]:
    """Single epoch pass. Returns (avg_loss, accuracy)."""
    model.train(train)
    total_loss, correct, total = 0.0, 0, 0

    with torch.set_grad_enabled(train):
        for X_batch, y_batch in loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            logits = model(X_batch)
            loss   = criterion(logits, y_batch)

            if train:
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            total_loss += loss.item() * len(y_batch)
            preds       = logits.argmax(dim=1)
            correct    += (preds == y_batch).sum().item()
            total      += len(y_batch)

    return total_loss / total, correct / total


# ─────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────

def main():
    args   = parse_args()
    set_seed(args.seed)
    os.makedirs(args.out, exist_ok=True)

    # ── Device ──────────────────────────────────────────────────────────
    if args.no_gpu or not torch.cuda.is_available():
        device = "cpu"
    else:
        device = "cuda"
    print(f"\n{'='*60}")
    print(f"  GaitLSTM Training")
    print(f"{'='*60}")
    print(f"  device     : {device}")
    print(f"  epochs     : {args.epochs}")
    print(f"  batch size : {args.batch}")
    print(f"  lr         : {args.lr}")
    print(f"  val split  : {args.val_split:.0%}")
    print(f"  output dir : {args.out}")
    print(f"{'='*60}\n")

    # ── Load data ───────────────────────────────────────────────────────
    print("[STEP 1/4] Loading dataset ...")
    X, y = load_dataset(verbose=True)
    print(f"\n  Dataset shape : X={X.shape}  y={y.shape}")
    print(f"  Class counts  : { {i: int((y==i).sum()) for i in range(N_CLASSES)} }")

    # ── Train / val split ───────────────────────────────────────────────
    print("\n[STEP 2/4] Splitting train/val ...")
    n_total = len(X)
    n_val   = max(1, int(n_total * args.val_split))
    n_train = n_total - n_val

    # shuffle indices
    rng     = np.random.default_rng(args.seed)
    indices = rng.permutation(n_total)
    train_idx, val_idx = indices[:n_train], indices[n_train:]

    X_train, y_train = X[train_idx], y[train_idx]
    X_val,   y_val   = X[val_idx],   y[val_idx]
    print(f"  train={len(X_train)}  val={len(X_val)}")

    # ── Normalise ────────────────────────────────────────────────────────
    print("\n[STEP 3/4] Fitting StandardScaler on train ...")
    scaler  = fit_scaler(X_train)
    X_train = apply_scaler(X_train, scaler)
    X_val   = apply_scaler(X_val,   scaler)

    # save scaler for inference
    import pickle
    scaler_path = os.path.join(args.out, "scaler.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"  Scaler saved -> {scaler_path}")

    # ── DataLoaders ──────────────────────────────────────────────────────
    train_ds = TensorDataset(
        torch.from_numpy(X_train),
        torch.from_numpy(y_train).long()
    )
    val_ds = TensorDataset(
        torch.from_numpy(X_val),
        torch.from_numpy(y_val).long()
    )
    train_loader = DataLoader(train_ds, batch_size=args.batch,
                              shuffle=True,  drop_last=False)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch,
                              shuffle=False, drop_last=False)

    # ── Model, loss, optimiser ───────────────────────────────────────────
    print("\n[STEP 4/4] Building model ...")
    model = build_model(device)

    # Weighted cross-entropy to handle potential class imbalance
    class_counts = np.bincount(y_train, minlength=N_CLASSES).astype(float)
    class_weights = 1.0 / np.maximum(class_counts, 1)
    class_weights /= class_weights.sum()
    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor(class_weights, dtype=torch.float32).to(device)
    )

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=args.wd
    )
    # Cosine annealing restarts
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=10, T_mult=2, eta_min=1e-6
    )

    # ── Training loop ────────────────────────────────────────────────────
    print("\n" + "-"*60)
    print(f"  {'Epoch':>6}  {'TrainLoss':>10}  {'TrainAcc':>9}  "
          f"{'ValLoss':>9}  {'ValAcc':>8}  {'LR':>9}  {'Time':>6}")
    print("-"*60)

    best_val_loss    = float("inf")
    patience_counter = 0
    best_ckpt_path   = os.path.join(args.out, "best_model.pt")

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()

        train_loss, train_acc = run_epoch(
            model, train_loader, criterion, optimizer, device, train=True
        )
        val_loss, val_acc = run_epoch(
            model, val_loader, criterion, None, device, train=False
        )
        scheduler.step()

        elapsed = time.time() - t0
        current_lr = optimizer.param_groups[0]["lr"]

        print(f"  {epoch:>6}  {train_loss:>10.4f}  {train_acc:>8.2%}  "
              f"{val_loss:>9.4f}  {val_acc:>7.2%}  "
              f"{current_lr:>9.2e}  {elapsed:>5.1f}s")

        # ── Checkpoint ──────────────────────────────────────────────────
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save({
                "epoch":       epoch,
                "model_state": model.state_dict(),
                "val_loss":    val_loss,
                "val_acc":     val_acc,
                "args":        vars(args),
            }, best_ckpt_path)
            print(f"           >> checkpoint saved (val_loss={val_loss:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"\n  Early stopping at epoch {epoch} "
                      f"(no improvement for {args.patience} epochs)")
                break

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Training complete.")
    print(f"  Best val loss : {best_val_loss:.4f}")
    print(f"  Checkpoint    : {best_ckpt_path}")
    print(f"{'='*60}\n")

    # ── Final evaluation on val set ───────────────────────────────────────
    print("Loading best checkpoint for final evaluation ...")
    ckpt = torch.load(best_ckpt_path, map_location=device)
    model.load_state_dict(ckpt["model_state"])

    _, final_acc = run_epoch(
        model, val_loader, criterion, None, device, train=False
    )
    print(f"Final validation accuracy: {final_acc:.2%}\n")

    # ── Per-class report ─────────────────────────────────────────────────
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for X_batch, y_batch in val_loader:
            logits = model(X_batch.to(device))
            preds  = logits.argmax(dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(y_batch.numpy())

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)

    phase_names = ["Heel Strike", "Stance", "Push-Off", "Swing"]
    print("-"*50)
    print(f"  {'Phase':<14}  {'Precision':>9}  {'Recall':>7}  {'F1':>6}")
    print("-"*50)
    for cls in range(N_CLASSES):
        tp = ((all_preds == cls) & (all_labels == cls)).sum()
        fp = ((all_preds == cls) & (all_labels != cls)).sum()
        fn = ((all_preds != cls) & (all_labels == cls)).sum()
        prec = tp / max(tp + fp, 1)
        rec  = tp / max(tp + fn, 1)
        f1   = 2 * prec * rec / max(prec + rec, 1e-9)
        print(f"  {phase_names[cls]:<14}  {prec:>9.2%}  {rec:>7.2%}  {f1:>6.2%}")
    print("-"*50 + "\n")


if __name__ == "__main__":
    main()
