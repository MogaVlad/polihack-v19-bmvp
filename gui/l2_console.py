import os
import customtkinter as ctk
from tkinter import filedialog

import config


class L2ConsoleTab:
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

        # ── Banner ──────────────────────────────────────────────
        banner = ctk.CTkFrame(wrapper, fg_color=("#fff3cd", "#3a2e10"), corner_radius=8)
        banner.pack(fill="x", padx=8, pady=(4, 8))

        ctk.CTkLabel(
            banner,
            text=(
                "⚠  This is L2: versioned prompts, manual data flow, raw text output. "
                "Switch to the Agent Library to see L3."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#856404", "#ffc107"),
            wraplength=750,
            justify="left",
        ).pack(padx=14, pady=10)

        # ── Controls ────────────────────────────────────────────
        controls = ctk.CTkFrame(wrapper, fg_color="transparent")
        controls.pack(fill="x", padx=8, pady=(0, 6))

        ctk.CTkLabel(
            controls, text="Prompt Template:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#8899aa"),
        ).pack(side="left", padx=(0, 6))

        templates = self._load_template_names()
        self.template_var = ctk.StringVar()

        self.template_combo = ctk.CTkComboBox(
            controls,
            values=templates,
            variable=self.template_var,
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
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.template_combo.pack(side="left", padx=(0, 8))
        if templates:
            self.template_combo.set(templates[0])

        ctk.CTkButton(
            controls, text="View Template", width=120, height=30, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("gray78", "#0f3460"), hover_color=("gray68", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"), command=self._view_template,
        ).pack(side="left")

        # ── Data input section ──────────────────────────────────
        data_card = ctk.CTkFrame(wrapper, fg_color=("gray92", "#162d50"), corner_radius=10)
        data_card.pack(fill="both", expand=True, padx=8, pady=4)

        data_header = ctk.CTkFrame(data_card, fg_color="transparent")
        data_header.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            data_header, text="DATA INPUT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("gray40", "#667788"),
        ).pack(side="left")

        ctk.CTkButton(
            data_header, text="Load File", width=90, height=26, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("gray78", "#0f3460"), hover_color=("gray68", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"), command=self._load_file,
        ).pack(side="right")

        self.data_input = ctk.CTkTextbox(
            data_card,
            height=120,
            corner_radius=8,
            fg_color=("gray96", "#0e1117"),
            text_color=("gray10", "#c0d0e0"),
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
        )
        self.data_input.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # ── Send button ─────────────────────────────────────────
        ctk.CTkButton(
            wrapper, text="📤  Send to LLM", height=36, corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#4a9eff", hover_color="#3a89dd",
            text_color="#ffffff", command=self._send_to_llm,
        ).pack(padx=8, pady=6)

        # ── Response section ────────────────────────────────────
        response_card = ctk.CTkFrame(wrapper, fg_color=("gray92", "#162d50"), corner_radius=10)
        response_card.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        ctk.CTkLabel(
            response_card, text="RAW RESPONSE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("gray40", "#667788"),
        ).pack(anchor="w", padx=12, pady=(10, 6))

        self.response_text = ctk.CTkTextbox(
            response_card,
            height=140,
            corner_radius=8,
            fg_color=("gray96", "#0e1117"),
            text_color=("gray10", "#c0d0e0"),
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled",
            wrap="word",
        )
        self.response_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ── Logic ────────────────────────────────────────────────────
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

        win = ctk.CTkToplevel()
        win.title(f"Template: {template_name}")
        win.geometry("620x520")

        textbox = ctk.CTkTextbox(
            win, corner_radius=8,
            fg_color=("gray96", "#0e1117"),
            text_color=("gray10", "#c0d0e0"),
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
        )
        textbox.pack(fill="both", expand=True, padx=16, pady=16)
        textbox.insert("1.0", content)
        textbox.configure(state="disabled")

    def _load_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            with open(filepath, "r", encoding="utf-8") as f:
                self.data_input.delete("1.0", "end")
                self.data_input.insert("1.0", f.read())

    def _send_to_llm(self):
        pass
