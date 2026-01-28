from PyQt6.QtWidgets import QVBoxLayout, QWidget


class ReviewList(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(12)

    def clear(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def add_card(self, card: QWidget) -> None:
        self.layout.addWidget(card)

    def finalize(self) -> None:
        self.layout.addStretch(1)
