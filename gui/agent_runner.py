import tkinter as tk
from tkinter import ttk
from typing import Optional

from models.agent_definition import AgentDefinition


class AgentRunnerTab:
    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self.current_agent: Optional[AgentDefinition] = None
        self._build_ui()

    def _build_ui(self):
        header = ttk.Frame(self.frame)
        header.pack(fill=tk.X, padx=10, pady=10)

        self.agent_name_label = ttk.Label(
            header,
            text="No agent loaded",
            font=("Segoe UI", 14, "bold"),
        )
        self.agent_name_label.pack(anchor="w")

        self.agent_goal_label = ttk.Label(
            header,
            text="Select an agent from the library to begin.",
            font=("Segoe UI", 10),
            foreground="#666666",
        )
        self.agent_goal_label.pack(anchor="w", pady=(2, 0))

        self.view_def_btn = ttk.Button(header, text="View Definition", command=self._view_definition)
        self.view_def_btn.pack(anchor="e")

        io_frame = ttk.Frame(self.frame)
        io_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        input_frame = ttk.LabelFrame(io_frame, text="INPUTS")
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.inputs_container = ttk.Frame(input_frame)
        self.inputs_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.input_widgets = {}

        self.run_btn = ttk.Button(input_frame, text="Run Agent", command=self._run_agent)
        self.run_btn.pack(pady=10)

        output_frame = ttk.LabelFrame(io_frame, text="OUTPUTS")
        output_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.output_text = tk.Text(
            output_frame,
            wrap=tk.WORD,
            height=10,
            state=tk.DISABLED,
            bg="#fafafa",
            font=("Consolas", 10),
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        export_frame = ttk.Frame(output_frame)
        export_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(export_frame, text="Export JSON", command=self._export_json).pack(side=tk.LEFT, padx=2)
        ttk.Button(export_frame, text="Show on Canvas", command=self._show_on_canvas).pack(side=tk.LEFT, padx=2)

        chat_frame = ttk.LabelFrame(self.frame, text="CONVERSATION")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        self.chat_display = tk.Text(
            chat_frame,
            wrap=tk.WORD,
            height=8,
            state=tk.DISABLED,
            bg="#fafafa",
            font=("Segoe UI", 10),
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 0))
        self.chat_display.tag_configure("agent", foreground="#2d5aa0")
        self.chat_display.tag_configure("user", foreground="#333333")

        msg_frame = ttk.Frame(chat_frame)
        msg_frame.pack(fill=tk.X, padx=5, pady=5)

        self.chat_input = ttk.Entry(msg_frame)
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_input.configure(state=tk.DISABLED)
        self.chat_input.bind("<Return>", lambda e: self._send_message())

        self.send_btn = ttk.Button(msg_frame, text="Send", command=self._send_message)
        self.send_btn.pack(side=tk.RIGHT)

    def load_agent(self, agent_def: AgentDefinition):
        self.current_agent = agent_def
        self.agent_name_label.configure(text=f"Agent: {agent_def.name}")
        self.agent_goal_label.configure(text=f"Goal: {agent_def.goal}")

        for widget in self.inputs_container.winfo_children():
            widget.destroy()
        self.input_widgets.clear()

        for inp in agent_def.inputs:
            row = ttk.Frame(self.inputs_container)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=f"{inp.name}:", width=15).pack(side=tk.LEFT)
            if inp.type in ("json", "text"):
                entry = ttk.Entry(row)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.input_widgets[inp.name] = entry
            elif inp.type == "image":
                entry = ttk.Entry(row)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
                ttk.Button(row, text="Browse...", command=lambda n=inp.name: self._browse_file(n)).pack(side=tk.RIGHT)
                self.input_widgets[inp.name] = entry

        self.output_text.configure(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.configure(state=tk.DISABLED)

        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_input.configure(state=tk.DISABLED)

    def _view_definition(self):
        if not self.current_agent:
            return
        import json
        win = tk.Toplevel(self.frame)
        win.title(f"Definition: {self.current_agent.name}")
        win.geometry("500x600")
        text = tk.Text(win, wrap=tk.WORD, font=("Consolas", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert("1.0", json.dumps(self.current_agent.to_dict(), indent=2))
        text.configure(state=tk.DISABLED)

    def _run_agent(self):
        pass

    def _send_message(self):
        pass

    def _export_json(self):
        pass

    def _show_on_canvas(self):
        pass

    def _browse_file(self, input_name: str):
        from tkinter import filedialog
        filepath = filedialog.askopenfilename()
        if filepath and input_name in self.input_widgets:
            self.input_widgets[input_name].delete(0, tk.END)
            self.input_widgets[input_name].insert(0, filepath)
