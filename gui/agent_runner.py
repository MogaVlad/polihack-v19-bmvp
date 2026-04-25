import tkinter as tk
import customtkinter as ctk
from typing import Optional
import re

from models.agent_definition import AgentDefinition


# Keywords that indicate flagged issues in agent responses
_FLAG_KEYWORDS = re.compile(
    r"\b(violation|warning|exceeded|insufficient|blocked|narrow|missing|"
    r"non-compliant|critical|fail|danger|unsafe|risk|dead.?end)\b",
    re.IGNORECASE,
)


class AgentRunnerTab:
    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        self.current_agent: Optional[AgentDefinition] = None
        self._has_run = False  # track whether the agent has been run at least once
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

        # Top row: agent name + status indicator
        top_row = ctk.CTkFrame(header_inner, fg_color="transparent")
        top_row.pack(fill="x")

        self.agent_name_label = ctk.CTkLabel(
            top_row,
            text="No agent loaded",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=("gray15", "#e0e0e0"),
        )
        self.agent_name_label.pack(side="left")

        self.status_indicator = ctk.CTkLabel(
            top_row,
            text="● Ready",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("gray50", "#667788"),
        )
        self.status_indicator.pack(side="right")

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

        # Conversation header with Clear Chat button
        chat_header_frame = ctk.CTkFrame(chat_card, fg_color="transparent")
        chat_header_frame.pack(fill="x", padx=12, pady=(12, 6))

        self._section_header(chat_header_frame, "CONVERSATION").pack(side="left", fill="x", expand=True)

        self.clear_chat_btn = ctk.CTkButton(
            chat_header_frame,
            text="Clear Chat",
            width=90,
            height=24,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color=("gray78", "#0f3460"),
            hover_color=("gray68", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"),
            command=self._clear_chat,
        )
        self.clear_chat_btn.pack(side="right", padx=(8, 0))

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

        # Configure tag colours for chat messages
        # Note: CTkTextbox forbids 'font' in tag_config due to scaling
        self.chat_display.tag_config("agent_label", foreground="#4a9eff")
        self.chat_display.tag_config("agent", foreground="#4a9eff")
        self.chat_display.tag_config("user_label", foreground="#e8b84d")
        self.chat_display.tag_config("user", foreground="#e0e0e0")
        self.chat_display.tag_config("flagged", foreground="#ff6b6b")
        self.chat_display.tag_config("timestamp", foreground="#555555")

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
            state="disabled",
        )
        self.send_btn.pack(side="right")

        # ── Constraints + Tools footer ──────────────────────────
        footer_frame = ctk.CTkFrame(wrapper, fg_color="transparent")
        footer_frame.pack(fill="x", padx=8, pady=(4, 8))
        footer_frame.grid_columnconfigure(0, weight=1)
        footer_frame.grid_columnconfigure(1, weight=1)

        constraints_card = ctk.CTkFrame(footer_frame, fg_color=("gray92", "#162d50"), corner_radius=10)
        constraints_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self._section_header(constraints_card, "CONSTRAINTS USED").pack(fill="x", padx=12, pady=(10, 4))
        self.constraints_label = ctk.CTkLabel(
            constraints_card,
            text="—",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("gray40", "#8899aa"),
            wraplength=350,
            justify="left",
            anchor="nw",
        )
        self.constraints_label.pack(fill="x", padx=14, pady=(0, 10))

        tools_card = ctk.CTkFrame(footer_frame, fg_color=("gray92", "#162d50"), corner_radius=10)
        tools_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self._section_header(tools_card, "TOOLS USED").pack(fill="x", padx=12, pady=(10, 4))
        self.tools_label = ctk.CTkLabel(
            tools_card,
            text="—",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("gray40", "#8899aa"),
            wraplength=350,
            justify="left",
            anchor="nw",
        )
        self.tools_label.pack(fill="x", padx=14, pady=(0, 10))

    # ── Chat message helpers ─────────────────────────────────────
    def _append_agent_message(self, text: str):
        """Append an agent message to the chat display with formatting."""
        self.chat_display.configure(state="normal")
        # Add spacing if not the first message
        if self.chat_display.get("1.0", "end").strip():
            self.chat_display.insert("end", "\n\n")
        self.chat_display.insert("end", "Agent: ", "agent_label")
        # Insert text with flagged-issue highlighting
        self._insert_with_highlights(text, "agent")
        self.chat_display.configure(state="disabled")
        self._auto_scroll()

    def _append_user_message(self, text: str):
        """Append a user message to the chat display with formatting."""
        self.chat_display.configure(state="normal")
        if self.chat_display.get("1.0", "end").strip():
            self.chat_display.insert("end", "\n\n")
        self.chat_display.insert("end", "You: ", "user_label")
        self.chat_display.insert("end", text, "user")
        self.chat_display.configure(state="disabled")
        self._auto_scroll()

    def _insert_with_highlights(self, text: str, base_tag: str):
        """Insert text, highlighting flagged keywords with a distinct color."""
        last_end = 0
        for match in _FLAG_KEYWORDS.finditer(text):
            # Insert normal text before the match
            if match.start() > last_end:
                self.chat_display.insert("end", text[last_end:match.start()], base_tag)
            # Insert the flagged keyword
            self.chat_display.insert("end", match.group(), "flagged")
            last_end = match.end()
        # Insert remaining text
        if last_end < len(text):
            self.chat_display.insert("end", text[last_end:], base_tag)

    def _auto_scroll(self):
        """Scroll the chat display to the bottom."""
        self.chat_display.see("end")

    def _set_chat_enabled(self, enabled: bool):
        """Enable or disable the chat input and send button."""
        state = "normal" if enabled else "disabled"
        self.chat_input.configure(state=state)
        self.send_btn.configure(state=state)

    def _set_status(self, text: str, color: str = "#667788"):
        """Update the status indicator in the header."""
        self.status_indicator.configure(text=f"● {text}", text_color=("gray50", color))

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

        # Clear chat and disable input
        self._clear_chat()
        self._set_chat_enabled(False)

        # Update constraints & tools footer
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
        """Stub — Phase 2 will wire this to engine/runner.py.
        For now, simulate a successful run to demonstrate UI flow."""
        if not self.current_agent:
            return

        self._set_status("Running…", "#ff9800")
        self.run_btn.configure(state="disabled")

        # Simulate completion (Phase 2 will replace with threaded engine call)
        self._has_run = True
        self._set_status("Done", "#4caf50")
        self.run_btn.configure(state="normal")
        self._set_chat_enabled(True)

        # Show a placeholder message in chat
        self._append_agent_message(
            f"Analysis complete for agent \"{self.current_agent.name}\". "
            f"You can ask follow-up questions about the results."
        )

    def _send_message(self):
        """Send a user message in the conversation panel."""
        if not self._has_run:
            return
        text = self.chat_input.get().strip()
        if not text:
            return
        self._append_user_message(text)
        self.chat_input.delete(0, "end")

        # Stub: echo acknowledgement (Phase 2 will call conversation.followup())
        self._append_agent_message(
            f"Thank you for your question. I'll process that with the "
            f"{self.current_agent.name} context. (Engine not yet wired.)"
        )

    def _clear_chat(self):
        """Clear all messages from the conversation panel."""
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")

    def _export_json(self):
        """Export agent results as JSON. Stub for Phase 2."""
        pass

    def _show_on_canvas(self):
        """Push results to canvas. Stub for Phase 2."""
        pass

    def _browse_file(self, input_name: str):
        from tkinter import filedialog
        filepath = filedialog.askopenfilename()
        if filepath and input_name in self.input_widgets:
            self.input_widgets[input_name].delete(0, "end")
            self.input_widgets[input_name].insert(0, filepath)
