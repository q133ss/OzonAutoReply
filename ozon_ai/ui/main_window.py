from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..db import Database
from .tabs.accounts import AccountsTab
from .tabs.reviews import ReviewsTab
from .tabs.settings import SettingsTab
from .title_bar import TitleBar


class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.setWindowTitle("Ozon автоответ")
        self.resize(1100, 750)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(16, 16, 16, 16)

        chrome = QFrame()
        chrome.setObjectName("Chrome")
        chrome_layout = QVBoxLayout(chrome)
        chrome_layout.setContentsMargins(12, 12, 12, 12)
        chrome_layout.setSpacing(8)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 180))
        chrome.setGraphicsEffect(shadow)

        title_bar = TitleBar("Ozon автоответ")
        title_bar.minimize_requested.connect(self.showMinimized)
        title_bar.maximize_requested.connect(self._toggle_maximize)
        title_bar.close_requested.connect(self.close)
        chrome_layout.addWidget(title_bar)

        tabs = QTabWidget()
        tabs.addTab(AccountsTab(db), "Аккаунты")
        tabs.addTab(ReviewsTab(db), "Отзывы")
        tabs.addTab(SettingsTab(db), "Настройки")
        chrome_layout.addWidget(tabs)

        root_layout.addWidget(chrome)
        self.setCentralWidget(root)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
