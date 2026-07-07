import scipy.io as sio
import os


def load_mat_file(mat_file, data_type="IMU"):

    data = sio.loadmat(mat_file)

    t = data["t"].flatten()

    plot_signals = []

    if data_type == "IMU":

        plot_signals = [
            ("p1", data["p1"].flatten()),
            ("p2", data["p2"].flatten()),
            ("pavg", data["pavg"].flatten())
        ]

    elif data_type == "IMU_ACCEL":

        plot_signals = [
            ("ax1", data["ax1"].flatten()),
            ("ay1", data["ay1"].flatten()),
            ("az1", data["az1"].flatten()),
            ("ax2", data["ax2"].flatten()),
            ("ay2", data["ay2"].flatten()),
            ("az2", data["az2"].flatten())
        ]

    elif data_type == "IMU_DERIV":

        plot_signals = [
            ("dx1", data["dx1"].flatten()),
            ("dy1", data["dy1"].flatten()),
            ("dz1", data["dz1"].flatten()),
            ("dx2", data["dx2"].flatten()),
            ("dy2", data["dy2"].flatten()),
            ("dz2", data["dz2"].flatten())
        ]

    elif data_type == "FSR":

        plot_signals = [
            ("fsr1", data["fsr1"].flatten()),
            ("fsr2", data["fsr2"].flatten()),
            ("fsr3", data["fsr3"].flatten())
        ]

    else:
        raise ValueError("Unsupported data type")

    return t, plot_signals