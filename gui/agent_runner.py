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
        self.chat_display.tag_config("location", foreground="#4caf50", underline=True)
        self.chat_display.tag_bind("location", "<Button-1>", self._on_location_click)
        self.chat_display.tag_bind("location", "<Enter>",
                                   lambda e: self.chat_display.configure(cursor="hand2"))
        self.chat_display.tag_bind("location", "<Leave>",
                                   lambda e: self.chat_display.configure(cursor=""))

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
        """Insert text with flagged keywords and clickable location references."""
        spans = []
        for m in _FLAG_KEYWORDS.finditer(text):
            spans.append((m.start(), m.end(), "flagged"))
        for m in _LOCATION_PATTERN.finditer(text):
            loc_tag = f"loc_{m.group()}"
            self.chat_display.tag_config(loc_tag, foreground="#4caf50", underline=True)
            self.chat_display.tag_bind(loc_tag, "<Button-1>", self._on_location_click)
            self.chat_display.tag_bind(loc_tag, "<Enter>",
                                       lambda e: self.chat_display.configure(cursor="hand2"))
            self.chat_display.tag_bind(loc_tag, "<Leave>",
                                       lambda e: self.chat_display.configure(cursor=""))
            spans.append((m.start(), m.end(), loc_tag))

        spans.sort(key=lambda s: s[0])

        # Remove overlapping spans (keep first)
        merged = []
        for s in spans:
            if merged and s[0] < merged[-1][1]:
                continue
            merged.append(s)

        last_end = 0
        for start, end, tag in merged:
            if start > last_end:
                self.chat_display.insert("end", text[last_end:start], base_tag)
            self.chat_display.insert("end", text[start:end], tag)
            last_end = end
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

    def _on_location_click(self, event):
        """Handle click on a location reference in the chat — highlight it on canvas."""
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
        """Load floor plan into canvas from inputs if not already loaded."""
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

    # ── Actions ───────────────────────────────────────────────────
    def _view_definition(self):
        if not self.current_agent:
            return

        root = self.parent.winfo_toplevel()

        overlay = ctk.CTkFrame(root, fg_color=("gray20", "#000000"), corner_radius=0)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.configure(fg_color=("gray20", "gray14"))

        card = ctk.CTkFrame(overlay, fg_color=("gray96", "#1a1a2e"), corner_radius=14, width=580, height=520)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text=f"Definition: {self.current_agent.name}",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=("gray10", "#e0e0e0"),
        ).pack(side="left")

        ctk.CTkButton(
            header, text="✕", width=32, height=32, corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("gray78", "#2a2a3e"), hover_color=("gray68", "#3a3a50"),
            text_color=("gray10", "#ff6b6b"),
            command=overlay.destroy,
        ).pack(side="right")

        textbox = ctk.CTkTextbox(
            card, corner_radius=8,
            fg_color=("white", "#0e1117"),
            text_color=("gray10", "#c0d0e0"),
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
        )
        textbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        textbox.insert("1.0", json.dumps(self.current_agent.to_dict(), indent=2))
        textbox.configure(state="disabled")

        overlay.bind("<Button-1>", lambda e: overlay.destroy() if e.widget == overlay else None)
        overlay.lift()

    def _collect_inputs(self) -> dict:
        """Collect input values from widgets. For file paths, read file contents."""
        inputs = {}
        for name, widget in self.input_widgets.items():
            value = widget.get().strip()
            # If the value looks like a file path, try to read the file
            if value and os.path.isfile(value):
                try:
                    with open(value, "r", encoding="utf-8") as f:
                        value = f.read()
                except Exception:
                    pass  # keep raw value if read fails
            inputs[name] = value
        return inputs

    def _run_agent(self):
        """Run the agent via engine in a background thread."""
        if not self.current_agent or self._is_running:
            return

        self._is_running = True
        self._set_status("Running…", "#ff9800")
        self.run_btn.configure(state="disabled")
        self._set_chat_enabled(False)
        if self.status_bar:
            self.status_bar.set_status(f"Running {self.current_agent.name}…", "#ff9800")

        inputs = self._collect_inputs()

        def on_status(msg):
            # Schedule UI update on main thread
            self.parent.after(0, lambda: self._set_status(msg, "#ff9800"))

        def on_complete(result: AgentResult):
            # Schedule UI update on main thread
            self.parent.after(0, lambda: self._on_run_complete(result))

        self._engine.run_agent_async(
            self.current_agent, inputs, on_complete, on_status
        )

    def _on_run_complete(self, result: AgentResult):
        """Handle agent run completion on the main thread."""
        self._is_running = False
        self._has_run = True
        self._last_result = result
        self.run_btn.configure(state="normal")

        try:
            if result.success:
                self._set_status("Done", "#4caf50")
                if self.status_bar:
                    self.status_bar.set_status(f"{self.current_agent.name}: Done", "#4caf50")
            else:
                self._set_status("Error", "#f44336")
                if self.status_bar:
                    self.status_bar.set_status(f"Error running {self.current_agent.name}", "#f44336")

            # Display structured output
            self.output_text.configure(state="normal")
            self.output_text.delete("1.0", "end")
            if result.outputs:
                self.output_text.insert("1.0", json.dumps(result.outputs, indent=2, default=str))
            elif result.error:
                self.output_text.insert("1.0", f"Error: {result.error}")
            self.output_text.configure(state="disabled")

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

            # Show initial agent message in chat
            explanation = result.explanation or result.error or "Agent run complete."
            self._append_agent_message(explanation)

            # Initialize conversation manager for follow-ups
            if self.current_agent.conversational:
                self._conversation = ConversationManager(self.current_agent, self._engine.client)
                system_prompt = PromptBuilder.build_system_prompt(
                    self.current_agent, result.tool_results
                )
                self._conversation.initialize(system_prompt, explanation, result.tool_results)
                self._set_chat_enabled(True)

            # Update metrics in status bar if available
            self._update_metrics(result)

        except Exception as e:
            self._set_status("Error", "#f44336")
            error_msg = f"Failed to process results: {e}"
            self.output_text.configure(state="normal")
            self.output_text.delete("1.0", "end")
            self.output_text.insert("1.0", error_msg)
            self.output_text.configure(state="disabled")
            self._append_agent_message(f"[Error: {error_msg}]")
            if self.status_bar:
                self.status_bar.set_status(error_msg, "#f44336")

    def _update_metrics(self, result: AgentResult):
        """Show violation metrics in status bar if tool results contain them."""
        if not self.status_bar:
            return
        for tool_name, tool_data in result.tool_results.items():
            try:
                parsed = json.loads(tool_data)
                if isinstance(parsed, list) and len(parsed) > 0:
                    # Count violations by severity
                    sevs = {}
                    for item in parsed:
                        if isinstance(item, dict) and "severity" in item:
                            s = item["severity"]
                            sevs[s] = sevs.get(s, 0) + 1
                    if sevs:
                        parts = [f"{v} {k}" for k, v in sevs.items()]
                        self.status_bar.set_status(
                            f"{sum(sevs.values())} violations ({', '.join(parts)})",
                            "#f44336" if sevs.get("critical", 0) > 0 else "#ff9800"
                        )
                        return
            except (json.JSONDecodeError, TypeError):
                continue

    def _send_message(self):
        """Send a follow-up message via ConversationManager."""
        if not self._has_run or self._is_running:
            return
        text = self.chat_input.get().strip()
        if not text:
            return
        self._append_user_message(text)
        self.chat_input.delete(0, "end")
        self._set_chat_enabled(False)
        self._set_status("Thinking…", "#ff9800")

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
            self._set_status("Done", "#4caf50")

    def _on_followup_complete(self, response: str):
        """Handle followup response on main thread."""
        try:
            self._append_agent_message(response)
        except Exception as e:
            self._append_agent_message(f"[Display error: {e}]")
        self._set_chat_enabled(True)
        self._set_status("Done", "#4caf50")

    def _clear_chat(self):
        """Clear all messages from the conversation panel."""
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")

    def _export_json(self):
        """Export agent results as JSON via file save dialog."""
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
                    self.status_bar.set_status(f"Exported to {os.path.basename(filepath)}", "#4caf50")
        except Exception as e:
            if self.status_bar:
                self.status_bar.set_status(f"Export failed: {e}", "#f44336")

    def _show_on_canvas(self):
        """Push floor plan and violations to the canvas panel."""
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
