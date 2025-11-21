from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSpinBox, QCheckBox, QProgressBar, QFileDialog)
from PyQt5.QtCore import QTimer, Qt, QRectF
from PyQt5.QtGui import QPainter, QFont, QColor
from ui.floating_toolbar import FloatingToolbar
from core.session_manager import SessionManager
import gc, time

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gesture Practice (Professional Skeleton)")
        self.session_manager = SessionManager()
        self.current_index = 0
        self.start_time = None
        self.duration = 3.0  # seconds per image
        self.tick_interval_ms = 100
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Top controls
        top = QHBoxLayout()
        self.folder_line = QLineEdit()
        btn_browse = QPushButton("Browse Folder")
        btn_browse.clicked.connect(self.browse_folder)
        top.addWidget(self.folder_line)
        top.addWidget(btn_browse)

        self.timer_spin = QSpinBox()
        self.timer_spin.setRange(1, 120)
        self.timer_spin.setValue(3)
        self.timer_spin.valueChanged.connect(self._on_timer_value_changed)
        top.addWidget(QLabel("Timer (sec):"))
        top.addWidget(self.timer_spin)

        self.session_spin = QSpinBox()
        self.session_spin.setRange(1, 500)
        self.session_spin.setValue(20)
        top.addWidget(QLabel("Session len:"))
        top.addWidget(self.session_spin)

        self.loop_cb = QCheckBox("Loop")
        top.addWidget(self.loop_cb)

        self.overlay_cb = QCheckBox("Overlay")
        self.overlay_cb.setChecked(True)
        top.addWidget(self.overlay_cb)

        self.layout.addLayout(top)

        # Display label (we will set pixmaps on it)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: black;")
        self.layout.addWidget(self.image_label, stretch=1)

        # Progress
        self.progress = QProgressBar()
        self.layout.addWidget(self.progress)

        # Controls
        ctrl = QHBoxLayout()
        btn_start = QPushButton("Start")
        btn_start.clicked.connect(self.start_session)
        btn_pause = QPushButton("Pause")
        btn_pause.clicked.connect(self.pause_session)
        btn_resume = QPushButton("Resume")
        btn_resume.clicked.connect(self.resume_session)
        btn_stop = QPushButton("Stop")
        btn_stop.clicked.connect(self.stop_session)
        for b in (btn_start, btn_pause, btn_resume, btn_stop):
            ctrl.addWidget(b)
        self.layout.addLayout(ctrl)

        # Floating toolbar
        self.floating_toolbar = FloatingToolbar(self)
        self.floating_toolbar.hide()

        # Timer (tick every 100ms)
        self.timer = QTimer()
        self.timer.setInterval(self.tick_interval_ms)
        self.timer.timeout.connect(self._tick)

    def _on_timer_value_changed(self, v):
        self.duration = float(v)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_line.setText(folder)

    def start_session(self):
        folder = self.folder_line.text()
        self.session_manager.load_session(folder, self.session_spin.value())
        if not self.session_manager.session_images:
            self.image_label.setText("No images found")
            return
        self.current_index = 0
        self._show_frame_index(self.current_index)
        self.floating_toolbar.show()
        self._position_toolbar()
        self.start_time = time.time()
        self.timer.start()

    def pause_session(self):
        self.timer.stop()

    def resume_session(self):
        self.start_time = time.time()
        self.timer.start()

    def stop_session(self):
        self.timer.stop()
        self.current_index = 0
        self.session_manager.current_display = None
        self.image_label.clear()
        self.floating_toolbar.hide()
        gc.collect()

    def _tick(self):
        # update countdown overlay; if elapsed >= duration advance frame
        if self.session_manager.current_display is None:
            return
        elapsed = time.time() - self.start_time if self.start_time else 0.0
        remaining = max(0, self.duration - elapsed)
        # when time finished, next frame
        if remaining <= 0:
            self.current_index += 1
            if self.current_index >= len(self.session_manager.session_images):
                if self.loop_cb.isChecked():
                    self.current_index = 0
                else:
                    self.stop_session()
                    return
            self._show_frame_index(self.current_index)
            self.start_time = time.time()
            return
        # refresh overlay (countdown) without reloading frame from disk
        self._render_current_display_with_overlay(remaining)

    def _show_frame_index(self, idx):
        gc.collect()
        frame = self.session_manager.get_frame(idx)
        self.progress.setValue(int((idx / max(1, len(self.session_manager.session_images))) * 100))
        self._render_current_display_with_overlay(self.duration)

    def _render_current_display_with_overlay(self, remaining_time):
        img = self.session_manager.current_display
        if img is None:
            return
        # build pixmap without upscaling: if image <= label size show original; if larger scale down keeping aspect
        pixmap = self.session_manager.to_qpixmap(img)
        if pixmap.isNull():
            return

        label_w = max(1, self.image_label.width())
        label_h = max(1, self.image_label.height())
        img_w = pixmap.width()
        img_h = pixmap.height()

        # Decide whether to scale down
        if img_w <= label_w and img_h <= label_h:
            draw_pix = pixmap
            draw_w, draw_h = img_w, img_h
        else:
            scaled = pixmap.scaled(label_w, label_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            draw_pix = scaled
            draw_w, draw_h = scaled.width(), scaled.height()

        # Compose overlay using QPainter
        composed = draw_pix.copy()
        painter = QPainter(composed)
        # draw countdown circle (small) + remaining seconds text if overlay enabled
        if self.overlay_cb.isChecked():
            radius = 36
            margin = 12
            cx = margin + radius
            cy = margin + radius
            # background circle
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor(0, 0, 0, 120))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

            # arc showing remaining proportion
            span = int((remaining_time / max(0.001, self.duration)) * 360 * 16)
            painter.setPen(QColor(0, 200, 0))
            painter.setBrush(Qt.NoBrush)
            # drawArc expects QRect
            painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2, 90 * 16, -span)

            # remaining seconds text
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Sans", 10, QFont.Bold))
            secs = int(round(remaining_time))
            painter.drawText(QRectF(cx - radius, cy - 12, radius * 2, 24), Qt.AlignCenter, f"{secs}s")

            # draw index/progress text bottom-left
            idx_text = f"{self.current_index + 1}/{len(self.session_manager.session_images)}"
            painter.setFont(QFont("Sans", 10))
            painter.drawText(10, draw_h - 10, idx_text)

        painter.end()

        # center composed pixmap into label by using QLabel.setPixmap of a container sized pixmap
        # create a container pixmap same as label size, fill black, then paint composed centered
        container = composed
        if draw_w != label_w or draw_h != label_h:
            from PyQt5.QtGui import QPixmap as Qp
            container = Qp(label_w, label_h)
            container.fill(QColor(0, 0, 0))
            tmp_painter = QPainter(container)
            x = (label_w - draw_w) // 2
            y = (label_h - draw_h) // 2
            tmp_painter.drawPixmap(x, y, composed)
            tmp_painter.end()

        self.image_label.setPixmap(container)
        # reposition toolbar
        self._position_toolbar()

    def _position_toolbar(self):
        # place bottom-right inside image_label
        self.floating_toolbar.adjustSize()
        x = self.image_label.x() + self.image_label.width() - self.floating_toolbar.width() - 12
        y = self.image_label.y() + self.image_label.height() - self.floating_toolbar.height() - 12
        # keep inside window bounds
        if x < 8: x = 8
        if y < 8: y = 8
        self.floating_toolbar.move(x, y)
        self.floating_toolbar.raise_()

    def apply_effect_and_refresh(self, effect):
        # call session manager to mutate current_display, then re-render overlay immediately
        self.session_manager.apply_effect(effect)
        # restart countdown for current frame
        self.start_time = time.time()
        self._render_current_display_with_overlay(self.duration)

    def closeEvent(self, event):
        self.stop_session()
        event.accept()

