import paho.mqtt.client as mqtt
from collections import deque
import time
import os
import scipy.io as sio
import matplotlib.pyplot as plt

from lib.imu_mqtt_handler import MQTTHandler
from lib.fsr_mqtt_handler import FSRHandler

from lib.imu_visualization import create_angle_plot, create_derivative_plot
from lib.fsr_visualization import create_fsr_plot

# NEW IMPORT
from lib.data_loader import load_and_plot_latest


# ================= MODE SELECT =================
MODE = "IMU"   # "IMU" or "FSR"

# ================= RECORDING CONFIG =================
RECORD_DURATION = 45  # seconds
recording_started = False
start_time = None


# ================= Buffers =================
buffers = {

    # IMU
    "feature": deque(maxlen=2000),
    "t": deque(maxlen=2000),
    "p1": deque(maxlen=2000),
    "p2": deque(maxlen=2000),
    "pavg": deque(maxlen=2000),

    "dt": deque(maxlen=2000),
    "dx1": deque(maxlen=2000),
    "dy1": deque(maxlen=2000),
    "dz1": deque(maxlen=2000),
    "dx2": deque(maxlen=2000),
    "dy2": deque(maxlen=2000),
    "dz2": deque(maxlen=2000),

    # FSR
    "fsr_t": deque(maxlen=2000),
    "fsr1": deque(maxlen=2000),
    "fsr2": deque(maxlen=2000),
    "fsr3": deque(maxlen=2000),
}

prev_vals = {
    "imu1_ax": None, "imu1_ay": None, "imu1_az": None,
    "imu2_ax": None, "imu2_ay": None, "imu2_az": None,
}


# ================= Handlers =================
imu_handler = MQTTHandler(buffers, prev_vals)
fsr_handler = FSRHandler(buffers)


# ================= MQTT =================
client = mqtt.Client()


def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected ✔")
    client.subscribe("esp32/imu")
    client.subscribe("esp32/fsr")


def on_message(client, userdata, msg):
    global recording_started, start_time

    # ===== ALWAYS PRINT RAW PAYLOAD =====
    try:
        print(f"[RAW MQTT] {msg.topic} -> {msg.payload.decode()}")
    except:
        pass

    # ===== START TIMER =====
    if not recording_started:
        recording_started = True
        start_time = time.time()
        print(f"\n[RECORDING STARTED] {RECORD_DURATION} seconds window\n")

    # ===== ROUTING =====
    if msg.topic == "esp32/imu":
        imu_handler.on_message(client, userdata, msg)

    elif msg.topic == "esp32/fsr":
        fsr_handler.on_message(client, userdata, msg)


client.on_connect = on_connect
client.on_message = on_message

client.connect("10.42.0.1", 1883)
client.loop_start()


# ================= FILE NAMING =================
def get_next_filename(prefix):
    i = 1
    while True:
        fname = f"{prefix}_{i}.mat"
        if not os.path.exists(fname):
            return fname
        i += 1


# ================= SAVE =================
def save_data():
    imu_file = get_next_filename("IMU_data")
    fsr_file = get_next_filename("FSR_data")

    print(f"\n[SAVING] {imu_file}, {fsr_file}")

    imu_data = {
        "t": list(buffers["t"]),
        "p1": list(buffers["p1"]),
        "p2": list(buffers["p2"]),
        "pavg": list(buffers["pavg"]),
        "dt": list(buffers["dt"]),
        "dx1": list(buffers["dx1"]),
        "dy1": list(buffers["dy1"]),
        "dz1": list(buffers["dz1"]),
        "dx2": list(buffers["dx2"]),
        "dy2": list(buffers["dy2"]),
        "dz2": list(buffers["dz2"]),
    }

    fsr_data = {
        "t": list(buffers["fsr_t"]),
        "fsr1": list(buffers["fsr1"]),
        "fsr2": list(buffers["fsr2"]),
        "fsr3": list(buffers["fsr3"]),
    }

    sio.savemat(imu_file, imu_data)
    sio.savemat(fsr_file, fsr_data)

    print("[SAVE COMPLETE]")


# ================= VISUALIZATION =================
try:

    if MODE == "IMU":
        create_angle_plot(buffers)
        create_derivative_plot(buffers)

    elif MODE == "FSR":
        create_fsr_plot(buffers)

    while True:

        plt.pause(0.1)

        if recording_started:
            elapsed = time.time() - start_time
            print(f"[TIME] {elapsed:.1f}s", end="\r")

            if elapsed >= RECORD_DURATION:
                print("\n[RECORDING COMPLETE]")
                break

finally:
    client.loop_stop()
    client.disconnect()
    save_data()

    # OPTIONAL: uncomment when needed
    # load_and_plot_latest(MODE)