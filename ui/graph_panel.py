import numpy as np

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class GraphPanel:

    def __init__(self, parent, state, timeline_callback):

        self.parent = parent
        self.state = state

        self.timeline_callback = timeline_callback

        self.fig = Figure(figsize=(7, 4), dpi=100)

        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(
            self.fig,
            master=parent
        )

        self.canvas_widget = self.canvas.get_tk_widget()

        # Without this, canvas may try to “own” available space and override intended fixed split behavior
        self.canvas_widget.pack_propagate(False)

        self.cursor = None

        self.dragging = False

        self.canvas.mpl_connect(
            "button_press_event",
            self.on_press
        )

        self.canvas.mpl_connect(
            "button_release_event",
            self.on_release
        )

        self.canvas.mpl_connect(
            "motion_notify_event",
            self.on_motion
        )

    def draw_signals(self):

        self.ax.clear()

        all_values = []

        for label, signal in self.state.plot_signals:

            self.ax.plot(
                self.state.t,
                signal,
                label=label
            )

            all_values.extend(signal)

        graph_time = self.state.playback_time + self.state.graph_offset
        self.cursor = self.ax.axvline(graph_time, color='red')

        self.ax.set_xlim(
            self.state.start_time,
            self.state.end_time
        )

        self.ax.set_ylim(
            np.min(all_values) - 2,
            np.max(all_values) + 2
        )

        self.ax.grid(True)

        self.ax.legend()

        self.canvas.draw()

    def update_cursor(self):

        if self.cursor is not None:

            graph_time = self.state.playback_time + self.state.graph_offset
            self.cursor.set_xdata([graph_time])

            self.canvas.draw_idle()

    def on_press(self, event):

        if event.inaxes != self.ax:
            return

        self.dragging = True

    def on_release(self, event):

        self.dragging = False

    def on_motion(self, event):

        if not self.dragging:
            return

        if event.xdata is None:
            return
        
        clicked_time = max(
            self.state.start_time,
            min(event.xdata, self.state.end_time)
        )

        # set alignment offset
        self.state.graph_offset = clicked_time - self.state.playback_time

        self.timeline_callback(self.state.playback_time)