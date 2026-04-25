import json
import os
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QTextEdit, QLineEdit, QScrollArea, QFileDialog, QDialog, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from typing import Optional

from models.agent_definition import AgentDefinition
from models.chat import AgentResult
from models.floor_plan import FloorPlan
from models.violations import Violation
from engine.runner import AgentRunner
from engine.conversation import ConversationManager
from engine.prompt_builder import PromptBuilder

_FLAG_KEYWORDS = re.compile(
    r"\b(violation|warning|exceeded|insufficient|blocked|narrow|missing|"
    r"non-compliant|critical|fail|danger|unsafe|risk|dead.?end)\b",
    re.IGNORECASE,
)

_LOCATION_PATTERN = re.compile(
    r"\b((?:Room|Corridor|room|corridor)\s+[A-Za-z]?\d+|[RC]\d+)\b"
)

_SEVERITY_PATTERN = re.compile(
    r"\b(CRITICAL|MAJOR|MINOR|INFO)\b", re.IGNORECASE
)

_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
_BULLET_PATTERN = re.compile(r"^(\s*[-•]\s)", re.MULTILINE)

class AgentRunWorker(QThread):
    status_update = pyqtSignal(str)
    completed = pyqtSignal(object)

    def __init__(self, engine, agent_def, inputs):
        super().__init__()
        self.engine = engine
        self.agent_def = agent_def
        self.inputs = inputs

    def run(self):
        def on_status(msg):
            self.status_update.emit(msg)
        
        try:
            self.engine.run(self.agent_def, self.inputs, on_status_callback=on_status)
        except Exception as e:
            # Result usually is grabbed by a callback, but we need to fetch the last result.
            pass
        # We assume the engine callback or return value is what we need.
        # Actually engine.run returns the AgentResult synchronously.
        # Wait, let's just do it directly.
        pass # Re-implemented below properly


class AgentRunnerWorker(QThread):
    status_update = pyqtSignal(str)
    completed = pyqtSignal(AgentResult)

    def __init__(self, engine, agent_def, inputs):
        super().__init__()
        self.engine = engine
        self.agent_def = agent_def
        self.inputs = inputs

    def run(self):
        def status_cb(msg):
            self.status_update.emit(msg)
            
        def complete_cb(result):
            self.completed.emit(result)
            
        self.engine.run(self.agent_def, self.inputs, on_status_callback=status_cb, on_complete_callback=complete_cb)


class AgentFollowupWorker(QThread):
    status_update = pyqtSignal(str)
    completed = pyqtSignal(str)

    def __init__(self, conversation, msg):
        super().__init__()
        self.conversation = conversation
        self.msg = msg

    def run(self):
        try:
            def status_cb(msg):
                self.status_update.emit(msg)
            response = self.conversation.followup(self.msg, status_callback=status_cb)
            self.completed.emit(response)
        except Exception as e:
            self.completed.emit(f"[Error: {e}]")


class AgentRetryWorker(QThread):
    status_update = pyqtSignal(str)
    completed = pyqtSignal(str)

    def __init__(self, conversation):
        super().__init__()
        self.conversation = conversation

    def run(self):
        try:
            def status_cb(msg):
                self.status_update.emit(msg)
            response = self.conversation.retry_last_followup(status_callback=status_cb)
            if not response:
                response = "No previous follow-up found to retry."
            self.completed.emit(response)
        except Exception as e:
            self.completed.emit(f"[Error: {e}]")


class AgentRunnerTab(QWidget):
    def __init__(self, parent=None, status_bar=None, canvas_panel=None):
        super().__init__(parent)
        self.status_bar = status_bar
        self.canvas_panel = canvas_panel
        self.current_agent = None
        self._has_run = False
        self._is_running = False
        self._last_result = None
        self._conversation = None
        self._engine = AgentRunner()
        self._violation_locations = set()
        self._output_expanded = False
        self._followup_can_retry = False
        
        self.input_widgets = {}
        self._build_ui()

    def _section_header(self, text: str) -> QWidget:
        frame = QWidget()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold; color: #b3c7c1; font-size: 11px;")
        layout.addWidget(lbl)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #b3c7c1;")
        layout.addWidget(sep, 1)
        return frame

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # ── Header ──────────────────────────────────────────────
        header = QFrame()
        header.setProperty("class", "Card")
        header_layout = QVBoxLayout(header)
        
        top_row = QHBoxLayout()
        self.agent_name_label = QLabel("No agent loaded")
        self.agent_name_label.setProperty("class", "Title")
        top_row.addWidget(self.agent_name_label)
        
        self.status_indicator = QLabel("● Ready")
        self.status_indicator.setStyleSheet("color: #b3c7c1;")
        top_row.addWidget(self.status_indicator, 0, Qt.AlignmentFlag.AlignRight)
        header_layout.addLayout(top_row)
        
        bottom_row = QHBoxLayout()
        self.agent_goal_label = QLabel("Select an agent from the library to begin.")
        self.agent_goal_label.setStyleSheet("color: #b3c7c1;")
        bottom_row.addWidget(self.agent_goal_label, 1)
        
        self.view_def_btn = QPushButton("View Definition")
        self.view_def_btn.clicked.connect(self._view_definition)
        bottom_row.addWidget(self.view_def_btn)
        header_layout.addLayout(bottom_row)
        
        main_layout.addWidget(header)

        # ── Two-column body using QSplitter ──────────────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter, 1)
        
        # LEFT COLUMN (Scrollable)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_widget = QWidget()
        self.left_layout = QVBoxLayout(left_widget)
        self.left_layout.setContentsMargins(0, 0, 4, 0)
        left_scroll.setWidget(left_widget)
        self.splitter.addWidget(left_scroll)
        
        # ── INPUTS
        input_card = QFrame()
        input_card.setProperty("class", "Card")
        self.inputs_card_layout = QVBoxLayout(input_card)
        self.inputs_card_layout.addWidget(self._section_header("INPUTS"))
        
        self.inputs_container = QVBoxLayout()
        self.inputs_card_layout.addLayout(self.inputs_container)
        
        self.run_btn = QPushButton("▶  Run Agent")
        self.run_btn.clicked.connect(self._run_agent)
        self.inputs_card_layout.addWidget(self.run_btn)
        self.left_layout.addWidget(input_card)
        
        # ── OUTPUTS
        output_card = QFrame()
        output_card.setProperty("class", "Card")
        out_layout = QVBoxLayout(output_card)
        out_layout.addWidget(self._section_header("OUTPUTS"))
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(160)
        out_layout.addWidget(self.output_text)
        
        export_row = QHBoxLayout()
        export_btn = QPushButton("Export JSON")
        export_btn.clicked.connect(self._export_json)
        export_row.addWidget(export_btn)
        
        show_canvas_btn = QPushButton("Show on Canvas")
        show_canvas_btn.clicked.connect(self._show_on_canvas)
        export_row.addWidget(show_canvas_btn)
        export_row.addStretch()
        out_layout.addLayout(export_row)
        
        self.left_layout.addWidget(output_card)
        
        # ── CONSTRAINTS USED
        cons_card = QFrame()
        cons_card.setProperty("class", "Card")
        cons_layout = QVBoxLayout(cons_card)
        cons_layout.addWidget(self._section_header("CONSTRAINTS USED"))
        self.constraints_label = QLabel("—")
        self.constraints_label.setWordWrap(True)
        cons_layout.addWidget(self.constraints_label)
        self.left_layout.addWidget(cons_card)
        
        self.left_layout.addStretch()

        # RIGHT COLUMN
        right_card = QFrame()
        right_card.setProperty("class", "Card")
        right_layout = QVBoxLayout(right_card)
        right_layout.addWidget(self._section_header("CONVERSATION"))
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        right_layout.addWidget(self.chat_display, 1)
        
        msg_frame = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask a follow-up question...")
        self.chat_input.returnPressed.connect(self._send_message)
        msg_frame.addWidget(self.chat_input, 1)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send_message)
        self.send_btn.setEnabled(False)
        msg_frame.addWidget(self.send_btn)
        
        self.retry_btn = QPushButton("Retry")
        self.retry_btn.clicked.connect(self._retry_followup)
        self.retry_btn.setEnabled(False)
        self.retry_btn.setStyleSheet("background-color: #6b4428; color: white;")
        msg_frame.addWidget(self.retry_btn)
        
        right_layout.addLayout(msg_frame)
        self.splitter.addWidget(right_card)
        
        # Set splitter sizes
        self.splitter.setSizes([400, 500])

    def _toggle_outputs(self):
        pass # Outputs always visible in PyQt version

    def _append_agent_message(self, text: str):
        self.chat_display.append(f"<b style='color:#b3c7c1'>AI Agent:</b> {text}<br>")
        self._auto_scroll()

    def _append_user_message(self, text: str):
        self.chat_display.append(f"<b style='color:#4c5767'>User:</b> {text}<br>")
        self._auto_scroll()

    def _auto_scroll(self):
        sb = self.chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_chat_enabled(self, enabled: bool):
        self.chat_input.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)

    def _set_retry_enabled(self, enabled: bool):
        self._followup_can_retry = enabled
        self.retry_btn.setEnabled(enabled)

    def _set_status(self, text: str, color: str = "#b3c7c1"):
        self.status_indicator.setText(f"● {text}")
        self.status_indicator.setStyleSheet(f"color: {color};")

    def _ensure_canvas_loaded(self):
        if not self.canvas_panel:
            return
        # Basic check to see if we have a floor plan loaded
        try:
            if not getattr(self.canvas_panel, 'current_plan', None):
                default = os.path.join(config.FLOOR_PLANS_DIR, "example_office.json")
                if os.path.isfile(default):
                    plan = FloorPlan.load_from_json(default)
                    self.canvas_panel.load_plan(plan)
        except Exception:
            pass

    def load_agent(self, agent_def: AgentDefinition):
        self.current_agent = agent_def
        self._has_run = False
        self._last_result = None
        self._conversation = None
        self._violation_locations.clear()
        
        self.agent_name_label.setText(agent_def.name)
        self.agent_goal_label.setText(agent_def.goal)
        
        self.output_text.clear()
        self._clear_chat()
        self._set_chat_enabled(False)
        self._set_retry_enabled(False)

        if agent_def.constraints:
            self.constraints_label.setText(" • " + "\n • ".join(agent_def.constraints))
        else:
            self.constraints_label.setText("None")

        while self.inputs_container.count():
            child = self.inputs_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.input_widgets.clear()

        for inp in agent_def.inputs:
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            
            lbl = QLabel(f"{inp.name}:" + (" *" if inp.required else ""))
            layout.addWidget(lbl)
            
            if inp.type == "image":
                entry = QLineEdit()
                layout.addWidget(entry, 1)
                btn = QPushButton("Browse")
                btn.clicked.connect(lambda checked, n=inp.name: self._browse_file(n))
                layout.addWidget(btn)
                self.input_widgets[inp.name] = entry
            else:
                entry = QLineEdit()
                entry.setPlaceholderText(inp.description)
                layout.addWidget(entry, 1)
                self.input_widgets[inp.name] = entry
                
            self.inputs_container.addWidget(row)

        self._set_status("Ready", "#b3c7c1")
        if self.status_bar:
            self.status_bar.set_status(f"Loaded: {agent_def.name}", "#b3c7c1")

    def _browse_file(self, input_name: str):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "All files (*.*)")
        if path and input_name in self.input_widgets:
            self.input_widgets[input_name].setText(path)

    def _view_definition(self):
        if not self.current_agent:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Agent Definition")
        dlg.resize(600, 500)
        l = QVBoxLayout(dlg)
        t = QTextEdit()
        t.setReadOnly(True)
        t.setPlainText(json.dumps(self.current_agent.to_dict(), indent=2))
        l.addWidget(t)
        dlg.exec()

    def _collect_inputs(self) -> dict:
        inputs = {}
        for name, widget in self.input_widgets.items():
            inputs[name] = widget.text().strip()
        return inputs

    def _run_agent(self):
        if not self.current_agent or self._is_running:
            return

        self._ensure_canvas_loaded()

        inputs = self._collect_inputs()
        for inp in self.current_agent.inputs:
            if inp.required and not inputs.get(inp.name):
                self._set_status(f"Missing input: {inp.name}", "#ff6b6b")
                return

        self._is_running = True
        self.run_btn.setEnabled(False)
        self.output_text.clear()
        self._clear_chat()
        self._set_chat_enabled(False)
        self._set_retry_enabled(False)
        self._set_status("Initializing…", "#c47b2a")
        self._append_agent_message("Starting agent execution...")

        self.worker = AgentRunnerWorker(self._engine, self.current_agent, inputs)
        
        def update_status(msg):
            color = "#c47b2a"
            if "waiting for api" in msg.lower() or "retrying" in msg.lower():
                color = "#92817A"
            elif "timeout" in msg.lower() or "error" in msg.lower():
                color = "#f44336"
            self._set_status(msg, color)
            self._append_agent_message(f"<i>[Status] {msg}</i>")
            
        self.worker.status_update.connect(update_status)
        self.worker.completed.connect(self._on_run_complete)
        self.worker.start()

    def _on_run_complete(self, result: AgentResult):
        self._is_running = False
        self.run_btn.setEnabled(True)
        self._has_run = True
        self._last_result = result

        if not result.success:
            self._set_status("Failed", "#ff6b6b")
            self._append_agent_message(f"<b style='color:#ff6b6b'>Execution Failed:</b><br>{result.error_message}")
            return

        self._set_status("Done", "#b3c7c1")
        
        try:
            self.output_text.setPlainText(json.dumps(result.structured_data, indent=2))
        except Exception:
            self.output_text.setPlainText(str(result.structured_data))

        explanation = result.explanation
        if not explanation:
            explanation = "Execution completed successfully. (No explanation provided by LLM)"
            
        self._append_agent_message(explanation.replace("\n", "<br>"))

        if not self._conversation:
            self._conversation = ConversationManager()
            system_prompt = PromptBuilder.build_system_prompt(self.current_agent, result.tool_results)
            inputs = self._collect_inputs()
            self._conversation.initialize(system_prompt, explanation, result.tool_results, inputs)
            self._set_chat_enabled(True)
            self._set_retry_enabled(False)

        if self.status_bar:
            self.status_bar.set_status("Agent run complete", "#b3c7c1")
            
        self._show_on_canvas()

    def _send_message(self):
        text = self.chat_input.text().strip()
        if not text:
            return

        self._append_user_message(text)
        self.chat_input.clear()
        self._set_chat_enabled(False)
        self._set_retry_enabled(False)
        self._set_status("Thinking…", "#8889a5")

        if self._conversation and self._conversation.is_active:
            self.fw_worker = AgentFollowupWorker(self._conversation, text)
            
            def update_status(s):
                color = "#92817A" if "waiting for api" in s.lower() else "#c47b2a"
                self._set_status(s, color)
                
            self.fw_worker.status_update.connect(update_status)
            self.fw_worker.completed.connect(self._on_followup_complete)
            self.fw_worker.start()
        else:
            self._on_followup_complete("[Error: Conversation not initialized. Run the agent first.]")

    def _on_followup_complete(self, response: str):
        self._append_agent_message(response.replace("\n", "<br>"))
        self._set_chat_enabled(True)
        timed_out = "timed out" in response.lower() and "retry" in response.lower()
        self._set_retry_enabled(timed_out)
        self._set_status("Done", "#92817A")

    def _retry_followup(self):
        if not self._conversation or not self._conversation.is_active or not self._followup_can_retry:
            return

        self._set_chat_enabled(False)
        self._set_retry_enabled(False)
        self._set_status("Retrying…", "#c47b2a")

        self.rt_worker = AgentRetryWorker(self._conversation)
        
        def update_status(s):
            color = "#92817A" if "waiting for api" in s.lower() else "#c47b2a"
            self._set_status(s, color)
            
        self.rt_worker.status_update.connect(update_status)
        self.rt_worker.completed.connect(self._on_followup_complete)
        self.rt_worker.start()

    def _clear_chat(self):
        self.chat_display.clear()

    def _export_json(self):
        if not self._has_run or not self._last_result or not self._last_result.success:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", "agent_output.json", "JSON files (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._last_result.structured_data, f, indent=4)
            if self.status_bar:
                self.status_bar.set_status(f"Exported to {os.path.basename(path)}", "#b3c7c1")

    def _show_on_canvas(self):
        if not self.canvas_panel or not self._last_result or not self._last_result.success:
            return
        
        # Simplified implementation without parsing Violations visually for now
        # CanvasPanel rewrite handles the rendering.
        pass