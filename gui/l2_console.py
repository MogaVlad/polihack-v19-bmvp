import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QComboBox,
    QPushButton, QTextEdit, QScrollArea, QFileDialog, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

import config
from llm.gemini_client import GeminiClient


class LlmWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, template_path, data):
        super().__init__()
        self.template_path = template_path
        self.data = data

    def run(self):
        try:
            client = GeminiClient()
            result = client.send_with_template(self.template_path, self.data)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(f"[Error]: {e}")


class L2ConsoleTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("L2ConsoleTab")
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        wrapper = QWidget()
        scroll_area.setWidget(wrapper)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(16, 16, 16, 16)
        wrapper_layout.setSpacing(12)

        banner = QFrame()
        banner.setProperty("class", "L2Plain")
        banner_layout = QVBoxLayout(banner)

        banner_title = QLabel("LEGACY PROMPTING")
        banner_title.setProperty("class", "SectionHeader")
        banner_layout.addWidget(banner_title)

        banner_lbl = QLabel(
            "Versioned prompts, manual data flow, raw text output.\n"
            "Switch to Agent Library for structured agent assisted workflow."
        )
        banner_lbl.setWordWrap(True)
        banner_layout.addWidget(banner_lbl)
        wrapper_layout.addWidget(banner)

        controls = QFrame()
        controls.setProperty("class", "L2Plain")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(6, 4, 6, 4)

        controls_layout.addWidget(QLabel("Prompt Template:"))

        self.template_combo = QComboBox()
        templates = self._load_template_names()
        self.template_combo.addItems(templates)
        controls_layout.addWidget(self.template_combo)

        view_btn = QPushButton("View Template")
        view_btn.setProperty("class", "L2PlainBtn")
        view_btn.clicked.connect(self._view_template)
        controls_layout.addWidget(view_btn)

        browse_btn = QPushButton("Browse...")
        browse_btn.setProperty("class", "L2PlainBtn")
        browse_btn.clicked.connect(self._browse_template)
        controls_layout.addWidget(browse_btn)

        controls_layout.addStretch()
        wrapper_layout.addWidget(controls)

        data_card = QFrame()
        data_card.setProperty("class", "L2Plain")
        data_layout = QVBoxLayout(data_card)

        data_header = QHBoxLayout()
        data_header_lbl = QLabel("DATA INPUT")
        data_header_lbl.setProperty("class", "SectionHeader")
        data_header.addWidget(data_header_lbl)

        load_btn = QPushButton("Load File")
        load_btn.setProperty("class", "L2PlainBtn")
        load_btn.clicked.connect(self._load_file)
        data_header.addWidget(load_btn, 0, Qt.AlignmentFlag.AlignRight)

        data_layout.addLayout(data_header)

        self.data_input = QTextEdit()
        self.data_input.setMinimumHeight(120)
        data_layout.addWidget(self.data_input)

        wrapper_layout.addWidget(data_card, 1)

        self.send_btn = QPushButton("Send to LLM")
        self.send_btn.setProperty("class", "L2PlainBtn")
        self.send_btn.clicked.connect(self._send_to_llm)
        wrapper_layout.addWidget(self.send_btn, 0, Qt.AlignmentFlag.AlignCenter)

        response_card = QFrame()
        response_card.setProperty("class", "L2Plain")
        response_layout = QVBoxLayout(response_card)

        resp_lbl = QLabel("RAW RESPONSE")
        resp_lbl.setProperty("class", "SectionHeader")
        response_layout.addWidget(resp_lbl)

        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setMinimumHeight(140)
        response_layout.addWidget(self.response_text)

        wrapper_layout.addWidget(response_card, 1)

    def _load_template_names(self):
        if not os.path.isdir(config.PROMPTS_DIR):
            return []
        return [f for f in sorted(os.listdir(config.PROMPTS_DIR)) if f.endswith(".md")]

    def _browse_template(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Prompt Template", "", "Prompt files (*.md *.txt);;All files (*.*)"
        )
        if not filepath:
            return
        name = os.path.basename(filepath)
        idx = self.template_combo.findText(name)
        if idx == -1:
            self.template_combo.addItem(name, filepath)
            self.template_combo.setCurrentIndex(self.template_combo.count() - 1)
        else:
            self.template_combo.setItemData(idx, filepath)
            self.template_combo.setCurrentIndex(idx)

    def _resolve_template_path(self) -> str:
        custom = self.template_combo.currentData()
        if custom and os.path.isfile(custom):
            return custom
        name = self.template_combo.currentText()
        if name:
            return os.path.join(config.PROMPTS_DIR, name)
        return ""

    def _view_template(self):
        template_name = self.template_combo.currentText()
        if not template_name:
            return

        filepath = self._resolve_template_path()
        if not os.path.isfile(filepath):
            return

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        win = QDialog(self)
        win.setWindowTitle(f"Template: {template_name}")
        win.resize(620, 520)

        layout = QVBoxLayout(win)
        textbox = QTextEdit()
        textbox.setReadOnly(True)
        textbox.setPlainText(content)
        layout.addWidget(textbox)
        win.exec()

    def _load_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Data File", "", "JSON files (*.json);;All files (*.*)"
        )
        if filepath:
            with open(filepath, "r", encoding="utf-8") as f:
                self.data_input.setPlainText(f.read())

    def _send_to_llm(self):
        template_name = self.template_combo.currentText()
        if not template_name:
            return

        template_path = self._resolve_template_path()
        data = self.data_input.toPlainText().strip()
        if not data:
            return

        self.send_btn.setEnabled(False)
        self.response_text.setPlainText("Sending to LLM...")

        self.worker = LlmWorker(template_path, data)
        self.worker.finished.connect(self._display_response)
        self.worker.start()

    def _display_response(self, text: str):
        self.send_btn.setEnabled(True)
        self.response_text.setPlainText(text)
