import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, List

import config
from models.agent_definition import AgentDefinition


class AgentLibrary:
    def __init__(
        self,
        parent: ttk.Frame,
        on_agent_selected: Callable,
        on_create_new: Callable,
    ):
        self.parent = parent
        self.on_agent_selected = on_agent_selected
        self.on_create_new = on_create_new
        self.agents: List[AgentDefinition] = []

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        title = ttk.Label(
            self.parent,
            text="AGENT LIBRARY",
            style="SidebarTitle.TLabel",
        )
        title.pack(padx=10, pady=(10, 5), anchor="w")

        search_frame = ttk.Frame(self.parent, style="Sidebar.TFrame")
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_agents())
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg="#3c3c3c",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
        )
        self.search_entry.pack(fill=tk.X)
        self.search_entry.insert(0, "Search...")
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)

        list_frame = ttk.Frame(self.parent, style="Sidebar.TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.agent_listbox = tk.Listbox(
            list_frame,
            bg="#2b2b2b",
            fg="#ffffff",
            selectbackground="#4a6fa5",
            selectforeground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
            activestyle="none",
            borderwidth=0,
        )
        self.agent_listbox.pack(fill=tk.BOTH, expand=True)
        self.agent_listbox.bind("<<ListboxSelect>>", self._on_select)

        create_btn = tk.Button(
            self.parent,
            text="+ Create New Agent",
            bg="#4a6fa5",
            fg="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            command=self.on_create_new,
        )
        create_btn.pack(fill=tk.X, padx=10, pady=10)

    def _on_search_focus_in(self, event):
        if self.search_entry.get() == "Search...":
            self.search_entry.delete(0, tk.END)

    def _on_search_focus_out(self, event):
        if not self.search_entry.get():
            self.search_entry.insert(0, "Search...")

    def refresh(self):
        self.agents = []
        self.agents.extend(AgentDefinition.load_all_from_directory(config.AGENTS_DIR))
        self.agents.extend(AgentDefinition.load_all_from_directory(config.USER_AGENTS_DIR))
        self._render_list(self.agents)

    def _render_list(self, agents: List[AgentDefinition]):
        self.agent_listbox.delete(0, tk.END)
        current_category = None
        self._display_agents = []

        for agent in agents:
            if agent.category != current_category:
                current_category = agent.category
                self.agent_listbox.insert(tk.END, f"  {current_category}")
                self.agent_listbox.itemconfig(tk.END, fg="#888888", selectbackground="#2b2b2b")
                self._display_agents.append(None)

            self.agent_listbox.insert(tk.END, f"    {agent.name}")
            self._display_agents.append(agent)

    def _filter_agents(self):
        query = self.search_var.get().lower()
        if query == "search..." or not query:
            self._render_list(self.agents)
            return
        filtered = [
            a for a in self.agents
            if query in a.name.lower() or query in a.goal.lower()
        ]
        self._render_list(filtered)

    def _on_select(self, event):
        selection = self.agent_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx < len(self._display_agents):
            agent = self._display_agents[idx]
            if agent is not None:
                self.on_agent_selected(agent)
