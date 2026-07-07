# mat_loader.py
import scipy.io as sio
import matplotlib.pyplot as plt
import glob
import os


# =========================================================
# FILE TYPE REGISTRY
# Maps a short key -> (file prefix, friendly label)
# =========================================================

FILE_TYPES = {
    "1": ("IMU_data",        "IMU Angles      (p1, p2, pavg)"),
    "2": ("IMU_accel",       "IMU Accel       (ax1/y1/z1, ax2/y2/z2)"),
    "3": ("IMU_derivatives", "IMU Derivatives (dx1/y1/z1, dx2/y2/z2)"),
    "4": ("FSR_data",        "FSR Pressure    (fsr1, fsr2, fsr3)"),
}


# =========================================================
# FILE DISCOVERY
# =========================================================

def get_files(prefix, search_dir):
    """
    Return a sorted list of all  <prefix>_N.mat  files
    found in `search_dir`.
    """
    pattern = os.path.join(search_dir, f"{prefix}_*.mat")
    return sorted(glob.glob(pattern))


def resolve_search_dir(raw_input, prefix):
    """
    Turn the user's path input into an absolute directory path.

    Rules
    -----
    - Empty string (just Enter)  -> root directory of the repo
    - 'dataset'                  -> <root>/dataset/<prefix>/
    - Any other relative path    -> resolved relative to repo root
    - Absolute path              -> used as-is
    """
    root = os.path.dirname(os.path.abspath(__file__))
    # loadmatfile.py lives at the project root; lib/mat_loader.py is one
    # level deeper, so we need to go up one extra level from here.
    root = os.path.dirname(root)   # project root

    if raw_input.strip() == "":
        # Default: root directory (where legacy .mat files live)
        return root

    path = raw_input.strip()

    # Convenience shorthand: just typing "dataset" expands to the
    # canonical dataset sub-folder for this prefix.
    if path.lower() in ("dataset", "dataset/", "dataset\\"):
        return os.path.join(root, "dataset", prefix)

    # Otherwise treat as relative-to-root or absolute
    if not os.path.isabs(path):
        path = os.path.join(root, path)

    return os.path.normpath(path)


# =========================================================
# PLOTTING
# =========================================================

def plot_mat_file(mat_file):
    """Load and plot a single .mat file, auto-detecting its type."""
    print(f"\n[LOADING] {mat_file}")

    try:
        data = sio.loadmat(mat_file)
    except Exception as e:
        print(f"[ERROR] Could not load file: {e}")
        return

    plt.figure(figsize=(12, 4))
    fname = os.path.basename(mat_file)

    if "fsr1" in data:
        t = data["t"].flatten()
        plt.plot(t, data["fsr1"].flatten(), label="FSR1")
        plt.plot(t, data["fsr2"].flatten(), label="FSR2")
        plt.plot(t, data["fsr3"].flatten(), label="FSR3")
        plt.title(f"FSR Pressure Data  |  {fname}")

    elif "p1" in data:
        t = data["t"].flatten()
        plt.plot(t, data["p1"].flatten(),   label="IMU1 pitch")
        plt.plot(t, data["p2"].flatten(),   label="IMU2 pitch")
        plt.plot(t, data["pavg"].flatten(), label="Average")
        plt.title(f"IMU Pitch Angles  |  {fname}")

    elif "ax1" in data:
        t = data["t"].flatten()
        plt.plot(t, data["ax1"].flatten(), label="ax1")
        plt.plot(t, data["ay1"].flatten(), label="ay1")
        plt.plot(t, data["az1"].flatten(), label="az1")
        plt.plot(t, data["ax2"].flatten(), label="ax2")
        plt.plot(t, data["ay2"].flatten(), label="ay2")
        plt.plot(t, data["az2"].flatten(), label="az2")
        plt.title(f"IMU Acceleration  |  {fname}")

    elif "dx1" in data:
        t = data["t"].flatten()
        plt.plot(t, data["dx1"].flatten(), label="dx1")
        plt.plot(t, data["dy1"].flatten(), label="dy1")
        plt.plot(t, data["dz1"].flatten(), label="dz1")
        plt.plot(t, data["dx2"].flatten(), label="dx2")
        plt.plot(t, data["dy2"].flatten(), label="dy2")
        plt.plot(t, data["dz2"].flatten(), label="dz2")
        plt.title(f"IMU Derivatives  |  {fname}")

    else:
        print("[WARNING] Unknown .mat format — cannot plot.")
        plt.close()
        return

    plt.xlabel("Time (s)")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True, alpha=0.35)
    plt.tight_layout()
    plt.show()


# =========================================================
# LEGACY HELPERS  (kept for backward-compat)
# =========================================================

def load_latest(prefix, search_dir="."):
    files = get_files(prefix, search_dir)
    if not files:
        print(f"[ERROR] No files matching '{prefix}_*.mat' in {search_dir}")
        return
    plot_mat_file(files[-1])