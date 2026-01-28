from typing import Optional

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class TitleBar(QWidget):
    minimize_requested = pyqtSignal()
    maximize_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, title: str = "") -> None:
        super().__init__()
        self._drag_pos: Optional[QPoint] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("TitleLabel")
        layout.addWidget(self.title_label, 1)

        self.min_button = QPushButton("—")
        self.min_button.setObjectName("WindowButton")
        self.min_button.setFixedSize(30, 24)
        self.min_button.clicked.connect(self.minimize_requested.emit)

        self.max_button = QPushButton("□")
        self.max_button.setObjectName("WindowButton")
        self.max_button.setFixedSize(30, 24)
        self.max_button.clicked.connect(self.maximize_requested.emit)

        self.close_button = QPushButton("×")
        self.close_button.setObjectName("CloseButton")
        self.close_button.setFixedSize(30, 24)
        self.close_button.clicked.connect(self.close_requested.emit)

        layout.addWidget(self.min_button)
        layout.addWidget(self.max_button)
        layout.addWidget(self.close_button)

        self.setFixedHeight(40)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            if not self.window().isMaximized():
                self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_requested.emit()
            event.accept()
        super().mouseDoubleClickEvent(event)
