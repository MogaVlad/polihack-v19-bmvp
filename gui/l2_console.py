import os
import tkinter as tk
from tkinter import ttk, filedialog

import config


class L2ConsoleTab:
    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self._build_ui()

    def _build_ui(self):
        banner = tk.Label(
            self.frame,
            text=(
                "This is L2: versioned prompts, manual data flow, raw text output. "
                "Switch to the Agent Library to see L3."
            ),
            bg="#fff3cd",
            fg="#856404",
            font=("Segoe UI", 10),
            wraplength=800,
            justify=tk.LEFT,
            padx=10,
            pady=8,
        )
        banner.pack(fill=tk.X, padx=10, pady=(10, 5))

        controls = ttk.Frame(self.frame)
        controls.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(controls, text="Prompt Template:").pack(side=tk.LEFT, padx=(0, 5))

        self.template_var = tk.StringVar()
        templates = self._load_template_names()
        self.template_combo = ttk.Combobox(
            controls,
            textvariable=self.template_var,
            values=templates,
            state="readonly",
            width=30,
        )
        self.template_combo.pack(side=tk.LEFT, padx=5)
        if templates:
            self.template_combo.current(0)

        ttk.Button(controls, text="View Template", command=self._view_template).pack(side=tk.LEFT, padx=5)

        data_frame = ttk.LabelFrame(self.frame, text="DATA INPUT")
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        btn_row = ttk.Frame(data_frame)
        btn_row.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_row, text="Load File", command=self._load_file).pack(side=tk.LEFT)

        self.data_input = tk.Text(
            data_frame,
            wrap=tk.WORD,
            height=8,
            font=("Consolas", 10),
        )
        self.data_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        ttk.Button(self.frame, text="Send to LLM", command=self._send_to_llm).pack(pady=5)

        response_frame = ttk.LabelFrame(self.frame, text="RAW RESPONSE")
        response_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        self.response_text = tk.Text(
            response_frame,
            wrap=tk.WORD,
            height=10,
            state=tk.DISABLED,
            bg="#fafafa",
            font=("Consolas", 10),
        )
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _load_template_names(self):
        if not os.path.isdir(config.PROMPTS_DIR):
            return []
        return [f for f in sorted(os.listdir(config.PROMPTS_DIR)) if f.endswith(".md")]

    def _view_template(self):
        template_name = self.template_var.get()
        if not template_name:
            return
        filepath = os.path.join(config.PROMPTS_DIR, template_name)
        if not os.path.isfile(filepath):
            return
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        win = tk.Toplevel(self.frame)
        win.title(f"Template: {template_name}")
        win.geometry("600x500")
        text = tk.Text(win, wrap=tk.WORD, font=("Consolas", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert("1.0", content)
        text.configure(state=tk.DISABLED)

    def _load_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            with open(filepath, "r", encoding="utf-8") as f:
                self.data_input.delete("1.0", tk.END)
                self.data_input.insert("1.0", f.read())

    def _send_to_llm(self):
        pass
