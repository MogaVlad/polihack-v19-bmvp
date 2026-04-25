import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QStackedWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon, QPixmap

import config
from gui.agent_library import AgentLibrary
from gui.agent_runner import AgentRunnerTab
from gui.agent_builder import AgentBuilderTab
from gui.l2_console import L2ConsoleTab
from gui.adoption_panel import AdoptionPanel
from gui.canvas import CanvasPanel
from gui.controls import StatusBar
from models.floor_plan import FloorPlan

SIDEBAR_WIDTH = 280
SIDEBAR_COLLAPSED = 0


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_TITLE)
        self.resize(1280, 820)
        self.setMinimumSize(960, 640)

        self._build_layout()

    def _build_layout(self):
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
        header_layout.setContentsMargins(12, 0, 16, 0)

        self.sidebar_toggle_btn = QPushButton("☰")
        self.sidebar_toggle_btn.setFixedSize(36, 36)
        self.sidebar_toggle_btn.setProperty("class", "HeaderBtn")
        self.sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)
        header_layout.addWidget(self.sidebar_toggle_btn)

        # icons live in gui/assets/icons/ (same folder as this file)
        _here = os.path.dirname(os.path.abspath(__file__))
        _icons = os.path.join(_here, "assets", "icons")

        def _px(name, size=20):
            lbl = QLabel()
            p = os.path.join(_icons, name)
            if os.path.isfile(p):
                lbl.setPixmap(QPixmap(p).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            return lbl

        def _ico(name):
            return QIcon(os.path.join(_icons, name))

        # window icon
        self.setWindowIcon(_ico("appicon.png"))

        header_layout.addWidget(_px("nexttotitle.png", 24))

        logo_label = QLabel("AgentArchitect")
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
        self.sidebar_expanded = True
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setProperty("class", "Sidebar")
        self.sidebar_frame.setMinimumWidth(SIDEBAR_WIDTH)
        self.sidebar_frame.setMaximumWidth(SIDEBAR_WIDTH)
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

        # ── Stacked pages (no tab bar) ─────────────────────────
        self.pages = QStackedWidget()
        right_layout.addWidget(self.pages, 1)

        # ── Canvas panel ────────────────────────────────────────
        self.canvas_panel = CanvasPanel(self.right_frame)
        self.canvas_panel.hide()
        right_layout.addWidget(self.canvas_panel, 2)

        # ── Status bar ──────────────────────────────────────────
        self.status_bar = StatusBar()
        main_layout.addWidget(self.status_bar)

        # ── Page contents ───────────────────────────────────────
        self.runner_tab = AgentRunnerTab(self.pages, status_bar=self.status_bar, canvas_panel=self.canvas_panel)
        self.builder_tab = AgentBuilderTab(self.pages, on_agent_saved=self._on_agent_saved, on_save_and_run=self._on_save_and_run)
        self.l2_tab = L2ConsoleTab(self.pages)
        self.adoption_tab = AdoptionPanel(self.pages)

        self.pages.addWidget(self.runner_tab)
        self.pages.addWidget(self.builder_tab)
        self.pages.addWidget(self.l2_tab)
        self.pages.addWidget(self.adoption_tab)

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
        nav_layout.setContentsMargins(12, 4, 12, 12)
        nav_layout.setSpacing(6)

        btn_legacy = QPushButton("  Legacy Prompting")
        btn_legacy.setProperty("class", "SidebarBtn")
        btn_legacy.setIcon(_ico("legacy.png"))
        btn_legacy.setIconSize(QSize(18, 18))
        btn_legacy.clicked.connect(lambda: self._set_active_view("Legacy Prompting"))
        nav_layout.addWidget(btn_legacy)

        btn_showcase = QPushButton("  Legacy → Agent")
        btn_showcase.setProperty("class", "SidebarBtn")
        btn_showcase.setIcon(_ico("l2tol3.png"))
        btn_showcase.setIconSize(QSize(18, 18))
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
        QShortcut(QKeySequence("Ctrl+B"), self).activated.connect(self._toggle_sidebar)

        self._preload_example_plan()

    # ── Sidebar collapse ────────────────────────────────────────
    def _toggle_sidebar(self):
        if self.sidebar_expanded:
            start, end = SIDEBAR_WIDTH, SIDEBAR_COLLAPSED
        else:
            start, end = SIDEBAR_COLLAPSED, SIDEBAR_WIDTH

        # Animate maximumWidth for the slide effect
        self._anim = QPropertyAnimation(self.sidebar_frame, b"maximumWidth")
        self._anim.setDuration(200)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # When expanding we must unlock minimumWidth first so it can grow;
        # when collapsing we animate minimumWidth down together.
        if self.sidebar_expanded:
            # collapsing: shrink min alongside max
            self.sidebar_frame.setMinimumWidth(0)
        else:
            # expanding: set min to 0 now so the frame can start at 0,
            # then snap it to SIDEBAR_WIDTH once fully open
            self.sidebar_frame.setMinimumWidth(0)

        def _on_finished():
            # Snap both constraints to the final value so layout can't drift
            self.sidebar_frame.setMinimumWidth(end)
            self.sidebar_frame.setMaximumWidth(end)

        self._anim.finished.connect(_on_finished)
        self._anim.start()
        self.sidebar_expanded = not self.sidebar_expanded

    # ── Navigation ──────────────────────────────────────────────
    def _set_active_view(self, view_name: str):
        tab_map = {
            "Legacy Prompting": self.l2_tab,
            "Legacy to Agent Showcase": self.adoption_tab,
        }
        widget = tab_map.get(view_name)
        if widget:
            self.pages.setCurrentWidget(widget)

    def _on_agent_selected(self, agent_def):
        self.runner_tab.load_agent(agent_def)
        self.pages.setCurrentWidget(self.runner_tab)
        self.status_bar.set_status(f"Loaded: {agent_def.name}", "#b3c7c1")

    def _on_create_new(self):
        self.pages.setCurrentWidget(self.builder_tab)
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