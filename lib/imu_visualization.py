import matplotlib.pyplot as plt
import matplotlib.animation as animation

ANIMATIONS = []

# ================= ANGLE PLOT =================
def create_angle_plot(buffers):

    fig, ax = plt.subplots(figsize=(13, 5))

    ax.set_title("Thigh Pitch Angles")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Pitch")
    ax.grid(True, alpha=0.3)

    ax.set_ylim(-40, 40)
    ax.set_xlim(0, 10)

    l1, = ax.plot([], [], label="IMU1")
    l2, = ax.plot([], [], label="IMU2")
    l3, = ax.plot([], [], label="AVG")

    ax.legend()

    def update(_):

        if buffers["t"]:

            t = list(buffers["t"])

            l1.set_data(t, buffers["p1"])
            l2.set_data(t, buffers["p2"])
            l3.set_data(t, buffers["pavg"])

            ax.set_xlim(max(0, t[-1] - 10), t[-1] + 1)

        return l1, l2, l3

    ani = animation.FuncAnimation(fig, update, interval=50)
    ANIMATIONS.append(ani)

    return fig, ani


# ================= DERIVATIVE PLOT =================
def create_derivative_plot(buffers):

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True)

    ax1.set_title("IMU1 Derivatives")
    ax2.set_title("IMU2 Derivatives")

    ax1.set_ylim(-5, 5)
    ax2.set_ylim(-5, 5)

    ax1.grid(True, alpha=0.3)
    ax2.grid(True, alpha=0.3)

    l1, = ax1.plot([], [], label="dx1")
    l2, = ax1.plot([], [], label="dy1")
    l3, = ax1.plot([], [], label="dz1")

    l4, = ax2.plot([], [], label="dx2")
    l5, = ax2.plot([], [], label="dy2")
    l6, = ax2.plot([], [], label="dz2")

    def update(_):

        if buffers["dt"]:

            t = list(buffers["dt"])

            l1.set_data(t, buffers["dx1"])
            l2.set_data(t, buffers["dy1"])
            l3.set_data(t, buffers["dz1"])

            l4.set_data(t, buffers["dx2"])
            l5.set_data(t, buffers["dy2"])
            l6.set_data(t, buffers["dz2"])

            ax1.set_xlim(max(0, t[-1] - 10), t[-1] + 1)
            ax2.set_xlim(max(0, t[-1] - 10), t[-1] + 1)

        return l1, l2, l3, l4, l5, l6

    ani = animation.FuncAnimation(fig, update, interval=50)
    ANIMATIONS.append(ani)

    return fig, ani