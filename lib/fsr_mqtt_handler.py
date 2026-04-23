# fsr_mqtt_handler.py
import json
import time
from .fsr_debug import debug_fsr


class FSRHandler:

    def __init__(self, buffers):
        self.buffers = buffers

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("[FSR MQTT] Connected ✔")
        else:
            print(f"[FSR MQTT] Connection failed rc={rc}")

    def on_message(self, client, userdata, msg):

        try:
            payload = json.loads(msg.payload.decode())

            # ===== DEBUG =====
            debug_fsr(payload)
            print("[FSR RAW]", payload)

            f1 = payload.get("fsr1", 0)
            f2 = payload.get("fsr2", 0)
            f3 = payload.get("fsr3", 0)

            # ===== TIME AXIS (separate from IMU) =====
            self.buffers["fsr_t"].append(time.time())

            # ===== VALUES =====
            self.buffers["fsr1"].append(f1)
            self.buffers["fsr2"].append(f2)
            self.buffers["fsr3"].append(f3)

            print(f"[FSR BUFFER] 1={f1} 2={f2} 3={f3}")

        except Exception as e:
            print(f"[FSR ERROR] {e}")