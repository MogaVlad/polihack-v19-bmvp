import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QLineEdit,
    QTextEdit, QScrollArea, QPushButton, QCheckBox, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt
from typing import Callable, List, Optional

from models.agent_definition import AgentDefinition, AgentInput, AgentOutput
from tools.registry import ToolRegistry
import config

class AgentBuilderTab(QWidget):
    def __init__(
        self,
        parent=None,
        on_agent_saved: Optional[Callable] = None,
        on_save_and_run: Optional[Callable[[AgentDefinition], None]] = None,
    ):
        super().__init__(parent)
        self.setObjectName("AgentBuilderTab")
        self.on_agent_saved = on_agent_saved
        self.on_save_and_run = on_save_and_run
        
        self.input_rows = []
        self.constraint_rows = []
        self.output_rows = []
        self.tool_vars = {}
        
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
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)
        
        self.wrapper = QWidget()
        self.scroll_area.setWidget(self.wrapper)
        self.wrapper_layout = QVBoxLayout(self.wrapper)
        self.wrapper_layout.setContentsMargins(16, 16, 16, 16)
        self.wrapper_layout.setSpacing(12)

        # Title
        title_lbl = QLabel("🔧  Create New Agent")
        title_lbl.setProperty("class", "Title")
        self.wrapper_layout.addWidget(title_lbl)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff6b6b; background-color: #4a1010; padding: 8px; border-radius: 4px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        self.wrapper_layout.addWidget(self.error_label)

        # ── Basic Info ─────────────────────────────────────
        basic_card = QFrame()
        basic_card.setProperty("class", "Card")
        basic_layout = QVBoxLayout(basic_card)
        basic_layout.addWidget(self._section_header("BASIC INFO"))
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name: *"))
        self.name_entry = QLineEdit()
        name_layout.addWidget(self.name_entry, 1)
        basic_layout.addLayout(name_layout)
        
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("Category:"))
        self.category_entry = QLineEdit("Custom")
        cat_layout.addWidget(self.category_entry, 1)
        basic_layout.addLayout(cat_layout)
        
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description: *"), 0, Qt.AlignmentFlag.AlignTop)
        self.desc_entry = QTextEdit()
        self.desc_entry.setFixedHeight(60)
        desc_layout.addWidget(self.desc_entry, 1)
        basic_layout.addLayout(desc_layout)
        
        self.wrapper_layout.addWidget(basic_card)

        # ── Prompting ──────────────────────────────────────
        prompt_card = QFrame()
        prompt_card.setProperty("class", "Card")
        prompt_layout = QVBoxLayout(prompt_card)
        prompt_layout.addWidget(self._section_header("PROMPTING"))
        
        sys_layout = QHBoxLayout()
        sys_layout.addWidget(QLabel("System Prompt: *"), 0, Qt.AlignmentFlag.AlignTop)
        self.system_prompt_entry = QTextEdit()
        self.system_prompt_entry.setFixedHeight(100)
        sys_layout.addWidget(self.system_prompt_entry, 1)
        prompt_layout.addLayout(sys_layout)
        
        self.wrapper_layout.addWidget(prompt_card)

        # ── Inputs ─────────────────────────────────────────
        input_card = QFrame()
        input_card.setProperty("class", "Card")
        self.input_layout = QVBoxLayout(input_card)
        
        inp_header = QHBoxLayout()
        inp_header.addWidget(self._section_header("INPUT SCHEMA"), 1)
        add_inp_btn = QPushButton("+ Add Input")
        add_inp_btn.clicked.connect(self._add_input_row)
        inp_header.addWidget(add_inp_btn)
        self.input_layout.addLayout(inp_header)
        
        self.inputs_container = QVBoxLayout()
        self.input_layout.addLayout(self.inputs_container)
        self.wrapper_layout.addWidget(input_card)

        # ── Constraints ────────────────────────────────────
        cons_card = QFrame()
        cons_card.setProperty("class", "Card")
        self.cons_layout = QVBoxLayout(cons_card)
        
        cons_header = QHBoxLayout()
        cons_header.addWidget(self._section_header("CONSTRAINTS & RULES"), 1)
        add_cons_btn = QPushButton("+ Add Constraint")
        add_cons_btn.clicked.connect(self._add_constraint_row)
        cons_header.addWidget(add_cons_btn)
        self.cons_layout.addLayout(cons_header)
        
        self.cons_container = QVBoxLayout()
        self.cons_layout.addLayout(self.cons_container)
        self.wrapper_layout.addWidget(cons_card)

        # ── Outputs ────────────────────────────────────────
        out_card = QFrame()
        out_card.setProperty("class", "Card")
        self.out_layout = QVBoxLayout(out_card)
        
        out_header = QHBoxLayout()
        out_header.addWidget(self._section_header("OUTPUT SCHEMA"), 1)
        add_out_btn = QPushButton("+ Add Output")
        add_out_btn.clicked.connect(self._add_output_row)
        out_header.addWidget(add_out_btn)
        self.out_layout.addLayout(out_header)
        
        self.outs_container = QVBoxLayout()
        self.out_layout.addLayout(self.outs_container)
        self.wrapper_layout.addWidget(out_card)

        # ── Capabilities ───────────────────────────────────
        cap_card = QFrame()
        cap_card.setProperty("class", "Card")
        cap_layout = QVBoxLayout(cap_card)
        cap_layout.addWidget(self._section_header("CAPABILITIES & TOOLS"))
        
        self.tool_container = QVBoxLayout()
        registry = ToolRegistry()
        for tool_name, tool_info in registry._tools.items():
            cb = QCheckBox(f"{tool_name} — {tool_info.description[:60]}...")
            self.tool_vars[tool_name] = cb
            self.tool_container.addWidget(cb)
        cap_layout.addLayout(self.tool_container)
        
        self.wrapper_layout.addWidget(cap_card)

        # ── Actions ────────────────────────────────────────
        action_frame = QFrame()
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(0, 16, 0, 16)
        
        save_btn = QPushButton("💾  Save Agent")
        save_btn.clicked.connect(self._save_agent)
        action_layout.addWidget(save_btn)
        
        save_run_btn = QPushButton("🚀  Save & Run")
        save_run_btn.clicked.connect(self._save_and_run_agent)
        action_layout.addWidget(save_run_btn)
        
        self.wrapper_layout.addWidget(action_frame)
        self.wrapper_layout.addStretch()

        # Add initial row
        self._add_input_row()

    def _create_row_frame(self):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        return row, layout

    def _add_input_row(self):
        row, layout = self._create_row_frame()
        
        name_entry = QLineEdit()
        name_entry.setPlaceholderText("Name (e.g. floor_plan)")
        layout.addWidget(name_entry, 2)
        
        type_combo = QComboBox()
        type_combo.addItems(["string", "number", "boolean", "image", "json"])
        layout.addWidget(type_combo, 1)
        
        desc_entry = QLineEdit()
        desc_entry.setPlaceholderText("Description")
        layout.addWidget(desc_entry, 3)
        
        req_cb = QCheckBox("Req")
        req_cb.setChecked(True)
        layout.addWidget(req_cb)
        
        del_btn = QPushButton("X")
        del_btn.setFixedWidth(30)
        del_btn.clicked.connect(lambda: self._remove_row(row, self.input_rows, self.inputs_container))
        layout.addWidget(del_btn)
        
        self.inputs_container.addWidget(row)
        self.input_rows.append({
            "frame": row,
            "name": name_entry,
            "type": type_combo,
            "desc": desc_entry,
            "req": req_cb
        })

    def _add_constraint_row(self):
        row, layout = self._create_row_frame()
        
        entry = QLineEdit()
        entry.setPlaceholderText("e.g. 'Must use metric units' or 'Never guess missing dimensions'")
        layout.addWidget(entry, 1)
        
        del_btn = QPushButton("X")
        del_btn.setFixedWidth(30)
        del_btn.clicked.connect(lambda: self._remove_row(row, self.constraint_rows, self.cons_container))
        layout.addWidget(del_btn)
        
        self.cons_container.addWidget(row)
        self.constraint_rows.append({"frame": row, "entry": entry})

    def _add_output_row(self):
        row, layout = self._create_row_frame()
        
        name_entry = QLineEdit()
        name_entry.setPlaceholderText("Field Name (e.g. violations)")
        layout.addWidget(name_entry, 2)
        
        type_combo = QComboBox()
        type_combo.addItems(["string", "number", "boolean", "array", "object"])
        layout.addWidget(type_combo, 1)
        
        desc_entry = QLineEdit()
        desc_entry.setPlaceholderText("Description")
        layout.addWidget(desc_entry, 3)
        
        del_btn = QPushButton("X")
        del_btn.setFixedWidth(30)
        del_btn.clicked.connect(lambda: self._remove_row(row, self.output_rows, self.outs_container))
        layout.addWidget(del_btn)
        
        self.outs_container.addWidget(row)
        self.output_rows.append({
            "frame": row,
            "name": name_entry,
            "type": type_combo,
            "desc": desc_entry
        })

    def _remove_row(self, row_widget, row_list, container_layout):
        container_layout.removeWidget(row_widget)
        row_widget.deleteLater()
        for r in row_list:
            if r["frame"] == row_widget:
                row_list.remove(r)
                break

    def _show_error(self, message: str):
        self.error_label.setText(f"⚠ {message}")
        self.error_label.show()
        # Scroll to top
        self.scroll_area.verticalScrollBar().setValue(0)

    def _hide_error(self):
        self.error_label.hide()

    def _gather_data(self) -> dict:
        data = {
            "id": self.name_entry.text().strip().lower().replace(" ", "_"),
            "name": self.name_entry.text().strip(),
            "category": self.category_entry.text().strip(),
            "goal": self.desc_entry.toPlainText().strip(),
            "conversation_guidelines": self.system_prompt_entry.toPlainText().strip(),
            "inputs": [],
            "constraints": [],
            "outputs": [],
            "tools": []
        }
        
        for r in self.input_rows:
            name = r["name"].text().strip()
            if name:
                data["inputs"].append({
                    "name": name,
                    "type": r["type"].currentText(),
                    "description": r["desc"].text().strip(),
                    "required": r["req"].isChecked()
                })
                
        for r in self.constraint_rows:
            val = r["entry"].text().strip()
            if val:
                data["constraints"].append(val)
                
        for r in self.output_rows:
            name = r["name"].text().strip()
            if name:
                data["outputs"].append({
                    "name": name,
                    "type": r["type"].currentText(),
                    "description": r["desc"].text().strip()
                })
                
        for tool_name, cb in self.tool_vars.items():
            if cb.isChecked():
                data["tools"].append(tool_name)
                
        return data

    def _validate(self, data: dict) -> bool:
        if not data["name"]:
            self._show_error("Agent name is required.")
            return False
        if not data["goal"]:
            self._show_error("Description/Goal is required.")
            return False
        if not data["conversation_guidelines"]:
            self._show_error("System prompt is required.")
            return False
        if not data["inputs"]:
            self._show_error("At least one input is required.")
            return False
            
        self._hide_error()
        return True

    def _save_agent(self) -> Optional[AgentDefinition]:
        data = self._gather_data()
        if not self._validate(data):
            return None
            
        filename = data["name"].lower().replace(" ", "_") + ".json"
        filepath = os.path.join(config.USER_AGENTS_DIR, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            
            agent_def = AgentDefinition.load_from_json(filepath)
            
            if self.on_agent_saved:
                self.on_agent_saved()
                
            QMessageBox.information(self, "Success", f"Agent '{agent_def.name}' saved successfully!")
            return agent_def
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save agent:\n{e}")
            return None

    def _save_and_run_agent(self):
        agent_def = self._save_agent()
        if agent_def and self.on_save_and_run:
            self.on_save_and_run(agent_def)

    def reset_form(self):
        self._hide_error()
        self.name_entry.clear()
        self.category_entry.setText("Custom")
        self.desc_entry.clear()
        self.system_prompt_entry.clear()
        
        # Clear rows
        for r in list(self.input_rows):
            self._remove_row(r["frame"], self.input_rows, self.inputs_container)
        for r in list(self.constraint_rows):
            self._remove_row(r["frame"], self.constraint_rows, self.cons_container)
        for r in list(self.output_rows):
            self._remove_row(r["frame"], self.output_rows, self.outs_container)
            
        for cb in self.tool_vars.values():
            cb.setChecked(False)
            
        self._add_input_row()
        self.scroll_area.verticalScrollBar().setValue(0)