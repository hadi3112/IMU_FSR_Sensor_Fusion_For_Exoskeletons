import os
import scipy.io as sio
import matplotlib.pyplot as plt


def get_latest_file(prefix):
    files = [f for f in os.listdir('.') if f.startswith(prefix) and f.endswith('.mat')]

    if not files:
        print(f"[LOADER] No files found for prefix: {prefix}")
        return None

    # Extract numeric suffix safely
    def extract_num(f):
        try:
            return int(f.split('_')[-1].replace('.mat', ''))
        except:
            return -1

    files.sort(key=extract_num)

    latest = files[-1]
    print(f"[LOADER] Loading latest file: {latest}")
    return latest


def load_and_plot_latest(mode="FSR"):
    prefix = "FSR_data" if mode == "FSR" else "IMU_data"

    file = get_latest_file(prefix)
    if file is None:
        return

    data = sio.loadmat(file)

    plt.figure(figsize=(10, 4))

    if mode == "FSR":
        plt.plot(data["t"].flatten(), data["fsr1"].flatten(), label="FSR1 (Toe)")
        plt.plot(data["t"].flatten(), data["fsr2"].flatten(), label="FSR2 (Ankle)")
        plt.plot(data["t"].flatten(), data["fsr3"].flatten(), label="FSR3 (Toe)")
        plt.title("Latest FSR Data")

    elif mode == "IMU":
        plt.plot(data["t"].flatten(), data["p1"].flatten(), label="IMU1")
        plt.plot(data["t"].flatten(), data["p2"].flatten(), label="IMU2")
        plt.plot(data["t"].flatten(), data["pavg"].flatten(), label="AVG")
        plt.title("Latest IMU Data")

    plt.legend()
    plt.grid()
    plt.show()