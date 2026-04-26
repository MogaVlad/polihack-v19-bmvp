import json
import os
import re
import html
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QTextEdit, QTextBrowser, QLineEdit, QScrollArea, QFileDialog, QDialog,
    QSplitter, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QTextCursor

from models.agent_definition import AgentDefinition
from models.chat import AgentResult
from models.floor_plan import FloorPlan
from models.violations import Violation
from engine.runner import AgentRunner
from engine.conversation import ConversationManager
from engine.prompt_builder import PromptBuilder
import config


_LOCATION_ID_RE = re.compile(r'\b([RCDE]\d+)\b')
_SEV_CHAT_COLORS = {
    "critical": "#e05555",
    "major": "#d4943a",
    "minor": "#c0a040",
    "info": "#8b81a2",
}


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

        try:
            result = self.engine.run_agent(self.agent_def, self.inputs, status_callback=status_cb)
            self.completed.emit(result)
        except Exception as e:
            self.completed.emit(
                AgentResult(
                    agent_id=self.agent_def.id,
                    success=False,
                    error=str(e),
                )
            )


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
    def __init__(self, parent=None, status_bar=None, canvas_panel=None, on_agent_deleted=None):
        super().__init__(parent)
        self.status_bar = status_bar
        self.canvas_panel = canvas_panel
        self.on_agent_deleted = on_agent_deleted
        self.current_agent = None
        self._has_run = False
        self._is_running = False
        self._last_result = None
        self._conversation = None
        self._engine = AgentRunner()
        self._violation_locations = set()
        self._followup_can_retry = False
        self._last_inputs = {}

        self.input_widgets = {}
        self._build_ui()

    def _section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("class", "SectionHeader")
        return lbl

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Header card
        header = QFrame()
        header.setProperty("class", "Card")
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(4)

        top_row = QHBoxLayout()
        self.agent_name_label = QLabel("No agent loaded")
        self.agent_name_label.setProperty("class", "Title")
        top_row.addWidget(self.agent_name_label)

        self.status_indicator = QLabel("Ready")
        self.status_indicator.setProperty("class", "Subtitle")
        top_row.addWidget(self.status_indicator, 0, Qt.AlignmentFlag.AlignRight)
        header_layout.addLayout(top_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate progress
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        header_layout.addWidget(self.progress_bar)

        self.agent_goal_label = QLabel("Select an agent from the library to begin.")
        self.agent_goal_label.setProperty("class", "Subtitle")
        self.agent_goal_label.setWordWrap(True)
        header_layout.addWidget(self.agent_goal_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.delete_btn = QPushButton("Delete Agent")
        self.delete_btn.setProperty("class", "DangerBtn")
        self.delete_btn.clicked.connect(self._delete_agent)
        self.delete_btn.hide()
        btn_row.addWidget(self.delete_btn)
        
        self.view_def_btn = QPushButton("View Definition")
        self.view_def_btn.clicked.connect(self._view_definition)
        btn_row.addWidget(self.view_def_btn)
        header_layout.addLayout(btn_row)

        main_layout.addWidget(header)

        # Two-column body
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter, 1)

        # LEFT COLUMN
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_widget = QWidget()
        self.left_layout = QVBoxLayout(left_widget)
        self.left_layout.setContentsMargins(0, 0, 6, 0)
        left_scroll.setWidget(left_widget)
        self.splitter.addWidget(left_scroll)

        # INPUTS
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

        # OUTPUTS
        output_card = QFrame()
        output_card.setProperty("class", "Card")
        out_layout = QVBoxLayout(output_card)
        out_layout.addWidget(self._section_header("OUTPUTS"))

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(140)
        out_layout.addWidget(self.output_text)

        export_row = QHBoxLayout()
        self.export_btn = QPushButton("Export JSON")
        self.export_btn.clicked.connect(self._export_json)
        export_row.addWidget(self.export_btn)

        self.show_canvas_btn = QPushButton("Show on Canvas")
        self.show_canvas_btn.clicked.connect(self._show_on_canvas)
        export_row.addWidget(self.show_canvas_btn)
        export_row.addStretch()
        out_layout.addLayout(export_row)

        self.left_layout.addWidget(output_card)

        # CONSTRAINTS
        cons_card = QFrame()
        cons_card.setProperty("class", "Card")
        cons_layout = QVBoxLayout(cons_card)
        cons_layout.addWidget(self._section_header("CONSTRAINTS USED"))
        self.constraints_label = QLabel("—")
        self.constraints_label.setWordWrap(True)
        self.constraints_label.setProperty("class", "Subtitle")
        cons_layout.addWidget(self.constraints_label)
        self.left_layout.addWidget(cons_card)

        self.left_layout.addStretch()

        # RIGHT COLUMN — CONVERSATION
        right_card = QFrame()
        right_card.setProperty("class", "Card")
        right_layout = QVBoxLayout(right_card)
        right_layout.addWidget(self._section_header("CONVERSATION"))

        self.chat_display = QTextBrowser()
        self.chat_display.setReadOnly(True)
        self.chat_display.setOpenExternalLinks(False)
        self.chat_display.setOpenLinks(False)
        self.chat_display.anchorClicked.connect(self._on_chat_link_clicked)
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
        msg_frame.addWidget(self.retry_btn)

        right_layout.addLayout(msg_frame)
        self.splitter.addWidget(right_card)

        self.splitter.setSizes([400, 500])

    # Chat helpers

    def _set_running_ui(self, running: bool):
        self._is_running = running

        # Main actions
        self.run_btn.setEnabled(not running and self.current_agent is not None)
        self.view_def_btn.setEnabled(not running)

        # Input fields
        for widget in self.input_widgets.values():
            widget.setEnabled(not running)

        # Output actions
        can_use_outputs = (not running) and self._has_run and self._last_result and self._last_result.success
        self.export_btn.setEnabled(can_use_outputs)
        self.show_canvas_btn.setEnabled(can_use_outputs)

        # Conversation actions
        can_chat = (not running) and self._has_run and self._conversation is not None and self._conversation.is_active
        self.chat_input.setEnabled(can_chat)
        self.send_btn.setEnabled(can_chat)
        self.retry_btn.setEnabled((not running) and self._followup_can_retry)

        if running:
            self.progress_bar.show()
        else:
            self.progress_bar.hide()

    def _append_agent_message(self, text: str):
        formatted = self._format_agent_message(text)
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
        self.chat_display.insertHtml(f"<b>Agent:</b> {formatted}")
        self.chat_display.insertHtml("<br>")
        self._auto_scroll()

    def _append_user_message(self, text: str):
        safe = html.escape(text)
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
        self.chat_display.insertHtml(f"<b>You:</b> {safe}")
        self.chat_display.insertHtml("<br>")
        self._auto_scroll()

    def _auto_scroll(self):
        sb = self.chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _format_agent_message(self, text: str) -> str:
        if not text:
            return ""

        message = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")

        # Preserve simple emphasis tags in status messages.
        placeholders = {
            "__TAG_I_OPEN__": "<i>",
            "__TAG_I_CLOSE__": "</i>",
            "__TAG_B_OPEN__": "<b>",
            "__TAG_B_CLOSE__": "</b>",
            "__TAG_U_OPEN__": "<u>",
            "__TAG_U_CLOSE__": "</u>",
        }
        for token, tag in placeholders.items():
            message = message.replace(tag, token)

        html_blocks = {}
        block_idx = 0

        # Replace fenced JSON blocks with human-readable reports.
        def replace_json_block(match: re.Match) -> str:
            nonlocal block_idx
            block = match.group(1)
            data = self._try_parse_json(block)
            if data is None:
                return match.group(0)
            report = self._json_to_report(data)
            pid = f"__HTML_BLOCK_{block_idx}__"
            html_blocks[pid] = self._report_to_html(report)
            block_idx += 1
            return pid

        # Replace fenced TEXT blocks with readable key/value lines.
        def replace_text_block(match: re.Match) -> str:
            nonlocal block_idx
            block = match.group(1).strip()
            lines = []
            for raw_line in block.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if ":" in line:
                    key, value = line.split(":", 1)
                    lines.append(f"{self._humanize_key(key)}: {value.strip()}")
                else:
                    lines.append(line)
            if not lines:
                return match.group(0)
            pid = f"__HTML_BLOCK_{block_idx}__"
            html_blocks[pid] = self._report_to_html(lines)
            block_idx += 1
            return pid

        message = re.sub(r"```json\s*([\s\S]*?)\s*```", replace_json_block, message, flags=re.IGNORECASE)
        message = re.sub(r"```text\s*([\s\S]*?)\s*```", replace_text_block, message, flags=re.IGNORECASE)

        # If the entire message is raw JSON, render it as a report.
        if message.strip().startswith("{") or message.strip().startswith("["):
            data = self._try_parse_json(message)
            if data is not None:
                raw = self._report_to_html(self._json_to_report(data))
                return self._inject_severity_colors(self._inject_location_links(raw))

        # Default: escape and keep line breaks.
        safe = html.escape(message).replace("\n", "<br>")
        for token, tag in placeholders.items():
            safe = safe.replace(token, tag)

        for pid, html_str in html_blocks.items():
            safe = safe.replace(pid, html_str)

        safe = self._inject_location_links(safe)
        safe = self._inject_severity_colors(safe)
        return safe

    @staticmethod
    def _try_parse_json(text: str):
        try:
            return json.loads(html.unescape(text))
        except Exception:
            return None

    def _json_to_report(self, data, indent: int = 0, skip_keys: set | None = None) -> list:
        lines = []
        pad = "  " * indent
        skip_keys = skip_keys or set()

        if isinstance(data, dict):
            for key, value in data.items():
                if key in skip_keys:
                    continue
                label = self._humanize_key(key)
                if isinstance(value, (dict, list)):
                    lines.append(f"{pad}{label}:")
                    lines.extend(self._json_to_report(value, indent + 1))
                else:
                    lines.append(f"{pad}{label}: {self._format_value(value)}")
        elif isinstance(data, list):
            if not data:
                lines.append(f"{pad}No items.")
            for idx, item in enumerate(data, start=1):
                if isinstance(item, dict):
                    title, used_keys = self._summarize_dict_item(item, idx)
                    lines.append(f"{pad}• {title}")
                    lines.extend(self._json_to_report(item, indent + 1, used_keys))
                elif isinstance(item, list):
                    lines.append(f"{pad}• Item {idx}:")
                    lines.extend(self._json_to_report(item, indent + 1))
                else:
                    lines.append(f"{pad}• {self._format_value(item)}")
        else:
            lines.append(f"{pad}{self._format_value(data)}")

        return lines

    @staticmethod
    def _report_to_html(lines: list) -> str:
        safe_lines = [html.escape(line) for line in lines]
        return "<br>".join(safe_lines)

    @staticmethod
    def _inject_location_links(text: str) -> str:
        def _replace(m):
            id_ = m.group(0)
            return (
                f'<a href="loc:{id_}" style="color:#5ba3cf;'
                f'text-decoration:none;font-weight:bold">{id_}</a>'
            )
        return _LOCATION_ID_RE.sub(_replace, text)

    @staticmethod
    def _inject_severity_colors(text: str) -> str:
        for sev, color in _SEV_CHAT_COLORS.items():
            text = re.sub(
                rf'\b({sev})\b',
                rf'<span style="color:{color};font-weight:bold">\1</span>',
                text,
                flags=re.IGNORECASE,
            )
        return text

    @staticmethod
    def _format_value(value) -> str:
        if value is None:
            return "—"
        if isinstance(value, bool):
            return "Yes" if value else "No"
        return str(value)

    @staticmethod
    def _humanize_key(key: str) -> str:
        return str(key).replace("_", " ").strip().title()

    @staticmethod
    def _summarize_dict_item(item: dict, idx: int) -> tuple[str, set]:
        parts = []
        used = set()
        for k in ("rule", "name", "title", "id"):
            if k in item and item[k]:
                parts.append(str(item[k]))
                used.add(k)
                break
        if "severity" in item and item["severity"]:
            parts.append(f"Severity: {item['severity']}")
            used.add("severity")
        if "location" in item and item["location"]:
            parts.append(f"Location: {item['location']}")
            used.add("location")
        header = " — ".join(parts) if parts else f"Item {idx}"
        return f"{header}:", used

    def _set_chat_enabled(self, enabled: bool):
        self.chat_input.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)

    def _on_chat_link_clicked(self, url: QUrl):
        url_str = url.toString()
        if url_str.startswith("loc:"):
            location_id = url_str[4:]
            if self.canvas_panel:
                self.canvas_panel.highlight_location(location_id)

    def _set_retry_enabled(self, enabled: bool):
        self._followup_can_retry = enabled
        self.retry_btn.setEnabled(enabled)

    def _set_status(self, text: str):
        self.status_indicator.setText(text)

    def _ensure_canvas_loaded(self):
        if not self.canvas_panel:
            return
        try:
            if not getattr(self.canvas_panel, "floor_plan", None):
                default = os.path.join("data", "floor_plans", "example_office.json")
                if os.path.isfile(default):
                    plan = FloorPlan.load_from_json(default)
                    self.canvas_panel.load_plan(plan)
        except Exception:
            pass

    # Agent loading

    def load_agent(self, agent_def: AgentDefinition):
        self.current_agent = agent_def
        self._has_run = False
        self._last_result = None
        self._conversation = None
        self._violation_locations.clear()
        self._set_retry_enabled(False)

        self.agent_name_label.setText(agent_def.name)
        self.agent_goal_label.setText(agent_def.goal)

        self.output_text.clear()
        self._clear_chat()
        self._set_chat_enabled(False)
        
        if self._find_user_agent_file(agent_def.id):
            self.delete_btn.show()
        else:
            self.delete_btn.hide()

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

            required = getattr(inp, "required", True)
            lbl = QLabel(f"{inp.name}:" + (" *" if required else ""))
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

        self._set_status("Ready")
        self._set_running_ui(False)
        if self.status_bar:
            self.status_bar.set_status(f"Loaded: {agent_def.name}")

    def _browse_file(self, input_name: str):
        if input_name == "floor_plan":
            filter_str = "Floor plans (*.json *.dxf *.png *.jpg *.jpeg *.pdf);;All files (*.*)"
        else:
            filter_str = "All files (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", filter_str)
        if path and input_name in self.input_widgets:
            self.input_widgets[input_name].setText(path)

    def _view_definition(self):
        if not self.current_agent:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Agent Definition")
        dlg.resize(600, 500)
        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(json.dumps(self.current_agent.to_dict(), indent=2))
        layout.addWidget(text)
        dlg.exec()

    def _find_user_agent_file(self, agent_id: str) -> str | None:
        if not agent_id or not os.path.isdir(config.USER_AGENTS_DIR):
            return None
        for filename in os.listdir(config.USER_AGENTS_DIR):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(config.USER_AGENTS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("id") == agent_id:
                    return filepath
            except Exception:
                continue
        return None

    def _delete_agent(self):
        if not self.current_agent:
            return

        agent_path = self._find_user_agent_file(self.current_agent.id)
        if not agent_path:
            return

        confirm = QMessageBox.question(
            self,
            "Delete Agent",
            f"Are you sure you want to permanently delete '{self.current_agent.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                os.remove(agent_path)
                if self.status_bar:
                    self.status_bar.set_status(f"Deleted agent: {self.current_agent.name}")
                if self.on_agent_deleted:
                    self.on_agent_deleted()
            except Exception:
                QMessageBox.warning(self, "Error", "Could not delete the agent file from disk.")

    def _collect_inputs(self) -> dict:
        inputs = {}
        for name, widget in self.input_widgets.items():
            value = widget.text().strip()
            if value and os.path.isfile(value):
                lower = value.lower()
                if lower.endswith(".json"):
                    try:
                        with open(value, "r", encoding="utf-8") as f:
                            inputs[name] = f.read()
                        continue
                    except OSError:
                        pass
                if lower.endswith(".dxf"):
                    inputs[name] = value
                    continue
            inputs[name] = value
        return inputs

    def _extract_plan_dict(self, payload):
        if not isinstance(payload, dict):
            return None
        if isinstance(payload.get("rooms"), list):
            return payload
        for key in ("parsed_plan", "floor_plan", "plan", "layout"):
            candidate = payload.get(key)
            if isinstance(candidate, dict) and isinstance(candidate.get("rooms"), list):
                return candidate
        for value in payload.values():
            if isinstance(value, dict) and isinstance(value.get("rooms"), list):
                return value
        return None

    def _plan_from_inputs(self) -> dict | None:
        for value in self._last_inputs.values():
            if not value:
                continue
            if isinstance(value, dict):
                plan = self._extract_plan_dict(value)
                if plan:
                    return plan
                continue
            if not isinstance(value, str):
                continue
            candidate = value.strip()
            if not candidate:
                continue
            if os.path.isfile(candidate) and candidate.lower().endswith(".json"):
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        parsed = json.load(f)
                    plan = self._extract_plan_dict(parsed)
                    if plan:
                        return plan
                except (OSError, json.JSONDecodeError):
                    continue
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            plan = self._extract_plan_dict(parsed)
            if plan:
                return plan
        return None

    @staticmethod
    def _is_violation_list(obj) -> bool:
        return (isinstance(obj, list) and obj
                and isinstance(obj[0], dict)
                and ("rule" in obj[0] or "severity" in obj[0]))

    def _extract_all_violations(self, payload) -> list:
        results = []
        if payload is None:
            return results
        if isinstance(payload, list):
            if self._is_violation_list(payload):
                return list(payload)
            return results
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except (json.JSONDecodeError, ValueError):
                return results
            return self._extract_all_violations(parsed)
        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, list) and self._is_violation_list(value):
                    results.extend(value)
                elif isinstance(value, str):
                    results.extend(self._extract_all_violations(value))
                elif isinstance(value, dict):
                    results.extend(self._extract_all_violations(value))
        return results

    def _parse_violations(self, *payloads) -> list[Violation]:
        parsed = []
        seen_ids: set[str] = set()
        for payload in payloads:
            for v in self._extract_all_violations(payload):
                if isinstance(v, dict):
                    vid = v.get("id", "")
                    if vid and vid in seen_ids:
                        continue
                    if vid:
                        seen_ids.add(vid)
                    parsed.append(Violation.from_dict(v))
        return parsed

    # Run

    def _run_agent(self):
        if not self.current_agent or self._is_running:
            return

        self._ensure_canvas_loaded()

        inputs = self._collect_inputs()
        self._last_inputs = inputs
        for inp in self.current_agent.inputs:
            if getattr(inp, "required", True) and not inputs.get(inp.name):
                self._set_status(f"Missing: {inp.name}")
                return

        self.output_text.clear()
        self._clear_chat()
        self._set_chat_enabled(False)
        self._set_retry_enabled(False)
        self._set_status("Initializing…")
        self._append_agent_message("Starting agent execution...")

        self._set_running_ui(True)

        self.worker = AgentRunnerWorker(self._engine, self.current_agent, inputs)

        def update_status(msg):
            self._set_status(msg)
            self._append_agent_message(f"<i>[Status] {msg}</i>")

        self.worker.status_update.connect(update_status)
        self.worker.completed.connect(self._on_run_complete)
        self.worker.start()

    def _on_run_complete(self, result: AgentResult):
        self._has_run = True
        self._last_result = result

        if not result.success:
            self._set_status("Failed")
            self._append_agent_message(f"<b>Execution Failed:</b>\n{result.error}")
            self._set_running_ui(False)
            return

        self._set_status("Done")

        try:
            self.output_text.setPlainText(json.dumps(result.outputs, indent=2))
        except Exception:
            self.output_text.setPlainText(str(result.outputs))

        explanation = result.explanation or "Execution completed successfully."
        self._append_agent_message(explanation)

        if not self._conversation:
            self._conversation = ConversationManager(self.current_agent)
            system_prompt = PromptBuilder.build_system_prompt(self.current_agent, result.tool_results)
            inputs = self._collect_inputs()
            self._conversation.initialize(system_prompt, explanation, result.tool_results, inputs)
            self._set_chat_enabled(True)
            self._set_retry_enabled(False)

        if self.status_bar:
            self.status_bar.set_status("Agent run complete")

        self._show_on_canvas()
        self._set_running_ui(False)

    # Conversation

    def _send_message(self):
        if self._is_running:
            return

        text = self.chat_input.text().strip()
        if not text:
            return

        self._append_user_message(text)
        self.chat_input.clear()
        self._set_chat_enabled(False)
        self._set_retry_enabled(False)
        self._set_status("Thinking…")
        self._set_running_ui(True)

        if self._conversation and self._conversation.is_active:
            self.fw_worker = AgentFollowupWorker(self._conversation, text)

            def update_status(s):
                self._set_status(s)

            self.fw_worker.status_update.connect(update_status)
            self.fw_worker.completed.connect(self._on_followup_complete)
            self.fw_worker.start()
        else:
            self._on_followup_complete("[Error: Conversation not initialized. Run the agent first.]")

    def _on_followup_complete(self, response: str):
        self._append_agent_message(response)
        resp_lower = response.lower()
        can_retry = (
            response.startswith("[Error")
            or "timed out" in resp_lower
            or "unavailable" in resp_lower
            or "retry" in resp_lower
        )
        self._set_retry_enabled(can_retry)
        self._set_status("Done")
        self._set_running_ui(False)

    def _retry_followup(self, *args):
        if self._is_running:
            return

        if not self._conversation or not self._conversation.is_active or not self._followup_can_retry:
            return

        self._set_chat_enabled(False)
        self._set_retry_enabled(False)
        self._set_status("Retrying…")
        self._set_running_ui(True)
        
        if self._conversation.last_user_message:
            self._append_user_message(f"[Retrying] {self._conversation.last_user_message}")

        self.rt_worker = AgentRetryWorker(self._conversation)

        def update_status(s):
            self._set_status(s)

        self.rt_worker.status_update.connect(update_status)
        self.rt_worker.completed.connect(self._on_followup_complete)
        self.rt_worker.start()

    def _clear_chat(self):
        self.chat_display.clear()

    # Export / Canvas

    def _export_json(self):
        if not self._has_run or not self._last_result or not self._last_result.success:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", "agent_output.json", "JSON files (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._last_result.outputs, f, indent=4)
            if self.status_bar:
                self.status_bar.set_status(f"Exported to {os.path.basename(path)}")

    def _show_on_canvas(self):
        if not self.canvas_panel or not self._last_result or not self._last_result.success:
            return

        data = self._last_result.outputs or {}
        tool_results = self._last_result.tool_results or {}
        plan_payload = self._extract_plan_dict(data) if data else None
        if not plan_payload:
            plan_payload = self._plan_from_inputs()
        if not data and not plan_payload and not tool_results:
            return
        if plan_payload:
            try:
                plan = FloorPlan.from_dict(plan_payload)
                self.canvas_panel.load_plan(plan)
            except (KeyError, TypeError):
                pass

        parsed = self._parse_violations(data, tool_results)
        if parsed:
            self.canvas_panel.show_violations(parsed)

        if not self.canvas_panel.visible:
            self.canvas_panel.toggle()
        self.canvas_panel.fit_to_window()
