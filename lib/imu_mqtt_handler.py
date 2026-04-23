#imu_mqtt_handler
import json
import time
import numpy as np

from .filters import low_pass_filter
from .features import build_feature_vector
from .imu_debug import debug_payload

DEBUG = True


class MQTTHandler:

    def __init__(self, buffers, prev_vals):
        self.buffers = buffers
        self.prev_vals = prev_vals

        self.prev_p1 = 0
        self.prev_p2 = 0

        self.start_time = time.time()

        self.CALIB_DURATION = 3.0
        self.calib_samples = []
        self.bias1 = 0
        self.bias2 = 0
        self.calibrated = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to broker")
            client.subscribe("esp32/imu")
        else:
            print(f"Connection failed: {rc}")

    def on_message(self, client, userdata, msg):

        # ===== Decode payload =====
        payload = json.loads(msg.payload.decode())

        # ===== DEBUG: print incoming payload =====
        debug_payload(payload, DEBUG)

        elapsed = time.time() - self.start_time

        # ===== Phase 1: Calibration collection =====
        if not self.calibrated and elapsed < self.CALIB_DURATION:
            print(f"[CALIBRATING] t={elapsed:.2f}s samples={len(self.calib_samples)}")
            self._collect_calibration(payload)
            return

        # ===== Phase 2: Compute bias =====
        if not self.calibrated:
            self._compute_bias()
            return

        # ===== Guard =====
        if "imu1" not in payload or "imu2" not in payload:  # not 'and'
            return

        imu1 = payload["imu1"]
        imu2 = payload["imu2"]

        p1 = imu1.get("pitch")
        p2 = imu2.get("pitch")

        if p1 is None or p2 is None:
            print("[IMU DROP] missing pitch:", imu1, imu2)
            return

        # ===== Extract acceleration =====
        ax1 = imu1.get("accel_x")
        ay1 = imu1.get("accel_y")
        az1 = imu1.get("accel_z")

        ax2 = imu2.get("accel_x")
        ay2 = imu2.get("accel_y")
        az2 = imu2.get("accel_z")

        if None in [ax1, ay1, az1, ax2, ay2, az2]:
            return

        # ===== Feature vector + derivatives =====
        fv, dx1, dy1, dz1, dx2, dy2, dz2 = build_feature_vector(
            ax1, ay1, az1,
            ax2, ay2, az2,
            self.prev_vals
        )

        self.buffers["feature"].append(fv)

        # ===== Derivative buffers =====
        self.buffers["dt"].append(elapsed)
        self.buffers["dx1"].append(dx1)
        self.buffers["dy1"].append(dy1)
        self.buffers["dz1"].append(dz1)
        self.buffers["dx2"].append(dx2)
        self.buffers["dy2"].append(dy2)
        self.buffers["dz2"].append(dz2)

        # ===== Angle processing =====
        p2 = -p2  # mirror correction

        p1 -= self.bias1
        p2 -= self.bias2

        p1 = low_pass_filter(self.prev_p1, p1)
        p2 = low_pass_filter(self.prev_p2, p2)

        self.prev_p1, self.prev_p2 = p1, p2

        p_avg = (p1 - p2) / 2.0

        # ===== Store angle buffers =====
        self.buffers["t"].append(elapsed)
        self.buffers["p1"].append(p1)
        self.buffers["p2"].append(p2)
        self.buffers["pavg"].append(p_avg)

        # ===== DEBUG: confirm angles are flowing =====
        print(
            f"[ANGLE BUFFER] size={len(self.buffers['t'])} | "
            f"p1={p1:.2f}, p2={p2:.2f}, avg={p_avg:.2f}"
        )

    # ==========================================================
    # Calibration helpers
    # ==========================================================

    def _collect_calibration(self, payload):
        if "imu1" in payload and "imu2" in payload:
            p1 = payload["imu1"].get("pitch")
            p2 = payload["imu2"].get("pitch")

            # IMPORTANT: must check None, not truthiness
            if p1 is not None and p2 is not None:
                self.calib_samples.append((p1, -p2))

                print(f"Calibration samples: {len(self.calib_samples)}")

    def _compute_bias(self):
        if len(self.calib_samples) > 10:
            self.bias1 = np.mean([x[0] for x in self.calib_samples])
            self.bias2 = np.mean([x[1] for x in self.calib_samples])

            self.calibrated = True

            print(
                f"Calibration done → bias1={self.bias1:.2f}, "
                f"bias2={self.bias2:.2f}"
            )