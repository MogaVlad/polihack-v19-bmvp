from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QLineEdit, QScrollArea, QWidget, QPushButton, QHBoxLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Callable, List

import config
from models.agent_definition import AgentDefinition

class AgentLibrary(QFrame):
    def __init__(self, parent=None, on_agent_selected: Callable = None, on_create_new: Callable = None):
        super().__init__(parent)
        self.setObjectName("AgentLibrary")
        
        self.on_agent_selected = on_agent_selected
        self.on_create_new = on_create_new
        self.agents: List[AgentDefinition] = []
        self._agent_buttons = []  # List of tuples (QPushButton, AgentDefinition)
        
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # Title
        title_label = QLabel("🗂  AGENT LIBRARY")
        title_label.setProperty("class", "Title")
        main_layout.addWidget(title_label)
        
        # Search
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search agents…")
        self.search_entry.textChanged.connect(self._filter_agents)
        main_layout.addWidget(self.search_entry)
        
        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(6)
        
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)
        
        # Create button
        self.create_btn = QPushButton("＋  Create New Agent")
        if self.on_create_new:
            self.create_btn.clicked.connect(self.on_create_new)
        main_layout.addWidget(self.create_btn)

    def refresh(self):
        self.agents = []
        self.agents.extend(AgentDefinition.load_all_from_directory(config.AGENTS_DIR))
        self.agents.extend(AgentDefinition.load_all_from_directory(config.USER_AGENTS_DIR))
        self._render_list(self.agents)

    def _render_list(self, agents: List[AgentDefinition]):
        # Clear existing
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self._agent_buttons.clear()
        
        current_category = None
        
        for agent in agents:
            # Category Header
            if agent.category != current_category:
                current_category = agent.category
                if current_category:
                    cat_label = QLabel(current_category.upper())
                    cat_label.setProperty("class", "Subtitle")
                    cat_label.setContentsMargins(0, 8, 0, 4)
                    self.scroll_layout.addWidget(cat_label)
            
            # Agent Button
            btn = QPushButton()
            btn.setProperty("class", "SidebarBtn")
            
            # Create a layout for the button to have title and subtitle
            btn_layout = QVBoxLayout(btn)
            btn_layout.setContentsMargins(12, 8, 12, 8)
            btn_layout.setSpacing(2)
            
            title = QLabel(agent.name)
            title.setStyleSheet("font-weight: bold; background: transparent; color: inherit;")
            title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            desc_text = (agent.goal[:40] + "…") if len(agent.goal) > 40 else agent.goal
            desc = QLabel(desc_text)
            desc.setStyleSheet("font-size: 11px; background: transparent; color: #b3c7c1;")
            desc.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            btn_layout.addWidget(title)
            btn_layout.addWidget(desc)
            
            # Click handler
            btn.clicked.connect(lambda checked, a=agent: self.on_agent_selected(a) if self.on_agent_selected else None)
            
            self.scroll_layout.addWidget(btn)
            self._agent_buttons.append((btn, agent))

    def _filter_agents(self, text: str):
        query = text.lower()
        for btn, agent in self._agent_buttons:
            if query in agent.name.lower() or query in agent.goal.lower() or query in (agent.category or "").lower():
                btn.show()
            else:
                btn.hide()