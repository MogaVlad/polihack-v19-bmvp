import os
import json
import tkinter as tk
from tkinter import ttk

import config


AGENT_PROMPT_PAIRS = [
    ("floor_plan_parser.json", "v1_parse_floor_plan.md"),
    ("egress_validator.json", "v1_check_egress.md"),
    ("evacuation_diagnoser.json", "v1_diagnose_issues.md"),
    ("exit_placement_advisor.json", "v1_propose_fixes.md"),
]


class AdoptionPanel:
    def __init__(self, parent: ttk.Notebook):
        self.frame = ttk.Frame(parent)
        self._build_ui()

    def _build_ui(self):
        ttk.Label(
            self.frame,
            text="L2 vs L3 — Side-by-Side Comparison",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=10, pady=10)

        summary = tk.Label(
            self.frame,
            text="Same task. L2 = copy-paste + raw text. L3 = structured agents with tools and conversation.",
            bg="#d4edda",
            fg="#155724",
            font=("Segoe UI", 10),
            padx=10,
            pady=8,
        )
        summary.pack(fill=tk.X, padx=10, pady=(0, 10))

        selector = ttk.Frame(self.frame)
        selector.pack(fill=tk.X, padx=10)
        ttk.Label(selector, text="Select pair:").pack(side=tk.LEFT, padx=(0, 5))

        pair_names = [p[0].replace(".json", "").replace("_", " ").title() for p in AGENT_PROMPT_PAIRS]
        self.pair_var = tk.StringVar()
        self.pair_combo = ttk.Combobox(
            selector,
            textvariable=self.pair_var,
            values=pair_names,
            state="readonly",
            width=30,
        )
        self.pair_combo.pack(side=tk.LEFT, padx=5)
        self.pair_combo.bind("<<ComboboxSelected>>", self._on_pair_selected)
        if pair_names:
            self.pair_combo.current(0)

        columns = ttk.Frame(self.frame)
        columns.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.LabelFrame(columns, text="L2 — Prompt Template")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.l2_text = tk.Text(left_frame, wrap=tk.WORD, font=("Consolas", 9), bg="#fff8e1")
        self.l2_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        right_frame = ttk.LabelFrame(columns, text="L3 — Agent Definition")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.l3_text = tk.Text(right_frame, wrap=tk.WORD, font=("Consolas", 9), bg="#e8f5e9")
        self.l3_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        annotations_frame = ttk.LabelFrame(self.frame, text="What Changed: L2 to L3")
        annotations_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        annotations = [
            "Structured I/O: Named inputs/outputs with types replace free-form text pasting",
            "Tool access: Agents can call domain tools (P118 validator, pathfinding) — prompts cannot",
            "Constraints: Domain rules are explicit and enforceable, not buried in prompt text",
            "Conversation: Multi-turn follow-up with scope boundaries, not one-shot Q&A",
            "Reusability: Anyone can run the agent without understanding the prompt",
        ]
        for a in annotations:
            ttk.Label(annotations_frame, text=f"  {a}", wraplength=800, justify=tk.LEFT).pack(
                anchor="w", padx=10, pady=2
            )

        self._on_pair_selected(None)

    def _on_pair_selected(self, event):
        idx = self.pair_combo.current()
        if idx < 0:
            return
        agent_file, prompt_file = AGENT_PROMPT_PAIRS[idx]

        prompt_path = os.path.join(config.PROMPTS_DIR, prompt_file)
        agent_path = os.path.join(config.AGENTS_DIR, agent_file)

        self.l2_text.configure(state=tk.NORMAL)
        self.l2_text.delete("1.0", tk.END)
        if os.path.isfile(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.l2_text.insert("1.0", f.read())
        else:
            self.l2_text.insert("1.0", "(Template not found)")
        self.l2_text.configure(state=tk.DISABLED)

        self.l3_text.configure(state=tk.NORMAL)
        self.l3_text.delete("1.0", tk.END)
        if os.path.isfile(agent_path):
            with open(agent_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.l3_text.insert("1.0", json.dumps(data, indent=2))
        else:
            self.l3_text.insert("1.0", "(Agent definition not found)")
        self.l3_text.configure(state=tk.DISABLED)
