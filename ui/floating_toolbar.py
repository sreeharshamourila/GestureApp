
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QPushButton

class FloatingToolbar(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setStyleSheet("""
            QFrame { background: rgba(40,40,40,200); border-radius:8px; }
            QPushButton { background: #e0e0e0; border: none; padding:4px; }
        """)
        layout = QHBoxLayout()
        layout.setContentsMargins(6,6,6,6)
        layout.setSpacing(6)
        self.setLayout(layout)

        buttons = [
            "Flip H", "Flip V", "Gray", "Color",
            "Rotate L", "Rotate R",
            "Bright+", "Bright-",
            "Contrast+", "Contrast-",
            "Sketch", "Sepia", "Poster",
            "Zoom+", "Zoom-", "Reset"
        ]

        for name in buttons:
            btn = QPushButton(name)
            btn.setFixedSize(78, 28)
            btn.clicked.connect(lambda checked, n=name: parent.apply_effect_and_refresh(n))
            layout.addWidget(btn)

        self.adjustSize()
        self.hide()
