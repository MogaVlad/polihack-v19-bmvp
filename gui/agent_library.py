import customtkinter as ctk
from typing import Callable, List, Optional

import config
from models.agent_definition import AgentDefinition


class AgentLibrary:
    def __init__(
        self,
        parent: ctk.CTkFrame,
        on_agent_selected: Callable,
        on_create_new: Callable,
    ):
        self.parent = parent
        self.on_agent_selected = on_agent_selected
        self.on_create_new = on_create_new
        self.agents: List[AgentDefinition] = []
        self._agent_buttons: List[tuple] = []  # (button, agent_def)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # ── Title ───────────────────────────────────────────────
        title_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        title_frame.pack(fill="x", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            title_frame,
            text="🗂  AGENT LIBRARY",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=("#543520", "#F1DABF"),
        ).pack(anchor="w")

        # ── Search ──────────────────────────────────────────────
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_agents())

        self.search_entry = ctk.CTkEntry(
            self.parent,
            placeholder_text="Search agents…",
            textvariable=self.search_var,
            height=32,
            corner_radius=8,
            border_width=1,
            fg_color=("#e5e5e5", "#2d1a0e"),
            border_color=("#543520", "#5c4a3a"),
            text_color=("#543520", "#F1DABF"),
            placeholder_text_color=("#92817A", "#92817A"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.search_entry.pack(fill="x", padx=16, pady=(8, 12))

        # ── Scrollable agent list ───────────────────────────────
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
            scrollbar_button_color=("#543520", "#92817A"),
            scrollbar_button_hover_color=("#6b4428", "#7a6a60"),
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=8, pady=0)

        # ── Create button ──────────────────────────────────────
        self.create_btn = ctk.CTkButton(
            self.parent,
            text="＋  Create New Agent",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=38,
            corner_radius=8,
            fg_color="#92817A",
            hover_color="#7a6a60",
            text_color="#ffffff",
            command=self.on_create_new,
        )
        self.create_btn.pack(fill="x", padx=16, pady=(8, 16))

    def refresh(self):
        self.agents = []
        self.agents.extend(AgentDefinition.load_all_from_directory(config.AGENTS_DIR))
        self.agents.extend(AgentDefinition.load_all_from_directory(config.USER_AGENTS_DIR))
        self._render_list(self.agents)

    def _render_list(self, agents: List[AgentDefinition]):
        # Clear existing
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self._agent_buttons.clear()

        current_category = None

        for agent in agents:
            # Category header
            if agent.category != current_category:
                current_category = agent.category

                if current_category is not None:
                    # spacer
                    ctk.CTkFrame(self.scroll_frame, height=8, fg_color="transparent").pack(fill="x")

                cat_label = ctk.CTkLabel(
                    self.scroll_frame,
                    text=f"  {current_category.upper()}",
                    font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                    text_color=("#92817A", "#92817A"),
                    anchor="w",
                )
                cat_label.pack(fill="x", padx=8, pady=(6, 2))

            # Agent card — frame with status dot + button
            card_frame = ctk.CTkFrame(
                self.scroll_frame,
                fg_color="transparent",
                height=36,
            )
            card_frame.pack(fill="x", padx=4, pady=1)

            # Status dot: green for pre-built, blue for user agents
            dot_color = "#92817A" if getattr(agent, "category", None) == "Custom" else "#92817A"
            ctk.CTkLabel(
                card_frame,
                text="●",
                font=ctk.CTkFont(size=8),
                text_color=dot_color,
                width=14,
            ).pack(side="left", padx=(4, 0))

            card = ctk.CTkButton(
                card_frame,
                text=agent.name,
                anchor="w",
                height=34,
                corner_radius=6,
                fg_color="transparent",
                hover_color=("#d4b896", "#2d1a0e"),
                text_color=("#e7d5a5", "#d0d8e8"),
                font=ctk.CTkFont(family="Segoe UI", size=12),
                command=lambda a=agent: self.on_agent_selected(a),
            )
            card.pack(side="left", fill="x", expand=True)
            self._agent_buttons.append((card, agent))

    def _filter_agents(self):
        query = self.search_var.get().lower().strip()
        if not query:
            self._render_list(self.agents)
            return
        filtered = [
            a for a in self.agents
            if query in a.name.lower() or query in a.goal.lower()
        ]
        self._render_list(filtered)