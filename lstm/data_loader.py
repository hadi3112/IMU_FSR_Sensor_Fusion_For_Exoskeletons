"""
lstm/data_loader.py

Loads all .mat recordings from the four dataset sub-folders, aligns every
modality onto a shared time-axis via linear interpolation, concatenates into
a single 18-feature vector per timestep, and returns fixed-length sliding-
window sequences ready for LSTM training.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SAMPLE PAIRING  —  how IMU_data_N links to FSR_data_N
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  All four modality folders contain files named with the SAME integer
  suffix N  (e.g. IMU_data_1.mat, IMU_accel_1.mat,
  IMU_derivatives_1.mat, FSR_data_1.mat).

  The loader iterates over a fixed, sorted list of sample indices (1–20)
  and for every N it ALWAYS opens:
      dataset/IMU_data/IMU_data_N.mat
      dataset/IMU_accel/IMU_accel_N.mat
      dataset/IMU_derivatives/IMU_derivatives_N.mat
      dataset/FSR_data/FSR_data_N.mat

  There is NO glob expansion, NO sorting-based guesswork and NO
  cross-index access. Index N in one folder is guaranteed to correspond
  to index N in every other folder. A full pairing manifest is printed
  at load time so you can verify at a glance.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 FSR ZERO-VALUE HANDLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Three distinct cases are handled:

  A) File absent / unreadable         → zeros, flagged as [NO FILE]
  B) File present, keys missing       → zeros, flagged as [BAD FORMAT]
  C) File present, all channels ≈ 0   → zeros kept as-is, flagged
                                         as [ALL-ZERO FSR] — the sensor
                                         was present but had no load.
                                         We keep the zeros because they
                                         ARE the correct signal for that
                                         recording (standing still, or
                                         sensor not under foot).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Feature layout  (18 features per timestep)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [0]  p1    IMU pitch angle — sensor 1
  [1]  p2    IMU pitch angle — sensor 2
  [2]  pavg  IMU pitch average
  [3]  ax1   IMU accel X — sensor 1
  [4]  ay1   IMU accel Y — sensor 1
  [5]  az1   IMU accel Z — sensor 1
  [6]  ax2   IMU accel X — sensor 2
  [7]  ay2   IMU accel Y — sensor 2
  [8]  az2   IMU accel Z — sensor 2
  [9]  dx1   IMU accel derivative X — sensor 1
  [10] dy1   IMU accel derivative Y — sensor 1
  [11] dz1   IMU accel derivative Z — sensor 1
  [12] dx2   IMU accel derivative X — sensor 2
  [13] dy2   IMU accel derivative Y — sensor 2
  [14] dz2   IMU accel derivative Z — sensor 2
  [15] fsr1  FSR sensor 1  (0.0 if absent / no load)
  [16] fsr2  FSR sensor 2  (0.0 if absent / no load)
  [17] fsr3  FSR sensor 3  (0.0 if absent / no load)

Gait labels are assigned per-window via quantile segmentation of the
average pitch signal into 4 phases:
  0 — Heel Strike
  1 — Stance
  2 — Push-Off
  3 — Swing
"""

from __future__ import annotations

import os
from typing import Optional, Tuple, List, Dict

import numpy as np
import scipy.io as sio
from scipy.interpolate import interp1d

# ─────────────────────────────────────────────────────────────────────────
# PATHS  (always resolved from the project root, regardless of cwd)
# ─────────────────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATASET_PATHS: Dict[str, str] = {
    "imu":   os.path.join(_ROOT, "dataset", "IMU_data"),
    "accel": os.path.join(_ROOT, "dataset", "IMU_accel"),
    "deriv": os.path.join(_ROOT, "dataset", "IMU_derivatives"),
    "fsr":   os.path.join(_ROOT, "dataset", "FSR_data"),
}

# ─────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────
N_FEATURES  = 18    # total concatenated feature width
N_CLASSES   = 4     # gait phase labels
WINDOW_SIZE = 100   # timesteps per LSTM sequence
WINDOW_STEP = 50    # sliding-window stride (50 % overlap)
N_SAMPLES   = 20    # number of recordings (1 … N_SAMPLES)

# Max absolute value below which an FSR channel is considered "all-zero"
FSR_ZERO_THRESHOLD = 1e-6


# ─────────────────────────────────────────────────────────────────────────
# LOW-LEVEL HELPERS
# ─────────────────────────────────────────────────────────────────────────

def _mat_path(folder: str, prefix: str, idx: int) -> str:
    """Build the canonical path for sample `idx` in `folder`."""
    return os.path.join(DATASET_PATHS[folder], f"{prefix}_{idx}.mat")


def _safe_load(path: str) -> Optional[dict]:
    """Load a .mat file; return None on any failure."""
    try:
        return sio.loadmat(path)
    except Exception as exc:
        print(f"    [WARN] Cannot load {os.path.basename(path)}: {exc}")
        return None


def _interp_to(t_src: np.ndarray,
               sig:   np.ndarray,
               t_dst: np.ndarray) -> np.ndarray:
    """
    Linearly interpolate `sig` (sampled at t_src) onto t_dst.
    Clips to the boundary values for out-of-range queries.
    """
    f = interp1d(t_src, sig,
                 kind="linear",
                 bounds_error=False,
                 fill_value=(sig[0], sig[-1]))
    return f(t_dst)


def _assign_labels(pavg: np.ndarray, n_classes: int = N_CLASSES) -> np.ndarray:
    """
    Per-timestep gait labels via uniform quantile segmentation of `pavg`.

    The pitch envelope is divided into `n_classes` bands of equal
    probability mass (quantile-based), assigning each timestep the
    band it falls into:
        0 — Heel Strike  (lowest pitch)
        1 — Stance
        2 — Push-Off
        3 — Swing        (highest pitch)
    """
    labels     = np.zeros(len(pavg), dtype=np.int64)
    thresholds = np.percentile(pavg, np.linspace(0, 100, n_classes + 1))
    for i in range(n_classes):
        lo   = thresholds[i]
        hi   = thresholds[i + 1]
        mask = (pavg >= lo) & (pavg <= hi)
        labels[mask] = i
    return labels


# ─────────────────────────────────────────────────────────────────────────
# PER-SAMPLE LOADER
# ─────────────────────────────────────────────────────────────────────────

def _load_sample(idx: int,
                 verbose: bool = True
                 ) -> Optional[Tuple[np.ndarray, np.ndarray, Dict]]:
    """
    Load recording `idx` across all four modalities and return:
        features : (T, N_FEATURES)  float32
        labels   : (T,)             int64
        manifest : dict with per-modality status strings (for audit log)

    Returns None if the primary IMU_data file is missing (can't proceed
    without the reference time axis and pitch angles).

    ───────────────────────────────────────────────────────────────────
    Pairing guarantee
    ───────────────────────────────────────────────────────────────────
    Every file accessed uses EXACTLY the same integer `idx`.  There is
    no sorting, no globbing, no index remapping.  File N of one modality
    is always paired with file N of every other modality.
    """

    manifest: Dict[str, str] = {"idx": str(idx)}

    # ── 1.  IMU angles (REQUIRED — defines reference time axis) ──────────
    imu_path = _mat_path("imu", "IMU_data", idx)
    imu      = _safe_load(imu_path)

    if imu is None or "t" not in imu or "p1" not in imu:
        manifest["imu"] = "MISSING — sample skipped"
        return None

    t_ref = imu["t"].flatten().astype(float)
    p1    = imu["p1"].flatten().astype(float)
    p2    = imu["p2"].flatten().astype(float)
    pavg  = imu["pavg"].flatten().astype(float)
    T     = len(t_ref)
    manifest["imu"] = f"OK  ({T} pts, t=[{t_ref[0]:.2f}…{t_ref[-1]:.2f}])"

    # ── 2.  IMU accelerations (optional — zeros if absent) ───────────────
    accel_path = _mat_path("accel", "IMU_accel", idx)
    accel      = _safe_load(accel_path)

    if accel is not None and "ax1" in accel:
        t_a = accel["t"].flatten().astype(float)
        ax1 = _interp_to(t_a, accel["ax1"].flatten(), t_ref)
        ay1 = _interp_to(t_a, accel["ay1"].flatten(), t_ref)
        az1 = _interp_to(t_a, accel["az1"].flatten(), t_ref)
        ax2 = _interp_to(t_a, accel["ax2"].flatten(), t_ref)
        ay2 = _interp_to(t_a, accel["ay2"].flatten(), t_ref)
        az2 = _interp_to(t_a, accel["az2"].flatten(), t_ref)
        manifest["accel"] = f"OK  ({len(t_a)} pts -> interp to {T})"
    else:
        ax1 = ay1 = az1 = ax2 = ay2 = az2 = np.zeros(T, dtype=float)
        manifest["accel"] = "MISSING -> zero-padded"

    # ── 3.  IMU derivatives (optional — zeros if absent) ─────────────────
    deriv_path = _mat_path("deriv", "IMU_derivatives", idx)
    deriv      = _safe_load(deriv_path)

    if deriv is not None and "dx1" in deriv:
        t_d = deriv["t"].flatten().astype(float)
        dx1 = _interp_to(t_d, deriv["dx1"].flatten(), t_ref)
        dy1 = _interp_to(t_d, deriv["dy1"].flatten(), t_ref)
        dz1 = _interp_to(t_d, deriv["dz1"].flatten(), t_ref)
        dx2 = _interp_to(t_d, deriv["dx2"].flatten(), t_ref)
        dy2 = _interp_to(t_d, deriv["dy2"].flatten(), t_ref)
        dz2 = _interp_to(t_d, deriv["dz2"].flatten(), t_ref)
        manifest["deriv"] = f"OK  ({len(t_d)} pts -> interp to {T})"
    else:
        dx1 = dy1 = dz1 = dx2 = dy2 = dz2 = np.zeros(T, dtype=float)
        manifest["deriv"] = "MISSING -> zero-padded"

    # ── 4.  FSR (optional — zeros carried through if absent OR all-zero) ──
    fsr_path = _mat_path("fsr", "FSR_data", idx)
    fsr      = _safe_load(fsr_path)

    if fsr is None:
        # File absent entirely
        fsr1 = fsr2 = fsr3 = np.zeros(T, dtype=float)
        manifest["fsr"] = "NO FILE → zero-padded"

    elif "fsr1" not in fsr:
        # File exists but doesn't contain expected keys (bad format)
        fsr1 = fsr2 = fsr3 = np.zeros(T, dtype=float)
        manifest["fsr"] = "BAD FORMAT → zero-padded"

    else:
        t_f  = fsr["t"].flatten().astype(float)
        fsr1 = _interp_to(t_f, fsr["fsr1"].flatten(), t_ref)
        fsr2 = _interp_to(t_f, fsr["fsr2"].flatten(), t_ref)
        fsr3 = _interp_to(t_f, fsr["fsr3"].flatten(), t_ref)

        # Detect all-zero FSR (sensor present but no load recorded)
        max_val = max(np.abs(fsr1).max(),
                      np.abs(fsr2).max(),
                      np.abs(fsr3).max())

        if max_val <= FSR_ZERO_THRESHOLD:
            # Zeros ARE the correct signal — keep them, just flag it
            manifest["fsr"] = (
                f"OK  ({len(t_f)} pts -> interp to {T})  "
                f"[ALL-ZERO FSR] sensor present but no pressure detected"
            )
        else:
            manifest["fsr"] = (
                f"OK  ({len(t_f)} pts -> interp to {T})  "
                f"max={max_val:.4f}"
            )

    # ── 5.  Concatenate feature matrix (T, 18) ────────────────────────────
    features = np.stack([
        p1,   p2,   pavg,          # IMU angles        [0-2]
        ax1,  ay1,  az1,           # IMU accel IMU1    [3-5]
        ax2,  ay2,  az2,           # IMU accel IMU2    [6-8]
        dx1,  dy1,  dz1,           # IMU deriv IMU1    [9-11]
        dx2,  dy2,  dz2,           # IMU deriv IMU2    [12-14]
        fsr1, fsr2, fsr3,          # FSR channels      [15-17]
    ], axis=1).astype(np.float32)

    # ── 6.  Quantile labels per timestep ─────────────────────────────────
    labels = _assign_labels(pavg)

    return features, labels, manifest


# ─────────────────────────────────────────────────────────────────────────
# SLIDING-WINDOW SEGMENTATION
# ─────────────────────────────────────────────────────────────────────────

def _sliding_windows(features: np.ndarray,
                     labels:   np.ndarray,
                     window:   int = WINDOW_SIZE,
                     step:     int = WINDOW_STEP
                     ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Slice a (T, F) recording into overlapping windows of length `window`.
    The label for each window = majority vote among its timestep labels.

    Returns:
        X : (N_windows, window, F)   float32
        y : (N_windows,)             int64
    """
    X_list: List[np.ndarray] = []
    y_list: List[int]        = []

    T     = len(features)
    start = 0
    while start + window <= T:
        win_feats  = features[start: start + window]     # (W, F)
        win_labels = labels[start: start + window]       # (W,)
        label      = int(np.bincount(win_labels).argmax())
        X_list.append(win_feats)
        y_list.append(label)
        start += step

    if not X_list:
        empty_X = np.empty((0, window, features.shape[1]), dtype=np.float32)
        empty_y = np.empty((0,), dtype=np.int64)
        return empty_X, empty_y

    return (np.array(X_list, dtype=np.float32),
            np.array(y_list,  dtype=np.int64))


# ─────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────

def load_dataset(verbose: bool = True
                 ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load all recordings, apply sliding windows, and return (X, y).

      X : (N_windows, WINDOW_SIZE, N_FEATURES)  float32
      y : (N_windows,)                           int64   (0..N_CLASSES-1)

    A pairing manifest table is printed so you can verify which files
    were loaded together.
    """
    X_all: List[np.ndarray] = []
    y_all: List[np.ndarray] = []
    manifests: List[Dict]   = []

    for idx in range(1, N_SAMPLES + 1):
        result = _load_sample(idx, verbose=verbose)
        if result is None:
            manifests.append({
                "idx":   str(idx),
                "imu":   "MISSING — skipped",
                "accel": "—",
                "deriv": "—",
                "fsr":   "—",
            })
            continue

        features, labels, manifest = result
        X_win, y_win = _sliding_windows(features, labels)

        if len(X_win) == 0:
            manifest["note"] = "⚠ too short for any window — skipped"
        else:
            X_all.append(X_win)
            y_all.append(y_win)
            manifest["note"] = f"{len(X_win)} windows produced"

        manifests.append(manifest)

    # ── Print pairing manifest ────────────────────────────────────────────
    _print_manifest(manifests)

    if not X_all:
        raise RuntimeError(
            "No data was loaded. Check that dataset/ sub-folders exist and "
            "contain properly named .mat files."
        )

    X = np.concatenate(X_all, axis=0)
    y = np.concatenate(y_all, axis=0)
    return X, y


def _print_manifest(manifests: List[Dict]) -> None:
    """Print the pairing audit table to stdout."""
    W = 72
    print()
    print("=" * W)
    print("  SAMPLE PAIRING MANIFEST  --  verify N->N alignment")
    print("=" * W)
    print(f"  {'#':>2}  {'IMU_data':^8}  {'IMU_accel':^10}  "
          f"{'IMU_deriv':^10}  {'FSR_data':^10}  Note")
    print("-" * W)

    for m in manifests:
        idx    = m.get("idx",   "?")
        imu    = "OK" if m.get("imu",   "").startswith("OK") else "MISS"
        accel  = "OK" if m.get("accel", "").startswith("OK") else "0s"
        deriv  = "OK" if m.get("deriv", "").startswith("OK") else "0s"
        fsr    = "OK" if m.get("fsr",   "").startswith("OK") else "0s"
        note   = m.get("note", "")

        # Annotate all-zero FSR
        if "ALL-ZERO" in m.get("fsr", ""):
            fsr = "0*"   # present but all-zero

        print(f"  {idx:>2}  {imu:^8}  {accel:^10}  {deriv:^10}  "
              f"{fsr:^10}  {note}")

    print("-" * W)
    print("  Legend: OK=loaded  0s=zero-padded  0*=present but all-zero signal")
    print("=" * W)
    print()
