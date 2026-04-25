from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QCheckBox, QWidget, QApplication
from PyQt6.QtCore import Qt
from gui.theme import get_stylesheet

class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBarFrame")
        self.setFixedHeight(36)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        
        self.status_label = QLabel("● Ready")
        self.status_label.setStyleSheet("color: #b3c7c1;")
        layout.addWidget(self.status_label)
        
        sep1 = QLabel("│")
        layout.addWidget(sep1)
        
        self.agents_label = QLabel("Agents: 0 loaded")
        layout.addWidget(self.agents_label)
        
        sep2 = QLabel("│")
        layout.addWidget(sep2)
        
        self.tools_label = QLabel("Tools: 0 available")
        layout.addWidget(self.tools_label)
        
        layout.addStretch()
        
        self.mode_label = QLabel("☀")
        layout.addWidget(self.mode_label)
        
        self.theme_switch = QCheckBox()
        self.theme_switch.setChecked(True)
        self.theme_switch.stateChanged.connect(self._toggle_theme)
        layout.addWidget(self.theme_switch)
        
        self.moon_label = QLabel("🌙")
        layout.addWidget(self.moon_label)

    def _toggle_theme(self):
        is_dark = self.theme_switch.isChecked()
        qss = get_stylesheet(dark_mode=is_dark)
        if QApplication.instance():
            QApplication.instance().setStyleSheet(qss)

    def set_status(self, text: str, color: str = "#b3c7c1"):
        self.status_label.setText(f"● {text}")
        self.status_label.setStyleSheet(f"color: {color};")

    def set_agent_count(self, count: int):
        self.agents_label.setText(f"Agents: {count} loaded")

    def set_tool_count(self, count: int):
        self.tools_label.setText(f"Tools: {count} available")

    @property
    def frame(self):
        return self