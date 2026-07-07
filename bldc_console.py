import customtkinter as ctk
import tkinter as tk
import threading
import random
import time
import queue
import json

# ================= CONFIG =================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

UPDATE_MS = 120
MAX_RPM = 3000
MAX_CURRENT = 10.0
MAX_TEMP = 80.0

incoming_queue = queue.Queue()


class PowerBar(ctk.CTkFrame):
    def __init__(self, parent, bars=24, command=None):
        super().__init__(parent, fg_color="transparent")

        self.command = command
        self.bars = bars
        self.value = 0

        self.canvas = tk.Canvas(
            self,
            width=760,
            height=95,
            bg="#111111",
            highlightthickness=0
        )
        self.canvas.pack()

        self.canvas.bind("<Button-1>", self.click)

        self.draw()

    def set(self, percent):
        self.value = max(0, min(100, int(percent)))
        self.draw()

    def click(self, event):
        w = self.canvas.winfo_width()
        percent = int((event.x / w) * 100)
        self.set(percent)

        if self.command:
            self.command(percent)

    def draw(self):
        self.canvas.delete("all")

        w = 760
        h = 95

        gap = 14
        bar_w = 8
        bar_h = 50
        bottom = 72

        filled = round((self.value / 100) * self.bars)

        x = 20

        for i in range(self.bars):

            if i < filled:
                color = "#56E36B"      # green
            elif i == filled:
                color = "white"         # marker
            else:
                color = "#6B6B6B"       # inactive

            self.canvas.create_rectangle(
                x,
                bottom - bar_h,
                x + bar_w,
                bottom,
                fill=color,
                width=0
            )

            x += gap + bar_w

# ================= FAKE MQTT PRODUCER =================
class FakeESP32(threading.Thread):
    """
    Simulates ESP32 publishing MQTT telemetry packets.
    """

    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        self.enabled = False
        self.target_speed = 0
        self.actual_speed = 0

    def set_speed(self, speed):
        self.target_speed = max(0, min(100, int(speed)))

    def set_enabled(self, enabled):
        self.enabled = enabled

    def stop(self):
        self.enabled = False
        self.target_speed = 0

    def run(self):
        while self.running:

            # ramp motor gradually
            if self.enabled:
                if self.actual_speed < self.target_speed:
                    self.actual_speed += min(2, self.target_speed - self.actual_speed)
                elif self.actual_speed > self.target_speed:
                    self.actual_speed -= min(2, self.actual_speed - self.target_speed)
            else:
                self.actual_speed = max(0, self.actual_speed - 5)

            speed = self.actual_speed

            rpm = int((speed / 100) * MAX_RPM + random.randint(-25, 25))
            rpm = max(0, rpm)

            current = round((speed / 100) * MAX_CURRENT + random.uniform(-0.15, 0.15), 2)
            current = max(0, current)

            temp = round(28 + (speed / 100) * 26 + random.uniform(-0.4, 0.4), 1)

            payload = {
                "rpm": rpm,
                "current": current,
                "temp": temp,
                "pot": speed,
                "enabled": self.enabled,
                "heartbeat": int(time.time())
            }

            incoming_queue.put(payload)

            time.sleep(UPDATE_MS / 1000)


# ================= UI =================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Strydex Fake MQTT BLDC Console")
        self.geometry("980x760")
        self.resizable(False, False)

        self.fake_esp = FakeESP32()
        self.fake_esp.start()

        self.user_dragging = False

        self.build_ui()
        self.poll_packets()

    def build_ui(self):
        title = ctk.CTkLabel(
            self,
            text="BLDC Motor Console (Fake MQTT)",
            font=("Arial", 28, "bold")
        )
        title.pack(pady=(20, 10))

        self.status = ctk.CTkLabel(
            self,
            text="STATUS: DISABLED",
            text_color="red",
            font=("Arial", 18, "bold")
        )
        self.status.pack(pady=10)

        # Slider frame
        frame = ctk.CTkFrame(self)
        frame.pack(padx=20, pady=20, fill="x")

        ctk.CTkLabel(
            frame,
            text="Speed Command",
            font=("Arial", 20)
        ).pack(pady=(20, 10))

        self.powerbar = PowerBar(
            frame,
            bars=24,
            command=self.slider_changed
        )
        self.powerbar.pack(pady=20)

        self.slider_val = ctk.CTkLabel(
            frame,
            text="0 %",
            font=("Arial", 24, "bold")
        )
        self.slider_val.pack(pady=(10, 20))

        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=15)

        self.enable_btn = ctk.CTkButton(
            btn_frame,
            text="ENABLE",
            width=180,
            height=48,
            command=self.toggle_enable,
            font=("Arial", 16, "bold")
        )
        self.enable_btn.grid(row=0, column=0, padx=10)

        stop_btn = ctk.CTkButton(
            btn_frame,
            text="EMERGENCY STOP",
            width=220,
            height=48,
            fg_color="red",
            hover_color="#AA0000",
            command=self.estop,
            font=("Arial", 16, "bold")
        )
        stop_btn.grid(row=0, column=1, padx=10)

        # Telemetry
        telem = ctk.CTkFrame(self)
        telem.pack(padx=20, pady=20, fill="x")

        self.rpm_label = self.metric(telem, "RPM", 0)
        self.current_label = self.metric(telem, "Current (A)", 1)
        self.temp_label = self.metric(telem, "Temp (°C)", 2)
        self.hb_label = self.metric(telem, "Heartbeat", 3)

        # Logs
        ctk.CTkLabel(
            self,
            text="Packet Log",
            font=("Arial", 18, "bold")
        ).pack()

        self.logbox = ctk.CTkTextbox(self, width=900, height=250)
        self.logbox.pack(padx=20, pady=15)

        self.log("[BOOT] Console started")
        self.log("[BOOT] Fake MQTT producer active")

    def metric(self, parent, title, col):
        frame = ctk.CTkFrame(parent, width=200, height=100)
        frame.grid(row=0, column=col, padx=12, pady=18)

        ctk.CTkLabel(
            frame,
            text=title,
            font=("Arial", 16)
        ).pack(pady=(14, 6))

        val = ctk.CTkLabel(
            frame,
            text="0",
            font=("Arial", 24, "bold")
        )
        val.pack(pady=(0, 14))

        return val

    def log(self, msg):
        stamp = time.strftime("%H:%M:%S")
        self.logbox.insert("end", f"[{stamp}] {msg}\n")
        self.logbox.see("end")

    def publish(self, packet):
        """
        Simulated outgoing MQTT publish.
        Later replace this with actual MQTT publish.
        """
        pretty = json.dumps(packet)
        self.log(f"[PUBLISH] {pretty}")

    def slider_changed(self, value):
        value = int(value)

        self.slider_val.configure(text=f"{value} %")

        packet = {
            "cmd": "set_speed",
            "value": value
        }

        self.publish(packet)

        self.fake_esp.set_speed(value)

    def toggle_enable(self):
        enabled_now = "DISABLED" in self.status.cget("text")

        if enabled_now:
            self.fake_esp.set_enabled(True)
            self.status.configure(
                text="STATUS: ENABLED",
                text_color="lime"
            )
            self.enable_btn.configure(text="DISABLE")
            self.publish({"cmd": "enable"})
        else:
            self.fake_esp.set_enabled(False)
            self.status.configure(
                text="STATUS: DISABLED",
                text_color="red"
            )
            self.enable_btn.configure(text="ENABLE")
            self.publish({"cmd": "disable"})

    def estop(self):
        self.fake_esp.stop()

        self.powerbar.set(0)
        self.slider_val.configure(text="0 %")

        self.status.configure(
            text="STATUS: EMERGENCY STOP",
            text_color="red"
        )

        self.enable_btn.configure(text="ENABLE")

        self.publish({"cmd": "estop"})
        self.log("[SAFETY] Emergency stop triggered")

    def process_payload(self, payload):
        """
        This is exactly where real MQTT payloads would go later.
        """

        # auto-sync slider position with incoming pot telemetry
        self.powerbar.set(payload["pot"])
        self.slider_val.configure(text=f'{payload["pot"]} %')

        self.rpm_label.configure(text=str(payload["rpm"]))
        self.current_label.configure(text=str(payload["current"]))
        self.temp_label.configure(text=str(payload["temp"]))
        self.hb_label.configure(text=str(payload["heartbeat"]))

        # occasional receive log
        if random.random() < 0.08:
            self.log(f"[RECV] {json.dumps(payload)}")

    def poll_packets(self):
        while not incoming_queue.empty():
            payload = incoming_queue.get()
            self.process_payload(payload)

        self.after(50, self.poll_packets)


if __name__ == "__main__":
    app = App()
    app.mainloop()