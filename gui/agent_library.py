from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QLineEdit, QScrollArea, QWidget, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt
from typing import Callable, List

import config
from models.agent_definition import AgentDefinition


class AgentCard(QPushButton):
    def __init__(self, agent: AgentDefinition, on_click: Callable, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.setProperty("class", "AgentCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(38)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(0)

        name = QLabel(agent.name)
        name.setProperty("class", "AgentCardTitle")
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(name)

        self.clicked.connect(lambda: on_click(agent))


class AgentLibrary(QFrame):
    def __init__(self, parent=None, on_agent_selected: Callable = None, on_create_new: Callable = None):
        super().__init__(parent)
        self.setObjectName("AgentLibrary")

        self.on_agent_selected = on_agent_selected
        self.on_create_new = on_create_new
        self.agents: List[AgentDefinition] = []
        self._cards: List[AgentCard] = []

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 14, 12, 12)
        main_layout.setSpacing(10)

        title_label = QLabel("AGENT LIBRARY")
        title_label.setProperty("class", "SidebarTitle")
        main_layout.addWidget(title_label)

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search agents…")
        self.search_entry.setProperty("class", "SidebarSearch")
        self.search_entry.textChanged.connect(self._filter_agents)
        main_layout.addWidget(self.search_entry)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(2)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        self.create_btn = QPushButton("＋  Create New Agent")
        self.create_btn.setProperty("class", "CreateBtn")
        if self.on_create_new:
            self.create_btn.clicked.connect(self.on_create_new)
        main_layout.addWidget(self.create_btn)

    def refresh(self):
        self.agents = []
        self.agents.extend(AgentDefinition.load_all_from_directory(config.AGENTS_DIR))
        self.agents.extend(AgentDefinition.load_all_from_directory(config.USER_AGENTS_DIR))
        self._render_list(self.agents)

    def _render_list(self, agents: List[AgentDefinition]):
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._cards.clear()

        current_category = None

        for agent in agents:
            if agent.category != current_category:
                current_category = agent.category
                if current_category:
                    cat_label = QLabel(current_category.upper())
                    cat_label.setProperty("class", "CategoryLabel")
                    cat_label.setContentsMargins(2, 10, 0, 2)
                    self.scroll_layout.addWidget(cat_label)

            card = AgentCard(agent, self._on_card_click)
            self.scroll_layout.addWidget(card)
            self._cards.append(card)

    def _on_card_click(self, agent: AgentDefinition):
        if self.on_agent_selected:
            self.on_agent_selected(agent)

    def _filter_agents(self, text: str):
        query = text.lower()
        for card in self._cards:
            a = card.agent
            visible = query in a.name.lower() or query in a.goal.lower() or query in (a.category or "").lower()
            card.setVisible(visible)
