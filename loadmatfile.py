# loadmatfile.py
#
# Interactive .mat file viewer.
# Run:  python loadmatfile.py
#
# Prompts you for:
#   1. File type  (IMU angles / IMU accel / IMU derivatives / FSR)
#   2. File number  (or 'all', or 'latest')
#   3. Search path  (Enter = root directory, 'dataset' = dataset sub-folder)

import os
import sys

# Make sure lib/ is importable regardless of cwd
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from lib.mat_loader import (
    FILE_TYPES,
    get_files,
    plot_mat_file,
    resolve_search_dir,
)


# =========================================================
# HELPERS
# =========================================================

def divider(char="=", width=56):
    print(char * width)


def ask(prompt, default=None):
    """Prompt the user and return their input stripped. Falls back to default."""
    suffix = f"  [{default}]" if default is not None else ""
    raw = input(f"{prompt}{suffix}: ").strip()
    if raw == "" and default is not None:
        return str(default)
    return raw


# =========================================================
# INTERACTIVE FLOW
# =========================================================

def choose_file_type():
    """Step 1 — pick IMU / Accel / Deriv / FSR."""
    divider()
    print("  MAT File Viewer  —  choose data type")
    divider()
    for key, (prefix, label) in FILE_TYPES.items():
        print(f"  [{key}]  {label}")
    divider("-")

    while True:
        choice = ask("Select type", default="1")
        if choice in FILE_TYPES:
            prefix, label = FILE_TYPES[choice]
            print(f"  >> Selected: {label}\n")
            return prefix, label
        print(f"  Invalid choice '{choice}'. Enter 1, 2, 3, or 4.")


def choose_search_path(prefix):
    """Step 2 — where to look for files."""
    print("  Search path options:")
    print("    Enter  ->  project root directory  (legacy .mat files)")
    print("    dataset  ->  dataset/{prefix}/ sub-folder")
    print("    Or type any relative/absolute path")
    divider("-")

    raw = ask("Path", default="")
    search_dir = resolve_search_dir(raw, prefix)

    print(f"  >> Searching in: {search_dir}\n")
    return search_dir


def list_available(prefix, search_dir):
    """Show the user which files actually exist in the chosen directory."""
    files = get_files(prefix, search_dir)
    if not files:
        print(f"\n  [!] No files matching '{prefix}_*.mat' found in:")
        print(f"      {search_dir}")
        print("      Check your path and try again.\n")
        return []

    print(f"  Found {len(files)} file(s):")
    for f in files:
        print(f"    {os.path.basename(f)}")
    return files


def choose_file_number(files, prefix):
    """Step 3 — pick a specific number, 'all', or 'latest'."""
    divider("-")
    print("  Options:")
    print("    <number>   open a specific file  (e.g. 3)")
    print("    all        open every file in sequence")
    print("    latest     open the last file in the list")
    divider("-")

    while True:
        choice = ask("File number / all / latest", default="latest").lower()

        if choice == "latest":
            return [files[-1]]

        if choice == "all":
            return files

        if choice.isdigit():
            target = os.path.join(
                os.path.dirname(files[0]),
                f"{prefix}_{choice}.mat"
            )
            if os.path.isfile(target):
                return [target]
            else:
                print(f"  [!] File not found: {os.path.basename(target)}")
                print("      Choose a number from the list above.")
        else:
            print(f"  [!] Invalid input '{choice}'. Enter a number, 'all', or 'latest'.")


# =========================================================
# MAIN
# =========================================================

def main():
    print()
    divider()
    print("  Gait Analysis  —  .mat File Viewer")
    divider()
    print()

    # --- Step 1: file type ---
    prefix, label = choose_file_type()

    # --- Step 2: search path ---
    search_dir = choose_search_path(prefix)

    # --- List what exists ---
    files = list_available(prefix, search_dir)
    if not files:
        sys.exit(1)

    # --- Step 3: which file(s) ---
    targets = choose_file_number(files, prefix)

    # --- Plot ---
    print()
    divider()
    print(f"  Opening {len(targets)} file(s) ...")
    divider()

    for path in targets:
        plot_mat_file(path)

    print("\n  Done.\n")


if __name__ == "__main__":
    main()