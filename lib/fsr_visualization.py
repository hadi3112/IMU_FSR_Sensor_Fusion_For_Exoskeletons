import matplotlib.pyplot as plt
import matplotlib.animation as animation

# ==========================================================
# GLOBAL ANIMATION STORE (CRITICAL: prevents garbage collection)
# ==========================================================
FSR_ANIMATIONS = []


def create_fsr_plot(buffers):

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.set_title("FSR Pressure Signals (Toe / Ankle)")
    ax.set_xlabel("Samples")
    ax.set_ylabel("Pressure")
    ax.grid(True, alpha=0.3)

    # Initial empty plots
    l1, = ax.plot([], [], label="FSR1 (Toe)")
    l2, = ax.plot([], [], label="FSR2 (Ankle)")
    l3, = ax.plot([], [], label="FSR3 (Toe)")

    ax.legend()

    # ==========================================================
    # UPDATE FUNCTION (RUNS IN MATPLOTLIB EVENT LOOP)
    # ==========================================================
    def update(frame):

        n = len(buffers["fsr1"])

        # HARD DEBUG: confirms animation is alive
        print("[FSR PLOT UPDATE] samples =", n)

        if n == 0:
            return l1, l2, l3

        # Convert buffers to lists (safe for matplotlib)
        x = list(range(n))

        y1 = list(buffers["fsr1"])
        y2 = list(buffers["fsr2"])
        y3 = list(buffers["fsr3"])

        # Update plot data
        l1.set_data(x, y1)
        l2.set_data(x, y2)
        l3.set_data(x, y3)

        # Dynamic axis window (stable view)
        ax.set_xlim(max(0, n - 100), n + 5)

        ymax = max(
            max(y1) if y1 else 1,
            max(y2) if y2 else 1,
            max(y3) if y3 else 1
        )

        ax.set_ylim(0, ymax + 10)

        # Force redraw
        fig.canvas.draw_idle()

        return l1, l2, l3

    # ==========================================================
    # ANIMATION CREATION (CRITICAL FIX HERE)
    # ==========================================================
    ani = animation.FuncAnimation(
        fig,
        update,
        interval=50,
        blit=False   # IMPORTANT: prevents blank rendering issues
    )

    # 🔴 CRITICAL: prevent garbage collection
    FSR_ANIMATIONS.append(ani)

    return fig, ani


def start_fsr_visualization(buffers):
    fig, _ = create_fsr_plot(buffers)
    plt.tight_layout()
    plt.show(block=True)