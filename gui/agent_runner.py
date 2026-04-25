import json
import os
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from typing import Optional
import re

from models.agent_definition import AgentDefinition
from models.chat import AgentResult
from models.floor_plan import FloorPlan
from models.violations import Violation
from engine.runner import AgentRunner
from engine.conversation import ConversationManager
from engine.prompt_builder import PromptBuilder


_FLAG_KEYWORDS = re.compile(
    r"\b(violation|warning|exceeded|insufficient|blocked|narrow|missing|"
    r"non-compliant|critical|fail|danger|unsafe|risk|dead.?end)\b",
    re.IGNORECASE,
)

_LOCATION_PATTERN = re.compile(
    r"\b((?:Room|Corridor|room|corridor)\s+[A-Za-z]?\d+|[RC]\d+)\b"
)

_SEVERITY_PATTERN = re.compile(
    r"\b(CRITICAL|MAJOR|MINOR|INFO)\b", re.IGNORECASE
)

_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")

_BULLET_PATTERN = re.compile(r"^(\s*[-•]\s)", re.MULTILINE)


class AgentRunnerTab:
    def __init__(self, parent: ctk.CTkFrame, status_bar=None, canvas_panel=None):
        self.parent = parent
        self.status_bar = status_bar
        self.canvas_panel = canvas_panel
        self.current_agent: Optional[AgentDefinition] = None
        self._has_run = False
        self._is_running = False
        self._last_result: Optional[AgentResult] = None
        self._conversation: Optional[ConversationManager] = None
        self._engine = AgentRunner()
        self._violation_locations: set = set()
        self._output_expanded = False  # collapsed by default
        self._build_ui()

    # ── Helpers ──────────────────────────────────────────────────
    def _section_header(self, parent, text: str):
        """Create a styled section header label."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(
            frame,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("#92817A", "#92817A"),
        ).pack(side="left")
        sep = ctk.CTkFrame(frame, height=1, fg_color=("#543520", "#92817A"))
        sep.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=1)
        return frame

    # ── Build UI ─────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────
        header = ctk.CTkFrame(self.parent, fg_color=("#e7d5a5", "#2d1a0e"), corner_radius=10)
        header.pack(fill="x", padx=8, pady=(6, 6))

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=16, pady=10)

        top_row = ctk.CTkFrame(header_inner, fg_color="transparent")
        top_row.pack(fill="x")

        self.agent_name_label = ctk.CTkLabel(
            top_row,
            text="No agent loaded",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=("#543520", "#F1DABF"),
        )
        self.agent_name_label.pack(side="left")

        self.status_indicator = ctk.CTkLabel(
            top_row,
            text="● Ready",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#92817A", "#92817A"),
        )
        self.status_indicator.pack(side="right")

        self.agent_goal_label = ctk.CTkLabel(
            header_inner,
            text="Select an agent from the library to begin.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#92817A", "#92817A"),
        )
        self.agent_goal_label.pack(anchor="w", pady=(2, 0))

        self.view_def_btn = ctk.CTkButton(
            header_inner,
            text="View Definition",
            width=130,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("#543520", "#2d1a0e"),
            hover_color=("#6b4428", "#3d2510"),
            text_color=("#e7d5a5", "#F1DABF"),
            command=self._view_definition,
        )
        self.view_def_btn.pack(anchor="e", pady=(4, 0))

        # ── Two-column body ──────────────────────────────────────
        body = ctk.CTkFrame(self.parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=5)
        body.grid_rowconfigure(0, weight=1)

        # ══════════════════════════════════════════════════════════
        # LEFT COLUMN — scrollable
        # ══════════════════════════════════════════════════════════
        left_scroll = ctk.CTkScrollableFrame(
            body,
            fg_color="transparent",
            scrollbar_button_color=("#543520", "#92817A"),
            scrollbar_button_hover_color=("#6b4428", "#7a6a60"),
        )
        left_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # ── INPUTS ──────────────────────────────────────────────
        input_card = ctk.CTkFrame(left_scroll, fg_color=("#e7d5a5", "#2d1a0e"), corner_radius=10)
        input_card.pack(fill="x", padx=0, pady=(0, 6))

        self._section_header(input_card, "INPUTS").pack(fill="x", padx=12, pady=(12, 6))

        # Dynamic per-agent field widgets (file paths, selectors, etc.)
        self.inputs_container = ctk.CTkFrame(input_card, fg_color="transparent")
        self.inputs_container.pack(fill="x", padx=12, pady=(0, 4))

        self.input_widgets = {}

        # Multi-line raw input textbox
        self.input_textbox = ctk.CTkTextbox(
            input_card,
            height=56,
            corner_radius=8,
            fg_color=("#f8f1e9", "#000500"),
            border_color=("#543520", "#92817A"),
            border_width=1,
            text_color=("#543520", "#F1DABF"),
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
        )
        self.input_textbox.pack(fill="x", padx=12, pady=(0, 6))

        def _prevent_scroll_input(event):
            delta = getattr(event, "delta", 0)
            if delta != 0:
                event.widget.yview_scroll(int(-1 * (delta / 120)), "units")
            elif event.num == 4:
                event.widget.yview_scroll(-1, "units")
            elif event.num == 5:
                event.widget.yview_scroll(1, "units")
            return "break"

        self.input_textbox._textbox.bind("<MouseWheel>", _prevent_scroll_input)
        self.input_textbox._textbox.bind("<Button-4>", _prevent_scroll_input)
        self.input_textbox._textbox.bind("<Button-5>", _prevent_scroll_input)

        self.run_btn = ctk.CTkButton(
            input_card,
            text="▶  Run Agent",
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#92817A",
            hover_color="#7a6a60",
            text_color="#ffffff",
            command=self._run_agent,
        )
        self.run_btn.pack(fill="x", padx=12, pady=(0, 12))

        # ── OUTPUTS (collapsible dropdown) ───────────────────────
        output_card = ctk.CTkFrame(left_scroll, fg_color=("#e7d5a5", "#2d1a0e"), corner_radius=10)
        output_card.pack(fill="x", padx=0, pady=(0, 6))

        # Header row acts as the toggle
        output_header = ctk.CTkFrame(output_card, fg_color="transparent", cursor="hand2")
        output_header.pack(fill="x", padx=12, pady=(10, 0))

        self._section_header(output_header, "OUTPUTS").pack(side="left", fill="x", expand=True)

        self.output_toggle_lbl = ctk.CTkLabel(
            output_header,
            text="▶",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("#92817A", "#92817A"),
            cursor="hand2",
        )
        self.output_toggle_lbl.pack(side="right", padx=(8, 0))

        # Bind both the frame and arrow label to toggle
        output_header.bind("<Button-1>", lambda e: self._toggle_outputs())
        self.output_toggle_lbl.bind("<Button-1>", lambda e: self._toggle_outputs())

        # Collapsible content frame
        self.output_content = ctk.CTkFrame(output_card, fg_color="transparent")
        # Not packed initially (collapsed)

        self.output_text = ctk.CTkTextbox(
            self.output_content,
            height=160,
            corner_radius=8,
            fg_color=("#f8f1e9", "#000500"),
            text_color=("#543520", "#F1DABF"),
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled",
            wrap="word",
        )
        self.output_text.pack(fill="both", expand=True, padx=12, pady=(6, 6))

        # Prevent scroll propagation on output textbox
        def _prevent_scroll_output(event):
            delta = getattr(event, "delta", 0)
            if delta != 0:
                event.widget.yview_scroll(int(-1 * (delta / 120)), "units")
            elif event.num == 4:
                event.widget.yview_scroll(-1, "units")
            elif event.num == 5:
                event.widget.yview_scroll(1, "units")
            return "break"

        self.output_text._textbox.bind("<MouseWheel>", _prevent_scroll_output)
        self.output_text._textbox.bind("<Button-4>", _prevent_scroll_output)
        self.output_text._textbox.bind("<Button-5>", _prevent_scroll_output)

        export_frame = ctk.CTkFrame(self.output_content, fg_color="transparent")
        export_frame.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            export_frame, text="Export JSON", width=110, height=28, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("#543520", "#2d1a0e"), hover_color=("#6b4428", "#3d2510"),
            text_color=("#e7d5a5", "#F1DABF"), command=self._export_json,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            export_frame, text="Show on Canvas", width=120, height=28, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("#543520", "#2d1a0e"), hover_color=("#6b4428", "#3d2510"),
            text_color=("#e7d5a5", "#F1DABF"), command=self._show_on_canvas,
        ).pack(side="left")

        # Collapsed padding spacer
        self.output_collapsed_pad = ctk.CTkFrame(output_card, fg_color="transparent", height=6)
        self.output_collapsed_pad.pack()

        # ── CONSTRAINTS USED ────────────────────────────────────
        constraints_card = ctk.CTkFrame(left_scroll, fg_color=("#e7d5a5", "#2d1a0e"), corner_radius=10)
        constraints_card.pack(fill="x", padx=0, pady=(0, 6))

        self._section_header(constraints_card, "CONSTRAINTS USED").pack(fill="x", padx=12, pady=(10, 4))
        self.constraints_label = ctk.CTkLabel(
            constraints_card,
            text="—",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#92817A", "#92817A"),
            wraplength=300,
            justify="left",
            anchor="nw",
        )
        self.constraints_label.pack(fill="x", padx=14, pady=(0, 10))

        # ── TOOLS USED ───────────────────────────────────────────
        tools_card = ctk.CTkFrame(left_scroll, fg_color=("#e7d5a5", "#2d1a0e"), corner_radius=10)
        tools_card.pack(fill="x", padx=0, pady=(0, 6))

        self._section_header(tools_card, "TOOLS USED").pack(fill="x", padx=12, pady=(10, 4))
        self.tools_label = ctk.CTkLabel(
            tools_card,
            text="—",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#92817A", "#92817A"),
            wraplength=300,
            justify="left",
            anchor="nw",
        )
        self.tools_label.pack(fill="x", padx=14, pady=(0, 10))

        # ══════════════════════════════════════════════════════════
        # RIGHT COLUMN — conversation (AI responses only)
        # ══════════════════════════════════════════════════════════
        right_card = ctk.CTkFrame(body, fg_color=("#e7d5a5", "#2d1a0e"), corner_radius=10)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right_card.grid_rowconfigure(1, weight=1)
        right_card.grid_columnconfigure(0, weight=1)

        # Conversation header
        chat_header_frame = ctk.CTkFrame(right_card, fg_color="transparent")
        chat_header_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        self._section_header(chat_header_frame, "CONVERSATION").pack(side="left", fill="x", expand=True)

        self.clear_chat_btn = ctk.CTkButton(
            chat_header_frame,
            text="Clear",
            width=72,
            height=24,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color=("#543520", "#2d1a0e"),
            hover_color=("#6b4428", "#3d2510"),
            text_color=("#e7d5a5", "#F1DABF"),
            command=self._clear_chat,
        )
        self.clear_chat_btn.pack(side="right", padx=(8, 0))

        # Chat display — fills the right column
        self.chat_display = ctk.CTkTextbox(
            right_card,
            corner_radius=8,
            fg_color=("#f8f1e9", "#000500"),
            text_color=("#543520", "#F1DABF"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            state="disabled",
            wrap="word",
        )
        self.chat_display.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))

        # Configure tag colours
        self.chat_display.tag_config("agent", foreground="#F1DABF")
        self.chat_display.tag_config("flagged", foreground="#ff6b6b")
        self.chat_display.tag_config("timestamp", foreground="#555555")
        self.chat_display.tag_config("bold", foreground="#e0e0e0")
        self.chat_display.tag_config("bullet", foreground="#8899aa")
        self.chat_display.tag_config("sev_critical", foreground="#f44336")
        self.chat_display.tag_config("sev_major", foreground="#c47b2a")
        self.chat_display.tag_config("sev_minor", foreground="#fdd835")
        self.chat_display.tag_config("location", foreground="#92817A", underline=True)
        self.chat_display.tag_bind("location", "<Button-1>", self._on_location_click)
        self.chat_display.tag_bind("location", "<Enter>",
                                   lambda e: self.chat_display.configure(cursor="hand2"))
        self.chat_display.tag_bind("location", "<Leave>",
                                   lambda e: self.chat_display.configure(cursor=""))

        # Prevent scroll propagation on chat display
        def _prevent_scroll_chat(event):
            delta = getattr(event, "delta", 0)
            if delta != 0:
                event.widget.yview_scroll(int(-1 * (delta / 120)), "units")
            elif event.num == 4:
                event.widget.yview_scroll(-1, "units")
            elif event.num == 5:
                event.widget.yview_scroll(1, "units")
            return "break"

        self.chat_display._textbox.bind("<MouseWheel>", _prevent_scroll_chat)
        self.chat_display._textbox.bind("<Button-4>", _prevent_scroll_chat)
        self.chat_display._textbox.bind("<Button-5>", _prevent_scroll_chat)

        # Message input row
        msg_frame = ctk.CTkFrame(right_card, fg_color="transparent")
        msg_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))

        self.chat_input = ctk.CTkEntry(
            msg_frame,
            placeholder_text="Type a follow-up question…",
            height=34,
            corner_radius=8,
            fg_color=("#f8f1e9", "#000500"),
            border_color=("#543520", "#92817A"),
            text_color=("#543520", "#F1DABF"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            state="disabled",
        )
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.chat_input.bind("<Return>", lambda e: self._send_message())

        self.send_btn = ctk.CTkButton(
            msg_frame,
            text="Send",
            width=70,
            height=34,
            corner_radius=8,
            fg_color="#92817A",
            hover_color="#7a6a60",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._send_message,
            state="disabled",
        )
        self.send_btn.pack(side="right")

    # ── Output dropdown toggle ────────────────────────────────────
    def _toggle_outputs(self):
        """Expand or collapse the outputs section."""
        self._output_expanded = not self._output_expanded
        if self._output_expanded:
            self.output_collapsed_pad.pack_forget()
            self.output_content.pack(fill="x")
            self.output_toggle_lbl.configure(text="▼")
        else:
            self.output_content.pack_forget()
            self.output_collapsed_pad.pack()
            self.output_toggle_lbl.configure(text="▶")

    # ── Chat message helpers ─────────────────────────────────────
    def _append_agent_message(self, text: str):
        """Append an AI-only response to the chat display with formatting."""
        self.chat_display.configure(state="normal")
        if self.chat_display.get("1.0", "end").strip():
            self.chat_display.insert("end", "\n\n")
        self._insert_with_highlights(text, "agent")
        self.chat_display.configure(state="disabled")
        self._auto_scroll()

    def _append_user_message(self, text: str):
        """Store user message context but do NOT display it in the conversation panel."""
        # User messages are intentionally hidden; conversation shows AI responses only.
        pass

    def _insert_with_highlights(self, text: str, base_tag: str):
        """Insert text with bold, bullets, severity colors, flagged keywords, and clickable locations."""
        clean_parts = []
        bold_spans = []
        last = 0
        for m in _BOLD_PATTERN.finditer(text):
            clean_parts.append(text[last:m.start()])
            bold_start = sum(len(p) for p in clean_parts)
            clean_parts.append(m.group(1))
            bold_spans.append((bold_start, bold_start + len(m.group(1))))
            last = m.end()
        clean_parts.append(text[last:])
        clean_text = "".join(clean_parts)

        spans = []
        for bs, be in bold_spans:
            spans.append((bs, be, "bold"))
        for m in _FLAG_KEYWORDS.finditer(clean_text):
            spans.append((m.start(), m.end(), "flagged"))
        for m in _SEVERITY_PATTERN.finditer(clean_text):
            word = m.group().upper()
            tag = {"CRITICAL": "sev_critical", "MAJOR": "sev_major",
                   "MINOR": "sev_minor", "INFO": "bullet"}.get(word, base_tag)
            spans.append((m.start(), m.end(), tag))
        for m in _LOCATION_PATTERN.finditer(clean_text):
            loc_tag = f"loc_{m.group()}"
            self.chat_display.tag_config(loc_tag, foreground="#92817A", underline=True)
            self.chat_display.tag_bind(loc_tag, "<Button-1>", self._on_location_click)
            self.chat_display.tag_bind(loc_tag, "<Enter>",
                                       lambda e: self.chat_display.configure(cursor="hand2"))
            self.chat_display.tag_bind(loc_tag, "<Leave>",
                                       lambda e: self.chat_display.configure(cursor=""))
            spans.append((m.start(), m.end(), loc_tag))
        for m in _BULLET_PATTERN.finditer(clean_text):
            spans.append((m.start(), m.end(), "bullet"))

        spans.sort(key=lambda s: s[0])

        merged = []
        for s in spans:
            if merged and s[0] < merged[-1][1]:
                continue
            merged.append(s)

        last_end = 0
        for start, end, tag in merged:
            if start > last_end:
                self.chat_display.insert("end", clean_text[last_end:start], base_tag)
            self.chat_display.insert("end", clean_text[start:end], tag)
            last_end = end
        if last_end < len(clean_text):
            self.chat_display.insert("end", clean_text[last_end:], base_tag)

    def _auto_scroll(self):
        self.chat_display.see("end")

    def _set_chat_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.chat_input.configure(state=state)
        self.send_btn.configure(state=state)

    def _set_status(self, text: str, color: str = "#667788"):
        self.status_indicator.configure(text=f"● {text}", text_color=("#92817A", color))

    def _on_location_click(self, event):
        if not self.canvas_panel:
            return
        idx = self.chat_display.index(f"@{event.x},{event.y}")
        tags = self.chat_display.tag_names(idx)
        for tag in tags:
            if tag.startswith("loc_"):
                raw = tag[4:]
                loc_id = re.sub(r"^(?:Room|Corridor)\s+", "", raw)
                self._ensure_canvas_loaded()
                self.canvas_panel.highlight_location(loc_id)
                return

    def _ensure_canvas_loaded(self):
        if not self.canvas_panel or self.canvas_panel.floor_plan:
            return
        for name, widget in self.input_widgets.items():
            value = widget.get().strip()
            if value and os.path.isfile(value) and value.endswith(".json"):
                try:
                    plan = FloorPlan.load_from_json(value)
                    self.canvas_panel.load_plan(plan)
                    if not self.canvas_panel.visible:
                        self.canvas_panel.toggle()
                    self.canvas_panel.fit_to_window()
                    return
                except Exception:
                    pass

    # ── Agent loading ────────────────────────────────────────────
    def load_agent(self, agent_def: AgentDefinition):
        self.current_agent = agent_def
        self._has_run = False
        self.agent_name_label.configure(text=f"⚙  {agent_def.name}")
        self.agent_goal_label.configure(text=agent_def.goal)
        self._set_status("Ready")

        # Clear inputs
        for widget in self.inputs_container.winfo_children():
            widget.destroy()
        self.input_widgets.clear()
        self.input_textbox.delete("1.0", "end")

        for inp in agent_def.inputs:
            row = ctk.CTkFrame(self.inputs_container, fg_color="transparent")
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(
                row, text=f"{inp.name}:", width=100, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=("#543520", "#92817A"),
            ).pack(side="left")

            if inp.type in ("json", "text"):
                entry = ctk.CTkEntry(
                    row, height=30, corner_radius=6,
                    fg_color=("#f8f1e9", "#000500"),
                    border_color=("#543520", "#92817A"),
                    text_color=("#543520", "#F1DABF"),
                    font=ctk.CTkFont(size=11),
                )
                entry.pack(side="left", fill="x", expand=True)
                self.input_widgets[inp.name] = entry
            elif inp.type == "image":
                entry = ctk.CTkEntry(
                    row, height=30, corner_radius=6,
                    fg_color=("#f8f1e9", "#000500"),
                    border_color=("#543520", "#92817A"),
                    text_color=("#543520", "#F1DABF"),
                    font=ctk.CTkFont(size=11),
                )
                entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
                ctk.CTkButton(
                    row, text="Browse…", width=80, height=28, corner_radius=6,
                    font=ctk.CTkFont(size=11),
                    fg_color=("#543520", "#2d1a0e"), hover_color=("#6b4428", "#3d2510"),
                    command=lambda n=inp.name: self._browse_file(n),
                ).pack(side="right")
                self.input_widgets[inp.name] = entry

        # Clear outputs textbox
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

        # Collapse outputs section when a new agent is loaded
        if self._output_expanded:
            self._toggle_outputs()

        # Clear chat and disable input
        self._clear_chat()
        self._set_chat_enabled(False)

        # Update constraints & tools
        if agent_def.constraints:
            constraints_text = "\n".join(f"• {c}" for c in agent_def.constraints)
        else:
            constraints_text = "—"
        self.constraints_label.configure(text=constraints_text)

        if agent_def.tools:
            tools_text = "\n".join(f"• {t}" for t in agent_def.tools)
        else:
            tools_text = "—"
        self.tools_label.configure(text=tools_text)

    # ── Actions ───────────────────────────────────────────────────
    def _view_definition(self):
        if not self.current_agent:
            return

        root = self.parent.winfo_toplevel()
        overlay = ctk.CTkFrame(root, fg_color=("#543520", "#000000"), corner_radius=0)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.configure(fg_color=("#f8f1e9", "#1a0e05"))

        card = ctk.CTkFrame(overlay, fg_color=("#f8f1e9", "#1a0e05"), corner_radius=14, width=580, height=520)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text=f"Definition: {self.current_agent.name}",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=("#543520", "#F1DABF"),
        ).pack(side="left")

        ctk.CTkButton(
            header, text="✕", width=32, height=32, corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#543520", "#2a2a3e"), hover_color=("#6b4428", "#3a3a50"),
            text_color=("#543520", "#ff6b6b"),
            command=overlay.destroy,
        ).pack(side="right")

        textbox = ctk.CTkTextbox(
            card, corner_radius=8,
            fg_color=("#f8f1e9", "#000500"),
            text_color=("#543520", "#F1DABF"),
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
        )
        textbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        textbox.insert("1.0", json.dumps(self.current_agent.to_dict(), indent=2))
        textbox.configure(state="disabled")

        overlay.bind("<Button-1>", lambda e: overlay.destroy() if e.widget == overlay else None)
        overlay.lift()

    def _collect_inputs(self) -> dict:
        inputs = {}
        for name, widget in self.input_widgets.items():
            value = widget.get().strip()
            if value and os.path.isfile(value):
                try:
                    with open(value, "r", encoding="utf-8") as f:
                        value = f.read()
                except Exception:
                    pass
            inputs[name] = value
        # Also collect from the raw input textbox if it has content
        raw = self.input_textbox.get("1.0", "end").strip()
        if raw:
            inputs.setdefault("input", raw)
        return inputs

    def _run_agent(self):
        if not self.current_agent or self._is_running:
            return

        self._is_running = True
        self._set_status("Running…", "#c47b2a")
        self.run_btn.configure(state="disabled")
        self._set_chat_enabled(False)
        if self.status_bar:
            self.status_bar.set_status(f"Running {self.current_agent.name}…", "#c47b2a")

        inputs = self._collect_inputs()

        def on_status(msg):
            self.parent.after(0, lambda: self._set_status(msg, "#c47b2a"))

        def on_complete(result: AgentResult):
            self.parent.after(0, lambda: self._on_run_complete(result))

        self._engine.run_agent_async(
            self.current_agent, inputs, on_complete, on_status
        )

    def _on_run_complete(self, result: AgentResult):
        self._is_running = False
        self._has_run = True
        self._last_result = result
        self.run_btn.configure(state="normal")

        try:
            if result.success:
                self._set_status("Done", "#92817A")
                if self.status_bar:
                    self.status_bar.set_status(f"{self.current_agent.name}: Done", "#92817A")
            else:
                self._set_status("Error", "#f44336")
                if self.status_bar:
                    self.status_bar.set_status(f"Error running {self.current_agent.name}", "#f44336")

            # Populate output textbox with JSON only
            self.output_text.configure(state="normal")
            self.output_text.delete("1.0", "end")
            if result.outputs:
                self.output_text.insert("1.0", json.dumps(result.outputs, indent=2, default=str))
            elif result.error:
                self.output_text.insert("1.0", json.dumps({"error": result.error}, indent=2))
            self.output_text.configure(state="disabled")

            # Auto-expand outputs after a run
            if not self._output_expanded:
                self._toggle_outputs()

            # Collect violation locations for canvas linking
            self._violation_locations.clear()
            for tool_data in result.tool_results.values():
                try:
                    parsed = json.loads(tool_data)
                    if isinstance(parsed, list):
                        for item in parsed:
                            if isinstance(item, dict) and "location" in item:
                                self._violation_locations.add(item["location"])
                except (json.JSONDecodeError, TypeError):
                    continue

            # Show AI explanation in conversation panel
            explanation = result.explanation or result.error or "Agent run complete."
            self._append_agent_message(explanation)

            # Auto-load canvas from JSON input if available
            self._ensure_canvas_loaded()

            # Initialize conversation manager for follow-ups
            if self.current_agent.conversational:
                self._conversation = ConversationManager(self.current_agent, self._engine.client)
                system_prompt = PromptBuilder.build_system_prompt(
                    self.current_agent, result.tool_results
                )
                self._conversation.initialize(system_prompt, explanation, result.tool_results)
                self._set_chat_enabled(True)

            self._update_metrics(result)

        except Exception as e:
            self._set_status("Error", "#f44336")
            error_msg = f"Failed to process results: {e}"
            self.output_text.configure(state="normal")
            self.output_text.delete("1.0", "end")
            self.output_text.insert("1.0", json.dumps({"error": error_msg}, indent=2))
            self.output_text.configure(state="disabled")
            self._append_agent_message(f"[Error: {error_msg}]")
            if self.status_bar:
                self.status_bar.set_status(error_msg, "#f44336")

    def _update_metrics(self, result: AgentResult):
        if not self.status_bar:
            return
        for tool_name, tool_data in result.tool_results.items():
            try:
                parsed = json.loads(tool_data)
                if isinstance(parsed, list) and len(parsed) > 0:
                    sevs = {}
                    for item in parsed:
                        if isinstance(item, dict) and "severity" in item:
                            s = item["severity"]
                            sevs[s] = sevs.get(s, 0) + 1
                    if sevs:
                        parts = [f"{v} {k}" for k, v in sevs.items()]
                        self.status_bar.set_status(
                            f"{sum(sevs.values())} violations ({', '.join(parts)})",
                            "#f44336" if sevs.get("critical", 0) > 0 else "#c47b2a"
                        )
                        return
            except (json.JSONDecodeError, TypeError):
                continue

    def _send_message(self):
        if not self._has_run or self._is_running:
            return
        text = self.chat_input.get().strip()
        if not text:
            return
        # User text is consumed but NOT shown in the conversation panel
        self.chat_input.delete(0, "end")
        self._set_chat_enabled(False)
        self._set_status("Thinking…", "#c47b2a")

        if self._conversation and self._conversation.is_active:
            user_msg = text
            def _do_followup():
                try:
                    response = self._conversation.followup(user_msg)
                    self.parent.after(0, lambda: self._on_followup_complete(response))
                except Exception as e:
                    self.parent.after(0, lambda: self._on_followup_complete(f"[Error: {e}]"))
            threading.Thread(target=_do_followup, daemon=True).start()
        else:
            self._append_agent_message("Conversation not available for this agent.")
            self._set_chat_enabled(True)
            self._set_status("Done", "#92817A")

    def _on_followup_complete(self, response: str):
        try:
            self._append_agent_message(response)
        except Exception as e:
            self._append_agent_message(f"[Display error: {e}]")
        self._set_chat_enabled(True)
        self._set_status("Done", "#92817A")

    def _clear_chat(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")

    def _export_json(self):
        if not self._last_result:
            return
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=f"{self.current_agent.id}_results.json" if self.current_agent else "results.json",
            )
            if filepath:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(self._last_result.to_dict(), f, indent=2, default=str)
                if self.status_bar:
                    self.status_bar.set_status(f"Exported to {os.path.basename(filepath)}", "#92817A")
        except Exception as e:
            if self.status_bar:
                self.status_bar.set_status(f"Export failed: {e}", "#f44336")

    def _show_on_canvas(self):
        if not self.canvas_panel or not self._last_result:
            return
        try:
            plan_loaded = False
            for name, widget in self.input_widgets.items():
                value = widget.get().strip()
                if value and os.path.isfile(value) and value.endswith(".json"):
                    try:
                        plan = FloorPlan.load_from_json(value)
                        self.canvas_panel.load_plan(plan)
                        plan_loaded = True
                        break
                    except Exception:
                        pass

            violations = []
            for tool_name, tool_data in self._last_result.tool_results.items():
                try:
                    parsed = json.loads(tool_data)
                    if isinstance(parsed, list):
                        for item in parsed:
                            if isinstance(item, dict) and "severity" in item:
                                violations.append(Violation.from_dict(item))
                except (json.JSONDecodeError, TypeError):
                    continue

            if violations:
                self.canvas_panel.show_violations(violations)

            if not self.canvas_panel.visible:
                self.canvas_panel.toggle()
            if plan_loaded:
                self.canvas_panel.fit_to_window()
        except Exception as e:
            if self.status_bar:
                self.status_bar.set_status(f"Canvas error: {e}", "#f44336")

    def _browse_file(self, input_name: str):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath and input_name in self.input_widgets:
            self.input_widgets[input_name].delete(0, "end")
            self.input_widgets[input_name].insert(0, filepath)