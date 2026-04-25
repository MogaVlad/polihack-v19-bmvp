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

        # Deep background
        self.root.configure(fg_color=("#98a3b3", "#4c5767"))

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
            fg_color=("#384c46", "#b3c7c1"),
            border_width=0,
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)

        logo_label = ctk.CTkLabel(
            header,
            text="⚡ AgentArchitect",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=("#98a3b3", "#4c5767"),
        )
        logo_label.pack(side="left", padx=16, pady=8)

        subtitle = ctk.CTkLabel(
            header,
            text="Engineering Agent Platform",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#f6f8f8", "#070909"),
        )
        subtitle.pack(side="left", padx=(0, 16), pady=8)

        # Toggle button is now part of the sidebar, removed from header.

        # ── Sidebar ─────────────────────────────────────────────
        self.sidebar_visible = True
        self.current_sidebar_width = 260
        self.sidebar_frame = ctk.CTkFrame(
            self.root,
            width=self.current_sidebar_width,
            corner_radius=0,
            fg_color=("#f6f8f8", "#070909"),
            border_width=0,
        )
        self.sidebar_frame.grid(row=1, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        # Inner container for the library so it doesn't squish during animation
        self.sidebar_content = ctk.CTkFrame(
            self.sidebar_frame,
            width=260,
            fg_color=("#f6f8f8", "#070909"),
        )
        self.sidebar_content.place(x=0, y=0, relheight=1.0)

        # ── Right content area ──────────────────────────────────
        self.right = ctk.CTkFrame(
            self.root,
            corner_radius=0,
            fg_color=("#f6f8f8", "#070909"),
            border_width=0,
        )
        self.right.grid(row=1, column=1, sticky="nsew")
        self.right.grid_columnconfigure(0, weight=1)

        # Use an inner frame with pack so canvas + tabview don't conflict
        right_inner = ctk.CTkFrame(self.right, fg_color=("#f6f8f8", "#070909"))
        right_inner.grid(row=0, column=0, sticky="nsew")
        self.right.grid_rowconfigure(0, weight=1)

        # ── Tabview ─────────────────────────────────────────────
        self.tabview = ctk.CTkTabview(
            right_inner,
            corner_radius=10,
            fg_color=("#98a3b3", "#4c5767"),
            segmented_button_fg_color=("#f6f8f8", "#070909"),
            segmented_button_selected_color="#384c46",
            segmented_button_selected_hover_color="#2a3a34",
            segmented_button_unselected_color=("#b3c7c1", "#3a4854"),
            segmented_button_unselected_hover_color=("#a0b5af", "#3a4854"),
            text_color=("#121715", "#e8edeb"),
            command=self._on_tab_changed,
        )
        # Increased padding to push tabs away from the sidebar edge
        self.tabview.pack(fill="both", expand=True, padx=24, pady=(16, 8))

        # Create tabs — L2 Console and L2 vs L3 are now sidebar buttons
        self.tabview.add("Agent Runner")
        self.tabview.add("Agent Builder")
        self.tabview.add("Legacy Prompting")
        self.tabview.add("Legacy to Agent Showcase")
        self.tabview.set("Agent Runner")
        self._on_tab_changed()

        # Fix light-mode black rectangles: explicitly set each tab
        # frame's background to match the tabview's fg_color so that
        # transparent children don't inherit a dark default.
        for tab_name in ("Agent Runner", "Agent Builder", "Legacy Prompting", "Legacy to Agent Showcase"):
            self.tabview.tab(tab_name).configure(fg_color=("#98a3b3", "#4c5767"))

        # ── Center the tab button bar ────────────────────────────
        def _center_tabs():
            seg = self.tabview._segmented_button
            seg.place_forget()
            seg.place(relx=0.5, y=8, anchor="n")
        self.tabview.after(100, _center_tabs)

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
        self.l2_tab = L2ConsoleTab(self.tabview.tab("Legacy Prompting"))
        self.adoption_tab = AdoptionPanel(self.tabview.tab("Legacy to Agent Showcase"))

        # ── Agent library sidebar ───────────────────────────────
        self.agent_library = AgentLibrary(
            self.sidebar_content,
            on_agent_selected=self._on_agent_selected,
            on_create_new=self._on_create_new,
        )

        self.status_bar.set_agent_count(len(self.agent_library.agents))

        from tools.registry import ToolRegistry
        self.status_bar.set_tool_count(len(ToolRegistry().list_tool_names()))

        # ── Sidebar navigation buttons ──────────────────────────
        nav_frame = ctk.CTkFrame(self.sidebar_content, fg_color="transparent")
        nav_frame.pack(fill="x", padx=16, pady=(4, 8), side="bottom")

        ctk.CTkButton(
            nav_frame,
            text="📜 Legacy Prompting",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=34,
            corner_radius=8,
            fg_color=("#384c46", "#4c5767"),
            hover_color=("#2a3a34", "#3a4854"),
            text_color=("#f6f8f8", "#e8edeb"),
            command=lambda: self.tabview.set("Legacy Prompting"),
        ).pack(fill="x", pady=(0, 6))

        ctk.CTkButton(
            nav_frame,
            text="📊 Legacy to Agent Showcase",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=34,
            corner_radius=8,
            fg_color=("#384c46", "#4c5767"),
            hover_color=("#2a3a34", "#3a4854"),
            text_color=("#f6f8f8", "#e8edeb"),
            command=lambda: self.tabview.set("Legacy to Agent Showcase"),
        ).pack(fill="x", pady=(0, 0))

        # ── Keyboard shortcuts ──────────────────────────────────
        self.root.bind_all("<Control-n>", lambda e: self._on_create_new())
        self.root.bind_all("<Control-s>", lambda e: self.builder_tab._save_agent())
        self.root.bind_all("<Control-q>", lambda e: self.root.quit())
        self.root.bind_all("<Control-r>", lambda e: self.runner_tab._run_agent())
        self.root.bind_all("<Control-e>", lambda e: self.runner_tab._export_json())
        self.root.bind_all("<F5>", lambda e: self._refresh_library())

    def _on_tab_changed(self):
        """Dynamically update text colors for the selected tab."""
        current_tab = self.tabview.get()
        if hasattr(self.tabview, "_segmented_button"):
            for name, btn in self.tabview._segmented_button._buttons_dict.items():
                if name == current_tab:
                    btn.configure(text_color=("#ffffff", "#e8edeb"))
                else:
                    btn.configure(text_color=("#121715", "#e8edeb"))

        # ── Floating Toggle Button ──────────────────────────────
        self.sidebar_toggle_btn = ctk.CTkButton(
            self.right,
            text="❮",
            width=28,
            height=64,
            corner_radius=8,
            bg_color="transparent",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            fg_color=("#384c46", "#4c5767"),
            hover_color=("#2a3a34", "#3a4854"),
            text_color=("#f6f8f8", "#e8edeb"),
            command=self._toggle_sidebar,
        )
        # Placed securely inside the right area, avoiding edge artifacts
        self.sidebar_toggle_btn.place(x=12, rely=0.5, anchor="w")

        # ── Pre-load example floor plan on canvas ───────────────
        self._preload_example_plan()

    # ── Callbacks ────────────────────────────────────────────────
    def _toggle_sidebar(self):
        """Instantly collapse / expand the Agent Library sidebar."""
        self.sidebar_visible = not self.sidebar_visible
        
        if self.sidebar_visible:
            self.current_sidebar_width = 260
            self.sidebar_frame.configure(width=260)
            self.sidebar_toggle_btn.configure(text="❮")
        else:
            self.current_sidebar_width = 0
            self.sidebar_frame.configure(width=0)
            self.sidebar_toggle_btn.configure(text="❯")

    def _on_agent_selected(self, agent_def):
        self.runner_tab.load_agent(agent_def)
        self.tabview.set("Agent Runner")
        self.status_bar.set_status(f"Loaded: {agent_def.name}", "#b3c7c1")

    def _on_create_new(self):
        self.tabview.set("Agent Builder")
        self.builder_tab.reset_form()
        self.status_bar.set_status("Creating new agent…", "#8889a5")

    def _on_agent_saved(self):
        """Called after the Agent Builder successfully saves a new agent."""
        self.agent_library.refresh()
        self.status_bar.set_agent_count(len(self.agent_library.agents))
        self.status_bar.set_status("Agent saved ✓", "#b3c7c1")

    def _on_save_and_run(self, agent_def):
        """Called after Save & Run — refresh library, then load the agent in the Runner."""
        self._on_agent_saved()
        self._on_agent_selected(agent_def)
        self.status_bar.set_status(f"Agent '{agent_def.name}' saved and loaded", "#b3c7c1")

    def _refresh_library(self):
        self.agent_library.refresh()
        self.status_bar.set_agent_count(len(self.agent_library.agents))
        self.status_bar.set_status("Library refreshed", "#b3c7c1")

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