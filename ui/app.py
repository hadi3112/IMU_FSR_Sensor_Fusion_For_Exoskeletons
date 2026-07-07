import tkinter as tk

from ui.state import AppState
from ui.video_panel import VideoPanel
from ui.graph_panel import GraphPanel
from ui.controls import Controls
from ui.mat_handler import load_mat_file


class GaitViewerApp:

    def __init__(self):

        self.root = tk.Tk()

        self.root.title("Interactive Gait Viewer")
        self.root.geometry("1400x800")

        self.state = AppState()

        # =====================================
        # ROOT LAYOUT
        # =====================================

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

        # =====================================
        # TOP FRAME (VIDEO + GRAPH SPLIT)
        # =====================================

        top_frame = tk.Frame(self.root)
        top_frame.grid(row=0, column=0, sticky="nsew")

        # IMPORTANT: enforce 50/50 split
        top_frame.grid_columnconfigure(0, weight=1, uniform="a")
        top_frame.grid_columnconfigure(1, weight=1, uniform="a")
        top_frame.grid_rowconfigure(0, weight=1)

        # =====================================
        # VIDEO PANEL (LEFT HALF)
        # =====================================

        video_frame = tk.Frame(top_frame, bg="black")
        video_frame.grid(row=0, column=0, sticky="nsew")

        self.video_label = tk.Label(video_frame, bg="black")
        self.video_label.place(relx=0.5, rely=0.5, anchor="center")

        self.video_panel = VideoPanel(self.root, self.state)
        self.video_panel.set_widget(self.video_label)

        # Placeholder text
        self.video_placeholder = tk.Label(
            video_frame,
            text="Uploaded MP4 Video will be displayed here",
            fg="white",
            bg="black",
            font=("Arial", 14)
        )

        self.video_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # =====================================
        # GRAPH PANEL (RIGHT HALF)
        # =====================================

        graph_frame = tk.Frame(top_frame, bg="white")
        graph_frame.grid(row=0, column=1, sticky="nsew")

        graph_frame.grid_propagate(False)

        self.graph_panel = GraphPanel(
            graph_frame,
            self.state,
            self.seek_time
        )

        self.graph_panel.canvas_widget.pack(
            fill=tk.BOTH,
            expand=True
        )

        # =====================================
        # CONTROLS (BOTTOM BAR)
        # =====================================

        self.controls = Controls(
            self.root,
            self.state,
            self.load_video,
            self.load_mat,
            self.apply_times,
            self.play,
            self.pause,
            self.seek_time
        )

        self.controls.frame.grid(row=1, column=0, sticky="ew")

        # =====================================
        # UPDATE LOOP
        # =====================================

        self.update_loop()
    # =========================================
    # LOAD VIDEO
    # =========================================

    def load_video(self, path):

        self.video_panel.load_video(path)

        self.controls.set_timeline_range(
            self.state.duration
        )

        # IMPORTANT: force first frame render
        self.state.current_time = 0.0

        # Remove placeholder text
        if hasattr(self, "video_placeholder"):
            self.video_placeholder.place_forget()

        self.video_panel.update_frame()
        self.graph_panel.update_cursor()
        self.controls.update_timeline(0.0)
        

    # =========================================
    # LOAD MAT
    # =========================================

    def load_mat(self, path):

        self.state.mat_path = path

        (
            self.state.t,
            self.state.plot_signals
        ) = load_mat_file(
            path,
            self.state.data_type
        )

        self.graph_panel.draw_signals()
        self.graph_panel.update_cursor()

    # =========================================
    # PLAYBACK
    # =========================================

    def play(self):
        self.state.is_playing = True

    def pause(self):
        self.state.is_playing = False

    # =========================================
    # SEEK TIME
    # =========================================

    def seek_time(self, value):

        self.state.playback_time = float(value)
        self.state.force_seek = True

        self.video_panel.update_frame()
        self.graph_panel.update_cursor()
        self.controls.update_timeline(self.state.current_time)

    # =========================================
    # APPLY START/END TIMES
    # =========================================

    def apply_times(self, start, end):

        self.state.start_time = float(start)
        self.state.end_time = float(end)

        # align graph so that start corresponds to current playback
        self.state.graph_offset = self.state.start_time - self.state.playback_time

        self.video_panel.update_frame()
        self.graph_panel.draw_signals()
        self.graph_panel.update_cursor()
        self.controls.update_timeline(self.state.playback_time)

    # =========================================
    # MAIN UPDATE LOOP
    # =========================================

    def update_loop(self):

        if self.state.is_playing:

            dt = (1 / self.state.fps) * self.state.playback_speed
            self.state.playback_time  += dt

            video_time = self.state.playback_time
            graph_time = self.state.playback_time + self.state.graph_offset

            if self.state.current_time >= self.state.end_time:
                self.state.current_time = self.state.end_time
                self.state.is_playing = False

            self.video_panel.update_frame()
            self.graph_panel.update_cursor()
            self.controls.update_timeline(self.state.playback_time)

        self.root.after(15, self.update_loop)

    # =========================================
    # RUN APP
    # =========================================

    def run(self):
        self.root.mainloop()