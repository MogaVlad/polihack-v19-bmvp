import tkinter as tk
import customtkinter as ctk
from typing import Optional

from models.agent_definition import AgentDefinition


class AgentRunnerTab:
    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        self.current_agent: Optional[AgentDefinition] = None
        self._build_ui()

    # ── Helpers ──────────────────────────────────────────────────
    def _section_header(self, parent, text: str):
        """Create a styled section header label."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(
            frame,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("gray40", "#667788"),
        ).pack(side="left")
        # Separator line
        sep = ctk.CTkFrame(frame, height=1, fg_color=("gray80", "#2a3f60"))
        sep.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=1)
        return frame

    # ── Build UI ─────────────────────────────────────────────────
    def _build_ui(self):
        wrapper = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
            scrollbar_button_color=("#bbb", "#2a3f60"),
        )
        wrapper.pack(fill="both", expand=True, padx=4, pady=4)

        # ── Header ──────────────────────────────────────────────
        header = ctk.CTkFrame(wrapper, fg_color=("gray92", "#162d50"), corner_radius=10)
        header.pack(fill="x", padx=8, pady=(4, 8))

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=16, pady=12)

        self.agent_name_label = ctk.CTkLabel(
            header_inner,
            text="No agent loaded",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=("gray15", "#e0e0e0"),
        )
        self.agent_name_label.pack(anchor="w")

        self.agent_goal_label = ctk.CTkLabel(
            header_inner,
            text="Select an agent from the library to begin.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray50", "#8899aa"),
        )
        self.agent_goal_label.pack(anchor="w", pady=(2, 0))

        self.view_def_btn = ctk.CTkButton(
            header_inner,
            text="View Definition",
            width=130,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("gray78", "#0f3460"),
            hover_color=("gray68", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"),
            command=self._view_definition,
        )
        self.view_def_btn.pack(anchor="e", pady=(4, 0))

        # ── I/O Section ─────────────────────────────────────────
        io_frame = ctk.CTkFrame(wrapper, fg_color="transparent")
        io_frame.pack(fill="both", expand=True, padx=8, pady=4)
        io_frame.grid_columnconfigure(0, weight=1)
        io_frame.grid_columnconfigure(1, weight=1)
        io_frame.grid_rowconfigure(0, weight=1)

        # Inputs
        input_card = ctk.CTkFrame(io_frame, fg_color=("gray92", "#162d50"), corner_radius=10)
        input_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=0)

        self._section_header(input_card, "INPUTS").pack(fill="x", padx=12, pady=(12, 6))

        self.inputs_container = ctk.CTkFrame(input_card, fg_color="transparent")
        self.inputs_container.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.input_widgets = {}

        self.run_btn = ctk.CTkButton(
            input_card,
            text="▶  Run Agent",
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#4a9eff",
            hover_color="#3a89dd",
            text_color="#ffffff",
            command=self._run_agent,
        )
        self.run_btn.pack(padx=12, pady=(4, 14))

        # Outputs
        output_card = ctk.CTkFrame(io_frame, fg_color=("gray92", "#162d50"), corner_radius=10)
        output_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=0)

        self._section_header(output_card, "OUTPUTS").pack(fill="x", padx=12, pady=(12, 6))

        self.output_text = ctk.CTkTextbox(
            output_card,
            height=120,
            corner_radius=8,
            fg_color=("gray96", "#0e1117"),
            text_color=("gray10", "#c0d0e0"),
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled",
            wrap="word",
        )
        self.output_text.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        export_frame = ctk.CTkFrame(output_card, fg_color="transparent")
        export_frame.pack(fill="x", padx=12, pady=(0, 14))

        ctk.CTkButton(
            export_frame, text="Export JSON", width=110, height=28, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("gray78", "#0f3460"), hover_color=("gray68", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"), command=self._export_json,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            export_frame, text="Show on Canvas", width=120, height=28, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("gray78", "#0f3460"), hover_color=("gray68", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"), command=self._show_on_canvas,
        ).pack(side="left")

        # ── Conversation ────────────────────────────────────────
        chat_card = ctk.CTkFrame(wrapper, fg_color=("gray92", "#162d50"), corner_radius=10)
        chat_card.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        self._section_header(chat_card, "CONVERSATION").pack(fill="x", padx=12, pady=(12, 6))

        self.chat_display = ctk.CTkTextbox(
            chat_card,
            height=100,
            corner_radius=8,
            fg_color=("gray96", "#0e1117"),
            text_color=("gray10", "#c0d0e0"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            state="disabled",
            wrap="word",
        )
        self.chat_display.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # Tag colours for chat messages
        self.chat_display.tag_config("agent", foreground="#4a9eff")
        self.chat_display.tag_config("user", foreground="#e0e0e0")

        msg_frame = ctk.CTkFrame(chat_card, fg_color="transparent")
        msg_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.chat_input = ctk.CTkEntry(
            msg_frame,
            placeholder_text="Type a follow-up question…",
            height=34,
            corner_radius=8,
            fg_color=("gray96", "#0e1117"),
            border_color=("gray75", "#2a3f60"),
            text_color=("gray10", "#e0e0e0"),
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
            fg_color="#4a9eff",
            hover_color="#3a89dd",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._send_message,
        )
        self.send_btn.pack(side="right")

    # ── Agent loading ────────────────────────────────────────────
    def load_agent(self, agent_def: AgentDefinition):
        self.current_agent = agent_def
        self.agent_name_label.configure(text=f"⚙  {agent_def.name}")
        self.agent_goal_label.configure(text=agent_def.goal)

        # Clear inputs
        for widget in self.inputs_container.winfo_children():
            widget.destroy()
        self.input_widgets.clear()

        for inp in agent_def.inputs:
            row = ctk.CTkFrame(self.inputs_container, fg_color="transparent")
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(
                row, text=f"{inp.name}:", width=100, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=("gray30", "#8899aa"),
            ).pack(side="left")

            if inp.type in ("json", "text"):
                entry = ctk.CTkEntry(
                    row, height=30, corner_radius=6,
                    fg_color=("gray96", "#0e1117"),
                    border_color=("gray75", "#2a3f60"),
                    text_color=("gray10", "#e0e0e0"),
                    font=ctk.CTkFont(size=11),
                )
                entry.pack(side="left", fill="x", expand=True)
                self.input_widgets[inp.name] = entry
            elif inp.type == "image":
                entry = ctk.CTkEntry(
                    row, height=30, corner_radius=6,
                    fg_color=("gray96", "#0e1117"),
                    border_color=("gray75", "#2a3f60"),
                    text_color=("gray10", "#e0e0e0"),
                    font=ctk.CTkFont(size=11),
                )
                entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

                ctk.CTkButton(
                    row, text="Browse…", width=80, height=28, corner_radius=6,
                    font=ctk.CTkFont(size=11),
                    fg_color=("gray78", "#0f3460"), hover_color=("gray68", "#1e4a8a"),
                    command=lambda n=inp.name: self._browse_file(n),
                ).pack(side="right")

                self.input_widgets[inp.name] = entry

        # Clear outputs
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

        # Clear chat
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        self.chat_input.configure(state="disabled")

    # ── Actions (stubs for Phase 2 wiring) ───────────────────────
    def _view_definition(self):
        if not self.current_agent:
            return
        import json

        win = ctk.CTkToplevel()
        win.title(f"Definition: {self.current_agent.name}")
        win.geometry("540x620")

        textbox = ctk.CTkTextbox(
            win, corner_radius=8,
            fg_color=("gray96", "#0e1117"),
            text_color=("gray10", "#c0d0e0"),
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
        )
        textbox.pack(fill="both", expand=True, padx=16, pady=16)
        textbox.insert("1.0", json.dumps(self.current_agent.to_dict(), indent=2))
        textbox.configure(state="disabled")

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
            self.input_widgets[input_name].delete(0, "end")
            self.input_widgets[input_name].insert(0, filepath)
