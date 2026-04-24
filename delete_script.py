from lib.data_Deleter import (
    delete_single_type,
    delete_range_type,
    delete_all_type,
    delete_all_data
)

# ================= OPTIONS =================
DATA_TYPE = "FSR"
# "IMU", "FSR", "IMU_ACCEL", "IMU_DERIV"

# ================= EXAMPLES =================

# Delete one file
# delete_single_type(DATA_TYPE, 3)

# Delete range
# delete_range_type(DATA_TYPE, 2, 6)

# Delete all of one type
delete_all_type(DATA_TYPE)

# Delete everything (ALL datasets)
# delete_all_data()