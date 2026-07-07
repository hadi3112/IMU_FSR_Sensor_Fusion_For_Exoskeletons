import matplotlib.pyplot as plt
import matplotlib.animation as animation

ANIMATIONS = []

def create_combined_plot(buffers):

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    fig.canvas.manager.set_window_title("Combined IMU & FSR View")

    # IMU Plot
    ax1.set_title("IMU Pitch Angles")
    ax1.set_ylabel("Pitch (degrees)")
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(-40, 40)
    ax1.set_xlim(0, 10)
    l1, = ax1.plot([], [], label="IMU1")
    l2, = ax1.plot([], [], label="IMU2")
    l3, = ax1.plot([], [], label="AVG")
    ax1.legend()

    # FSR Plot
    ax2.set_title("FSR Raw Values")
    ax2.set_xlabel("Samples")
    ax2.set_ylabel("Raw ADC (0-4095)")
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(-50, 4200)
    ax2.set_xlim(0, 100)
    f1, = ax2.plot([], [], label="FSR1")
    f2, = ax2.plot([], [], label="FSR2")
    f3, = ax2.plot([], [], label="FSR3")
    ax2.legend()

    # ONE unified update function — this is the fix
    def update(frame):

        # Update IMU
        if buffers["t"]:
            t = list(buffers["t"])
            l1.set_data(t, list(buffers["p1"]))
            l2.set_data(t, list(buffers["p2"]))
            l3.set_data(t, list(buffers["pavg"]))
            ax1.set_xlim(max(0, t[-1] - 10), t[-1] + 1)

        # Update FSR
        n = len(buffers["fsr1"])
        if n > 0:
            x = list(range(n))
            f1.set_data(x, list(buffers["fsr1"]))
            f2.set_data(x, list(buffers["fsr2"]))
            f3.set_data(x, list(buffers["fsr3"]))
            ax2.set_xlim(max(0, n - 100), n + 5)

        return l1, l2, l3, f1, f2, f3

    ani = animation.FuncAnimation(fig, update, interval=50, blit=False, cache_frame_data=False)
    ANIMATIONS.append(ani)

    return fig, ani
