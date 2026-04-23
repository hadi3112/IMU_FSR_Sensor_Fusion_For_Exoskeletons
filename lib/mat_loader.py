import scipy.io as sio
import matplotlib.pyplot as plt
import glob
import os


def plot_mat_file(mat_file):
    print(f"[LOADING] {mat_file}")

    data = sio.loadmat(mat_file)
    plt.figure(figsize=(10, 4))

    if "fsr1" in data:
        t = data["t"].flatten()
        plt.plot(t, data["fsr1"].flatten(), label="FSR1")
        plt.plot(t, data["fsr2"].flatten(), label="FSR2")
        plt.plot(t, data["fsr3"].flatten(), label="FSR3")
        plt.title(f"FSR Data → {os.path.basename(mat_file)}")

    elif "p1" in data:
        t = data["t"].flatten()
        plt.plot(t, data["p1"].flatten(), label="IMU1")
        plt.plot(t, data["p2"].flatten(), label="IMU2")
        plt.plot(t, data["pavg"].flatten(), label="AVG")
        plt.title(f"IMU Angles → {os.path.basename(mat_file)}")

    elif "ax1" in data:
        t = data["t"].flatten()
        plt.plot(t, data["ax1"].flatten(), label="ax1")
        plt.plot(t, data["ay1"].flatten(), label="ay1")
        plt.plot(t, data["az1"].flatten(), label="az1")
        plt.plot(t, data["ax2"].flatten(), label="ax2")
        plt.plot(t, data["ay2"].flatten(), label="ay2")
        plt.plot(t, data["az2"].flatten(), label="az2")
        plt.title(f"IMU Acceleration → {os.path.basename(mat_file)}")

    elif "dx1" in data:
        t = data["t"].flatten()
        plt.plot(t, data["dx1"].flatten(), label="dx1")
        plt.plot(t, data["dy1"].flatten(), label="dy1")
        plt.plot(t, data["dz1"].flatten(), label="dz1")
        plt.plot(t, data["dx2"].flatten(), label="dx2")
        plt.plot(t, data["dy2"].flatten(), label="dy2")
        plt.plot(t, data["dz2"].flatten(), label="dz2")
        plt.title(f"IMU Derivatives → {os.path.basename(mat_file)}")

    else:
        print("[WARNING] Unknown MAT format")
        return

    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True)
    plt.show()


def get_files(prefix):
    return sorted(glob.glob(f"{prefix}_*.mat"))


def load_latest(prefix):
    files = get_files(prefix)
    if not files:
        print("[ERROR] No files found")
        return

    latest = files[-1]
    plot_mat_file(latest)