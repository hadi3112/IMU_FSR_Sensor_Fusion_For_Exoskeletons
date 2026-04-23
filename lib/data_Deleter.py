import os


# ================= INTERNAL =================
def _get_matching_files(prefix):
    files = [f for f in os.listdir('.') if f.startswith(prefix) and f.endswith('.mat')]

    def extract_num(f):
        try:
            return int(f.split('_')[-1].replace('.mat', ''))
        except:
            return -1

    files = [(f, extract_num(f)) for f in files]
    files = [f for f, n in files if n != -1]

    return sorted(files, key=lambda x: int(x.split('_')[-1].replace('.mat', '')))


def _delete_file(fname):
    if os.path.exists(fname):
        os.remove(fname)
        print(f"[DELETE] {fname}")
    else:
        print(f"[SKIP] Not found: {fname}")


# ================= PUBLIC API =================

def delete_single(prefix, index):
    """
    Delete one file:
    delete_single("FSR_data", 3)
    → deletes FSR_data_3.mat
    """
    fname = f"{prefix}_{index}.mat"
    _delete_file(fname)


def delete_range(prefix, start, end):
    """
    Delete a range (inclusive):
    delete_range("IMU_data", 2, 5)
    → deletes IMU_data_2.mat ... IMU_data_5.mat
    """
    print(f"[DELETE RANGE] {prefix}_{start} → {prefix}_{end}")

    for i in range(start, end + 1):
        fname = f"{prefix}_{i}.mat"
        _delete_file(fname)


def delete_all(prefix):
    """
    Delete ALL files with prefix:
    delete_all("FSR_data")
    """
    files = _get_matching_files(prefix)

    if not files:
        print(f"[INFO] No files found for prefix: {prefix}")
        return

    print(f"[DELETE ALL] {len(files)} files for {prefix}")

    for f in files:
        _delete_file(f)


def delete_all_data():
    """
    Delete BOTH IMU and FSR datasets
    """
    print("[DELETE ALL DATASETS]")
    delete_all("IMU_data")
    delete_all("FSR_data")