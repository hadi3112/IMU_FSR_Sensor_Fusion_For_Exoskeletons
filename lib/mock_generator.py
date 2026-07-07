import time
import math
import random
import threading
import json

class FakeMessage:
    def __init__(self, topic, payload_dict):
        self.topic = topic
        self.payload = json.dumps(payload_dict).encode()

def _generate_mock_mqtt_data(client, on_message_callback):
    t = 0
    print("[MOCK] Injecting fake MQTT JSON payloads into handlers...")
    while True:
        # 1. IMU Payload (exact JSON structure)
        p = 20 * math.sin(t)
        imu_json = {
            "imu1": {"pitch": p, "accel_x": 0.1, "accel_y": 0.2, "accel_z": 0.98},
            "imu2": {"pitch": -p, "accel_x": -0.1, "accel_y": -0.2, "accel_z": 0.98}
        }
        on_message_callback(client, None, FakeMessage("esp32/imu", imu_json))

        # 2. FSR Payload (exact JSON structure, 0 to 4096 raw values as requested)
        fsr_val = random.randint(0, 4096)
        fsr_json = {
            "fsr1": fsr_val,
            "fsr2": fsr_val,
            "fsr3": fsr_val
        }
        on_message_callback(client, None, FakeMessage("esp32/fsr", fsr_json))

        time.sleep(0.05)
        t += 0.2

def start_mock_generator(client, on_message_callback):
    """Starts the mock data generator in a background thread."""
    thread = threading.Thread(
        target=_generate_mock_mqtt_data, 
        args=(client, on_message_callback), 
        daemon=True
    )
    thread.start()
