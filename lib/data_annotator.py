import numpy as np
import scipy.io as sio
import os
import matplotlib.pyplot as plt


# ================= CONFIG =================
DATASET_DIR = "dataset"
ANNOTATED_DIR = "annotated"

WINDOW_SECONDS = 3   # optional (not strictly needed for labeling)


# ================= LOADERS =================
def load_imu(index):
    data = sio.loadmat(f"{DATASET_DIR}/IMU_data/IMU_data_{index}.mat")
    return data["t"].flatten(), data["pavg"].flatten()


def load_fsr(index):
    path = f"{DATASET_DIR}/FSR_data/FSR_data_{index}.mat"
    if not os.path.exists(path):
        return None, None, None
    data = sio.loadmat(path)
    return (
        data["fsr1"].flatten(),
        data["fsr2"].flatten(),
        data["fsr3"].flatten()
    )


# ================= IMU LABELING =================
def label_from_imu(pavg):
    dp = np.gradient(pavg)
    labels = np.zeros(len(pavg), dtype=int)

    threshold = np.std(dp) * 0.2

    for i in range(1, len(pavg) - 1):

        # Heel strike (peak)
        if dp[i - 1] > 0 and dp[i] <= 0 and abs(dp[i - 1]) > threshold:
            labels[i] = 1

        # Toe-off (valley)
        elif dp[i - 1] < 0 and dp[i] >= 0 and abs(dp[i - 1]) > threshold:
            labels[i] = 3

        # Stance (low motion)
        elif abs(dp[i]) < threshold * 0.5:
            labels[i] = 2

        else:
            labels[i] = 0

    return labels


# ================= FSR LABELING =================
def label_from_fsr(fsr1, fsr2, fsr3):
    labels = np.zeros(len(fsr1), dtype=int)

    for i in range(len(fsr1)):

        total = fsr1[i] + fsr2[i] + fsr3[i]

        # Swing
        if total < 300:
            labels[i] = 0

        # Heel strike
        elif fsr1[i] > fsr2[i] and fsr1[i] > fsr3[i] and fsr1[i] > 2000:
            labels[i] = 1

        # Toe-off
        elif fsr2[i] > 2500 or fsr3[i] > 2500:
            labels[i] = 3

        # Stance
        else:
            labels[i] = 2

    return labels


# ================= RECONCILIATION =================
def reconcile_labels(imu_labels, fsr_labels):
    final = np.zeros(len(imu_labels), dtype=int)

    for i in range(len(imu_labels)):
        if imu_labels[i] == fsr_labels[i]:
            final[i] = imu_labels[i]
        else:
            # prioritize FSR if strong signal
            final[i] = fsr_labels[i]

    return final


# ================= VISUALIZATION =================
def plot_annotated(t, pavg, labels, index):

    colors = {
        0: "yellow",   # swing
        1: "red",      # heel strike
        2: "green",    # stance
        3: "orange"    # toe-off
    }

    plt.figure(figsize=(12, 4))

    for i in range(len(t) - 1):
        plt.plot(t[i:i+2], pavg[i:i+2], color=colors[labels[i]])

    plt.title(f"Annotated IMU Data {index}")
    plt.xlabel("Time")
    plt.ylabel("pavg")

    os.makedirs(ANNOTATED_DIR, exist_ok=True)
    plt.savefig(f"{ANNOTATED_DIR}/annotated_{index}.png")
    plt.close()


# ================= SAVE =================
def save_labels(t, labels, index):
    os.makedirs(ANNOTATED_DIR, exist_ok=True)

    sio.savemat(
        f"{ANNOTATED_DIR}/labels_{index}.mat",
        {
            "t": t,
            "labels": labels
        }
    )


# ================= PROCESS ONE =================
def process_one(index):

    print(f"[PROCESSING] {index}")

    t, pavg = load_imu(index)

    imu_labels = label_from_imu(pavg)

    fsr1, fsr2, fsr3 = load_fsr(index)

    if fsr1 is not None:
        fsr_labels = label_from_fsr(fsr1, fsr2, fsr3)
        labels = reconcile_labels(imu_labels, fsr_labels)
    else:
        labels = imu_labels

    plot_annotated(t, pavg, labels, index)
    save_labels(t, labels, index)

    print(f"[DONE] {index}")


# ================= BATCH PROCESS =================
def process_all():

    files = os.listdir(f"{DATASET_DIR}/IMU_data")

    indices = [
        int(f.split("_")[-1].split(".")[0])
        for f in files if f.startswith("IMU_data")
    ]

    indices.sort()

    for idx in indices:
        process_one(idx)


# ================= MAIN =================
if __name__ == "__main__":

    MODE = "single"   # "single" or "batch"
    TARGET_INDEX = 1

    if MODE == "single":
        process_one(TARGET_INDEX)

    else:
        process_all()