import cv2
from PIL import Image, ImageTk


class VideoPanel:

    def __init__(self, parent, state):

        self.parent = parent
        self.state = state

        self.label = None

    def set_widget(self, label_widget):
        self.label = label_widget

    def load_video(self, path):

        self.state.video_path = path

        self.state.cap = cv2.VideoCapture(path)

        self.state.fps = self.state.cap.get(cv2.CAP_PROP_FPS)

        self.state.total_frames = int(
            self.state.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        self.state.duration = (
            self.state.total_frames / self.state.fps
        )

        self.state.end_time = self.state.duration

    def update_frame(self):

        if self.state.cap is None:
            return

        frame_number = int(
            self.state.playback_time * self.state.fps
        )

        # clamp frame index
        frame_number = max(
            0,
            min(
                frame_number,
                self.state.total_frames - 1
            )
        )

        # only seek when needed
        if self.state.force_seek:

            self.state.cap.set(
                cv2.CAP_PROP_POS_FRAMES,
                frame_number
            )

            self.state.force_seek = False

        ret, frame = self.state.cap.read()

        if not ret:
            return

        # BGR -> RGB
        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        # convert to PIL image
        img = Image.fromarray(frame)

        # fixed rendering size
        img = img.resize(
            (640, 480),
            Image.Resampling.LANCZOS
        )

        # PIL -> Tkinter image
        imgtk = ImageTk.PhotoImage(image=img)

        # prevent garbage collection
        self.label.imgtk = imgtk

        # display image
        self.label.configure(image=imgtk)