import tkinter as tk
from tkinter import ttk
from typing import List

from models.agent_definition import AgentDefinition, AgentInput, AgentOutput
from tools.registry import ToolRegistry
import config


class AgentBuilderTab:
    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self.input_rows: List[dict] = []
        self.constraint_rows: List[tk.Entry] = []
        self.output_rows: List[dict] = []
        self.tool_vars = {}
        self._build_ui()

    def _build_ui(self):
        canvas = tk.Canvas(self.frame, borderwidth=0, bg="#f5f5f5")
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(self.scroll_frame, text="CREATE NEW AGENT", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=10, pady=10
        )

        basic_frame = ttk.LabelFrame(self.scroll_frame, text="Basic Info")
        basic_frame.pack(fill=tk.X, padx=10, pady=5)

        row = ttk.Frame(basic_frame)
        row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row, text="Name:", width=12).pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(row)
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        row = ttk.Frame(basic_frame)
        row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row, text="Category:", width=12).pack(side=tk.LEFT)
        self.category_entry = ttk.Entry(row)
        self.category_entry.insert(0, "Custom")
        self.category_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        row = ttk.Frame(basic_frame)
        row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row, text="Goal:", width=12).pack(side=tk.LEFT)
        self.goal_text = tk.Text(row, height=3, wrap=tk.WORD, font=("Segoe UI", 10))
        self.goal_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        inputs_frame = ttk.LabelFrame(self.scroll_frame, text="INPUTS")
        inputs_frame.pack(fill=tk.X, padx=10, pady=5)
        self.inputs_container = ttk.Frame(inputs_frame)
        self.inputs_container.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(inputs_frame, text="+ Add Input", command=self._add_input_row).pack(padx=5, pady=5)

        constraints_frame = ttk.LabelFrame(self.scroll_frame, text="CONSTRAINTS")
        constraints_frame.pack(fill=tk.X, padx=10, pady=5)
        self.constraints_container = ttk.Frame(constraints_frame)
        self.constraints_container.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(constraints_frame, text="+ Add Constraint", command=self._add_constraint_row).pack(padx=5, pady=5)

        outputs_frame = ttk.LabelFrame(self.scroll_frame, text="OUTPUTS")
        outputs_frame.pack(fill=tk.X, padx=10, pady=5)
        self.outputs_container = ttk.Frame(outputs_frame)
        self.outputs_container.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(outputs_frame, text="+ Add Output", command=self._add_output_row).pack(padx=5, pady=5)

        tools_frame = ttk.LabelFrame(self.scroll_frame, text="TOOLS")
        tools_frame.pack(fill=tk.X, padx=10, pady=5)
        registry = ToolRegistry()
        for key in registry.list_tool_names():
            info = registry.get_tool_info(key)
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(tools_frame, text=f"{info.name} — {info.description}", variable=var)
            cb.pack(anchor="w", padx=10, pady=2)
            self.tool_vars[key] = var

        conv_frame = ttk.Frame(self.scroll_frame)
        conv_frame.pack(fill=tk.X, padx=10, pady=5)
        self.conversational_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(conv_frame, text="Enable follow-up conversation", variable=self.conversational_var).pack(
            anchor="w"
        )

        btn_frame = ttk.Frame(self.scroll_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=15)
        ttk.Button(btn_frame, text="Save Agent", command=self._save_agent).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save & Run", command=self._save_and_run).pack(side=tk.LEFT, padx=5)

    def _add_input_row(self):
        row = ttk.Frame(self.inputs_container)
        row.pack(fill=tk.X, pady=2)
        name_entry = ttk.Entry(row, width=15)
        name_entry.pack(side=tk.LEFT, padx=2)
        name_entry.insert(0, "name")
        type_combo = ttk.Combobox(row, values=["json", "text", "image", "number"], width=8, state="readonly")
        type_combo.set("json")
        type_combo.pack(side=tk.LEFT, padx=2)
        desc_entry = ttk.Entry(row)
        desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        desc_entry.insert(0, "Description...")
        self.input_rows.append({"name": name_entry, "type": type_combo, "desc": desc_entry})

    def _add_constraint_row(self):
        row = ttk.Frame(self.constraints_container)
        row.pack(fill=tk.X, pady=2)
        entry = ttk.Entry(row)
        entry.pack(fill=tk.X)
        self.constraint_rows.append(entry)

    def _add_output_row(self):
        row = ttk.Frame(self.outputs_container)
        row.pack(fill=tk.X, pady=2)
        name_entry = ttk.Entry(row, width=15)
        name_entry.pack(side=tk.LEFT, padx=2)
        name_entry.insert(0, "name")
        type_combo = ttk.Combobox(row, values=["json", "text", "number"], width=8, state="readonly")
        type_combo.set("json")
        type_combo.pack(side=tk.LEFT, padx=2)
        desc_entry = ttk.Entry(row)
        desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        desc_entry.insert(0, "Description...")
        self.output_rows.append({"name": name_entry, "type": type_combo, "desc": desc_entry})

    def _build_definition(self) -> AgentDefinition:
        name = self.name_entry.get().strip()
        agent_id = name.lower().replace(" ", "_")
        category = self.category_entry.get().strip() or "Custom"
        goal = self.goal_text.get("1.0", tk.END).strip()

        inputs = []
        for r in self.input_rows:
            inputs.append(AgentInput(
                name=r["name"].get().strip(),
                type=r["type"].get(),
                description=r["desc"].get().strip(),
            ))

        constraints = [e.get().strip() for e in self.constraint_rows if e.get().strip()]

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

    def _save_agent(self) -> AgentDefinition:
        import os
        definition = self._build_definition()
        filepath = os.path.join(config.USER_AGENTS_DIR, f"{definition.id}.json")
        definition.save_to_json(filepath)
        return definition

    def _save_and_run(self):
        self._save_agent()

    def reset_form(self):
        self.name_entry.delete(0, tk.END)
        self.category_entry.delete(0, tk.END)
        self.category_entry.insert(0, "Custom")
        self.goal_text.delete("1.0", tk.END)

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
