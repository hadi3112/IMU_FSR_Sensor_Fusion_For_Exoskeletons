import numpy as np
import scipy.io as sio
import os
import matplotlib.pyplot as plt
from getSamplingFreq import estimate_fs


# ================= CONFIG =================
DATASET_DIR = "dataset"
ANNOTATED_DIR = "annotated"

WINDOW_SECONDS = 2
OVERLAP = 0.2

def print_gait_color_table():
    print("\n[GAIT PHASE COLOR MAP]")
    print("--------------------------------")
    print("0 : SWING        -> yellow")
    print("1 : HEEL_STRIKE  -> red")
    print("2 : STANCE       -> green")
    print("3 : TOE_OFF      -> orange")
    print("--------------------------------\n")

# =================PLOTTING =================
def save_labels(t, labels, index):
    os.makedirs(ANNOTATED_DIR, exist_ok=True)

    sio.savemat(
        f"{ANNOTATED_DIR}/labels_{index}.mat",
        {
            "t": t,
            "labels": labels
        }
    )

def plot_annotated(t, pavg, labels, index):

    colors = {
        0: "yellow",
        1: "red",
        2: "green",
        3: "orange"
    }

    plt.figure(figsize=(12, 4))

    for i in range(len(t) - 1):
        plt.plot(t[i:i+2], pavg[i:i+2], color=colors[labels[i]])

    os.makedirs(ANNOTATED_DIR, exist_ok=True)

    plt.savefig(f"{ANNOTATED_DIR}/annotated_{index}.png")
    plt.close()

# ================= LOADERS =================
def load_imu(index):
    data = sio.loadmat(f"{DATASET_DIR}/IMU_data/IMU_data_{index}.mat")
    return data["t"].flatten(), data["pavg"].flatten()


def load_fsr(index):
    path = f"{DATASET_DIR}/FSR_data/FSR_data_{index}.mat"
    if not os.path.exists(path):
        return None, None, None

    data = sio.loadmat(path)
    return data["fsr1"].flatten(), data["fsr2"].flatten(), data["fsr3"].flatten()


# ================= FS INFO =================
def get_fs_info(t):
    FS, N, duration, dt_stats = estimate_fs(t)
    return FS, N, duration, dt_stats


# ================= IMU LABELING =================
def label_from_imu(pavg, window_size):

    dp = np.gradient(pavg)
    votes = np.zeros((len(pavg), 4))

    step_size = int(window_size * (1 - OVERLAP))
    if step_size < 1:
        step_size = 1

    threshold = np.std(dp) * 0.2
    low_motion = threshold * 0.5

    for start in range(0, len(pavg) - window_size, step_size):

        end = start + window_size
        window_dp = dp[start:end]

        if len(window_dp) == 0:
            continue

        mean_motion = np.mean(np.abs(window_dp))
        max_dp = np.max(window_dp)
        min_dp = np.min(window_dp)

        if max_dp > threshold:
            w_label = 1
        elif min_dp < -threshold:
            w_label = 3
        elif mean_motion < low_motion:
            w_label = 2
        else:
            w_label = 2

        votes[start:end, w_label] += 1

    return np.argmax(votes, axis=1)


# ================= FSR LABELING =================
def label_from_fsr(fsr1, fsr2, fsr3):

    labels = np.zeros(len(fsr1), dtype=int)

    for i in range(len(fsr1)):

        total = fsr1[i] + fsr2[i] + fsr3[i]

        if total < 300:
            labels[i] = 0
        elif fsr1[i] > fsr2[i] and fsr1[i] > fsr3[i] and fsr1[i] > 2000:
            labels[i] = 1
        elif fsr2[i] > 2500 or fsr3[i] > 2500:
            labels[i] = 3
        else:
            labels[i] = 2

    return labels


# ================= RECONCILIATION =================
def reconcile_labels(imu_labels, fsr_labels):
    return np.where(imu_labels == fsr_labels, imu_labels, fsr_labels)


# ================= TEMPOREAL STRUCTURE ENFORCEMENT =================
VALID_TRANSITIONS = {
    0: [1],     # SWING → HEEL_STRIKE
    1: [2],     # HEEL_STRIKE → STANCE
    2: [3],     # STANCE → TOE_OFF only
    3: [0]      # TOE_OFF → SWING
}


def enforce_temporal_structure(labels):

    cleaned = labels.copy()

    for i in range(1, len(labels)):
        prev = cleaned[i - 1]
        curr = cleaned[i]

        if curr not in VALID_TRANSITIONS.get(prev, []):
            cleaned[i] = prev  # force valid continuity

    return cleaned


# ================= SCORE (FIXED VERSION) =================
def compress(labels):
    """remove consecutive duplicates"""
    out = [labels[0]]
    for l in labels[1:]:
        if l != out[-1]:
            out.append(l)
    return np.array(out)


def score_sequence(labels):

    labels = compress(labels)  # CRITICAL FIX

    invalid = 0

    for i in range(1, len(labels)):
        prev = labels[i - 1]
        curr = labels[i]

        if curr not in VALID_TRANSITIONS.get(prev, []):
            invalid += 1

    return invalid, len(labels)


# ================= PROCESS ONE =================
def process_one(index):

    print(f"[PROCESSING] {index}")

    t, pavg = load_imu(index)

    FS, N, duration, dt_stats = get_fs_info(t)

    window_size = int(WINDOW_SECONDS * FS)

    print(f"FS = {FS:.2f} Hz | Samples = {N} | Window = {window_size}")

    imu_labels = label_from_imu(pavg, window_size)

    fsr1, fsr2, fsr3 = load_fsr(index)

    if fsr1 is not None:
        fsr_labels = label_from_fsr(fsr1, fsr2, fsr3)
        labels = reconcile_labels(imu_labels, fsr_labels)
    else:
        labels = imu_labels

    # enforce structure
    labels = enforce_temporal_structure(labels)

    # optional debug score
    invalid, length = score_sequence(labels)
    print(f"[SEQ SCORE] invalid transitions = {invalid} | events = {length}")

    print(f"[DONE] {index}")

    plot_annotated(t, pavg, labels, index)
    save_labels(t, labels, index)


# ================= MAIN =================
if __name__ == "__main__":

    MODE = "single"
    TARGET_INDEX = 10

    print_gait_color_table()

    if MODE == "single":
        process_one(TARGET_INDEX)
    else:
        for i in range(1, 10):
            process_one(i)