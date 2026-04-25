import tkinter as tk
from tkinter import ttk

import config
from gui.agent_library import AgentLibrary
from gui.agent_runner import AgentRunnerTab
from gui.agent_builder import AgentBuilderTab
from gui.l2_console import L2ConsoleTab
from gui.adoption_panel import AdoptionPanel
from gui.canvas import CanvasPanel
from gui.controls import StatusBar


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(config.APP_TITLE)
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        self._setup_styles()
        self._build_layout()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Sidebar.TFrame", background="#2b2b2b")
        style.configure(
            "Sidebar.TLabel",
            background="#2b2b2b",
            foreground="#ffffff",
            font=("Segoe UI", 10),
        )
        style.configure(
            "SidebarTitle.TLabel",
            background="#2b2b2b",
            foreground="#ffffff",
            font=("Segoe UI", 12, "bold"),
        )
        style.configure("Content.TFrame", background="#f5f5f5")

    def _build_layout(self):
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        self.sidebar_frame = ttk.Frame(main_pane, style="Sidebar.TFrame", width=250)
        main_pane.add(self.sidebar_frame, weight=0)

        right_container = ttk.Frame(main_pane, style="Content.TFrame")
        main_pane.add(right_container, weight=1)

        self.notebook = ttk.Notebook(right_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.runner_tab = AgentRunnerTab(self.notebook)
        self.notebook.add(self.runner_tab.frame, text="Agent Runner")

        self.builder_tab = AgentBuilderTab(self.notebook)
        self.notebook.add(self.builder_tab.frame, text="Agent Builder")

        self.l2_tab = L2ConsoleTab(self.notebook)
        self.notebook.add(self.l2_tab.frame, text="L2 Console")

        self.adoption_tab = AdoptionPanel(self.notebook)
        self.notebook.add(self.adoption_tab.frame, text="L2 vs L3")

        self.canvas_panel = CanvasPanel(right_container)

        self.status_bar = StatusBar(self.root)
        self.status_bar.frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.agent_library = AgentLibrary(
            self.sidebar_frame,
            on_agent_selected=self._on_agent_selected,
            on_create_new=self._on_create_new,
        )

    def _on_agent_selected(self, agent_def):
        self.runner_tab.load_agent(agent_def)
        self.notebook.select(0)
        self.status_bar.set_status(f"Loaded agent: {agent_def.name}")

    def _on_create_new(self):
        self.notebook.select(1)
        self.builder_tab.reset_form()
        self.status_bar.set_status("Creating new agent...")

    def run(self):
        self.root.mainloop()
