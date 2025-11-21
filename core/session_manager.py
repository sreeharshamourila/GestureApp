
import cv2
import os
import tempfile
import random
import numpy as np
from PyQt5.QtGui import QImage, QPixmap
from core import transformations as T

MAX_DIM = 1600  # keep a reasonable internal max (very large images will be shrunk for safety)

class SessionManager:
    def __init__(self):
        self.session_images = []   # list of dicts: {"type":"image"/"video","path":...}
        self.video_pool = []       # up to 10 video paths sampled
        self.temp_dir = tempfile.TemporaryDirectory()
        self.current_image = None      # original at (possibly reduced) internal resolution
        self.current_display = None    # transformed version (temporary effects)
        self.zoom_level = 1.0
        self.brightness = 0
        self.contrast = 1.0

    def load_session(self, folder, session_length):
        # Build pools
        images = []
        videos = []
        if not os.path.isdir(folder):
            self.session_images = []
            return
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                ext = name.lower().split('.')[-1]
                if ext in ('jpg', 'jpeg', 'png', 'bmp', 'webp'):
                    images.append(path)
                elif ext in ('mp4', 'mov', 'avi', 'mkv'):
                    videos.append(path)

        # sample up to 10 videos for lazy extraction
        self.video_pool = random.sample(videos, min(10, len(videos)))

        # build session list by randomly choosing between available images & videos
        pool = []
        if images:
            pool.extend([('image', p) for p in images])
        if self.video_pool:
            pool.extend([('video', p) for p in self.video_pool])
        if not pool:
            self.session_images = []
            return

        self.session_images = []
        for _ in range(session_length):
            typ, p = random.choice(pool)
            self.session_images.append({"type": typ, "path": p})

    def safe_imread(self, path):
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            # return a blank placeholder
            return 255 * np.ones((600, 800, 3), dtype=np.uint8)
        return self._limit_size(img)

    def get_random_frame_from_video(self, video_path):
        cap = cv2.VideoCapture(video_path)
        try:
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total <= 0:
                return 255 * np.ones((600, 800, 3), dtype=np.uint8)
            idx = random.randint(0, total - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                return 255 * np.ones((600, 800, 3), dtype=np.uint8)
            return self._limit_size(frame)
        finally:
            cap.release()

    def _limit_size(self, img):
        # preserve aspect and original resolution when possible,
        # but cap largest dimension to MAX_DIM for internal safety
        h, w = img.shape[:2]
        scale = min(MAX_DIM / max(w, h), 1.0)  # never upscale here
        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return img

    def get_frame(self, index):
        if index < 0 or index >= len(self.session_images):
            return None
        entry = self.session_images[index]
        if entry["type"] == "image":
            img = self.safe_imread(entry["path"])
        else:
            img = self.get_random_frame_from_video(entry["path"])

        self.current_image = img  # base image at internal (original or limited) resolution
        self.reset_effects()
        self.current_display = img.copy()
        return self.current_display

    def reset_effects(self):
        self.zoom_level = 1.0
        self.brightness = 0
        self.contrast = 1.0

    def to_qpixmap(self, img, max_display_w=None, max_display_h=None):
        """
        Convert BGR numpy image to QPixmap.
        DO NOT upscale here — scaling for widget is handled by UI code.
        """
        if img is None:
            return QPixmap()
        try:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = img_rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            return QPixmap.fromImage(qimg)
        except Exception as e:
            print("QImage conversion failed:", e)
            return QPixmap()

    # Centralized effects (callable from UI)
    def apply_effect(self, effect):
        if self.current_image is None:
            return
        base = self.current_display.copy()

        # map effect names to functions
        if effect == "Flip H":
            self.current_display = T.flip_horizontal(base)
        elif effect == "Flip V":
            self.current_display = T.flip_vertical(base)
        elif effect == "Gray":
            self.current_display = T.grayscale(base)
        elif effect == "Color":
            self.current_display = to_color = self.current_image.copy()
            self.current_display = to_color
        elif effect == "Rotate L":
            self.current_display = T.rotate_left(base)
        elif effect == "Rotate R":
            self.current_display = T.rotate_right(base)
        elif effect == "Bright+":
            self.brightness = min(self.brightness + 20, 200)
            self.current_display = T.adjust_brightness(self.current_image, self.brightness)
        elif effect == "Bright-":
            self.brightness = max(self.brightness - 20, -200)
            self.current_display = T.adjust_brightness(self.current_image, self.brightness)
        elif effect == "Contrast+":
            self.contrast = min(self.contrast * 1.15, 3.0)
            self.current_display = T.adjust_contrast(self.current_image, self.contrast)
        elif effect == "Contrast-":
            self.contrast = max(self.contrast / 1.15, 0.3)
            self.current_display = T.adjust_contrast(self.current_image, self.contrast)
        elif effect == "Sketch":
            self.current_display = T.sketch(base)
        elif effect == "Sepia":
            self.current_display = T.sepia(base)
        elif effect == "Poster":
            self.current_display = T.posterize(base, levels=4)
        elif effect == "Zoom+":
            self.zoom_level = min(self.zoom_level + 0.15, 3.0)
            self.current_display = T.zoom(self.current_image, self.zoom_level)
        elif effect == "Zoom-":
            self.zoom_level = max(self.zoom_level - 0.15, 0.5)
            self.current_display = T.zoom(self.current_image, self.zoom_level)
        elif effect == "Reset":
            self.reset_effects()
            self.current_display = self.current_image.copy()

