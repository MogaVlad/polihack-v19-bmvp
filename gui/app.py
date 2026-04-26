import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QStackedWidget, QApplication
)
from PyQt6.QtCore import QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, Qt, QSize
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon, QPixmap

import config
from gui.agent_library import AgentLibrary
from gui.agent_runner import AgentRunnerTab
from gui.agent_builder import AgentBuilderTab
from gui.l2_console import L2ConsoleTab
from gui.adoption_panel import AdoptionPanel
from gui.canvas import CanvasPanel
from gui.controls import StatusBar
from gui.splash import SplashOverlay
from models.floor_plan import FloorPlan

SIDEBAR_WIDTH = 280
SIDEBAR_COLLAPSED = 0


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_TITLE)
        self.resize(1280, 820)
        self.setMinimumSize(960, 640)

        self._dark_mode = True
        self._icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")

        self._build_layout()

    def _build_layout(self):
        self.central_widget = QWidget()
        self.central_widget.setObjectName("AppRoot")
        self.setCentralWidget(self.central_widget)

        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
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

        self._title_icon_lbl = QLabel()
        self._title_icon_lbl.setFixedSize(26, 26)
        header_layout.addWidget(self._title_icon_lbl)

        self.logo_label = QLabel("AgentArchitect")
        self.logo_label.setProperty("class", "Title")
        header_layout.addWidget(self.logo_label)

        subtitle = QLabel("Engineering Agent Platform")
        subtitle.setProperty("class", "Subtitle")
        header_layout.addWidget(subtitle, 1)

        main_layout.addWidget(self.header)

        # Body
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        main_layout.addWidget(body_widget, 1)

        # Sidebar
        self.sidebar_expanded = True
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setProperty("class", "Sidebar")
        self.sidebar_frame.setMinimumWidth(SIDEBAR_WIDTH)
        self.sidebar_frame.setMaximumWidth(SIDEBAR_WIDTH)
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        body_layout.addWidget(self.sidebar_frame)

        # Right content area
        self.right_frame = QFrame()
        self.right_frame.setObjectName("ContentRoot")
        right_layout = QVBoxLayout(self.right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        body_layout.addWidget(self.right_frame, 1)

        # Stacked pages
        self.pages = QStackedWidget()
        self.pages.setObjectName("ContentPages")
        right_layout.addWidget(self.pages, 1)

        # Canvas panel
        self.canvas_panel = CanvasPanel(self.right_frame)
        right_layout.addWidget(self.canvas_panel, 2)

        # Status bar with theme toggle callback
        self.status_bar = StatusBar(on_theme_change=self.apply_theme)
        main_layout.addWidget(self.status_bar)

        # Page contents
        self.runner_tab = AgentRunnerTab(
            self.pages, 
            status_bar=self.status_bar, 
            canvas_panel=self.canvas_panel,
            on_agent_deleted=self._on_agent_deleted
        )
        self.builder_tab = AgentBuilderTab(
            self.pages,
            on_agent_saved=self._on_agent_saved,
            on_save_and_run=self._on_save_and_run
        )
        self.l2_tab = L2ConsoleTab(self.pages)
        self.adoption_tab = AdoptionPanel(self.pages)

        self.pages.addWidget(self.runner_tab)
        self.pages.addWidget(self.builder_tab)
        self.pages.addWidget(self.l2_tab)
        self.pages.addWidget(self.adoption_tab)
        self.pages.currentChanged.connect(self._on_page_changed)
        self._on_page_changed(self.pages.currentIndex())

        # Agent library sidebar
        self.agent_library = AgentLibrary(
            self.sidebar_frame,
            on_agent_selected=self._on_agent_selected,
            on_create_new=self._on_create_new,
        )
        sidebar_layout.addWidget(self.agent_library, 1)

        self.status_bar.set_agent_count(len(self.agent_library.agents))

        from tools.registry import ToolRegistry
        self.status_bar.set_tool_count(len(ToolRegistry().list_tool_names()))

        # Sidebar navigation buttons
        nav_frame = QFrame()
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(12, 4, 12, 12)
        nav_layout.setSpacing(6)

        self._btn_legacy = QPushButton("  Legacy Prompting")
        self._btn_legacy.setProperty("class", "SidebarBtn")
        self._btn_legacy.setIconSize(QSize(18, 18))
        self._btn_legacy.clicked.connect(lambda: self._set_active_view("Legacy Prompting"))
        nav_layout.addWidget(self._btn_legacy)

        self._btn_showcase = QPushButton("  Legacy -> Agent")
        self._btn_showcase.setProperty("class", "SidebarBtn")
        self._btn_showcase.setIconSize(QSize(18, 18))
        self._btn_showcase.clicked.connect(lambda: self._set_active_view("Legacy to Agent Showcase"))
        nav_layout.addWidget(self._btn_showcase)

        sidebar_layout.addWidget(nav_frame)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._on_create_new)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.builder_tab._save_agent)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self.runner_tab._run_agent)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.runner_tab._export_json)
        QShortcut(QKeySequence("F5"), self).activated.connect(self._refresh_library)
        QShortcut(QKeySequence("Ctrl+B"), self).activated.connect(self._toggle_sidebar)

        self._apply_icons()
        self._preload_example_plan()
        
        # Create and show Splash Screen on top
        self.splash = SplashOverlay(self.central_widget, self.logo_label)
        self.splash.finished.connect(self._on_splash_finished)
        self.splash.destroyed.connect(self._on_splash_destroyed)
        self.splash.show()
    # Icon helpers
    def _icon_path(self, name: str) -> str:
        suffix = "dark" if self._dark_mode else "light"
        return os.path.join(self._icons_dir, f"{name}_{suffix}.png")

    def _make_icon(self, name: str) -> QIcon:
        return QIcon(self._icon_path(name))

    def _make_pixmap(self, name: str, size: int) -> QPixmap:
        path = self._icon_path(name)
        if os.path.isfile(path):
            return QPixmap(path).scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return QPixmap()

    def _apply_icons(self):
        app_icon = os.path.join(self._icons_dir, "appicon_light.png")
        if os.path.isfile(app_icon):
            self.setWindowIcon(QIcon(app_icon))
        self._title_icon_lbl.setPixmap(self._make_pixmap("nexttotitle", 24))
        self._btn_legacy.setIcon(self._make_icon("legacy"))
        self._btn_showcase.setIcon(self._make_icon("l2tol3"))

    def apply_theme(self, dark_mode: bool):
        from gui.theme import get_stylesheet

        self._dark_mode = dark_mode
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(dark_mode=dark_mode))
        if self.canvas_panel:
            self.canvas_panel.apply_theme(dark_mode)
        self._apply_icons()

    def _toggle_sidebar(self):
        if hasattr(self, "_sidebar_anim") and self._sidebar_anim:
            self._sidebar_anim.stop()

        start = self.sidebar_frame.width()
        target_expanded = not self.sidebar_expanded
        end = SIDEBAR_WIDTH if target_expanded else SIDEBAR_COLLAPSED

        self._sidebar_anim = QParallelAnimationGroup(self)
        for prop in (b"minimumWidth", b"maximumWidth"):
            anim = QPropertyAnimation(self.sidebar_frame, prop)
            anim.setDuration(200)
            anim.setStartValue(start)
            anim.setEndValue(end)
            anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._sidebar_anim.addAnimation(anim)

        def _on_finished():
            self.sidebar_frame.setMinimumWidth(end)
            self.sidebar_frame.setMaximumWidth(end)

        self._sidebar_anim.finished.connect(_on_finished)
        self._sidebar_anim.start()
        self.sidebar_expanded = target_expanded

    def _set_active_view(self, view_name: str):
        tab_map = {
            "Legacy Prompting": self.l2_tab,
            "Legacy to Agent Showcase": self.adoption_tab,
        }
        widget = tab_map.get(view_name)
        if widget:
            self.pages.setCurrentWidget(widget)

    def _on_page_changed(self, index: int):
        current = self.pages.widget(index)
        if current is self.runner_tab:
            self.canvas_panel.show()
        else:
            self.canvas_panel.hide()

    def _on_agent_selected(self, agent_def):
        self.runner_tab.load_agent(agent_def)
        self.pages.setCurrentWidget(self.runner_tab)
        self.status_bar.set_status(f"Loaded: {agent_def.name}", "#b3c7c1")

    def _on_create_new(self):
        self.pages.setCurrentWidget(self.builder_tab)
        self.builder_tab.reset_form()
        self.status_bar.set_status("Creating new agent...", "#8889a5")

    def _on_agent_saved(self):
        self.agent_library.refresh()
        self.status_bar.set_agent_count(len(self.agent_library.agents))
        self.status_bar.set_status("Agent saved", "#b3c7c1")

    def _on_save_and_run(self, agent_def):
        self._on_agent_saved()
        self._on_agent_selected(agent_def)
        self.status_bar.set_status(f"Agent '{agent_def.name}' saved and loaded", "#b3c7c1")
        
    def _on_agent_deleted(self):
        self.agent_library.refresh()
        self.status_bar.set_agent_count(len(self.agent_library.agents))
        self.pages.setCurrentWidget(self.l2_tab) # Switch to a neutral tab or empty view
        self.status_bar.set_status("Agent deleted", "#b3c7c1")

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

    def _on_splash_finished(self):
        self._clear_splash()

    def _on_splash_destroyed(self, _=None):
        self._clear_splash()

    def _clear_splash(self):
        self.splash = None
                
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'splash') and self.splash:
            self.splash.resize(self.central_widget.size())
