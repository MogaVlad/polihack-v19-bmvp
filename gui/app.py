import os
import customtkinter as ctk

import config
from gui.agent_library import AgentLibrary
from gui.agent_runner import AgentRunnerTab
from gui.agent_builder import AgentBuilderTab
from gui.l2_console import L2ConsoleTab
from gui.adoption_panel import AdoptionPanel
from gui.canvas import CanvasPanel
from gui.controls import StatusBar
from models.floor_plan import FloorPlan


class App:
    def __init__(self):
        # ── Global CTk theming ──────────────────────────────────
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title(config.APP_TITLE)
        self.root.geometry("1280x820")
        self.root.minsize(960, 640)

        # Make the root use a deep navy background in dark mode
        self.root.configure(fg_color=("#f0f0f0", "#0e1117"))

        self._build_layout()

    # ────────────────────────────────────────────────────────────
    def _build_layout(self):
        # Grid: sidebar (col 0), main content (col 1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # ── Header bar ──────────────────────────────────────────
        header = ctk.CTkFrame(
            self.root,
            height=48,
            corner_radius=0,
            fg_color=("#ffffff", "#16213e"),
            border_width=0,
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)

        logo_label = ctk.CTkLabel(
            header,
            text="⚡ AgentForge",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=("#1a1a2e", "#4a9eff"),
        )
        logo_label.pack(side="left", padx=16, pady=8)

        subtitle = ctk.CTkLabel(
            header,
            text="Engineering Agent Platform",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray50", "#8899aa"),
        )
        subtitle.pack(side="left", padx=(0, 16), pady=8)

        # ── Sidebar toggle button ────────────────────────────────
        self.sidebar_visible = True
        self.sidebar_toggle_btn = ctk.CTkButton(
            header,
            text="☰",
            width=36,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            fg_color=("#dde4ee", "#0f3460"),
            hover_color=("#c8d0dd", "#1e4a8a"),
            text_color=("gray20", "#c0d0e0"),
            command=self._toggle_sidebar,
        )
        self.sidebar_toggle_btn.pack(side="left", padx=(4, 0), pady=8)

        # ── Sidebar ─────────────────────────────────────────────
        self.sidebar_frame = ctk.CTkFrame(
            self.root,
            width=260,
            corner_radius=0,
            fg_color=("#e8ecf1", "#16213e"),
            border_width=0,
        )
        self.sidebar_frame.grid(row=1, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        # ── Right content area ──────────────────────────────────
        right = ctk.CTkFrame(
            self.root,
            corner_radius=0,
            fg_color=("#f5f5f5", "#0e1117"),
            border_width=0,
        )
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)

        # Use an inner frame with pack so canvas + tabview don't conflict
        right_inner = ctk.CTkFrame(right, fg_color="transparent")
        right_inner.grid(row=0, column=0, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)

        # ── Tabview ─────────────────────────────────────────────
        self.tabview = ctk.CTkTabview(
            right_inner,
            corner_radius=10,
            fg_color=("#ffffff", "#1a1a2e"),
            segmented_button_fg_color=("#dde4ee", "#0f3460"),
            segmented_button_selected_color="#4a9eff",
            segmented_button_selected_hover_color="#3a89dd",
            segmented_button_unselected_color=("#c8d0dd", "#162d50"),
            segmented_button_unselected_hover_color=("#b0bccf", "#1e3a6a"),
            text_color=("gray10", "#e0e0e0"),
        )
        self.tabview.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # Create tabs
        self.tabview.add("Agent Runner")
        self.tabview.add("Agent Builder")
        self.tabview.add("L2 Console")
        self.tabview.add("L2 vs L3")
        self.tabview.set("Agent Runner")

        # Fix light-mode black rectangles: explicitly set each tab
        # frame's background to match the tabview's fg_color so that
        # transparent children don't inherit a dark default.
        for tab_name in ("Agent Runner", "Agent Builder", "L2 Console", "L2 vs L3"):
            self.tabview.tab(tab_name).configure(fg_color=("#ffffff", "#1a1a2e"))

        # ── Canvas panel (below tabs) ───────────────────────────
        self.canvas_panel = CanvasPanel(right_inner)

        # ── Status bar ──────────────────────────────────────────
        self.status_bar = StatusBar(self.root)
        self.status_bar.frame.grid(row=2, column=0, columnspan=2, sticky="ew")

        # ── Tab contents (created after status_bar/canvas so we can pass refs) ──
        self.runner_tab = AgentRunnerTab(
            self.tabview.tab("Agent Runner"),
            status_bar=self.status_bar,
            canvas_panel=self.canvas_panel,
        )
        self.builder_tab = AgentBuilderTab(
            self.tabview.tab("Agent Builder"),
            on_agent_saved=self._on_agent_saved,
            on_save_and_run=self._on_save_and_run,
        )
        self.l2_tab = L2ConsoleTab(self.tabview.tab("L2 Console"))
        self.adoption_tab = AdoptionPanel(self.tabview.tab("L2 vs L3"))

        # ── Agent library sidebar ───────────────────────────────
        self.agent_library = AgentLibrary(
            self.sidebar_frame,
            on_agent_selected=self._on_agent_selected,
            on_create_new=self._on_create_new,
        )

        self.status_bar.set_agent_count(len(self.agent_library.agents))

        from tools.registry import ToolRegistry
        self.status_bar.set_tool_count(len(ToolRegistry().list_tool_names()))

        # ── Keyboard shortcuts ──────────────────────────────────
        self.root.bind_all("<Control-n>", lambda e: self._on_create_new())
        self.root.bind_all("<Control-r>", lambda e: self.runner_tab._run_agent())
        self.root.bind_all("<Control-e>", lambda e: self.runner_tab._export_json())
        self.root.bind_all("<F5>", lambda e: self._refresh_library())

        # ── Pre-load example floor plan on canvas ───────────────
        self._preload_example_plan()

    # ── Callbacks ────────────────────────────────────────────────
    def _toggle_sidebar(self):
        """Collapse / expand the Agent Library sidebar."""
        if self.sidebar_visible:
            self.sidebar_frame.grid_remove()
            self.sidebar_toggle_btn.configure(text="☰")
            self.sidebar_visible = False
        else:
            self.sidebar_frame.grid()
            self.sidebar_toggle_btn.configure(text="✕")
            self.sidebar_visible = True

    def _on_agent_selected(self, agent_def):
        self.runner_tab.load_agent(agent_def)
        self.tabview.set("Agent Runner")
        self.status_bar.set_status(f"Loaded: {agent_def.name}", "#4a9eff")

    def _on_create_new(self):
        self.tabview.set("Agent Builder")
        self.builder_tab.reset_form()
        self.status_bar.set_status("Creating new agent…", "#ff9800")

    def _on_agent_saved(self):
        """Called after the Agent Builder successfully saves a new agent."""
        self.agent_library.refresh()
        self.status_bar.set_agent_count(len(self.agent_library.agents))
        self.status_bar.set_status("Agent saved ✓", "#4caf50")

    def _on_save_and_run(self, agent_def):
        """Called after Save & Run — refresh library, then load the agent in the Runner."""
        self._on_agent_saved()
        self._on_agent_selected(agent_def)
        self.status_bar.set_status(f"Agent '{agent_def.name}' saved and loaded", "#4caf50")

    def _refresh_library(self):
        self.agent_library.refresh()
        self.status_bar.set_agent_count(len(self.agent_library.agents))
        self.status_bar.set_status("Library refreshed", "#4a9eff")

    def _preload_example_plan(self):
        """Load the first example floor plan into the canvas on startup."""
        default = os.path.join(config.FLOOR_PLANS_DIR, "example_office.json")
        if os.path.isfile(default):
            try:
                plan = FloorPlan.load_from_json(default)
                self.canvas_panel.load_plan(plan)
            except Exception:
                pass

    def run(self):
        self.root.mainloop()
