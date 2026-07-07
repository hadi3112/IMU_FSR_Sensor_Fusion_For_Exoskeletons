import tkinter as tk
from tkinter import ttk
from tkinter import filedialog


class Controls:

    def __init__(
        self,
        parent,
        state,
        load_video_callback,
        load_mat_callback,
        apply_time_callback,
        play_callback,
        pause_callback,
        seek_callback
    ):

        self.parent = parent
        self.state = state

        # for Synching Scrub Ui element with when its dragged ad callback is fired
        self.is_scrubbing = False

        self.frame = tk.Frame(parent)

        # =====================
        # FILE BUTTONS
        # =====================
        tk.Button(
            self.frame,
            text="Load MP4",
            command=lambda: self.load_video(load_video_callback)
        ).pack(side=tk.LEFT)

        tk.Button(
            self.frame,
            text="Load MAT",
            command=lambda: self.load_mat(load_mat_callback)
        ).pack(side=tk.LEFT)

        # =====================
        # PLAYBACK
        # =====================

        tk.Button(
            self.frame,
            text="Play",
            command=play_callback
        ).pack(side=tk.LEFT)

        tk.Button(
            self.frame,
            text="Pause",
            command=pause_callback
        ).pack(side=tk.LEFT)

        # =====================
        # SPEED
        # =====================

        self.speed_var = tk.DoubleVar(value=1.0)

        speed_box = ttk.Combobox(
            self.frame,
            textvariable=self.speed_var,
            values=[0.25, 0.5, 1.0, 2.0, 4.0],
            width=5
        )

        speed_box.pack(side=tk.LEFT)

        speed_box.bind(
            "<<ComboboxSelected>>",
            self.update_speed
        )

        # =====================
        # START / END
        # =====================

        tk.Label(self.frame, text="Start").pack(side=tk.LEFT)

        self.start_entry = tk.Entry(self.frame, width=6)
        self.start_entry.insert(0, "0")
        self.start_entry.pack(side=tk.LEFT)

        tk.Label(self.frame, text="End").pack(side=tk.LEFT)

        self.end_entry = tk.Entry(self.frame, width=6)
        self.end_entry.insert(0, "10")
        self.end_entry.pack(side=tk.LEFT)

        tk.Button(
            self.frame,
            text="Apply",
            command=lambda: apply_time_callback(
                self.start_entry.get(),
                self.end_entry.get()
            )
        ).pack(side=tk.LEFT)

        # =====================
        # TIMELINE
        # =====================

        self.timeline = tk.Scale(
            self.frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            resolution=0.01,
            length=1200
        )

        self.timeline.pack(side=tk.TOP, fill=tk.X)

        # Explicit mouse event handling for Scrubbing mp4
        self.timeline.bind("<ButtonPress-1>", self.on_scrub_start)
        self.timeline.bind("<B1-Motion>", self.on_scrub_move)
        self.timeline.bind("<ButtonRelease-1>", self.on_scrub_end)

        self.seek_callback = seek_callback

    def load_video(self, callback):

        path = filedialog.askopenfilename(
            filetypes=[("MP4 Files", "*.mp4")]
        )

        if path:
            callback(path)

    def load_mat(self, callback):

        path = filedialog.askopenfilename(
            filetypes=[("MAT Files", "*.mat")]
        )

        if path:
            callback(path)

    def update_speed(self, event=None):

        self.state.playback_speed = (
            self.speed_var.get()
        )

    def on_timeline_change(self, value):

        self.seek_callback(float(value))

    def on_scrub_start(self, event):
        self.is_scrubbing = True
        self.state.timeline_locked = True
    
    def on_scrub_move(self, event):

        value = self.timeline.get()
        self.seek_callback(float(value))
    
    def on_scrub_end(self, event):
        self.is_scrubbing = False
        self.state.timeline_locked = False
    
    def set_timeline_range(self, duration):

        self.timeline.config(to=duration)

    def update_timeline(self, current_time):

        # do not override user dragging
        # drag → seek video immediately: video updates → slider NOT overwritten during drag
        # release → playback resumes control
        if self.is_scrubbing:
            return

        self.timeline.set(current_time)