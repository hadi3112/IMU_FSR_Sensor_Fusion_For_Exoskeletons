import numpy as np
import scipy.io as sio
import os


# ================= FILE HANDLING =================
def get_next_filename(prefix):
    i = 1
    while True:
        fname = f"{prefix}_{i}.mat"
        if not os.path.exists(fname):
            return fname
        i += 1


# ================= LOAD IMU =================
def load_imu_file(filename):
    data = sio.loadmat(filename)

    t = data["t"].flatten()
    pavg = data["pavg"].flatten()

    return t, pavg


# ================= GAIT EVENT DETECTION =================
def detect_gait_events(pavg):
    dp = np.gradient(pavg)
    threshold = np.std(pavg) * 0.15

    heel_strikes = []
    toe_offs = []

    for i in range(1, len(dp) - 1):

        # Peak → start of descending → heel strike region
        if dp[i-1] > 0 and dp[i] <= 0 and abs(dp[i-1]) > threshold:
            heel_strikes.append(i)

        # Valley → start of rising → toe-off
        if dp[i-1] < 0 and dp[i] >= 0 and abs(dp[i-1]) > threshold:
            toe_offs.append(i)

    return heel_strikes, toe_offs


# ================= MAIN GENERATOR =================
def generate_fsr(t, pavg, decay_rate=0.02):
    n = len(t)

    fsr1 = np.zeros(n)
    fsr2 = np.zeros(n)
    fsr3 = np.zeros(n)

    heel_strikes, toe_offs = detect_gait_events(pavg)

    # ensure matching pairs
    events = sorted(heel_strikes + toe_offs)

    # ================= STATE MACHINE =================
    for i in range(len(events) - 1):
        start = events[i]
        end = events[i + 1]

        segment_len = end - start
        if segment_len <= 5:
            continue

        # random variability
        amp_scale = np.random.uniform(0.8, 1.2)
        noise_scale = np.random.uniform(50, 120)

        for j in range(start, end):
            phase = (j - start) / segment_len

            # ===== HEEL STRIKE REGION =====
            if phase < 0.15:
                fsr1[j] = np.random.uniform(2500, 4000) * amp_scale * (phase / 0.15)
                fsr2[j] = np.random.uniform(0, 300)
                fsr3[j] = np.random.uniform(0, 150)

            # ===== LOADING =====
            elif phase < 0.4:
                fsr1[j] = np.random.uniform(1800, 3000) * amp_scale
                fsr2[j] = np.random.uniform(1500, 3200) * amp_scale * (phase - 0.15) / 0.25
                fsr3[j] = np.random.uniform(1200, 2800) * amp_scale * (phase - 0.15) / 0.25

            # ===== STANCE =====
            elif phase < 0.7:
                fsr1[j] = np.random.uniform(1200, 2500) * amp_scale
                fsr2[j] = np.random.uniform(2500, 3800) * amp_scale
                fsr3[j] = fsr2[j] - np.random.uniform(50, 300)

            # ===== TOE OFF =====
            elif phase < 0.9:
                fsr1[j] = np.random.uniform(0, 500)
                fsr2[j] = np.random.uniform(3000, 3800) * amp_scale
                fsr3[j] = fsr2[j] - np.random.uniform(20, 150)

            # ===== SWING (DECAY) =====
            else:
                decay = np.exp(-decay_rate * (j - start))
                fsr1[j] *= decay
                fsr2[j] *= decay
                fsr3[j] *= decay

    # ================= NOISE =================
    noise = np.random.normal(0, 80, n)
    fsr1 += noise
    fsr2 += noise
    fsr3 += noise

    # ================= ARTIFACTS =================
    for _ in range(int(n * 0.02)):
        idx = np.random.randint(0, n)
        spike = np.random.uniform(200, 500)
        fsr1[idx] += spike
        fsr2[idx] += spike
        fsr3[idx] += spike

    for _ in range(int(n * 0.02)):
        idx = np.random.randint(0, n)
        dip = np.random.uniform(200, 400)
        fsr1[idx] -= dip
        fsr2[idx] -= dip
        fsr3[idx] -= dip

    # ================= CLAMP =================
    fsr1 = np.clip(fsr1, 0, 4095)
    fsr2 = np.clip(fsr2, 0, 4095)
    fsr3 = np.clip(fsr3, 0, 4095)

    return fsr1, fsr2, fsr3


# ================= MAIN EXECUTION =================
if __name__ == "__main__":

    imu_file = "IMU_data_7.mat"                  # <--- change as needed

    print(f"[LOADING] {imu_file}")
    t, pavg = load_imu_file(imu_file)

    print("[GENERATING FSR DATA]")
    fsr1, fsr2, fsr3 = generate_fsr(
        t,
        pavg,
        decay_rate=0.03   # <-- tunable parameter
    )

    fsr_data = {
        "t": t,
        "fsr1": fsr1,
        "fsr2": fsr2,
        "fsr3": fsr3
    }

    out_file = get_next_filename("FSR_data")
    sio.savemat(out_file, fsr_data)

    print(f"[SAVED] {out_file}")