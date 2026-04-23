import scipy.io as sio
import matplotlib.pyplot as plt
import glob
import os


# ================= CORE PLOT FUNCTION =================
def plot_mat_file(mat_file):
    print(f"[LOADING] {mat_file}")

    data = sio.loadmat(mat_file)

    plt.figure(figsize=(10, 4))

    if "fsr1" in data:
        t = data["t"].flatten()

        plt.plot(t, data["fsr1"].flatten(), label="FSR1 (Toe)")
        plt.plot(t, data["fsr2"].flatten(), label="FSR2 (Ankle)")
        plt.plot(t, data["fsr3"].flatten(), label="FSR3 (Toe)")

        plt.title(f"FSR Data → {os.path.basename(mat_file)}")

    elif "p1" in data:
        t = data["t"].flatten()

        plt.plot(t, data["p1"].flatten(), label="IMU1")
        plt.plot(t, data["p2"].flatten(), label="IMU2")
        plt.plot(t, data["pavg"].flatten(), label="AVG")

        plt.title(f"IMU Angles → {os.path.basename(mat_file)}")

    else:
        print("[WARNING] Unknown MAT format")
        return

    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True)
    plt.show()


# ================= GET FILE LIST =================
def get_files(prefix):
    files = sorted(glob.glob(f"{prefix}_*.mat"))
    return files


# ================= LOAD MODES =================
def load_single(prefix, index):
    file = f"{prefix}_{index}.mat"

    if not os.path.exists(file):
        print(f"[ERROR] File not found: {file}")
        return

    get_sample_count(file)   # ← ADD THIS
    plot_mat_file(file)


def load_range(prefix, start, end):
    for i in range(start, end + 1):
        file = f"{prefix}_{i}.mat"

        if os.path.exists(file):
            plot_mat_file(file)
        else:
            print(f"[SKIP] {file} not found")


def load_all(prefix):
    files = get_files(prefix)

    if not files:
        print("[ERROR] No files found")
        return

    for f in files:
        plot_mat_file(f)


def load_latest(prefix):
    files = get_files(prefix)

    if not files:
        print("[ERROR] No files found")
        return

    latest = files[-1]

    get_sample_count(latest)   # ← ADD THIS
    plot_mat_file(latest)

# ================= SAMPLE COUNT =================
def get_sample_count(mat_file):
    print(f"[COUNTING] {mat_file}")

    data = sio.loadmat(mat_file)

    # Prefer time vector if available
    if "t" in data:
        count = len(data["t"].flatten())
        print(f"[SAMPLES] {count}")
        return count

    # Fallback: infer from any array
    for key in data:
        if not key.startswith("__"):
            try:
                arr = data[key]
                if hasattr(arr, "shape") and len(arr.shape) > 0:
                    count = arr.shape[0]
                    print(f"[SAMPLES] {count} (from '{key}')")
                    return count
            except:
                continue

    print("[WARNING] Could not determine sample count")
    return None