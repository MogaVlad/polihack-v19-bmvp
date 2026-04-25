import os
import json
import customtkinter as ctk

import config


AGENT_PROMPT_PAIRS = [
    ("floor_plan_parser.json", "v1_parse_floor_plan.md"),
    ("egress_validator.json", "v1_check_egress.md"),
    ("evacuation_diagnoser.json", "v1_diagnose_issues.md"),
    ("exit_placement_advisor.json", "v1_propose_fixes.md"),
]


class AdoptionPanel:
    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        self._build_ui()

    def _build_ui(self):
        wrapper = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
            scrollbar_button_color=("#bbb", "#2a3f60"),
        )
        wrapper.pack(fill="both", expand=True, padx=4, pady=4)

        # ── Title ───────────────────────────────────────────────
        ctk.CTkLabel(
            wrapper,
            text="📊  L2 vs L3 — Side-by-Side Comparison",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=("gray15", "#e0e0e0"),
        ).pack(anchor="w", padx=12, pady=(8, 6))

        # ── Summary banner ──────────────────────────────────────
        banner = ctk.CTkFrame(wrapper, fg_color=("#d4edda", "#1a3a2a"), corner_radius=8)
        banner.pack(fill="x", padx=8, pady=(0, 10))

        ctk.CTkLabel(
            banner,
            text="Same task. L2 = copy-paste + raw text. L3 = structured agents with tools and conversation.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#155724", "#4caf50"),
            wraplength=750,
            justify="left",
        ).pack(padx=14, pady=10)

        # ── Pair selector ───────────────────────────────────────
        selector = ctk.CTkFrame(wrapper, fg_color="transparent")
        selector.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkLabel(
            selector, text="Select pair:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#8899aa"),
        ).pack(side="left", padx=(4, 8))

        pair_names = [p[0].replace(".json", "").replace("_", " ").title() for p in AGENT_PROMPT_PAIRS]

        self.pair_combo = ctk.CTkComboBox(
            selector,
            values=pair_names,
            width=240,
            height=30,
            corner_radius=6,
            state="readonly",
            fg_color=("gray96", "#0e1117"),
            border_color=("gray75", "#2a3f60"),
            button_color=("gray75", "#1e4a8a"),
            button_hover_color=("gray60", "#3a5f90"),
            text_color=("gray10", "#e0e0e0"),
            dropdown_fg_color=("gray96", "#162d50"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._on_pair_selected,
        )
        self.pair_combo.pack(side="left")
        if pair_names:
            self.pair_combo.set(pair_names[0])

        # ── Two-column comparison ───────────────────────────────
        columns = ctk.CTkFrame(wrapper, fg_color="transparent")
        columns.pack(fill="both", expand=True, padx=8, pady=4)
        columns.grid_columnconfigure(0, weight=1)
        columns.grid_columnconfigure(1, weight=1)
        columns.grid_rowconfigure(0, weight=1)

        # L2 side
        left_card = ctk.CTkFrame(columns, fg_color=("gray92", "#162d50"), corner_radius=10)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ctk.CTkLabel(
            left_card, text="L2 — Prompt Template",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("gray30", "#ffc107"),
        ).pack(anchor="w", padx=12, pady=(10, 6))

        self.l2_text = ctk.CTkTextbox(
            left_card,
            corner_radius=8,
            fg_color=("#fff8e1", "#1a1a10"),
            text_color=("gray15", "#d4c088"),
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word",
        )
        self.l2_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # L3 side
        right_card = ctk.CTkFrame(columns, fg_color=("gray92", "#162d50"), corner_radius=10)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        ctk.CTkLabel(
            right_card, text="L3 — Agent Definition",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("gray30", "#4caf50"),
        ).pack(anchor="w", padx=12, pady=(10, 6))

        self.l3_text = ctk.CTkTextbox(
            right_card,
            corner_radius=8,
            fg_color=("#e8f5e9", "#0a1a10"),
            text_color=("gray15", "#88d4a0"),
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word",
        )
        self.l3_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # ── Annotations ─────────────────────────────────────────
        ann_card = ctk.CTkFrame(wrapper, fg_color=("gray92", "#162d50"), corner_radius=10)
        ann_card.pack(fill="x", padx=8, pady=(8, 8))

        ctk.CTkLabel(
            ann_card, text="What Changed: L2 → L3",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("gray30", "#c0d0e0"),
        ).pack(anchor="w", padx=12, pady=(10, 6))

        annotations = [
            "✦  Structured I/O: Named inputs/outputs with types replace free-form text pasting",
            "✦  Tool access: Agents can call domain tools (P118 validator, pathfinding) — prompts cannot",
            "✦  Constraints: Domain rules are explicit and enforceable, not buried in prompt text",
            "✦  Conversation: Multi-turn follow-up with scope boundaries, not one-shot Q&A",
            "✦  Reusability: Anyone can run the agent without understanding the prompt",
        ]
        for a in annotations:
            ctk.CTkLabel(
                ann_card, text=a,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=("gray30", "#8899aa"),
                wraplength=750,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=16, pady=2)

        # Spacer at bottom
        ctk.CTkFrame(ann_card, height=8, fg_color="transparent").pack()

        # Load initial pair
        self._on_pair_selected(pair_names[0] if pair_names else "")

    def _on_pair_selected(self, selected_value):
        # Find index by matching name
        pair_names = [p[0].replace(".json", "").replace("_", " ").title() for p in AGENT_PROMPT_PAIRS]
        if selected_value not in pair_names:
            return
        idx = pair_names.index(selected_value)

        agent_file, prompt_file = AGENT_PROMPT_PAIRS[idx]

        prompt_path = os.path.join(config.PROMPTS_DIR, prompt_file)
        agent_path = os.path.join(config.AGENTS_DIR, agent_file)

        # L2 side
        self.l2_text.configure(state="normal")
        self.l2_text.delete("1.0", "end")
        if os.path.isfile(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.l2_text.insert("1.0", f.read())
        else:
            self.l2_text.insert("1.0", "(Template not found)")
        self.l2_text.configure(state="disabled")

        # L3 side
        self.l3_text.configure(state="normal")
        self.l3_text.delete("1.0", "end")
        if os.path.isfile(agent_path):
            with open(agent_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.l3_text.insert("1.0", json.dumps(data, indent=2))
        else:
            self.l3_text.insert("1.0", "(Agent definition not found)")
        self.l3_text.configure(state="disabled")
