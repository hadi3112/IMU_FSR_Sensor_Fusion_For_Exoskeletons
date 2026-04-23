Project Setup and Execution Guide

1. Clone Repository

Windows

Open Command Prompt or PowerShell: cd path git clone
https://github.com/your-repo.git cd your-repo

Linux

Open terminal: cd /path/to/your/projects git clone
https://github.com/your-repo.git cd your-repo

------------------------------------------------------------------------

2. Python Environment Setup

Ensure Python 3.8+ is installed.

Install dependencies: pip install -r requirements.txt

If requirements.txt is missing, install manually: pip install paho-mqtt
scipy matplotlib numpy

------------------------------------------------------------------------

3. MQTT Setup (Raspberry Pi Required)

Overview

System requires a Raspberry Pi acting as MQTT broker and local network
host.

Steps (High-Level)

1.  Create local network using static IP addressing
2.  Configure Raspberry Pi with static IP
3.  Install MQTT broker (e.g., Mosquitto)
4.  Restrict connections to local IP range only

TBD

(Add exact scripts and commands for broker setup here)

------------------------------------------------------------------------

4. ESP32 Firmware Setup

Navigate to: ESP_codes/

This contains template firmware: - 2 IMUs (single leg) - 3 FSR sensors
(foot)

Notes: - Adjust sensor count based on your hardware - System currently
supports: - Hip joint angle estimation - Ground reaction force
estimation

Flash code to ESP32 using Arduino IDE or ESP-IDF.

------------------------------------------------------------------------

5. Running the System

Step 1: Start MQTT Broker (on Raspberry Pi)

Step 2: Power ESP32 devices

Step 3: Run Python UI

cd main_project_directory python main.py

------------------------------------------------------------------------

6. Expected Behavior

-   IMU data streamed via MQTT
-   FSR data streamed via MQTT
-   Python UI subscribes and visualizes:
    -   Angles
    -   Forces
    -   Derived signals

------------------------------------------------------------------------

7. Notes

-   Ensure all devices are on same local network
-   Verify MQTT topics match between ESP and Python
-   Check firewall/network restrictions if connection fails
