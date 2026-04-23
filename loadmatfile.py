from lib.mat_loader import (
    load_single,
    load_range,
    load_all,
    load_latest
)

# ================= CONFIG =================

MODE = "latest"  
# "single"
# "range"
# "all"
# "latest"

#DATA_TYPE = "FSR"  
DATA_TYPE = "IMU"  
# "FSR" or "IMU"

INDEX = 1
RANGE_START = 1
RANGE_END = 5

# ================= PREFIX =================

if DATA_TYPE == "FSR":
    prefix = "FSR_data"
elif DATA_TYPE == "IMU":
    prefix = "IMU_data"
else:
    raise ValueError("Invalid DATA_TYPE")

# ================= EXECUTION =================

if MODE == "single":
    load_single(prefix, INDEX)

elif MODE == "range":
    load_range(prefix, RANGE_START, RANGE_END)

elif MODE == "all":
    load_all(prefix)

elif MODE == "latest":
    load_latest(prefix)

else:
    print("[ERROR] Invalid MODE")