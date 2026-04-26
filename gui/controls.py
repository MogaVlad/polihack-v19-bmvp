from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QApplication, QPushButton
from gui.theme import get_stylesheet


class StatusBar(QFrame):
    def __init__(self, parent=None, on_theme_change=None):
        super().__init__(parent)
        self._on_theme_change = on_theme_change
        self.setObjectName("StatusBarFrame")
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

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

        self.theme_label = QLabel("Theme: Dark")
        self.theme_label.setProperty("class", "Subtitle")
        layout.addWidget(self.theme_label)

        self.theme_toggle_btn = QPushButton("Switch to Light")
        self.theme_toggle_btn.setProperty("class", "ThemeToggle")
        self.theme_toggle_btn.setCheckable(True)
        self.theme_toggle_btn.setChecked(True)  # Start in dark mode
        self.theme_toggle_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_toggle_btn)

        # Keep label/button state synced on startup
        self._apply_theme_ui(True)

    def _apply_theme_ui(self, is_dark: bool):
        self.theme_label.setText(f"Theme: {'Dark' if is_dark else 'Light'}")
        self.theme_toggle_btn.setText("Switch to Light" if is_dark else "Switch to Dark")

    def _toggle_theme(self):
        is_dark = self.theme_toggle_btn.isChecked()
        self._apply_theme_ui(is_dark)

        if self._on_theme_change:
            self._on_theme_change(is_dark)
            return

        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setStyleSheet(get_stylesheet(dark_mode=is_dark))

    def set_status(self, text: str, _color: str = ""):
        self.status_label.setText(text)

    def set_agent_count(self, count: int):
        self.agents_label.setText(f"Agents: {count}")

    def set_tool_count(self, count: int):
        self.tools_label.setText(f"Tools: {count}")

    @property
    def frame(self):
        return self
