import paho.mqtt.client as mqtt
import json
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import time
import numpy as np

# ======== Previous values for derivatives =========
prev_vals = {
    "imu1_ax": None, "imu1_ay": None, "imu1_az": None,
    "imu2_ax": None, "imu2_ay": None, "imu2_az": None,
}

# ======== Feature buffer =========
feature_buffer = deque(maxlen=500)

# ======== MQTT Config =========
BROKER = "10.42.0.1"
PORT   = 1883
TOPIC  = "esp32/imu"

# ======== Buffers — Angles =========
timestamps = deque(maxlen=500)
pitch_imu1 = deque(maxlen=500)
pitch_imu2 = deque(maxlen=500)
pitch_avg  = deque(maxlen=500)

# ======== Buffers — Derivatives =========
deriv_timestamps = deque(maxlen=500)
dx1_buf = deque(maxlen=500)
dy1_buf = deque(maxlen=500)
dz1_buf = deque(maxlen=500)
dx2_buf = deque(maxlen=500)
dy2_buf = deque(maxlen=500)
dz2_buf = deque(maxlen=500)

start_time = time.time()

# ======================================================
# LOW-PASS FILTER CONFIG
# -------------------------------------------------------
# ALPHA controls smoothing strength for derivatives:
#   Lower  = smoother but more lag  (e.g. 0.1)
#   Higher = less smooth, more responsive (e.g. 0.5)
#
# To DISABLE filtering on derivatives entirely,
# set FILTER_DERIVATIVES = False — no other changes needed.
# ======================================================
FILTER_DERIVATIVES = True
DERIV_ALPHA = 0.2

# ---- Previous filtered derivative values (for low-pass state) ----
prev_deriv = {
    "dx1": 0.0, "dy1": 0.0, "dz1": 0.0,
    "dx2": 0.0, "dy2": 0.0, "dz2": 0.0,
}

def low_pass_filter(prev, new, alpha=0.2):
    """
    Exponential moving average low-pass filter.
    alpha=1.0 → no filtering (raw passthrough)
    alpha→0   → heavy smoothing
    """
    return alpha * new + (1 - alpha) * prev

def filter_derivative(key, raw_value):
    """
    Apply low-pass filter to a derivative value if FILTER_DERIVATIVES is True.
    Otherwise returns the raw value unchanged.

    To disable:  set FILTER_DERIVATIVES = False at the top of the file.
    To re-enable: set FILTER_DERIVATIVES = True.
    """
    if not FILTER_DERIVATIVES:
        return raw_value  # ← passthrough, no filtering applied

    smoothed = low_pass_filter(prev_deriv[key], raw_value, alpha=DERIV_ALPHA)
    prev_deriv[key] = smoothed
    return smoothed

def build_feature_vector(ax1, ay1, az1, ax2, ay2, az2, prev_vals):
    # ---- Compute raw derivatives ----
    dx1_raw = compute_derivative(prev_vals, "imu1_ax", ax1)
    dy1_raw = compute_derivative(prev_vals, "imu1_ay", ay1)
    dz1_raw = compute_derivative(prev_vals, "imu1_az", az1)
    dx2_raw = compute_derivative(prev_vals, "imu2_ax", ax2)
    dy2_raw = compute_derivative(prev_vals, "imu2_ay", ay2)
    dz2_raw = compute_derivative(prev_vals, "imu2_az", az2)

    # ---- Apply derivative filter (toggle via FILTER_DERIVATIVES flag) ----
    dx1 = filter_derivative("dx1", dx1_raw)
    dy1 = filter_derivative("dy1", dy1_raw)
    dz1 = filter_derivative("dz1", dz1_raw)
    dx2 = filter_derivative("dx2", dx2_raw)
    dy2 = filter_derivative("dy2", dy2_raw)
    dz2 = filter_derivative("dz2", dz2_raw)

    # ---- Placeholder FSR values (3 per foot = 6 total) ----
    fsr_values = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    feature_vector = [
        # IMU1 raw accelerations
        ax1, ay1, az1,
        # IMU2 raw accelerations
        ax2, ay2, az2,
        # IMU1 derivatives (filtered or raw depending on flag)
        dx1, dy1, dz1,
        # IMU2 derivatives (filtered or raw depending on flag)
        dx2, dy2, dz2,
        # FSR placeholders
        *fsr_values
    ]

    return feature_vector, dx1, dy1, dz1, dx2, dy2, dz2

def compute_derivative(prev_dict, key, current_value):
    prev = prev_dict[key]
    if prev is None:
        prev_dict[key] = current_value
        return 0.0  # first sample has no previous → return zero
    derivative = current_value - prev
    prev_dict[key] = current_value
    return derivative

# ======== Low-pass filter state for pitch angles =========
prev_p1 = 0
prev_p2 = 0

# ======== Calibration =========
CALIB_DURATION = 3.0
calib_samples  = []
bias1 = 0
bias2 = 0
calibrated = False

# ======== MQTT Callbacks =========
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT broker at {BROKER}")
        client.subscribe(TOPIC)
    else:
        print(f"Connection failed with code {rc}")

def on_message(client, userdata, msg):
    global prev_p1, prev_p2, bias1, bias2, calibrated, calib_samples

    try:
        payload = json.loads(msg.payload.decode())
        print(payload)
        elapsed = time.time() - start_time

        # ---- Phase 1: Collect calibration samples for first CALIB_DURATION seconds ----
        if not calibrated and elapsed < CALIB_DURATION:
            if "imu1" in payload and "imu2" in payload:
                p1 = payload["imu1"].get("pitch", None)
                p2 = payload["imu2"].get("pitch", None)
                if p1 is not None and p2 is not None:
                    p2 = -p2  # mirror correction before storing
                    calib_samples.append((p1, p2))
            return

        # ---- Phase 2: Compute bias from collected samples ----
        if not calibrated and len(calib_samples) > 10:
            bias1 = np.mean([x[0] for x in calib_samples])
            bias2 = np.mean([x[1] for x in calib_samples])
            calibrated = True
            print(f"Calibration done → bias1={bias1:.2f}°, bias2={bias2:.2f}°")
            print(f"Derivative filtering: {'ON  (alpha={})'.format(DERIV_ALPHA) if FILTER_DERIVATIVES else 'OFF (raw)'}")
            return

        if not calibrated:
            return

        # ---- Guard: both IMUs must be present ----
        if "imu1" not in payload or "imu2" not in payload:
            return

        imu1 = payload["imu1"]
        imu2 = payload["imu2"]

        p1 = imu1.get("pitch", None)
        p2 = imu2.get("pitch", None)

        if p1 is None or p2 is None:
            return

        # ---- Extract raw acceleration values ----
        ax1 = imu1.get("accel_x", None)
        ay1 = imu1.get("accel_y", None)
        az1 = imu1.get("accel_z", None)
        ax2 = imu2.get("accel_x", None)
        ay2 = imu2.get("accel_y", None)
        az2 = imu2.get("accel_z", None)

        if None in [ax1, ay1, az1, ax2, ay2, az2]:
            return

        # ---- Build feature vector with raw accel + filtered derivatives ----
        feature_vector, dx1, dy1, dz1, dx2, dy2, dz2 = build_feature_vector(
            ax1, ay1, az1,
            ax2, ay2, az2,
            prev_vals
        )
        feature_buffer.append(feature_vector)

        # ---- Store derivatives for plotting ----
        deriv_timestamps.append(elapsed)
        dx1_buf.append(dx1)
        dy1_buf.append(dy1)
        dz1_buf.append(dz1)
        dx2_buf.append(dx2)
        dy2_buf.append(dy2)
        dz2_buf.append(dz2)

        # ---- Align IMU2 (physically mirrored mounting) ----
        p2 = -p2

        # ---- Remove standing bias ----
        p1 = p1 - bias1
        p2 = p2 - bias2

        # ---- Smooth pitch angles with low-pass filter ----
        p1 = low_pass_filter(prev_p1, p1)
        p2 = low_pass_filter(prev_p2, p2)
        prev_p1 = p1
        prev_p2 = p2

        # ---- Control signal: differential average ----
        p_avg = (p1 - p2) / 2.0

        # ---- Store angles ----
        timestamps.append(elapsed)
        pitch_imu1.append(p1)
        pitch_imu2.append(p2)
        pitch_avg.append(p_avg)

        # ---- Console output: angles + live range ----
        p1_range = (min(pitch_imu1), max(pitch_imu1))
        p2_range = (min(pitch_imu2), max(pitch_imu2))
        print(
            f"t={elapsed:6.1f}s | "
            f"IMU1={p1:+6.2f}°  [{p1_range[0]:+6.2f}, {p1_range[1]:+6.2f}] | "
            f"IMU2={p2:+6.2f}°  [{p2_range[0]:+6.2f}, {p2_range[1]:+6.2f}] | "
            f"avg={p_avg:+6.2f}°"
        )

    except Exception as e:
        print(f"Error: {e}")

# ======== Figure 1 — Angle Plot =========
fig1, ax1_plot = plt.subplots(figsize=(13, 5))
fig1.canvas.manager.set_window_title("Thigh Pitch Angles")
ax1_plot.set_title("Fused Thigh Pitch Angle (IMU1, IMU2, Average)", fontsize=14)
ax1_plot.set_xlabel("Time (seconds)")
ax1_plot.set_ylabel("Pitch (degrees)")
ax1_plot.set_ylim(-40, 40)
ax1_plot.axhline(0, color='gray', linestyle='--', linewidth=1)
ax1_plot.grid(True, alpha=0.3)

line_imu1, = ax1_plot.plot([], [], color='blue',   linewidth=1.5, alpha=0.6, label='IMU 1')
line_imu2, = ax1_plot.plot([], [], color='orange', linewidth=1.5, alpha=0.6, label='IMU 2')
line_avg,  = ax1_plot.plot([], [], color='green',  linewidth=3,               label='Average (Control)')
ax1_plot.legend(loc='upper left')

# ======== Figure 2 — Derivative Plot =========
fig2, (ax_d1, ax_d2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
fig2.canvas.manager.set_window_title("Acceleration Derivatives")

# Title reflects current filter state
deriv_title = (
    f"Acceleration Derivatives — filter ON (alpha={DERIV_ALPHA})"
    if FILTER_DERIVATIVES else
    "Acceleration Derivatives — filter OFF (raw)"
)
fig2.suptitle(deriv_title, fontsize=13)

ax_d1.set_title("IMU 1 Derivatives")
ax_d1.set_ylabel("dAccel (m/s² per sample)")
ax_d1.set_ylim(-5, 5)
ax_d1.axhline(0, color='gray', linestyle='--', linewidth=1)
ax_d1.grid(True, alpha=0.3)
line_dx1, = ax_d1.plot([], [], color='red',   linewidth=1.5, label='dX1')
line_dy1, = ax_d1.plot([], [], color='green', linewidth=1.5, label='dY1')
line_dz1, = ax_d1.plot([], [], color='blue',  linewidth=1.5, label='dZ1')
ax_d1.legend(loc='upper left')

ax_d2.set_title("IMU 2 Derivatives")
ax_d2.set_xlabel("Time (seconds)")
ax_d2.set_ylabel("dAccel (m/s² per sample)")
ax_d2.set_ylim(-5, 5)
ax_d2.axhline(0, color='gray', linestyle='--', linewidth=1)
ax_d2.grid(True, alpha=0.3)
line_dx2, = ax_d2.plot([], [], color='red',   linewidth=1.5, label='dX2')
line_dy2, = ax_d2.plot([], [], color='green', linewidth=1.5, label='dY2')
line_dz2, = ax_d2.plot([], [], color='blue',  linewidth=1.5, label='dZ2')
ax_d2.legend(loc='upper left')

# ======== Animation — Angles =========
def update_angle_plot(frame):
    if timestamps:
        line_imu1.set_data(timestamps, [-v for v in pitch_imu1])
        line_imu2.set_data(timestamps, pitch_imu2)
        line_avg.set_data(timestamps,  [-v for v in pitch_avg])
        ax1_plot.set_xlim(max(0, timestamps[-1] - 10), timestamps[-1] + 1)
    return line_imu1, line_imu2, line_avg

# ======== Animation — Derivatives =========
def update_deriv_plot(frame):
    if deriv_timestamps:
        t    = deriv_timestamps
        xmin = max(0, t[-1] - 10)
        xmax = t[-1] + 1

        line_dx1.set_data(t, dx1_buf)
        line_dy1.set_data(t, dy1_buf)
        line_dz1.set_data(t, dz1_buf)

        line_dx2.set_data(t, dx2_buf)
        line_dy2.set_data(t, dy2_buf)
        line_dz2.set_data(t, dz2_buf)

        ax_d1.set_xlim(xmin, xmax)
        ax_d2.set_xlim(xmin, xmax)

    return line_dx1, line_dy1, line_dz1, line_dx2, line_dy2, line_dz2

# ======== MQTT Client =========
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, keepalive=60)
mqtt_client.loop_start()

# ======== Run Both Animations =========
ani1 = animation.FuncAnimation(fig1, update_angle_plot, interval=100, blit=False)
ani2 = animation.FuncAnimation(fig2, update_deriv_plot, interval=100, blit=False)

print("Live plot running...")
plt.tight_layout()
plt.show()

mqtt_client.loop_stop()
mqtt_client.disconnect()