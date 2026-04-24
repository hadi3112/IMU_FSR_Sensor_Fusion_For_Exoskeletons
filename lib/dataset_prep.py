import os
import shutil

# ================= CONFIG =================
PREFIXES = [
    "IMU_data",
    "FSR_data",
    "IMU_accel",
    "IMU_derivatives"
]

DATASET_DIR = "dataset"


# ================= SETUP =================
def create_structure():
    if not os.path.exists(DATASET_DIR):
        os.mkdir(DATASET_DIR)

    for prefix in PREFIXES:
        folder_path = os.path.join(DATASET_DIR, prefix)
        os.makedirs(folder_path, exist_ok=True)


# ================= FILE ORGANIZATION =================
def organize_files():
    files = [f for f in os.listdir('.') if f.endswith('.mat')]

    for file in files:
        for prefix in PREFIXES:
            if file.startswith(prefix):
                src = os.path.join('.', file)
                dst = os.path.join(DATASET_DIR, prefix, file)

                print(f"[MOVE] {file} → {DATASET_DIR}/{prefix}/")
                shutil.move(src, dst)
                break


# ================= MAIN =================
if __name__ == "__main__":
    print("[SETUP] Creating dataset structure...")
    create_structure()

    print("[PROCESS] Organizing all .mat files in Root project directory...")
    organize_files()

    print("[DONE] Dataset organized successfully.")