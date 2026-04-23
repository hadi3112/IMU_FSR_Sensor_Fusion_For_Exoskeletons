from lib.data_Deleter import delete_single
from lib.data_Deleter import delete_range
from lib.data_Deleter import delete_all

delete_all("IMU_data")
delete_all("FSR_data")

# delete_range("IMU_data", 2, 6)
# delete_single("IMU_data", 3)

