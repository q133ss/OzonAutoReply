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
    background: #1C1E26;
    border-radius: 18px;
}

QTabWidget::pane {
    border: none;
    background: #1C1E26;
}

QTabBar::tab {
    background: #2B2F3A;
    padding: 8px 16px;
    border-radius: 10px;
    margin-right: 6px;
}

QTabBar::tab:selected {
    background: #3A3F4B;
}

QTabBar::tab:hover {
    background: #424857;
}

QScrollArea {
    background: #1C1E26;
    border-radius: 10px;
}

QScrollArea::viewport {
    background: #1C1E26;
}

QListWidget {
    background: #232833;
    border-radius: 10px;
    padding: 6px;
}

QLineEdit, QSpinBox, QPlainTextEdit {
    background: #2A2F3A;
    border: 1px solid #3C4454;
    border-radius: 10px;
    padding: 6px 8px;
}

QSpinBox {
    padding-right: 24px;
}

QSpinBox::up-button, QSpinBox::down-button {
    subcontrol-origin: border;
    width: 20px;
    background: #2F3543;
    border-left: 1px solid #3C4454;
}

QSpinBox::up-button {
    subcontrol-position: top right;
    border-top-right-radius: 10px;
}

QSpinBox::down-button {
    subcontrol-position: bottom right;
    border-bottom-right-radius: 10px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #394152;
}

QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
    background: #424C60;
}

QSpinBox::up-arrow {
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 6px solid #E9EAF0;
}

QSpinBox::down-arrow {
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #E9EAF0;
}

QPlainTextEdit {
    selection-background-color: rgba(70, 130, 255, 180);
}

QPushButton {
    background: #303644;
    border: 1px solid #3F4758;
    border-radius: 10px;
    padding: 6px 14px;
}

QPushButton:hover {
    background: #394152;
}

QPushButton:pressed {
    background: #424C60;
}

#ReviewCard {
    background: #232833;
    border: 1px solid #343B48;
    border-radius: 14px;
}

#ReviewList {
    background: #1C1E26;
}

#ExamplesTab {
    background: #1C1E26;
}

#ExamplesForm {
    background: #1C1E26;
}

#ExamplesListContainer {
    background: #1C1E26;
}

#ExamplesList {
    background: #232833;
    border: 1px solid #343B48;
    border-radius: 10px;
    padding: 6px;
}

#RatingBadge {
    background: #2F6BFF;
    border: 1px solid #4D80FF;
    border-radius: 10px;
    padding: 2px 8px;
    min-width: 24px;
    text-align: center;
}

#MetaText {
    color: #B6BBC6;
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
    background: #2B2F3A;
    font-size: 11pt;
    padding: 0px;
}

#WindowButton:hover {
    background: #3A3F4B;
}

#CloseButton {
    border-radius: 7px;
    font-size: 11pt;
    padding: 0px;
    background: #D04B4B;
    border: 1px solid #E07C7C;
}

#CloseButton:hover {
    background: #E25C5C;
}
"""
