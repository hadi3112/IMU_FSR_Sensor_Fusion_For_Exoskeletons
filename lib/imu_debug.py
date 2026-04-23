def debug_payload(payload, enabled=True):
    if not enabled:
        return

    try:
        imu1 = payload.get("imu1", {})
        imu2 = payload.get("imu2", {})

        print(
            f"[PAYLOAD] "
            f"IMU1 pitch={imu1.get('pitch')} "
            f"ax={imu1.get('accel_x')} "
            f"ay={imu1.get('accel_y')} "
            f"az={imu1.get('accel_z')} | "
            f"IMU2 pitch={imu2.get('pitch')} "
            f"ax={imu2.get('accel_x')} "
            f"ay={imu2.get('accel_y')} "
            f"az={imu2.get('accel_z')}"
        )

    except Exception as e:
        print(f"[DEBUG ERROR] {e}")