from lib.mat_loader import load_latest

# ================= CONFIG =================

DATA_TYPE = "IMU"
# OPTIONS:
# "IMU"
# "FSR"
# "IMU_ACCEL"
# "IMU_DERIV"

# ================= PREFIX =================

if DATA_TYPE == "FSR":
    prefix = "FSR_data"

elif DATA_TYPE == "IMU":
    prefix = "IMU_data"

elif DATA_TYPE == "IMU_ACCEL":
    prefix = "IMU_accel"

elif DATA_TYPE == "IMU_DERIV":
    prefix = "IMU_derivatives"

else:
    raise ValueError("Invalid DATA_TYPE")

# ================= EXECUTION =================

load_latest(prefix)