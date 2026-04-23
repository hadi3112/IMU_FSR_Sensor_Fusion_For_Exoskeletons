import os
from send2trash import send2trash


# ================= CONFIG =================
DRY_RUN = False   # True = preview only, no deletion


# ================= PREFIX MAP =================
PREFIX_MAP = {
    "IMU": "IMU_data",
    "FSR": "FSR_data",
    "IMU_ACCEL": "IMU_accel",
    "IMU_DERIV": "IMU_derivatives",
}


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


def _safe_delete(fname):
    if not os.path.exists(fname):
        print(f"[SKIP] Not found: {fname}")
        return

    if DRY_RUN:
        print(f"[DRY RUN] Would delete: {fname}")
        return

    try:
        send2trash(fname)
        print(f"[RECYCLE BIN] {fname}")
    except Exception as e:
        print(f"[ERROR] Failed to delete {fname}: {e}")


def _confirm(prompt):
    resp = input(f"{prompt} (y/n): ").strip().lower()
    return resp == "y"


# ================= CORE DELETE =================

def delete_single(prefix, index):
    fname = f"{prefix}_{index}.mat"
    _safe_delete(fname)


def delete_range(prefix, start, end):
    print(f"[DELETE RANGE] {prefix}_{start} → {prefix}_{end}")

    if not _confirm("Confirm delete range?"):
        print("[CANCELLED]")
        return

    for i in range(start, end + 1):
        fname = f"{prefix}_{i}.mat"
        _safe_delete(fname)


def delete_all(prefix):
    files = _get_matching_files(prefix)

    if not files:
        print(f"[INFO] No files found for prefix: {prefix}")
        return

    print(f"[DELETE ALL] {len(files)} files for {prefix}")

    if not _confirm("Confirm delete ALL?"):
        print("[CANCELLED]")
        return

    for f in files:
        _safe_delete(f)


# ================= NEW: DATA-TYPE BASED API =================

def delete_single_type(data_type, index):
    prefix = PREFIX_MAP.get(data_type)
    if not prefix:
        raise ValueError("Invalid DATA_TYPE")
    delete_single(prefix, index)


def delete_range_type(data_type, start, end):
    prefix = PREFIX_MAP.get(data_type)
    if not prefix:
        raise ValueError("Invalid DATA_TYPE")
    delete_range(prefix, start, end)


def delete_all_type(data_type):
    prefix = PREFIX_MAP.get(data_type)
    if not prefix:
        raise ValueError("Invalid DATA_TYPE")
    delete_all(prefix)


# ================= BULK OPERATIONS =================

def delete_all_data():
    print("[DELETE ALL DATASETS]")

    if not _confirm("Delete ALL datasets (IMU + FSR + ACCEL + DERIV)?"):
        print("[CANCELLED]")
        return

    for prefix in PREFIX_MAP.values():
        delete_all(prefix)


def delete_range_all_types(start, end):
    print(f"[DELETE RANGE ALL TYPES] {start} → {end}")

    if not _confirm("Confirm delete across ALL data types?"):
        print("[CANCELLED]")
        return

    for prefix in PREFIX_MAP.values():
        delete_range(prefix, start, end)