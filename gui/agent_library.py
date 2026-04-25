from typing import Callable, List, Dict
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QWidget, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt

import config
from models.agent_definition import AgentDefinition


def _elide(text: str, max_len: int = 60) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


class AgentCard(QPushButton):
    def __init__(self, agent: AgentDefinition, on_click: Callable, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.setProperty("class", "AgentCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(56)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(2)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        name = QLabel(agent.name)
        name.setProperty("class", "AgentCardTitle")
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        top_row.addWidget(name, 1)

        status = QLabel("●")
        if agent.category and agent.category.lower() == "custom":
            status.setProperty("class", "StatusDotCustom")
            status.setToolTip("Custom agent")
        elif agent.category:
            status.setProperty("class", "StatusDotBuiltIn")
            status.setToolTip("Built-in agent")
        else:
            status.setProperty("class", "StatusDotUnknown")
            status.setToolTip("Uncategorized agent")
        status.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        top_row.addWidget(status, 0, Qt.AlignmentFlag.AlignRight)

        layout.addLayout(top_row)

        subtitle = QLabel(_elide(agent.goal, 72))
        subtitle.setProperty("class", "AgentCardSubtitle")
        subtitle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(subtitle)

        self.clicked.connect(lambda: on_click(agent))


class AgentLibrary(QFrame):
    def __init__(self, parent=None, on_agent_selected: Callable = None, on_create_new: Callable = None):
        super().__init__(parent)
        self.setObjectName("AgentLibrary")

        self.on_agent_selected = on_agent_selected
        self.on_create_new = on_create_new
        self.agents: List[AgentDefinition] = []
        self._cards: List[AgentCard] = []
        self._category_headers: Dict[str, QLabel] = {}

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
        self.scroll_layout.setSpacing(4)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        self.create_btn = QPushButton("+  Create New Agent")
        self.create_btn.setProperty("class", "CreateBtn")
        if self.on_create_new:
            self.create_btn.clicked.connect(self.on_create_new)
        main_layout.addWidget(self.create_btn)

    def refresh(self):
        self.agents = []
        self.agents.extend(AgentDefinition.load_all_from_directory(config.AGENTS_DIR))
        self.agents.extend(AgentDefinition.load_all_from_directory(config.USER_AGENTS_DIR))
        self._render_list(self.agents)

    def _category_sort_key(self, category: str):
        c = (category or "").strip()
        if c.lower() == "fire safety":
            return (0, c.lower())
        if c.lower() == "custom":
            return (1, c.lower())
        return (2, c.lower())

    def _render_list(self, agents: List[AgentDefinition]):
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._cards.clear()
        self._category_headers.clear()

        grouped: Dict[str, List[AgentDefinition]] = {}
        for agent in agents:
            category = (agent.category or "Uncategorized").strip() or "Uncategorized"
            grouped.setdefault(category, []).append(agent)

        for category in sorted(grouped.keys(), key=self._category_sort_key):
            cat_label = QLabel(category.upper())
            cat_label.setProperty("class", "CategoryLabel")
            cat_label.setContentsMargins(2, 8, 0, 2)
            self.scroll_layout.addWidget(cat_label)
            self._category_headers[category] = cat_label

            for agent in grouped[category]:
                card = AgentCard(agent, self._on_card_click)
                self.scroll_layout.addWidget(card)
                self._cards.append(card)

    def _on_card_click(self, agent: AgentDefinition):
        if self.on_agent_selected:
            self.on_agent_selected(agent)

    def _filter_agents(self, text: str):
        query = text.lower().strip()
        visible_per_category: Dict[str, int] = {}

        for card in self._cards:
            a = card.agent
            category = (a.category or "Uncategorized").strip() or "Uncategorized"
            visible = (
                not query
                or query in a.name.lower()
                or query in a.goal.lower()
                or query in category.lower()
            )
            card.setVisible(visible)
            if visible:
                visible_per_category[category] = visible_per_category.get(category, 0) + 1

        for category, header in self._category_headers.items():
            header.setVisible(visible_per_category.get(category, 0) > 0 or not query)
