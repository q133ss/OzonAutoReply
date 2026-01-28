APP_STYLESHEET = """
QWidget {
    color: #E9EAF0;
    font-size: 12pt;
    font-family: "Segoe UI Variable", "Segoe UI";
}

#Root, QMainWindow {
    background: transparent;
}

#Chrome {
    background: rgba(28, 30, 38, 180);
    border-radius: 18px;
}

QTabWidget::pane {
    border: none;
}

QTabBar::tab {
    background: rgba(255, 255, 255, 22);
    padding: 8px 16px;
    border-radius: 10px;
    margin-right: 6px;
}

QTabBar::tab:selected {
    background: rgba(255, 255, 255, 48);
}

QTabBar::tab:hover {
    background: rgba(255, 255, 255, 60);
}

QScrollArea {
    background: transparent;
}

QListWidget {
    background: rgba(0, 0, 0, 40);
    border-radius: 10px;
    padding: 6px;
}

QLineEdit, QSpinBox, QPlainTextEdit {
    background: rgba(0, 0, 0, 70);
    border: 1px solid rgba(255, 255, 255, 35);
    border-radius: 10px;
    padding: 6px 8px;
}

QPlainTextEdit {
    selection-background-color: rgba(70, 130, 255, 140);
}

QPushButton {
    background: rgba(255, 255, 255, 28);
    border: 1px solid rgba(255, 255, 255, 50);
    border-radius: 10px;
    padding: 6px 14px;
}

QPushButton:hover {
    background: rgba(255, 255, 255, 48);
}

QPushButton:pressed {
    background: rgba(255, 255, 255, 68);
}

#ReviewCard {
    background: rgba(255, 255, 255, 18);
    border: 1px solid rgba(255, 255, 255, 40);
    border-radius: 14px;
}

#RatingBadge {
    background: rgba(76, 140, 255, 80);
    border: 1px solid rgba(76, 140, 255, 150);
    border-radius: 10px;
    padding: 2px 8px;
    min-width: 24px;
    text-align: center;
}

#MetaText {
    color: rgba(233, 234, 240, 160);
}

#StatusLabel {
    color: #7CE399;
}

#TitleLabel {
    font-size: 13pt;
    font-weight: 600;
}

#WindowButton {
    border-radius: 7px;
    background: rgba(255, 255, 255, 18);
    font-size: 11pt;
    padding: 0px;
}

#WindowButton:hover {
    background: rgba(255, 255, 255, 40);
}

#CloseButton {
    border-radius: 7px;
    font-size: 11pt;
    padding: 0px;
    background: rgba(255, 92, 92, 70);
    border: 1px solid rgba(255, 120, 120, 140);
}

#CloseButton:hover {
    background: rgba(255, 92, 92, 120);
}
"""
