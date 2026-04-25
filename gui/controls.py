from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QCheckBox, QApplication
from PyQt6.QtCore import Qt
from gui.theme import get_stylesheet


class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBarFrame")
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)

        self.status_label = QLabel("Ready")
        self.status_label.setProperty("class", "Subtitle")
        layout.addWidget(self.status_label)

        sep1 = QLabel("|")
        sep1.setProperty("class", "Subtitle")
        layout.addWidget(sep1)

        self.agents_label = QLabel("Agents: 0")
        self.agents_label.setProperty("class", "Subtitle")
        layout.addWidget(self.agents_label)

        sep2 = QLabel("|")
        sep2.setProperty("class", "Subtitle")
        layout.addWidget(sep2)

        self.tools_label = QLabel("Tools: 0")
        self.tools_label.setProperty("class", "Subtitle")
        layout.addWidget(self.tools_label)

        layout.addStretch()

        self.theme_switch = QCheckBox("Dark")
        self.theme_switch.setChecked(True)
        self.theme_switch.stateChanged.connect(self._toggle_theme)
        layout.addWidget(self.theme_switch)

    def _toggle_theme(self):
        is_dark = self.theme_switch.isChecked()
        qss = get_stylesheet(dark_mode=is_dark)
        if QApplication.instance():
            QApplication.instance().setStyleSheet(qss)

    def set_status(self, text: str, _color: str = ""):
        self.status_label.setText(text)

    def set_agent_count(self, count: int):
        self.agents_label.setText(f"Agents: {count}")

    def set_tool_count(self, count: int):
        self.tools_label.setText(f"Tools: {count}")

    @property
    def frame(self):
        return self
