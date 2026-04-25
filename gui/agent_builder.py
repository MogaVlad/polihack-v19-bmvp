import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, List, Optional

from models.agent_definition import AgentDefinition, AgentInput, AgentOutput
from tools.registry import ToolRegistry
import config


class AgentBuilderTab:
    def __init__(
        self,
        parent: ctk.CTkFrame,
        on_agent_saved: Optional[Callable] = None,
        on_save_and_run: Optional[Callable[[AgentDefinition], None]] = None,
    ):
        self.parent = parent
        self.on_agent_saved = on_agent_saved
        self.on_save_and_run = on_save_and_run
        self.input_rows: List[dict] = []
        self.constraint_rows: List[dict] = []  # {"frame": CTkFrame, "entry": CTkEntry}
        self.output_rows: List[dict] = []
        self.tool_vars = {}
        self._build_ui()

    # ── Helpers ──────────────────────────────────────────────────
    def _section_header(self, parent, text: str):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(
            frame, text=text,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("gray40", "#667788"),
        ).pack(side="left")
        sep = ctk.CTkFrame(frame, height=1, fg_color=("gray80", "#2a3f60"))
        sep.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=1)
        return frame

    # ── Build UI ─────────────────────────────────────────────────
    def _build_ui(self):
        self.scroll = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
            scrollbar_button_color=("#bbb", "#2a3f60"),
        )
        self.scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # ── Title ───────────────────────────────────────────────
        ctk.CTkLabel(
            self.scroll,
            text="🔧  Create New Agent",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=("gray15", "#e0e0e0"),
        ).pack(anchor="w", padx=12, pady=(8, 12))

        # ── Validation error label (hidden by default) ──────────
        self.error_frame = ctk.CTkFrame(self.scroll, fg_color=("#4a1010", "#4a1010"), corner_radius=8, height=0)
        self.error_frame.pack(fill="x", padx=8, pady=(0, 4))
        self.error_frame.pack_propagate(False)  # start collapsed

        self.error_label = ctk.CTkLabel(
            self.error_frame,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#cc0000", "#ff6b6b"),
            wraplength=700,
            justify="left",
        )
        self.error_label.pack(anchor="w", padx=12, pady=8)

        # ── Basic info card ─────────────────────────────────────
        basic_card = ctk.CTkFrame(self.scroll, fg_color=("gray92", "#162d50"), corner_radius=10)
        basic_card.pack(fill="x", padx=8, pady=4)
        self._section_header(basic_card, "BASIC INFO").pack(fill="x", padx=12, pady=(12, 8))

        # Name
        row_name = ctk.CTkFrame(basic_card, fg_color="transparent")
        row_name.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(row_name, text="Name: *", width=80, anchor="w",
                     font=ctk.CTkFont(size=12), text_color=("gray30", "#8899aa")).pack(side="left")
        self.name_entry = ctk.CTkEntry(
            row_name, height=30, corner_radius=6,
            fg_color=("gray96", "#0e1117"), border_color=("gray75", "#2a3f60"),
            text_color=("gray10", "#e0e0e0"), font=ctk.CTkFont(size=12),
        )
        self.name_entry.pack(side="left", fill="x", expand=True)

        # Category
        row_cat = ctk.CTkFrame(basic_card, fg_color="transparent")
        row_cat.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(row_cat, text="Category:", width=80, anchor="w",
                     font=ctk.CTkFont(size=12), text_color=("gray30", "#8899aa")).pack(side="left")
        self.category_entry = ctk.CTkEntry(
            row_cat, height=30, corner_radius=6,
            fg_color=("gray96", "#0e1117"), border_color=("gray75", "#2a3f60"),
            text_color=("gray10", "#e0e0e0"), font=ctk.CTkFont(size=12),
        )
        self.category_entry.pack(side="left", fill="x", expand=True)
        self.category_entry.insert(0, "Custom")

        # Goal
        row_goal = ctk.CTkFrame(basic_card, fg_color="transparent")
        row_goal.pack(fill="x", padx=12, pady=(3, 12))
        ctk.CTkLabel(row_goal, text="Goal: *", width=80, anchor="nw",
                     font=ctk.CTkFont(size=12), text_color=("gray30", "#8899aa")).pack(side="left", anchor="n")
        self.goal_text = ctk.CTkTextbox(
            row_goal, height=70, corner_radius=6,
            fg_color=("gray96", "#0e1117"), text_color=("gray10", "#e0e0e0"),
            font=ctk.CTkFont(family="Segoe UI", size=12), wrap="word",
        )
        self.goal_text.pack(side="left", fill="x", expand=True)

        # ── Inputs card ─────────────────────────────────────────
        inputs_card = ctk.CTkFrame(self.scroll, fg_color=("gray92", "#162d50"), corner_radius=10)
        inputs_card.pack(fill="x", padx=8, pady=4)
        self._section_header(inputs_card, "INPUTS").pack(fill="x", padx=12, pady=(12, 6))

        self.inputs_container = ctk.CTkFrame(inputs_card, fg_color="transparent")
        self.inputs_container.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkButton(
            inputs_card, text="＋ Add Input", width=120, height=28, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("gray78", "#0f3460"), hover_color=("gray68", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"), command=self._add_input_row,
        ).pack(padx=12, pady=(4, 12))

        # ── Constraints card ────────────────────────────────────
        constraints_card = ctk.CTkFrame(self.scroll, fg_color=("gray92", "#162d50"), corner_radius=10)
        constraints_card.pack(fill="x", padx=8, pady=4)
        self._section_header(constraints_card, "CONSTRAINTS").pack(fill="x", padx=12, pady=(12, 6))

        self.constraints_container = ctk.CTkFrame(constraints_card, fg_color="transparent")
        self.constraints_container.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkButton(
            constraints_card, text="＋ Add Constraint", width=140, height=28, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("gray78", "#0f3460"), hover_color=("gray68", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"), command=self._add_constraint_row,
        ).pack(padx=12, pady=(4, 12))

        # ── Outputs card ────────────────────────────────────────
        outputs_card = ctk.CTkFrame(self.scroll, fg_color=("gray92", "#162d50"), corner_radius=10)
        outputs_card.pack(fill="x", padx=8, pady=4)
        self._section_header(outputs_card, "OUTPUTS").pack(fill="x", padx=12, pady=(12, 6))

        self.outputs_container = ctk.CTkFrame(outputs_card, fg_color="transparent")
        self.outputs_container.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkButton(
            outputs_card, text="＋ Add Output", width=130, height=28, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("gray78", "#0f3460"), hover_color=("gray68", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"), command=self._add_output_row,
        ).pack(padx=12, pady=(4, 12))

        # ── Tools card ──────────────────────────────────────────
        tools_card = ctk.CTkFrame(self.scroll, fg_color=("gray92", "#162d50"), corner_radius=10)
        tools_card.pack(fill="x", padx=8, pady=4)
        self._section_header(tools_card, "TOOLS").pack(fill="x", padx=12, pady=(12, 8))

        registry = ToolRegistry()
        for key in registry.list_tool_names():
            info = registry.get_tool_info(key)
            var = ctk.BooleanVar()
            cb = ctk.CTkCheckBox(
                tools_card,
                text=f"{info.name} — {info.description}",
                variable=var,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=("gray20", "#c0d0e0"),
                fg_color="#4a9eff",
                hover_color="#3a89dd",
                border_color=("gray60", "#3a5070"),
            )
            cb.pack(anchor="w", padx=16, pady=3)
            self.tool_vars[key] = var

        # Spacer
        ctk.CTkFrame(tools_card, height=8, fg_color="transparent").pack()

        # ── Conversational toggle ───────────────────────────────
        conv_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        conv_frame.pack(fill="x", padx=12, pady=8)

        self.conversational_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            conv_frame,
            text="Enable follow-up conversation",
            variable=self.conversational_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray20", "#c0d0e0"),
            fg_color="#4a9eff", hover_color="#3a89dd",
            border_color=("gray60", "#3a5070"),
        ).pack(anchor="w")

        # ── Action buttons ──────────────────────────────────────
        btn_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(8, 20))

        ctk.CTkButton(
            btn_frame, text="Save Agent", width=140, height=36, corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=("gray70", "#0f3460"), hover_color=("gray60", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"), command=self._save_agent,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Save & Run", width=140, height=36, corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#4a9eff", hover_color="#3a89dd",
            text_color="#ffffff", command=self._save_and_run,
        ).pack(side="left")

    # ── Dynamic rows ─────────────────────────────────────────────
    def _add_input_row(self):
        row = ctk.CTkFrame(self.inputs_container, fg_color="transparent")
        row.pack(fill="x", pady=3)

        name_entry = ctk.CTkEntry(
            row, width=130, height=28, corner_radius=6, placeholder_text="name",
            fg_color=("gray96", "#0e1117"), border_color=("gray75", "#2a3f60"),
            text_color=("gray10", "#e0e0e0"), font=ctk.CTkFont(size=11),
        )
        name_entry.pack(side="left", padx=(0, 4))

        type_combo = ctk.CTkComboBox(
            row, values=["json", "text", "image", "number"], width=90, height=28,
            corner_radius=6, state="readonly",
            fg_color=("gray96", "#0e1117"), border_color=("gray75", "#2a3f60"),
            button_color=("gray75", "#1e4a8a"), button_hover_color=("gray60", "#3a5f90"),
            text_color=("gray10", "#e0e0e0"), font=ctk.CTkFont(size=11),
            dropdown_fg_color=("gray96", "#162d50"),
        )
        type_combo.set("json")
        type_combo.pack(side="left", padx=(0, 4))

        desc_entry = ctk.CTkEntry(
            row, height=28, corner_radius=6, placeholder_text="Description…",
            fg_color=("gray96", "#0e1117"), border_color=("gray75", "#2a3f60"),
            text_color=("gray10", "#e0e0e0"), font=ctk.CTkFont(size=11),
        )
        desc_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        row_data = {"frame": row, "name": name_entry, "type": type_combo, "desc": desc_entry}

        remove_btn = ctk.CTkButton(
            row, text="✕", width=28, height=28, corner_radius=6,
            font=ctk.CTkFont(size=12),
            fg_color=("gray78", "#3a2020"), hover_color=("gray68", "#5a3030"),
            text_color=("gray10", "#ff6b6b"),
            command=lambda rd=row_data: self._remove_input_row(rd),
        )
        remove_btn.pack(side="right")

        self.input_rows.append(row_data)

    def _remove_input_row(self, row_data: dict):
        row_data["frame"].destroy()
        if row_data in self.input_rows:
            self.input_rows.remove(row_data)

    def _add_constraint_row(self):
        row = ctk.CTkFrame(self.constraints_container, fg_color="transparent")
        row.pack(fill="x", pady=3)

        entry = ctk.CTkEntry(
            row, height=28, corner_radius=6, placeholder_text="Enter a constraint…",
            fg_color=("gray96", "#0e1117"), border_color=("gray75", "#2a3f60"),
            text_color=("gray10", "#e0e0e0"), font=ctk.CTkFont(size=11),
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        row_data = {"frame": row, "entry": entry}

        remove_btn = ctk.CTkButton(
            row, text="✕", width=28, height=28, corner_radius=6,
            font=ctk.CTkFont(size=12),
            fg_color=("gray78", "#3a2020"), hover_color=("gray68", "#5a3030"),
            text_color=("gray10", "#ff6b6b"),
            command=lambda rd=row_data: self._remove_constraint_row(rd),
        )
        remove_btn.pack(side="right")

        self.constraint_rows.append(row_data)

    def _remove_constraint_row(self, row_data: dict):
        row_data["frame"].destroy()
        if row_data in self.constraint_rows:
            self.constraint_rows.remove(row_data)

    def _add_output_row(self):
        row = ctk.CTkFrame(self.outputs_container, fg_color="transparent")
        row.pack(fill="x", pady=3)

        name_entry = ctk.CTkEntry(
            row, width=130, height=28, corner_radius=6, placeholder_text="name",
            fg_color=("gray96", "#0e1117"), border_color=("gray75", "#2a3f60"),
            text_color=("gray10", "#e0e0e0"), font=ctk.CTkFont(size=11),
        )
        name_entry.pack(side="left", padx=(0, 4))

        type_combo = ctk.CTkComboBox(
            row, values=["json", "text", "number"], width=90, height=28,
            corner_radius=6, state="readonly",
            fg_color=("gray96", "#0e1117"), border_color=("gray75", "#2a3f60"),
            button_color=("gray75", "#1e4a8a"), button_hover_color=("gray60", "#3a5f90"),
            text_color=("gray10", "#e0e0e0"), font=ctk.CTkFont(size=11),
            dropdown_fg_color=("gray96", "#162d50"),
        )
        type_combo.set("json")
        type_combo.pack(side="left", padx=(0, 4))

        desc_entry = ctk.CTkEntry(
            row, height=28, corner_radius=6, placeholder_text="Description…",
            fg_color=("gray96", "#0e1117"), border_color=("gray75", "#2a3f60"),
            text_color=("gray10", "#e0e0e0"), font=ctk.CTkFont(size=11),
        )
        desc_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        row_data = {"frame": row, "name": name_entry, "type": type_combo, "desc": desc_entry}

        remove_btn = ctk.CTkButton(
            row, text="✕", width=28, height=28, corner_radius=6,
            font=ctk.CTkFont(size=12),
            fg_color=("gray78", "#3a2020"), hover_color=("gray68", "#5a3030"),
            text_color=("gray10", "#ff6b6b"),
            command=lambda rd=row_data: self._remove_output_row(rd),
        )
        remove_btn.pack(side="right")

        self.output_rows.append(row_data)

    def _remove_output_row(self, row_data: dict):
        row_data["frame"].destroy()
        if row_data in self.output_rows:
            self.output_rows.remove(row_data)

    # ── Validation ───────────────────────────────────────────────
    def _validate_form(self) -> Optional[str]:
        """Validate the builder form. Returns an error message or None if valid."""
        name = self.name_entry.get().strip()
        if not name:
            return "Agent name is required."

        goal = self.goal_text.get("1.0", "end").strip()
        if not goal:
            return "Agent goal is required."

        # Check input rows have names
        for i, r in enumerate(self.input_rows):
            if not r["name"].get().strip():
                return f"Input #{i+1} is missing a name."

        # Check output rows have names
        for i, r in enumerate(self.output_rows):
            if not r["name"].get().strip():
                return f"Output #{i+1} is missing a name."

        return None

    def _show_error(self, message: str):
        """Display a validation error message via messagebox."""
        from tkinter import messagebox
        messagebox.showwarning("Validation Error", message)

    def _hide_error(self):
        """No-op — messagebox is self-dismissing."""
        pass

    # ── Build definition ─────────────────────────────────────────
    def _build_definition(self) -> AgentDefinition:
        name = self.name_entry.get().strip()
        agent_id = name.lower().replace(" ", "_")
        category = self.category_entry.get().strip() or "Custom"
        goal = self.goal_text.get("1.0", "end").strip()

        inputs = []
        for r in self.input_rows:
            inputs.append(AgentInput(
                name=r["name"].get().strip(),
                type=r["type"].get(),
                description=r["desc"].get().strip(),
            ))

        constraints = [
            r["entry"].get().strip()
            for r in self.constraint_rows
            if r["entry"].get().strip()
        ]

        outputs = []
        for r in self.output_rows:
            outputs.append(AgentOutput(
                name=r["name"].get().strip(),
                type=r["type"].get(),
                description=r["desc"].get().strip(),
            ))

        tools = [k for k, v in self.tool_vars.items() if v.get()]

        return AgentDefinition(
            id=agent_id,
            name=name,
            category=category,
            goal=goal,
            inputs=inputs,
            constraints=constraints,
            outputs=outputs,
            tools=tools,
            conversational=self.conversational_var.get(),
        )

    def _save_agent(self) -> Optional[AgentDefinition]:
        """Validate and save the agent definition. Returns the definition or None on error."""
        import os

        # Validate first
        error = self._validate_form()
        if error:
            self._show_error(error)
            return None

        self._hide_error()
        definition = self._build_definition()
        filepath = os.path.join(config.USER_AGENTS_DIR, f"{definition.id}.json")
        definition.save_to_json(filepath)

        # Notify the app that a new agent was saved
        if self.on_agent_saved:
            self.on_agent_saved()

        return definition

    def _save_and_run(self):
        """Save the agent and immediately switch to the Runner tab with it loaded."""
        definition = self._save_agent()
        if definition is None:
            return  # Validation failed

        if self.on_save_and_run:
            self.on_save_and_run(definition)

    def reset_form(self):
        self.name_entry.delete(0, "end")
        self.category_entry.delete(0, "end")
        self.category_entry.insert(0, "Custom")
        self.goal_text.delete("1.0", "end")

        for widget in self.inputs_container.winfo_children():
            widget.destroy()
        self.input_rows.clear()

        for widget in self.constraints_container.winfo_children():
            widget.destroy()
        self.constraint_rows.clear()

        for widget in self.outputs_container.winfo_children():
            widget.destroy()
        self.output_rows.clear()

        for var in self.tool_vars.values():
            var.set(False)

        self.conversational_var.set(True)

        self._hide_error()
