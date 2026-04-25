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

_PAIR_ANNOTATIONS = [
    [
        "Structured I/O: Legacy pastes raw image data into a prompt. Agent defines a typed 'image' input and produces a JSON floor plan schema as output.",
        "Tool access: Agent uses Gemini Vision API as a registered tool — the prompt has no tool concept.",
        "Conversation: Agent proactively flags ambiguous features (unusual room shapes) and asks for clarification. Legacy gives a one-shot answer.",
        "Reusability: Anyone can run the Floor Plan Parser agent without knowing how the prompt works.",
    ],
    [
        "Structured I/O: Legacy expects pasted JSON in a text prompt. Agent declares a typed 'json' input field and outputs a structured violation list.",
        "Tool access: Agent calls P118 Validator and Pathfinding tools for real calculations. Legacy relies on the LLM to guess distances and rules.",
        "Constraints: Agent explicitly lists P118 rules (30m travel, 1.4m corridors, min 2 exits). Legacy buries them in prose instructions.",
        "Reusability: The Egress Validator agent can be re-run on any floor plan without modifying the prompt.",
    ],
    [
        "Structured I/O: Legacy returns free-form text explanation. Agent produces ranked diagnoses with severity and impact scores.",
        "Conversation: Agent can answer follow-up questions about specific violations. Legacy requires re-sending the entire prompt.",
        "Scope boundaries: Agent redirects validation questions to the Egress Validator agent instead of guessing.",
        "Constraints: Agent uses severity ranking rules to prioritize which violations to explain first.",
    ],
    [
        "Structured I/O: Legacy gives text suggestions. Agent produces ranked fix proposals with justification and effort estimates.",
        "Tool access: Agent calls Pathfinding and P118 Validator to verify that proposed fixes actually resolve violations. Legacy cannot verify.",
        "Conversation: Agent handles pushback ('Can't add a south exit') and offers alternatives. Legacy is one-shot.",
        "Constraints: Agent respects building constraints and checks proposals against P118 rules before suggesting them.",
    ],
]


class AdoptionPanel:
    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        self._build_ui()

    def _build_ui(self):
        wrapper = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
            scrollbar_button_color=("#384c46", "#b3c7c1"),
        )
        wrapper.pack(fill="both", expand=True, padx=4, pady=4)

        # ── Title ───────────────────────────────────────────────
        ctk.CTkLabel(
            wrapper,
            text="📊  Legacy vs Agent — Side-by-Side Comparison",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=("#121715", "#e8edeb"),
        ).pack(anchor="w", padx=12, pady=(8, 6))

        # ── Summary banner ──────────────────────────────────────
        banner = ctk.CTkFrame(wrapper, fg_color=("#f6f8f8", "#070909"), corner_radius=8)
        banner.pack(fill="x", padx=8, pady=(0, 10))

        ctk.CTkLabel(
            banner,
            text="Same task. Legacy = copy-paste + raw text. Agent = structured agents with tools and conversation.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#121715", "#b3c7c1"),
            wraplength=750,
            justify="left",
        ).pack(padx=14, pady=10)

        # ── Pair selector ───────────────────────────────────────
        selector = ctk.CTkFrame(wrapper, fg_color="transparent")
        selector.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkLabel(
            selector, text="Select pair:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#121715", "#b3c7c1"),
        ).pack(side="left", padx=(4, 8))

        pair_names = [p[0].replace(".json", "").replace("_", " ").title() for p in AGENT_PROMPT_PAIRS]

        self.pair_combo = ctk.CTkComboBox(
            selector,
            values=pair_names,
            width=240,
            height=30,
            corner_radius=6,
            state="readonly",
            fg_color=("#98a3b3", "#4c5767"),
            border_color=("#384c46", "#b3c7c1"),
            button_color=("#384c46", "#070909"),
            button_hover_color=("#2a3a34", "#1a2428"),
            text_color=("#121715", "#e8edeb"),
            dropdown_fg_color=("#f6f8f8", "#4c5767"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._on_pair_selected,
        )
        self.pair_combo.pack(side="left")
        if pair_names:
            self.pair_combo.set(pair_names[0])

        # ── Two-column comparison ───────────────────────────────
        columns = ctk.CTkFrame(wrapper, fg_color="transparent")
        columns.pack(fill="both", expand=True, padx=8, pady=4)
        columns.grid_columnconfigure(0, weight=5)
        columns.grid_columnconfigure(1, weight=0)
        columns.grid_columnconfigure(2, weight=5)
        columns.grid_rowconfigure(0, weight=1)

        # Legacy side
        left_card = ctk.CTkFrame(columns, fg_color=("#f6f8f8", "#070909"), corner_radius=10)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ctk.CTkLabel(
            left_card, text="Legacy — Prompt Template",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#121715", "#8889a5"),
        ).pack(anchor="w", padx=12, pady=(10, 6))

        self.l2_text = ctk.CTkTextbox(
            left_card,
            corner_radius=8,
            fg_color=("#98a3b3", "#4c5767"),
            text_color=("#121715", "#e8edeb"),
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word",
        )
        self.l2_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Arrow column
        arrow_frame = ctk.CTkFrame(columns, fg_color="transparent", width=48)
        arrow_frame.grid(row=0, column=1, sticky="ns", padx=2)
        arrow_frame.grid_propagate(False)

        ctk.CTkLabel(
            arrow_frame, text="→",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=("#b3c7c1", "#b3c7c1"),
        ).place(relx=0.5, rely=0.35, anchor="center")

        ctk.CTkLabel(
            arrow_frame, text="Legacy→Agent",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=("#121715", "#667788"),
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            arrow_frame, text="→",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=("#b3c7c1", "#b3c7c1"),
        ).place(relx=0.5, rely=0.65, anchor="center")

        # Agent side
        right_card = ctk.CTkFrame(columns, fg_color=("#f6f8f8", "#070909"), corner_radius=10)
        right_card.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

        ctk.CTkLabel(
            right_card, text="Agent — Agent Definition",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#121715", "#b3c7c1"),
        ).pack(anchor="w", padx=12, pady=(10, 6))

        self.l3_text = ctk.CTkTextbox(
            right_card,
            corner_radius=8,
            fg_color=("#98a3b3", "#4c5767"),
            text_color=("#121715", "#e8edeb"),
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word",
        )
        self.l3_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Fix: prevent mouse wheel from propagating to the parent scrollable frame
        def _prevent_scroll(event):
            delta = getattr(event, "delta", 0)
            if delta != 0:
                event.widget.yview_scroll(int(-1 * (delta / 120)), "units")
            elif event.num == 4:
                event.widget.yview_scroll(-1, "units")
            elif event.num == 5:
                event.widget.yview_scroll(1, "units")
            return "break"

        self.l2_text._textbox.bind("<MouseWheel>", _prevent_scroll)
        self.l2_text._textbox.bind("<Button-4>", _prevent_scroll)
        self.l2_text._textbox.bind("<Button-5>", _prevent_scroll)
        self.l3_text._textbox.bind("<MouseWheel>", _prevent_scroll)
        self.l3_text._textbox.bind("<Button-4>", _prevent_scroll)
        self.l3_text._textbox.bind("<Button-5>", _prevent_scroll)

        # ── Annotations ─────────────────────────────────────────
        self.ann_card = ctk.CTkFrame(wrapper, fg_color=("#f6f8f8", "#070909"), corner_radius=10)
        self.ann_card.pack(fill="x", padx=8, pady=(8, 8))

        ctk.CTkLabel(
            self.ann_card, text="What Changed: Legacy → Agent",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#121715", "#b3c7c1"),
        ).pack(anchor="w", padx=12, pady=(10, 6))

        self.ann_container = ctk.CTkFrame(self.ann_card, fg_color="transparent")
        self.ann_container.pack(fill="x", padx=0, pady=(0, 8))

        # Load initial pair
        self._on_pair_selected(pair_names[0] if pair_names else "")

    def _on_pair_selected(self, selected_value):
        pair_names = [p[0].replace(".json", "").replace("_", " ").title() for p in AGENT_PROMPT_PAIRS]
        if selected_value not in pair_names:
            return
        idx = pair_names.index(selected_value)

        agent_file, prompt_file = AGENT_PROMPT_PAIRS[idx]

        prompt_path = os.path.join(config.PROMPTS_DIR, prompt_file)
        agent_path = os.path.join(config.AGENTS_DIR, agent_file)

        # Legacy side
        self.l2_text.configure(state="normal")
        self.l2_text.delete("1.0", "end")
        if os.path.isfile(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.l2_text.insert("1.0", f.read())
        else:
            self.l2_text.insert("1.0", "(Template not found)")
        self.l2_text.configure(state="disabled")

        # Agent side
        self.l3_text.configure(state="normal")
        self.l3_text.delete("1.0", "end")
        if os.path.isfile(agent_path):
            with open(agent_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.l3_text.insert("1.0", json.dumps(data, indent=2))
        else:
            self.l3_text.insert("1.0", "(Agent definition not found)")
        self.l3_text.configure(state="disabled")

        # Update annotations for this pair
        for widget in self.ann_container.winfo_children():
            widget.destroy()

        annotations = _PAIR_ANNOTATIONS[idx] if idx < len(_PAIR_ANNOTATIONS) else []
        for a in annotations:
            ctk.CTkLabel(
                self.ann_container, text=f"  {a}",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=("#121715", "#b3c7c1"),
                wraplength=750,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=16, pady=2)