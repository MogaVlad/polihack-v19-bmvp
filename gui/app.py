import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, 
    QTabWidget, QPushButton, QStackedWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QKeySequence, QShortcut

import config
from gui.agent_library import AgentLibrary
from gui.agent_runner import AgentRunnerTab
from gui.agent_builder import AgentBuilderTab
from gui.l2_console import L2ConsoleTab
from gui.adoption_panel import AdoptionPanel
from gui.canvas import CanvasPanel
from gui.controls import StatusBar
from models.floor_plan import FloorPlan

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_TITLE)
        self.resize(1280, 820)
        self.setMinimumSize(960, 640)

        self._build_layout()

    def _build_layout(self):
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header bar ──────────────────────────────────────────
        self.header = QFrame()
        self.header.setProperty("class", "Header")
        self.header.setFixedHeight(48)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        
        logo_label = QLabel("⚡ AgentArchitect")
        logo_label.setProperty("class", "Title")
        header_layout.addWidget(logo_label)
        
        subtitle = QLabel("Engineering Agent Platform")
        subtitle.setProperty("class", "Subtitle")
        header_layout.addWidget(subtitle, 1)
        
        main_layout.addWidget(self.header)

        # ── Body ────────────────────────────────────────────────
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        main_layout.addWidget(body_widget, 1)

        # ── Sidebar ─────────────────────────────────────────────
        self.sidebar_visible = True
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setProperty("class", "Sidebar")
        self.sidebar_frame.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        body_layout.addWidget(self.sidebar_frame)

        # ── Right content area ──────────────────────────────────
        self.right_frame = QFrame()
        right_layout = QVBoxLayout(self.right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        body_layout.addWidget(self.right_frame, 1)

        # ── Tabview ─────────────────────────────────────────────
        self.tabview = QTabWidget()
        self.tabview.setDocumentMode(True)
        right_layout.addWidget(self.tabview, 1)

        # ── Canvas panel (below tabs - mock for now) ────────────
        self.canvas_panel = CanvasPanel(self.right_frame)
        self.canvas_panel.hide() # Initially hidden
        right_layout.addWidget(self.canvas_panel, 2)

        # ── Status bar ──────────────────────────────────────────
        self.status_bar = StatusBar()
        main_layout.addWidget(self.status_bar)

        # ── Tab contents ────────────────────────────────────────
        self.runner_tab = AgentRunnerTab(self.tabview, status_bar=self.status_bar, canvas_panel=self.canvas_panel)
        self.builder_tab = AgentBuilderTab(self.tabview, on_agent_saved=self._on_agent_saved, on_save_and_run=self._on_save_and_run)
        self.l2_tab = L2ConsoleTab(self.tabview)
        self.adoption_tab = AdoptionPanel(self.tabview)

        self.tabview.addTab(self.runner_tab, "Agent Runner")
        self.tabview.addTab(self.builder_tab, "Agent Builder")
        
        # ── Agent library sidebar ───────────────────────────────
        self.agent_library = AgentLibrary(
            self.sidebar_frame,
            on_agent_selected=self._on_agent_selected,
            on_create_new=self._on_create_new,
        )
        sidebar_layout.addWidget(self.agent_library, 1)

        self.status_bar.set_agent_count(len(self.agent_library.agents))
        
        from tools.registry import ToolRegistry
        self.status_bar.set_tool_count(len(ToolRegistry().list_tool_names()))

        # ── Sidebar navigation buttons ──────────────────────────
        nav_frame = QFrame()
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(16, 4, 16, 16)
        
        btn_legacy = QPushButton("📜 Legacy Prompting")
        btn_legacy.setProperty("class", "SidebarBtn")
        btn_legacy.clicked.connect(lambda: self._set_active_view("Legacy Prompting"))
        nav_layout.addWidget(btn_legacy)
        
        btn_showcase = QPushButton("📊 Legacy to Agent Showcase")
        btn_showcase.setProperty("class", "SidebarBtn")
        btn_showcase.clicked.connect(lambda: self._set_active_view("Legacy to Agent Showcase"))
        nav_layout.addWidget(btn_showcase)
        
        sidebar_layout.addWidget(nav_frame)

        # ── Keyboard shortcuts ──────────────────────────────────
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._on_create_new)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.builder_tab._save_agent)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self.runner_tab._run_agent)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.runner_tab._export_json)
        QShortcut(QKeySequence("F5"), self).activated.connect(self._refresh_library)

        # ── Pre-load example floor plan on canvas ───────────────
        self._preload_example_plan()

    def _set_active_view(self, view_name: str):
        # We will handle the manual setting of active view here
        # Since legacy and showcase are not strictly in QTabWidget, we can insert/remove them or just use QStackedWidget.
        # For simplicity, we can add them to QTabWidget but hide the tabs, or just use setCurrentIndex
        pass

    def _on_agent_selected(self, agent_def):
        self.runner_tab.load_agent(agent_def)
        self.tabview.setCurrentWidget(self.runner_tab)
        self.status_bar.set_status(f"Loaded: {agent_def.name}", "#b3c7c1")

    def _on_create_new(self):
        self.tabview.setCurrentWidget(self.builder_tab)
        self.builder_tab.reset_form()
        self.status_bar.set_status("Creating new agent…", "#8889a5")

    def _on_agent_saved(self):
        self.agent_library.refresh()
        self.status_bar.set_agent_count(len(self.agent_library.agents))
        self.status_bar.set_status("Agent saved ✓", "#b3c7c1")

    def _on_save_and_run(self, agent_def):
        self._on_agent_saved()
        self._on_agent_selected(agent_def)
        self.status_bar.set_status(f"Agent '{agent_def.name}' saved and loaded", "#b3c7c1")

    def _refresh_library(self):
        self.agent_library.refresh()
        self.status_bar.set_agent_count(len(self.agent_library.agents))
        self.status_bar.set_status("Library refreshed", "#b3c7c1")

    def _preload_example_plan(self):
        default = os.path.join(config.FLOOR_PLANS_DIR, "example_office.json")
        if os.path.isfile(default):
            try:
                plan = FloorPlan.load_from_json(default)
                self.canvas_panel.load_plan(plan)
            except Exception:
                pass